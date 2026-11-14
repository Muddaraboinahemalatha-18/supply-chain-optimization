import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SCENARIO_DIR = BASE_DIR / "data" / "scenarios"

EXCEPTION_FILE = SCENARIO_DIR / "exception_scenarios.csv"
VALID_FILE = SCENARIO_DIR / "valid_scenarios.csv"
OLD_GT_FILE = SCENARIO_DIR / "exception_ground_truth.csv"
COMBINED_GT_FILE = SCENARIO_DIR / "combined_ground_truth.csv"


def read_csv(file_path):
    with open(file_path, "r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def check(condition, message):
    if not condition:
        raise ValueError(message)
    print(f"PASS: {message}")


def main():
    print("=" * 75)
    print("COMBINED GROUND TRUTH VALIDATION")
    print("=" * 75)

    exception_scenarios = read_csv(EXCEPTION_FILE)
    valid_scenarios = read_csv(VALID_FILE)
    old_ground_truth = read_csv(OLD_GT_FILE)
    combined_ground_truth = read_csv(COMBINED_GT_FILE)

    input_ids = {
        row["scenario_id"]
        for row in exception_scenarios + valid_scenarios
    }

    ground_truth_ids = [
        row["scenario_id"] for row in combined_ground_truth
    ]

    check(
        len(combined_ground_truth) == 10,
        "Combined ground truth contains exactly 10 records."
    )

    check(
        len(ground_truth_ids) == len(set(ground_truth_ids)),
        "Ground truth scenario IDs are unique."
    )

    check(
        set(ground_truth_ids) == input_ids,
        "Ground truth IDs match all exception and valid input scenarios."
    )

    invalid_rows = [
        row for row in combined_ground_truth
        if row["expected_label"] == "INVALID"
    ]

    valid_rows = [
        row for row in combined_ground_truth
        if row["expected_label"] == "VALID"
    ]

    check(
        len(invalid_rows) == 5 and len(valid_rows) == 5,
        "Ground truth contains 5 INVALID and 5 VALID scenarios."
    )

    for row in combined_ground_truth:
        if row["expected_label"] == "INVALID":
            check(
                row["expected_decision"] in ("REJECT", "FLAG"),
                f'{row["scenario_id"]} has a valid exception decision.'
            )
        else:
            check(
                row["issue_type"] == "NONE"
                and row["expected_decision"] == "ACCEPT",
                f'{row["scenario_id"]} is correctly labelled as valid.'
            )

        check(
            bool(row["explanation"].strip()),
            f'{row["scenario_id"]} has an explanation.'
        )

    old_gt = {
        row["scenario_id"]: row
        for row in old_ground_truth
    }

    combined_gt = {
        row["scenario_id"]: row
        for row in combined_ground_truth
    }

    check(
        all(
            scenario_id in combined_gt
            and combined_gt[scenario_id]["issue_type"] == old_row["issue_type"]
            and combined_gt[scenario_id]["expected_label"] == old_row["expected_label"]
            and combined_gt[scenario_id]["expected_decision"] == old_row["expected_decision"]
            for scenario_id, old_row in old_gt.items()
        ),
        "All five original exception ground-truth records are preserved."
    )

    print("-" * 75)
    print("SUMMARY")
    print("-" * 75)
    print("Total scenarios:", len(combined_ground_truth))
    print("Invalid scenarios:", len(invalid_rows))
    print("Valid scenarios:", len(valid_rows))
    print("Ground truth validation: PASSED")
    print("Database changes: NONE")
    print("=" * 75)


if __name__ == "__main__":
    main()