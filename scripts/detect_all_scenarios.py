
import csv
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILES = [
    BASE_DIR / "data" / "scenarios" / "exception_scenarios.csv",
    BASE_DIR / "data" / "scenarios" / "valid_scenarios.csv"
]

OUTPUT_FILE = (
    BASE_DIR / "data" / "scenarios" / "combined_detection_results.csv"
)


def detect_scenario(row):
    issues = []

    # Rule 1: Inbound double counting
    if row["inbound_included_in_snapshot"]:
        included = row["inbound_included_in_snapshot"].lower() == "true"
        received = float(row["received_inbound_quantity"] or 0)
        additional = float(row["additional_inbound_quantity"] or 0)

        if included and received > 0 and additional > 0:
            issues.append("INBOUND_DOUBLE_COUNT")

    # Rule 2: Unapproved substitute
    if row["substitute_sku_id"]:
        relationship = (
            row["substitute_relationship_exists"].lower() == "true"
        )
        approved = row["substitute_approved"].lower() == "true"

        if not relationship or not approved:
            issues.append("UNAPPROVED_SUBSTITUTE")

    # Rule 3: Supplier capacity exceeded
    if row["proposed_quantity"] and row["capacity_quantity"]:
        proposed = float(row["proposed_quantity"])
        capacity = float(row["capacity_quantity"])

        if proposed > capacity:
            issues.append("CAPACITY_EXCEEDED")

    # Rule 4: Missing or ineffective lead time
    if row["lead_time_record_exists"]:
        record_exists = (
            row["lead_time_record_exists"].lower() == "true"
        )

        planning_date = date.fromisoformat(row["planning_date"])
        effective_from = date.fromisoformat(
            row["lead_time_effective_from"]
        )

        effective_to = row["lead_time_effective_to"]

        effective = planning_date >= effective_from

        if effective_to:
            effective = (
                effective
                and planning_date <= date.fromisoformat(effective_to)
            )

        if not record_exists or not effective:
            issues.append("MISSING_LEAD_TIME")

    # Rule 5: Unit-of-measure mismatch
    if row["supply_unit"] and row["demand_unit"] and row["inventory_unit"]:
        supply = row["supply_unit"]
        demand = row["demand_unit"]
        inventory = row["inventory_unit"]

        conversion = (
            row["unit_conversion_available"].lower() == "true"
        )

        if (
            (supply != demand or supply != inventory)
            and not conversion
        ):
            issues.append("UOM_MISMATCH")

    if not issues:
        return "NONE", "ACCEPT", "No exception detected."

    # Preserve the policy: missing lead time is a flag;
    # other listed exceptions are rejected.
    decision = "FLAG" if issues == ["MISSING_LEAD_TIME"] else "REJECT"

    return ";".join(issues), decision, " | ".join(issues)


def main():
    print("=" * 75)
    print("COMBINED SUPPLY CHAIN SCENARIO DETECTION")
    print("=" * 75)

    all_rows = []

    for file_path in INPUT_FILES:
        if not file_path.exists():
            raise FileNotFoundError(file_path)

        with open(
            file_path, "r", newline="", encoding="utf-8-sig"
        ) as file:
            reader = csv.DictReader(file)
            all_rows.extend(list(reader))

    scenario_ids = [row["scenario_id"] for row in all_rows]

    if len(scenario_ids) != len(set(scenario_ids)):
        raise ValueError("Duplicate scenario IDs across input files.")

    results = []

    for row in all_rows:
        issue, decision, reason = detect_scenario(row)

        results.append({
            "scenario_id": row["scenario_id"],
            "detected_issue_type": issue,
            "detected_decision": decision,
            "detection_reason": reason
        })

    with open(
        OUTPUT_FILE, "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "scenario_id",
                "detected_issue_type",
                "detected_decision",
                "detection_reason"
            ]
        )
        writer.writeheader()
        writer.writerows(results)

    print("\nDETECTION RESULTS")
    print("-" * 75)

    for row in results:
        print(
            f"{row['scenario_id']} | "
            f"{row['detected_issue_type']} | "
            f"{row['detected_decision']}"
        )

    exception_count = sum(
        1 for row in results
        if row["detected_issue_type"] != "NONE"
    )

    accepted_count = len(results) - exception_count

    print("\nSUMMARY")
    print("-" * 75)
    print(f"Total scenarios: {len(results)}")
    print(f"Exceptions detected: {exception_count}")
    print(f"Accepted scenarios: {accepted_count}")
    print(f"Results saved: {OUTPUT_FILE.name}")
    print("Database changes: NONE")
    print("=" * 75)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, FileNotFoundError) as error:
        print("\nDETECTION FAILED")
        print(error)
