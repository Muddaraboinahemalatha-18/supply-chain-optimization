import csv
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

TRANSACTION_DIR = (
    BASE_DIR / "data" / "generated" / "transactions"
)

LEAD_TIME_FILE = TRANSACTION_DIR / "lead_time.csv"
OPTIONS_FILE = TRANSACTION_DIR / "mitigation_options.csv"

SNAPSHOT_DATE = date(2026, 1, 1)


def read_csv(path):
    with open(path, "r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def parse_date(value):
    if not value:
        return None

    return datetime.strptime(value, "%Y-%m-%d").date()


def to_int(value, default=-1):
    if value is None or str(value).strip() == "":
        return default

    return int(float(value))


def main():

    lead_times = read_csv(LEAD_TIME_FILE)
    options = read_csv(OPTIONS_FILE)

    lead_time_by_id = {
        row["lead_time_id"]: row
        for row in lead_times
    }

    supplier_options = [
        row for row in options
        if row["option_type"] == "SUPPLIER_PURCHASE"
    ]

    failure_counts = Counter()
    failure_samples = defaultdict(list)

    for option in supplier_options:

        problems = []

        planned_date = parse_date(
            option["planned_order_date"]
        )

        arrival_date = parse_date(
            option["expected_arrival_date"]
        )

        required_date = parse_date(
            option["required_arrival_date"]
        )

        lead_days = to_int(
            option["lead_time_days"]
        )

        lead_row = lead_time_by_id.get(
            option["lead_time_id"]
        )

        if planned_date is None:
            problems.append("MISSING_PLANNED_ORDER_DATE")

        if arrival_date is None:
            problems.append("MISSING_EXPECTED_ARRIVAL_DATE")

        if required_date is None:
            problems.append("MISSING_REQUIRED_ARRIVAL_DATE")

        if lead_days < 0:
            problems.append("MISSING_OR_INVALID_LEAD_DAYS")

        if lead_row is None:
            problems.append("LEAD_TIME_ID_NOT_FOUND")

        if planned_date is not None:

            if (
                option["rule_check_status"] == "PASS"
                and planned_date < SNAPSHOT_DATE
            ):
                problems.append(
                    "FEASIBLE_OPTION_ORDER_DATE_BEFORE_SNAPSHOT"
                )

            if (
                option["capacity_week"]
                != f"{planned_date.isocalendar().year}-W"
                f"{planned_date.isocalendar().week:02d}"
            ):
                problems.append("CAPACITY_WEEK_MISMATCH")

        if (
            planned_date is not None
            and arrival_date is not None
            and lead_days >= 0
        ):
            calculated_arrival = (
                planned_date + timedelta(days=lead_days)
            )

            if calculated_arrival != arrival_date:
                problems.append("ARRIVAL_DATE_ARITHMETIC_MISMATCH")

        if (
            arrival_date is not None
            and required_date is not None
            and arrival_date > required_date
        ):
            problems.append("ARRIVAL_AFTER_REQUIRED_DATE")

        if lead_row is not None:

            if (
                lead_row["supplier_id"] != option["supplier_id"]
            ):
                problems.append("SUPPLIER_ID_MISMATCH")

            if (
                lead_row["location_id"] != option["location_id"]
            ):
                problems.append("LOCATION_ID_MISMATCH")

            effective_from = parse_date(
                lead_row["effective_from"]
            )

            effective_to = parse_date(
                lead_row["effective_to"]
            )

            if planned_date is not None:

                check_date = max(
                    planned_date,
                    SNAPSHOT_DATE
                )

                if (
                    effective_from is None
                    or check_date < effective_from
                    or (
                        effective_to is not None
                        and check_date > effective_to
                    )
                ):
                    problems.append(
                        "LEAD_TIME_NOT_EFFECTIVE_ON_ORDER_DATE"
                    )

        for problem in problems:

            failure_counts[problem] += 1

            if len(failure_samples[problem]) < 5:
                failure_samples[problem].append({
                    "option_id": option["option_id"],
                    "shortage_id": option["shortage_id"],
                    "supplier_id": option["supplier_id"],
                    "location_id": option["location_id"],
                    "lead_time_id": option["lead_time_id"],
                    "planned_order_date": option["planned_order_date"],
                    "lead_time_days": option["lead_time_days"],
                    "expected_arrival_date": option["expected_arrival_date"],
                    "required_arrival_date": option["required_arrival_date"],
                    "capacity_week": option["capacity_week"],
                    "rule_check_status": option["rule_check_status"],
                    "feasibility_status": option["feasibility_status"],
                })

    print("=" * 76)
    print("MITIGATION LEAD-TIME DIAGNOSTIC")
    print("=" * 76)

    print("\nRECORD COUNTS")
    print("Supplier options:", len(supplier_options))
    print("Lead-time source records:", len(lead_times))
    print("Lead-time IDs available:", len(lead_time_by_id))

    print("\nFAILURE REASON COUNTS")

    if not failure_counts:
        print("No lead-time or planned-order-date inconsistencies found.")

    for reason, count in sorted(failure_counts.items()):
        print(f"{reason}: {count}")

    print("\nSAMPLE FAILED RECORDS")

    for reason, samples in sorted(failure_samples.items()):

        print("\n" + "-" * 76)
        print(reason)
        print("-" * 76)

        for sample in samples:
            print(sample)

    print("\n" + "=" * 76)
    print("DIAGNOSTIC COMPLETED")
    print("Source CSV files modified: NONE")
    print("Database changes: NONE")
    print("=" * 76)


if __name__ == "__main__":
    main()