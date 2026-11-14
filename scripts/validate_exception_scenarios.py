import csv
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BASE_DIR / "data" / "scenarios" / "exception_scenarios.csv"
GROUND_TRUTH_FILE = BASE_DIR / "data" / "scenarios" / "exception_ground_truth.csv"

EXPECTED_SCENARIOS = {
    "EXC-001",
    "EXC-002",
    "EXC-003",
    "EXC-004",
    "EXC-005"
}

EXPECTED_ISSUES = {
    "EXC-001": "INBOUND_DOUBLE_COUNT",
    "EXC-002": "UNAPPROVED_SUBSTITUTE",
    "EXC-003": "CAPACITY_EXCEEDED",
    "EXC-004": "MISSING_LEAD_TIME",
    "EXC-005": "UOM_MISMATCH"
}

EXPECTED_INPUT_COLUMNS = [
    "scenario_id", "sku_id", "location_id", "supplier_id",
    "planning_week", "planning_date", "base_available_quantity",
    "received_inbound_quantity", "inbound_included_in_snapshot",
    "additional_inbound_quantity", "projected_available_quantity",
    "original_sku_id", "substitute_sku_id",
    "substitute_relationship_exists", "substitute_approved",
    "substitute_conversion_factor", "proposed_quantity",
    "capacity_quantity", "capacity_source", "lead_time_record_exists",
    "lead_time_days", "lead_time_effective_from",
    "lead_time_effective_to", "demand_unit", "inventory_unit",
    "supply_unit", "unit_conversion_available"
]

EXPECTED_GT_COLUMNS = [
    "ground_truth_id", "scenario_id", "issue_type",
    "expected_label", "expected_decision", "explanation"
]


def load_csv(file_path):
    with open(file_path, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        return reader.fieldnames, list(reader)


def validate():
    print("=" * 75)
    print("EXCEPTION SCENARIO CSV VALIDATION")
    print("=" * 75)

    # Check files exist
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    if not GROUND_TRUTH_FILE.exists():
        raise FileNotFoundError(
            f"Ground-truth file not found: {GROUND_TRUTH_FILE}"
        )

    # Load files
    input_columns, scenarios = load_csv(INPUT_FILE)
    gt_columns, ground_truth = load_csv(GROUND_TRUTH_FILE)

    # Check headers
    assert input_columns == EXPECTED_INPUT_COLUMNS, (
        "Input CSV columns do not match the expected structure."
    )

    assert gt_columns == EXPECTED_GT_COLUMNS, (
        "Ground-truth CSV columns do not match the expected structure."
    )

    print("\n1. CSV STRUCTURE")
    print("-" * 75)
    print(f"Input columns: {len(input_columns)} - PASS")
    print(f"Ground-truth columns: {len(gt_columns)} - PASS")

    # Check row counts and scenario IDs
    scenario_ids = [row["scenario_id"] for row in scenarios]
    gt_scenario_ids = [row["scenario_id"] for row in ground_truth]

    assert len(scenarios) == 5, "Expected exactly 5 input scenarios."
    assert len(ground_truth) == 5, "Expected exactly 5 ground-truth rows."
    assert len(set(scenario_ids)) == 5, "Duplicate scenario IDs found."
    assert len(set(gt_scenario_ids)) == 5, "Duplicate ground-truth scenario IDs found."
    assert set(scenario_ids) == EXPECTED_SCENARIOS
    assert set(gt_scenario_ids) == EXPECTED_SCENARIOS

    print("\n2. SCENARIO IDENTIFIERS")
    print("-" * 75)
    print("Five unique scenario IDs: PASS")
    print("Five matching ground-truth IDs: PASS")

    # Ensure labels are not leaked into input features
    forbidden_columns = {
        "issue_type", "expected_label",
        "expected_decision", "explanation"
    }

    assert not forbidden_columns.intersection(input_columns), (
        "Ground-truth information must not appear in the input CSV."
    )

    print("\n3. GROUND-TRUTH SEPARATION")
    print("-" * 75)
    print("Input file contains no expected labels or issue types: PASS")

    # Build scenario lookup
    scenario_by_id = {
        row["scenario_id"]: row for row in scenarios
    }

    gt_by_id = {
        row["scenario_id"]: row for row in ground_truth
    }

    # Validate ground-truth values
    for scenario_id, expected_issue in EXPECTED_ISSUES.items():
        gt = gt_by_id[scenario_id]

        assert gt["issue_type"] == expected_issue
        assert gt["expected_label"] == "INVALID"
        assert gt["expected_decision"] in {"REJECT", "FLAG"}
        assert gt["explanation"].strip() != ""

    print("\n4. GROUND-TRUTH CONTENT")
    print("-" * 75)
    print("All five issue types and expected decisions: PASS")

    # EXC-001: inbound double counting
    row = scenario_by_id["EXC-001"]

    base = float(row["base_available_quantity"])
    received = float(row["received_inbound_quantity"])
    additional = float(row["additional_inbound_quantity"])
    projected = float(row["projected_available_quantity"])

    assert row["inbound_included_in_snapshot"].lower() == "true"
    assert received == additional
    assert projected == base + additional

    print("\n5. BUSINESS RULE VALIDATION")
    print("-" * 75)
    print("EXC-001 inbound double-count scenario: PASS")

    # EXC-002: unapproved substitute
    row = scenario_by_id["EXC-002"]

    assert row["substitute_relationship_exists"].lower() == "false"
    assert row["substitute_approved"].lower() == "false"
    assert row["original_sku_id"] != row["substitute_sku_id"]

    print("EXC-002 unapproved substitute scenario: PASS")

    # EXC-003: supplier capacity exceeded
    row = scenario_by_id["EXC-003"]

    proposed = float(row["proposed_quantity"])
    capacity = float(row["capacity_quantity"])

    assert proposed > capacity
    assert row["capacity_source"] == "SYNTHETIC"

    print("EXC-003 capacity exceeded scenario: PASS")

    # EXC-004: lead-time record not effective on planning date
    row = scenario_by_id["EXC-004"]

    planning_date = date.fromisoformat(row["planning_date"])
    effective_from = date.fromisoformat(row["lead_time_effective_from"])

    assert row["lead_time_record_exists"].lower() == "true"
    assert planning_date < effective_from

    print("EXC-004 missing effective lead-time scenario: PASS")

    # EXC-005: unit-of-measure mismatch
    row = scenario_by_id["EXC-005"]

    assert float(row["proposed_quantity"]) > 0
    assert row["demand_unit"] == "Kg"
    assert row["inventory_unit"] == "Kg"
    assert row["supply_unit"] == "Liter"
    assert row["unit_conversion_available"].lower() == "false"

    print("EXC-005 UOM mismatch scenario: PASS")

    print("\n" + "=" * 75)
    print("RESULT: ALL VALIDATIONS PASSED")
    print("Input scenarios: 5")
    print("Ground-truth records: 5")
    print("Database changes: NONE")
    print("=" * 75)


if __name__ == "__main__":
    try:
        validate()
    except (AssertionError, ValueError, KeyError, FileNotFoundError) as error:
        print("\nVALIDATION FAILED")
        print(error)
