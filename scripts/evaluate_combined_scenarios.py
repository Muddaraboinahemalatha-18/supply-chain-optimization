
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SCENARIO_DIR = BASE_DIR / "data" / "scenarios"

RESULTS_FILE = SCENARIO_DIR / "combined_detection_results.csv"
GROUND_TRUTH_FILE = SCENARIO_DIR / "combined_ground_truth.csv"
OUTPUT_FILE = SCENARIO_DIR / "combined_evaluation_results.csv"


def read_csv(file_path):
    with open(file_path, "r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def percentage(value, total):
    if total == 0:
        return 0.0
    return (value / total) * 100


def main():
    print("=" * 75)
    print("COMBINED SCENARIO EVALUATION")
    print("=" * 75)

    results = read_csv(RESULTS_FILE)
    ground_truth = read_csv(GROUND_TRUTH_FILE)

    result_ids = [row["scenario_id"] for row in results]
    truth_ids = [row["scenario_id"] for row in ground_truth]

    if len(result_ids) != len(set(result_ids)):
        raise ValueError("Duplicate scenario IDs found in detection results.")

    if len(truth_ids) != len(set(truth_ids)):
        raise ValueError("Duplicate scenario IDs found in ground truth.")

    if set(result_ids) != set(truth_ids):
        raise ValueError(
            "Detection result IDs do not match ground-truth IDs."
        )

    truth_lookup = {
        row["scenario_id"]: row for row in ground_truth
    }

    tp = 0
    fp = 0
    fn = 0
    tn = 0
    exact_matches = 0

    evaluation_rows = []

    print("\nSCENARIO-BY-SCENARIO COMPARISON")
    print("-" * 75)

    for result in results:
        scenario_id = result["scenario_id"]
        expected = truth_lookup[scenario_id]

        expected_label = expected["expected_label"]
        detected_label = (
            "INVALID"
            if result["detected_issue_type"] != "NONE"
            else "VALID"
        )

        expected_issue = expected["issue_type"]
        detected_issue = result["detected_issue_type"]

        expected_decision = expected["expected_decision"]
        detected_decision = result["detected_decision"]

        if expected_label == "INVALID" and detected_label == "INVALID":
            tp += 1
        elif expected_label == "VALID" and detected_label == "INVALID":
            fp += 1
        elif expected_label == "INVALID" and detected_label == "VALID":
            fn += 1
        elif expected_label == "VALID" and detected_label == "VALID":
            tn += 1

        exact_match = (
            expected_label == detected_label
            and expected_issue == detected_issue
            and expected_decision == detected_decision
        )

        if exact_match:
            exact_matches += 1

        status = "PASS" if exact_match else "FAIL"

        print(
            f"{scenario_id} | "
            f"Expected: {expected_issue}/{expected_decision} | "
            f"Detected: {detected_issue}/{detected_decision} | "
            f"{status}"
        )

        evaluation_rows.append({
            "scenario_id": scenario_id,
            "expected_label": expected_label,
            "detected_label": detected_label,
            "expected_issue_type": expected_issue,
            "detected_issue_type": detected_issue,
            "expected_decision": expected_decision,
            "detected_decision": detected_decision,
            "exact_match": "YES" if exact_match else "NO",
            "evaluation_status": status
        })

    total = len(ground_truth)

    accuracy = percentage(tp + tn, total)
    precision = percentage(tp, tp + fp)
    recall = percentage(tp, tp + fn)
    specificity = percentage(tn, tn + fp)

    f1_denominator = (2 * tp) + fp + fn
    f1_score = percentage(
        (2 * tp) / f1_denominator if f1_denominator else 0,
        1
    )

    exact_match_rate = percentage(exact_matches, total)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as file:
        fieldnames = evaluation_rows[0].keys()
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(evaluation_rows)

    print("\nCONFUSION MATRIX")
    print("-" * 75)
    print("True Positives (TP):", tp)
    print("False Positives (FP):", fp)
    print("False Negatives (FN):", fn)
    print("True Negatives (TN):", tn)

    print("\nEVALUATION METRICS")
    print("-" * 75)
    print(f"Accuracy:         {accuracy:.2f}%")
    print(f"Precision:        {precision:.2f}%")
    print(f"Recall:           {recall:.2f}%")
    print(f"Specificity:      {specificity:.2f}%")
    print(f"F1-score:         {f1_score:.2f}%")
    print(f"Exact match rate: {exact_match_rate:.2f}%")

    print("\nSUMMARY")
    print("-" * 75)
    print("Total scenarios:", total)
    print("Correct exact matches:", exact_matches)
    print("Failed exact matches:", total - exact_matches)
    print("Evaluation results saved:", OUTPUT_FILE.name)
    print("Database changes: NONE")

    if exact_matches == total:
        print("OVERALL RESULT: PASSED")
    else:
        print("OVERALL RESULT: REVIEW REQUIRED")

    print("=" * 75)


if __name__ == "__main__":
    main()
