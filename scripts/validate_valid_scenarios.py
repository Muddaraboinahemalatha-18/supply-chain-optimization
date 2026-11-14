
import csv
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parents[1]
FILE = BASE_DIR / "data" / "scenarios" / "valid_scenarios.csv"

EXPECTED_IDS = {
    "VAL-001", "VAL-002", "VAL-003", "VAL-004", "VAL-005"
}


def main():
    print("=" * 75)
    print("VALID BASELINE SCENARIO VALIDATION")
    print("=" * 75)

    with open(FILE, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames
        rows = list(reader)

    assert len(columns) == 27, "Expected 27 columns."
    assert len(rows) == 5, "Expected exactly 5 scenarios."

    ids = [row["scenario_id"] for row in rows]
    assert len(set(ids)) == 5, "Duplicate scenario IDs found."
    assert set(ids) == EXPECTED_IDS, "Unexpected scenario IDs."

    print("\n1. CSV STRUCTURE: PASS")
    print("27 columns and 5 unique scenarios: PASS")

    data = {row["scenario_id"]: row for row in rows}

    # VAL-001: No inbound double count
    r = data["VAL-001"]
    assert r["inbound_included_in_snapshot"].lower() == "true"
    assert float(r["additional_inbound_quantity"]) == 0
    assert float(r["projected_available_quantity"]) == float(
        r["base_available_quantity"]
    )

    print("VAL-001 inbound reconciliation: PASS")

    # VAL-002: Approved substitute
    r = data["VAL-002"]
    assert r["substitute_relationship_exists"].lower() == "true"
    assert r["substitute_approved"].lower() == "true"
    assert float(r["substitute_conversion_factor"]) > 0

    print("VAL-002 approved substitute: PASS")

    # VAL-003: Proposed quantity does not exceed capacity
    r = data["VAL-003"]
    assert float(r["proposed_quantity"]) == float(r["capacity_quantity"])
    assert r["capacity_source"] == "SYNTHETIC"

    print("VAL-003 supplier capacity: PASS")

    # VAL-004: Lead-time record is effective
    r = data["VAL-004"]
    planning_date = date.fromisoformat(r["planning_date"])
    effective_from = date.fromisoformat(r["lead_time_effective_from"])

    assert r["lead_time_record_exists"].lower() == "true"
    assert planning_date >= effective_from

    if r["lead_time_effective_to"]:
        effective_to = date.fromisoformat(r["lead_time_effective_to"])
        assert planning_date <= effective_to

    print("VAL-004 effective lead time: PASS")

    # VAL-005: Units match
    r = data["VAL-005"]
    assert r["demand_unit"] == r["inventory_unit"]
    assert r["inventory_unit"] == r["supply_unit"]

    print("VAL-005 unit-of-measure consistency: PASS")

    print("\n" + "=" * 75)
    print("RESULT: ALL VALID BASELINE SCENARIOS PASSED")
    print("Scenarios validated: 5")
    print("Database changes: NONE")
    print("=" * 75)


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, ValueError, KeyError, FileNotFoundError) as error:
        print("\nVALIDATION FAILED")
        print(error)
