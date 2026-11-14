
import csv
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BASE_DIR / "data" / "scenarios" / "exception_scenarios.csv"
OUTPUT_FILE = BASE_DIR / "data" / "scenarios" / "exception_detection_results.csv"


def detect_scenario(row):
    scenario_id = row["scenario_id"]

    # EXC-001: Received inbound is already included in inventory
    if scenario_id == "EXC-001":
        included = row["inbound_included_in_snapshot"].lower() == "true"
        received = float(row["received_inbound_quantity"])
        additional = float(row["additional_inbound_quantity"])

        if included and received > 0 and additional > 0:
            return (
                "INBOUND_DOUBLE_COUNT",
                "REJECT",
                "Received inbound is already included in the inventory snapshot."
            )

    # EXC-002: Substitute SKU is not approved
    elif scenario_id == "EXC-002":
        relationship_exists = (
            row["substitute_relationship_exists"].lower() == "true"
        )
        approved = row["substitute_approved"].lower() == "true"

        if not relationship_exists or not approved:
            return (
                "UNAPPROVED_SUBSTITUTE",
                "REJECT",
                "Substitute SKU does not have an approved relationship."
            )

    # EXC-003: Proposed purchase exceeds supplier capacity
    elif scenario_id == "EXC-003":
        proposed = float(row["proposed_quantity"])
        capacity = float(row["capacity_quantity"])

        if proposed > capacity:
            return (
                "CAPACITY_EXCEEDED",
                "REJECT",
                f"Proposed quantity {proposed} exceeds capacity {capacity}."
            )

    # EXC-004: Lead-time record is not effective on planning date
    elif scenario_id == "EXC-004":
        record_exists = (
            row["lead_time_record_exists"].lower() == "true"
        )

        planning_date = date.fromisoformat(row["planning_date"])
        effective_from = date.fromisoformat(
            row["lead_time_effective_from"]
        )

        effective_to = row["lead_time_effective_to"]

        is_effective = planning_date >= effective_from

        if effective_to:
            is_effective = (
                is_effective
                and planning_date <= date.fromisoformat(effective_to)
            )

        if not record_exists or not is_effective:
            return (
                "MISSING_LEAD_TIME",
                "FLAG",
                "No effective lead-time record exists on the planning date."
            )

    # EXC-005: Supply unit differs without an available conversion
    elif scenario_id == "EXC-005":
        demand_unit = row["demand_unit"]
        inventory_unit = row["inventory_unit"]
        supply_unit = row["supply_unit"]

        conversion_available = (
            row["unit_conversion_available"].lower() == "true"
        )

        if (
            supply_unit != demand_unit
            or supply_unit != inventory_unit
        ) and not conversion_available:
            return (
                "UOM_MISMATCH",
                "REJECT",
                "Supply unit differs and no unit conversion is available."
            )

    return (
        "NO_EXCEPTION",
        "ACCEPT",
        "No exception detected."
    )


def main():
    print("=" * 75)
    print("EXCEPTION SCENARIO DETECTION")
    print("=" * 75)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    results = []

    with open(INPUT_FILE, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            issue_type, decision, reason = detect_scenario(row)

            results.append({
                "scenario_id": row["scenario_id"],
                "detected_issue_type": issue_type,
                "detected_decision": decision,
                "detection_reason": reason
            })

    output_columns = [
        "scenario_id",
        "detected_issue_type",
        "detected_decision",
        "detection_reason"
    ]

    with open(
        OUTPUT_FILE, "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=output_columns)
        writer.writeheader()
        writer.writerows(results)

    print("\nDETECTION RESULTS")
    print("-" * 75)

    for result in results:
        print(
            f"{result['scenario_id']} | "
            f"{result['detected_issue_type']} | "
            f"{result['detected_decision']}"
        )

    detected_count = sum(
        1 for result in results
        if result["detected_issue_type"] != "NO_EXCEPTION"
    )

    print("\n" + "=" * 75)
    print(f"Scenarios processed: {len(results)}")
    print(f"Exceptions detected: {detected_count}")
    print(f"Results saved: {OUTPUT_FILE.name}")
    print("Database changes: NONE")
    print("=" * 75)


if __name__ == "__main__":
    main()
