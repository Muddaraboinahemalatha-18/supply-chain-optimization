
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

RESULTS_FILE = (
    BASE_DIR / "data" / "scenarios" / "exception_detection_results.csv"
)
GROUND_TRUTH_FILE = (
    BASE_DIR / "data" / "scenarios" / "exception_ground_truth.csv"
)


def load_csv(file_path):
    with open(file_path, "r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def main():
    print("=" * 75)
    print("EXCEPTION DETECTION EVALUATION")
    print("=" * 75)

    if not RESULTS_FILE.exists():
        raise FileNotFoundError("Detection results CSV not found.")

    if not GROUND_TRUTH_FILE.exists():
        raise FileNotFoundError("Ground-truth CSV not found.")

    results = load_csv(RESULTS_FILE)
    ground_truth = load_csv(GROUND_TRUTH_FILE)

    result_by_id = {row["scenario_id"]: row for row in results}
    truth_by_id = {row["scenario_id"]: row for row in ground_truth}

    if len(result_by_id) != len(results):
        raise ValueError("Duplicate scenario IDs in detection results.")

    if len(truth_by_id) != len(ground_truth):
        raise ValueError("Duplicate scenario IDs in ground truth.")

    if set(result_by_id) != set(truth_by_id):
        raise ValueError("Scenario IDs do not match between the two files.")

    true_positive = 0
    false_positive = 0
    false_negative = 0
    true_negative = 0
    exact_matches = 0

    print("\nSCENARIO-BY-SCENARIO COMPARISON")
    print("-" * 75)

    for scenario_id in sorted(truth_by_id):
        detected = result_by_id[scenario_id]
        expected = truth_by_id[scenario_id]

        detected_issue = detected["detected_issue_type"]
        detected_decision = detected["detected_decision"]

        # An exception detection represents an INVALID prediction.
        predicted_label = (
            "INVALID" if detected_issue != "NO_EXCEPTION" else "VALID"
        )

        expected_label = expected["expected_label"]
        expected_issue = expected["issue_type"]
        expected_decision = expected["expected_decision"]

        if predicted_label == "INVALID" and expected_label == "INVALID":
            true_positive += 1
        elif predicted_label == "INVALID" and expected_label == "VALID":
            false_positive += 1
        elif predicted_label == "VALID" and expected_label == "INVALID":
            false_negative += 1
        else:
            true_negative += 1

        issue_match = detected_issue == expected_issue
        decision_match = detected_decision == expected_decision
        label_match = predicted_label == expected_label

        if issue_match and decision_match and label_match:
            exact_matches += 1
            status = "PASS"
        else:
            status = "FAIL"

        print(
            f"{scenario_id} | "
            f"Issue: {'PASS' if issue_match else 'FAIL'} | "
            f"Decision: {'PASS' if decision_match else 'FAIL'} | "
            f"Label: {'PASS' if label_match else 'FAIL'} | "
            f"{status}"
        )

    total = len(ground_truth)

    accuracy = (true_positive + true_negative) / total * 100
    precision = (
        true_positive / (true_positive + false_positive) * 100
        if true_positive + false_positive else 0
    )
    recall = (
        true_positive / (true_positive + false_negative) * 100
        if true_positive + false_negative else 0
    )
    f1_score = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0
    )

    exact_match_rate = exact_matches / total * 100

    print("\nEVALUATION METRICS")
    print("-" * 75)
    print(f"Total scenarios: {total}")
    print(f"True positives: {true_positive}")
    print(f"False positives: {false_positive}")
    print(f"False negatives: {false_negative}")
    print(f"True negatives: {true_negative}")
    print(f"Accuracy: {accuracy:.2f}%")
    print(f"Precision: {precision:.2f}%")
    print(f"Recall: {recall:.2f}%")
    print(f"F1-score: {f1_score:.2f}%")
    print(f"Exact issue and decision match: {exact_match_rate:.2f}%")

    print("\nEVALUATION SUMMARY")
    print("-" * 75)

    if exact_matches == total:
        print("RESULT: ALL SCENARIOS MATCH GROUND TRUTH")
    else:
        print("RESULT: SOME SCENARIOS DO NOT MATCH GROUND TRUTH")

    print("Database changes: NONE")
    print("=" * 75)

    print(
        "\nNOTE: All five test cases are positive exception cases. "
        "Negative test cases are needed to evaluate specificity "
        "and false-positive performance."
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, FileNotFoundError) as error:
        print("\nEVALUATION FAILED")
        print(error)
