
import csv
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent
MASTER = BASE / "data" / "generated" / "full" / "master_data"
TRANS = BASE / "data" / "generated" / "full" / "transactions"

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

sub_path = MASTER / "sku_substitute.csv"
if not sub_path.exists():
    sub_path = TRANS / "sku_substitute.csv"

substitutes = {
    r["substitute_id"]: r for r in read_csv(sub_path)
}

options = read_csv(TRANS / "mitigation_options.csv")

print("=" * 75)
print("INSPECTION OF SIX SUBSTITUTE OPTIONS")
print("=" * 75)

count = 0

for option in options:
    if option["option_type"] != "APPROVED_SUBSTITUTE":
        continue

    sub = substitutes.get(option["substitute_id"])
    if sub is None:
        continue

    required = datetime.strptime(
        option["required_arrival_date"], "%Y-%m-%d"
    ).date()

    effective_from = datetime.strptime(
        sub["effective_from"], "%Y-%m-%d"
    ).date()

    if required < effective_from:
        count += 1

        print(f"\nFAILED RECORD {count}")
        print("Option ID:", option["option_id"])
        print("Shortage ID:", option["shortage_id"])
        print("Substitute ID:", option["substitute_id"])
        print("SKU:", option["sku_id"])
        print("Substitute SKU:", option["substitute_sku_id"])
        print("Shortage week:", option["shortage_week"])
        print("Required arrival:", option["required_arrival_date"])
        print("Substitute effective from:", sub["effective_from"])
        print("Planned order date:", option["planned_order_date"])
        print("Expected arrival date:", option["expected_arrival_date"])
        print("Feasibility status:", option["feasibility_status"])
        print("Rule check status:", option["rule_check_status"])
        print("Decision reason:", option["decision_reason"])
        print("Primary recommendation:", option["is_primary_recommendation"])

print("\nTotal failed records inspected:", count)
print("No files modified.")
