import argparse
import csv

from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


# ============================================================
# PATHS AND TOLERANCE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

MASTER_DIR = None
TRANSACTION_DIR = None

SNAPSHOT_DATE = date(2026, 1, 1)
TOLERANCE = 0.000001


# ============================================================
# HELPERS
# ============================================================

def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with open(path, "r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def number(value, default=0.0):
    if value is None or str(value).strip() == "":
        return default
    return float(value)


def integer(value, default=0):
    if value is None or str(value).strip() == "":
        return default
    return int(float(value))


def truth(value):
    return str(value).strip().upper() in {
        "1", "TRUE", "YES", "Y", "APPROVED"
    }


def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def close(a, b):
    return abs(float(a) - float(b)) <= TOLERANCE


def effective_on(record, check_date):
    start = parse_date(record.get("effective_from"))
    end = parse_date(record.get("effective_to"))

    if start is None or check_date < start:
        return False

    if end is not None and check_date > end:
        return False

    return True


def report(name, passed, detail=""):
    status = "PASSED" if passed else "FAILED"
    suffix = f" | {detail}" if detail else ""
    print(f"{name}: {status}{suffix}")
    return passed


def week_start(week_value):
    year_text, week_text = week_value.split("-W")
    return date.fromisocalendar(
        int(year_text),
        int(week_text),
        1
    )


def iso_week(check_date):
    iso = check_date.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


# ============================================================
# LOAD INPUTS AND GENERATED OUTPUTS
# ============================================================

def load_data():

    policy_path = MASTER_DIR / "supplier_sku_policy.csv"
    if not policy_path.exists():
        policy_path = TRANSACTION_DIR / "supplier_sku_policy.csv"

    substitute_path = MASTER_DIR / "sku_substitute.csv"
    if not substitute_path.exists():
        substitute_path = TRANSACTION_DIR / "sku_substitute.csv"

    return {
        "skus": read_csv(MASTER_DIR / "sku.csv"),
        "supplier_sku": read_csv(MASTER_DIR / "supplier_sku.csv"),
        "policies": read_csv(policy_path),
        "substitutes": read_csv(substitute_path),

        "capacities": read_csv(TRANSACTION_DIR / "supplier_capacity.csv"),
        "lead_times": read_csv(TRANSACTION_DIR / "lead_time.csv"),
        "purchase_orders": read_csv(TRANSACTION_DIR / "purchase_order.csv"),
        "purchase_order_lines": read_csv(TRANSACTION_DIR / "purchase_order_line.csv"),
        "shortages": read_csv(TRANSACTION_DIR / "projected_shortages.csv"),
        "projections": read_csv(TRANSACTION_DIR / "weekly_inventory_projection.csv"),
        "options": read_csv(TRANSACTION_DIR / "mitigation_options.csv"),
        "summary": read_csv(TRANSACTION_DIR / "mitigation_summary.csv"),
    }

# ============================================================
# BUILD SOURCE INDEXES
# ============================================================

def build_indexes(data):

    indexes = {}

    indexes["sku"] = {
        row["sku_id"]: row
        for row in data["skus"]
    }

    indexes["supplier_relationship"] = {
        (row["supplier_id"], row["sku_id"]): row
        for row in data["supplier_sku"]
    }

    indexes["policy"] = {
        row["policy_id"]: row
        for row in data["policies"]
    }

    indexes["capacity"] = {
        (
            row["supplier_id"],
            row["sku_id"],
            row["capacity_week"]
        ): row
        for row in data["capacities"]
    }

    indexes["lead_time"] = {
        row["lead_time_id"]: row
        for row in data["lead_times"]
    }

    indexes["substitute"] = {
        row["substitute_id"]: row
        for row in data["substitutes"]
    }

    indexes["shortage"] = {
        row["shortage_id"]: row
        for row in data["shortages"]
    }

    indexes["projection"] = {
        (
            row["sku_id"],
            row["location_id"],
            row["forecast_week"]
        ): row
        for row in data["projections"]
    }

    indexes["sku_substitutes"] = defaultdict(list)

    for row in data["substitutes"]:
        indexes["sku_substitutes"][
            row["original_sku_id"]
        ].append(row)

    return indexes


# ============================================================
# RECONSTRUCT EXISTING PO CAPACITY USAGE
# ============================================================

def calculate_existing_po_usage(data):

    po_by_id = {
        row["po_id"]: row
        for row in data["purchase_orders"]
    }

    usage = defaultdict(float)
    joined_count = 0

    for line in data["purchase_order_lines"]:

        po = po_by_id.get(line["po_id"])

        if po is None:
            continue

        order_date = parse_date(po["order_date"])

        if order_date is None:
            continue

        key = (
            po["supplier_id"],
            line["sku_id"],
            iso_week(order_date)
        )

        usage[key] += number(line["order_quantity"])
        joined_count += 1

    return usage, joined_count


# ============================================================
# VERIFY OPTION RECORDS
# ============================================================

def verify_options(data, indexes, existing_usage):

    options = data["options"]

    option_ids = [row["option_id"] for row in options]

    unique_ids = (
        len(option_ids) == len(set(option_ids))
    )

    option_by_id = {
        row["option_id"]: row
        for row in options
    }

    shortage_ids = set(indexes["shortage"])

    all_shortage_references_valid = all(
        row["shortage_id"] in shortage_ids
        for row in options
    )

    all_blocked_have_reason = all(
        bool(row["decision_reason"].strip())
        for row in options
        if row["feasibility_status"] == "BLOCKED"
    )

    supplier_math_check = True
    supplier_policy_check = True
    supplier_approval_check = True
    supplier_lead_check = True
    supplier_capacity_source_check = True

    substitute_math_check = True
    substitute_approval_check = True
    substitute_stock_source_check = True

    for option in options:

        option_type = option["option_type"]

        shortage = indexes["shortage"].get(
            option["shortage_id"]
        )

        if shortage is None:
            continue

        shortage_quantity = number(
            option["shortage_quantity"]
        )

        proposed_quantity = number(
            option["proposed_quantity"]
        )

        equivalent_quantity = number(
            option["equivalent_original_quantity"]
        )

        uncovered_quantity = number(
            option["uncovered_shortage_quantity"]
        )

        estimated_cost = number(
            option["estimated_cost"]
        )

        if option_type == "SUPPLIER_PURCHASE":

            supplier_id = option["supplier_id"]
            sku_id = option["sku_id"]

            relationship = indexes[
                "supplier_relationship"
            ].get((supplier_id, sku_id))

            if relationship is None or not truth(
                relationship.get("is_approved")
            ):
                supplier_approval_check = False

            policy = indexes["policy"].get(
                option["policy_id"]
            )

            if policy is None:
                supplier_policy_check = False
            else:
                if (
                    policy["supplier_id"] != supplier_id
                    or policy["sku_id"] != sku_id
                ):
                    supplier_policy_check = False

                planned_date = parse_date(
                    option["planned_order_date"]
                )

                if planned_date is not None:
                    policy_check_date = max(
                        planned_date,
                        SNAPSHOT_DATE
                    )

                    if not effective_on(
                        policy,
                        policy_check_date
                    ):
                        supplier_policy_check = False

                moq = number(
                    option["minimum_order_quantity"]
                )

                unit_cost = number(
                    option["unit_cost"]
                )

                if proposed_quantity > 0:

                    if moq <= 0:
                        supplier_math_check = False
                    else:
                        multiple = proposed_quantity / moq

                        if not close(
                            multiple,
                            round(multiple)
                        ):
                            supplier_math_check = False

                if not close(
                    estimated_cost,
                    proposed_quantity * unit_cost
                ):
                    supplier_math_check = False

            if not close(
                equivalent_quantity,
                proposed_quantity
            ):
                supplier_math_check = False

            expected_uncovered = max(
                0.0,
                shortage_quantity - proposed_quantity
            )

            if not close(
                uncovered_quantity,
                expected_uncovered
            ):
                supplier_math_check = False

            # Check the planned order date and arrival date.
            planned_date = parse_date(
                option["planned_order_date"]
            )

            arrival_date = parse_date(
                option["expected_arrival_date"]
            )

            required_date = parse_date(
                option["required_arrival_date"]
            )

            lead_days = integer(
                option["lead_time_days"],
                -1
            )

            lead_row = indexes["lead_time"].get(
                option["lead_time_id"]
            )

            if (
                planned_date is None
                or arrival_date is None
                or required_date is None
                or lead_days < 0
                or lead_row is None
            ):
                supplier_lead_check = False

            else:
                if (
                   (
                        option["rule_check_status"] == "PASS"
                        and planned_date < SNAPSHOT_DATE
                    )
                    or planned_date + timedelta(days=lead_days)
                    != arrival_date
                    or arrival_date > required_date
                    or lead_row["supplier_id"] != supplier_id
                    or lead_row["location_id"] != option["location_id"]
                   ):
                        supplier_lead_check = False

            # Verify that capacity is for the planned order week.
            if planned_date is not None:

                planned_week = iso_week(planned_date)

                if option["capacity_week"] != planned_week:
                    supplier_lead_check = False

                capacity_key = (
                    supplier_id,
                    sku_id,
                    planned_week
                )

                capacity_row = indexes["capacity"].get(
                    capacity_key
                )

                if capacity_row is None:
                    if option["rule_check_status"] == "PASS":
                        supplier_capacity_source_check = False
                else:
                    if (
                        option["capacity_id"]
                        != capacity_row["capacity_id"]
                    ):
                        supplier_capacity_source_check = False

            if option["capacity_source"] != "SYNTHETIC":
                supplier_capacity_source_check = False

        elif option_type == "APPROVED_SUBSTITUTE":

            substitute = indexes["substitute"].get(
                option["substitute_id"]
            )

            if substitute is None:
                substitute_approval_check = False
            else:
                if (
                    substitute["original_sku_id"] != option["sku_id"]
                    or substitute["substitute_sku_id"]
                    != option["substitute_sku_id"]
                    or not truth(substitute["is_approved"])
                ):
                    substitute_approval_check = False

                required_date = parse_date(
                    option["required_arrival_date"]
                )

                if (
                    option["feasibility_status"] != "BLOCKED"
                    and (
                        required_date is None
                        or not effective_on(substitute, required_date)
                    )
                ):
                    substitute_approval_check = False

                conversion = number(
                    substitute["conversion_factor"]
                )

                if conversion <= 0:
                    substitute_math_check = False
                else:
                    expected_equivalent = (
                        proposed_quantity / conversion
                    )

                    if not close(
                        equivalent_quantity,
                        expected_equivalent
                    ):
                        substitute_math_check = False

            original_sku = indexes["sku"].get(
                option["sku_id"]
            )

            substitute_sku = indexes["sku"].get(
                option["substitute_sku_id"]
            )

            if (
                original_sku is None
                or substitute_sku is None
                or original_sku["unit_of_measure"]
                != substitute_sku["unit_of_measure"]
                or original_sku["unit_of_measure"]
                != option["unit_of_measure"]
            ):
                substitute_math_check = False

            expected_uncovered = max(
                0.0,
                shortage_quantity - equivalent_quantity
            )

            if not close(
                uncovered_quantity,
                expected_uncovered
            ):
                substitute_math_check = False

            if substitute_sku is not None:
                substitute_cost = number(
                    substitute_sku["unit_cost"]
                )

                if not close(
                    estimated_cost,
                    proposed_quantity * substitute_cost
                ):
                    substitute_math_check = False

            if (
                option["capacity_source"]
                != "EXISTING_PROJECTED_STOCK"
            ):
                substitute_stock_source_check = False

        else:
            supplier_math_check = False

    # --------------------------------------------------------
    # Verify primary supplier allocations against capacity.
    # --------------------------------------------------------

    primary_rows = [
        row for row in options
        if integer(row["is_primary_recommendation"]) == 1
    ]

    supplier_allocations = defaultdict(float)

    for row in primary_rows:

        if row["option_type"] != "SUPPLIER_PURCHASE":
            continue

        key = (
            row["supplier_id"],
            row["sku_id"],
            row["capacity_week"]
        )

        supplier_allocations[key] += number(
            row["proposed_quantity"]
        )

    supplier_capacity_check = True

    for key, allocated in supplier_allocations.items():

        capacity = indexes["capacity"].get(key)

        if capacity is None:
            supplier_capacity_check = False
            continue

        available = max(
            0.0,
            number(capacity["maximum_quantity"])
            - existing_usage.get(key, 0.0)
        )

        if allocated > available + TOLERANCE:
            supplier_capacity_check = False

    # --------------------------------------------------------
    # Verify primary substitute stock allocations.
    # --------------------------------------------------------

    substitute_allocations = defaultdict(float)

    for row in primary_rows:

        if row["option_type"] != "APPROVED_SUBSTITUTE":
            continue

        key = (
            row["substitute_sku_id"],
            row["location_id"],
            row["shortage_week"]
        )

        substitute_allocations[key] += number(
            row["proposed_quantity"]
        )

    substitute_stock_check = True

    for key, allocated in substitute_allocations.items():

        projection = indexes["projection"].get(key)

        if projection is None:
            substitute_stock_check = False
            continue

        surplus = max(
            0.0,
            number(projection["ending_available_balance"])
        )

        if allocated > surplus + TOLERANCE:
            substitute_stock_check = False

    checks = [
        report(
            "Option ID uniqueness",
            unique_ids,
            f"{len(options)} option rows"
        ),
        report(
            "Option shortage references",
            all_shortage_references_valid
        ),
        report(
            "Blocked options have decision reasons",
            all_blocked_have_reason
        ),
        report(
            "Supplier approval references",
            supplier_approval_check
        ),
        report(
            "Supplier policy references and effective dates",
            supplier_policy_check
        ),
        report(
            "Supplier quantity, MOQ and cost arithmetic",
            supplier_math_check
        ),
        report(
            "Supplier lead-time and planned order week",
            supplier_lead_check
        ),
        report(
            "Synthetic supplier capacity references",
            supplier_capacity_source_check
        ),
        report(
            "Primary supplier capacity allocation",
            supplier_capacity_check
        ),
        report(
            "Approved substitute and effective-date checks",
            substitute_approval_check
        ),
        report(
            "Substitute quantity, conversion and cost arithmetic",
            substitute_math_check
        ),
        report(
            "Substitute stock source",
            substitute_stock_source_check
        ),
        report(
            "Primary substitute stock allocation",
            substitute_stock_check
        ),
    ]

    return (
        all(checks),
        option_by_id,
        primary_rows
    )


# ============================================================
# VERIFY SUMMARY AGAINST OPTIONS AND SHORTAGES
# ============================================================

def verify_summary(data, option_by_id, primary_rows):

    summary = data["summary"]
    shortages = data["shortages"]

    summary_ids = [
        row["shortage_id"]
        for row in summary
    ]

    source_shortage_ids = [
        row["shortage_id"]
        for row in shortages
    ]

    one_summary_per_shortage = (
        len(summary) == len(shortages)
        and len(summary_ids) == len(set(summary_ids))
        and set(summary_ids) == set(source_shortage_ids)
    )

    primary_by_shortage = defaultdict(list)

    for option in primary_rows:
        primary_by_shortage[
            option["shortage_id"]
        ].append(option)

    primary_count_check = all(
        len(rows) <= 1
        for rows in primary_by_shortage.values()
    )

    summary_match_check = True
    primary_flag_check = True

    for row in summary:

        shortage_id = row["shortage_id"]
        primary_option_id = row["primary_option_id"]

        matching_primary = primary_by_shortage.get(
            shortage_id,
            []
        )

        if primary_option_id:

            option = option_by_id.get(
                primary_option_id
            )

            if option is None:
                summary_match_check = False
                continue

            if (
                len(matching_primary) != 1
                or matching_primary[0]["option_id"]
                != primary_option_id
            ):
                primary_flag_check = False

            comparisons = [
                (
                    row["primary_option_type"],
                    option["option_type"]
                ),
                (
                    number(row["proposed_quantity"]),
                    number(option["proposed_quantity"])
                ),
                (
                    number(row["equivalent_original_quantity"]),
                    number(option["equivalent_original_quantity"])
                ),
                (
                    number(row["uncovered_shortage_quantity"]),
                    number(option["uncovered_shortage_quantity"])
                ),
                (
                    number(row["estimated_cost"]),
                    number(option["estimated_cost"])
                ),
                (
                    row["feasibility_status"],
                    option["feasibility_status"]
                ),
            ]

            for left, right in comparisons:

                if isinstance(left, (int, float)):
                    if not close(left, right):
                        summary_match_check = False
                elif left != right:
                    summary_match_check = False

        else:

            if matching_primary:
                primary_flag_check = False

            if row["feasibility_status"] != "NO_FEASIBLE_OPTION":
                summary_match_check = False

            source_shortage = next(
                (
                    item for item in shortages
                    if item["shortage_id"] == shortage_id
                ),
                None
            )

            if source_shortage is not None:

                if (
                    not close(
                        number(row["proposed_quantity"]),
                        0
                    )
                    or not close(
                        number(row["uncovered_shortage_quantity"]),
                        number(source_shortage["shortage_quantity"])
                    )
                ):
                    summary_match_check = False

    checks = [
        report(
            "Exactly one summary row per shortage",
            one_summary_per_shortage
        ),
        report(
            "Maximum one primary option per shortage",
            primary_count_check
        ),
        report(
            "Summary values match selected primary options",
            summary_match_check
        ),
        report(
            "Primary option flags match summary",
            primary_flag_check
        ),
    ]

    return all(checks)


# ============================================================
# QUANTITY AND COST RECONCILIATION
# ============================================================

def print_reconciliation(data, primary_rows):

    shortage_total = sum(
        number(row["shortage_quantity"])
        for row in data["shortages"]
    )

    recommended_equivalent_total = sum(
        number(row["equivalent_original_quantity"])
        for row in primary_rows
    )

    uncovered_total = sum(
        number(row["uncovered_shortage_quantity"])
        for row in data["summary"]
    )

    primary_cost_total = sum(
        number(row["estimated_cost"])
        for row in primary_rows
    )

    # MOQ can cause a supplier purchase recommendation
    # to exceed the original shortage quantity.
    moq_rounding_excess = 0.0

    for row in primary_rows:

        if row["option_type"] != "SUPPLIER_PURCHASE":
            continue

        shortage_quantity = number(
            row["shortage_quantity"]
        )

        equivalent_quantity = number(
            row["equivalent_original_quantity"]
        )

        moq_rounding_excess += max(
            0.0,
            equivalent_quantity - shortage_quantity
        )

    expected_equivalent_total = (
        shortage_total
        - uncovered_total
        + moq_rounding_excess
    )

    print("\nQUANTITY AND COST RECONCILIATION")
    print("-" * 68)

    print(
        "Total projected shortage:",
        round(shortage_total, 2)
    )

    print(
        "Recommended equivalent quantity:",
        round(recommended_equivalent_total, 2)
    )

    print(
        "Uncovered shortage quantity:",
        round(uncovered_total, 2)
    )

    print(
        "MOQ rounding excess:",
        round(moq_rounding_excess, 2)
    )

    print(
        "Expected recommended quantity:",
        round(expected_equivalent_total, 2)
    )

    print(
        "Primary recommended cost:",
        round(primary_cost_total, 2)
    )

    quantity_reconciliation = close(
        recommended_equivalent_total,
        expected_equivalent_total
    )

    print(
        "Quantity reconciliation:",
        "PASSED" if quantity_reconciliation else "FAILED"
    )

    return quantity_reconciliation


# ============================================================
# MAIN
# ============================================================

def main():

    global MASTER_DIR, TRANSACTION_DIR

    parser = argparse.ArgumentParser(
        description="Independently verify scale-specific mitigation recommendations."
    )

    parser.add_argument(
        "--scale",
        choices=["starter", "full"],
        required=True,
        help="Dataset scale to verify (starter or full)."
    )

    args = parser.parse_args()

    scale_dir = BASE_DIR / "data" / "generated" / args.scale
    MASTER_DIR = scale_dir / "master_data"
    TRANSACTION_DIR = scale_dir / "transactions"

    print("=" * 76)
    print("INDEPENDENT MITIGATION RECOMMENDATION VERIFICATION")
    print("Scale:", args.scale)
    print("Input directory:", scale_dir)
    print("INDEPENDENT MITIGATION RECOMMENDATION VERIFICATION")
    print("=" * 76)

    data = load_data()

    print("\n1. INPUT AND OUTPUT RECORD COUNTS")

    print("Projected shortages:", len(data["shortages"]))
    print("Mitigation option rows:", len(data["options"]))
    print("Mitigation summary rows:", len(data["summary"]))

    indexes = build_indexes(data)

    existing_usage, joined_count = (
        calculate_existing_po_usage(data)
    )

    print(
        "Existing purchase order lines joined:",
        joined_count
    )

    print("\n2. OPTION-LEVEL VERIFICATION")

    options_passed, option_by_id, primary_rows = (
        verify_options(
            data,
            indexes,
            existing_usage
        )
    )

    print("\n3. SUMMARY-LEVEL VERIFICATION")

    summary_passed = verify_summary(
        data,
        option_by_id,
        primary_rows
    )

    print("\n4. QUANTITY RECONCILIATION")

    quantity_passed = print_reconciliation(
        data,
        primary_rows
    )

    print("\n5. RECOMMENDATION STATUS DISTRIBUTION")

    status_counts = defaultdict(int)
    type_counts = defaultdict(int)

    for row in data["options"]:
        status_counts[row["feasibility_status"]] += 1
        type_counts[row["option_type"]] += 1

    for status in sorted(status_counts):
        print(f"{status}: {status_counts[status]}")

    for option_type in sorted(type_counts):
        print(f"{option_type}: {type_counts[option_type]}")

    print("\n6. PRIMARY RECOMMENDATION COUNTS")

    supplier_primary_count = sum(
        1 for row in primary_rows
        if row["option_type"] == "SUPPLIER_PURCHASE"
    )

    substitute_primary_count = sum(
        1 for row in primary_rows
        if row["option_type"] == "APPROVED_SUBSTITUTE"
    )

    no_option_count = sum(
        1 for row in data["summary"]
        if row["feasibility_status"] == "NO_FEASIBLE_OPTION"
    )

    print("Primary supplier recommendations:", supplier_primary_count)
    print("Primary substitute recommendations:", substitute_primary_count)
    print("Shortages without a primary recommendation:", no_option_count)

    print("\n" + "=" * 76)

    if all([
        options_passed,
        summary_passed,
        quantity_passed
    ]):
        print("ALL INDEPENDENT MITIGATION CHECKS PASSED")
    else:
        print("INDEPENDENT VERIFICATION FAILED")
        print("Review the failed checks before proceeding.")

    print("Database changes: NONE")
    print("Generated CSV files modified: NONE")

    print("=" * 76)


if __name__ == "__main__":
    main()