
import csv
from pathlib import Path
from collections import defaultdict
from datetime import date

BASE_DIR = Path(__file__).resolve().parents[1]
MASTER_DIR = BASE_DIR / "data" / "generated" / "master_data"
DATA_DIR = BASE_DIR / "data" / "generated" / "transactions"


def read_csv(folder, filename):
    with open(folder / filename, "r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def get_week(date_text):
    iso = date.fromisoformat(date_text).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


policies = read_csv(MASTER_DIR, "supplier_sku_policy.csv")
supplier_skus = read_csv(MASTER_DIR, "supplier_sku.csv")
capacities = read_csv(DATA_DIR, "supplier_capacity.csv")
lead_times = read_csv(DATA_DIR, "lead_time.csv")
purchase_orders = read_csv(DATA_DIR, "purchase_order.csv")
po_lines = read_csv(DATA_DIR, "purchase_order_line.csv")
shortages = read_csv(DATA_DIR, "projected_shortages.csv")
substitutes = read_csv(MASTER_DIR, "sku_substitute.csv")

print("=" * 75)
print("SUPPLIER MITIGATION CAPACITY VERIFICATION")
print("=" * 75)

# 1. Check policy and approval coverage.

policy_keys = {
    (r["supplier_id"], r["sku_id"])
    for r in policies
}

approved_keys = {
    (r["supplier_id"], r["sku_id"])
    for r in supplier_skus
    if r["is_approved"] == "1"
}

capacity_keys = {
    (r["supplier_id"], r["sku_id"], r["capacity_week"])
    for r in capacities
}

print("\n1. SUPPLIER POLICY AND APPROVAL COVERAGE")
print("-" * 75)
print("Supplier-SKU policy records:", len(policies))
print("Supplier-SKU relationship records:", len(supplier_skus))
print("Approved supplier-SKU relationships:", len(approved_keys))
print("Policy relationships:", len(policy_keys))
print("Capacity records:", len(capacities))

print(
    "Approved relationships with policy:",
    sum(1 for key in approved_keys if key in policy_keys)
)

# 2. Join existing PO lines to their supplier and order dates.

po_lookup = {
    row["po_id"]: row
    for row in purchase_orders
}

existing_commitments = defaultdict(float)
joined_records = []

for line in po_lines:

    po = po_lookup.get(line["po_id"])

    if po is None:
        raise ValueError(
            f"Purchase order not found: {line['po_id']}"
        )

    order_week = get_week(po["order_date"])
    expected_week = get_week(po["expected_date"])

    key = (
        po["supplier_id"],
        line["sku_id"],
        order_week
    )

    existing_commitments[key] += float(line["order_quantity"])

    joined_records.append({
        "po_id": po["po_id"],
        "po_line_id": line["po_line_id"],
        "supplier_id": po["supplier_id"],
        "sku_id": line["sku_id"],
        "location_id": line["location_id"],
        "order_date": po["order_date"],
        "order_week": order_week,
        "expected_date": po["expected_date"],
        "expected_week": expected_week,
        "order_quantity": float(line["order_quantity"]),
        "po_status": po["status"]
    })

print("\n2. EXISTING PURCHASE ORDER JOIN")
print("-" * 75)
print("Purchase orders:", len(purchase_orders))
print("Purchase order lines:", len(po_lines))
print("Successfully joined PO lines:", len(joined_records))

print("\nFIRST 10 JOINED RECORDS")

for row in joined_records[:10]:
    print(row)

# 3. Compare capacity with existing PO quantities.
# This is a diagnostic comparison only. The correct capacity
# allocation week must be confirmed before recommendations.

capacity_lookup = {
    (
        row["supplier_id"],
        row["sku_id"],
        row["capacity_week"]
    ): float(row["maximum_quantity"])
    for row in capacities
}

print("\n3. CAPACITY WEEK COMPARISON")
print("-" * 75)

for row in joined_records[:10]:

    key = (
        row["supplier_id"],
        row["sku_id"],
        row["order_week"]
    )

    expected_key = (
        row["supplier_id"],
        row["sku_id"],
        row["expected_week"]
    )

    order_week_capacity = capacity_lookup.get(key)
    expected_week_capacity = capacity_lookup.get(expected_key)

    print(
        row["po_line_id"],
        "| Order week:", row["order_week"],
        "| Expected week:", row["expected_week"],
        "| Order-week capacity:", order_week_capacity,
        "| Expected-week capacity:", expected_week_capacity
    )

# 4. Summarize supplier lead-time coverage.

lead_time_keys = {
    (row["supplier_id"], row["location_id"])
    for row in lead_times
}

shortage_supplier_pairs = set()

for shortage in shortages:
    shortage_supplier_pairs.update(
        (row["supplier_id"], shortage["location_id"])
        for row in policies
        if row["sku_id"] == shortage["sku_id"]
        and (row["supplier_id"], row["sku_id"]) in approved_keys
    )

print("\n4. LEAD-TIME COVERAGE")
print("-" * 75)
print("Lead-time records:", len(lead_times))
print("Approved supplier-location pairs relevant to shortages:",
      len(shortage_supplier_pairs))
print("Pairs with lead-time records:",
      sum(1 for key in shortage_supplier_pairs if key in lead_time_keys))

# 5. Substitute summary.

approved_substitutes = [
    row for row in substitutes
    if row["is_approved"] == "1"
]

print("\n5. SUBSTITUTE SUMMARY")
print("-" * 75)
print("Total substitute relationships:", len(substitutes))
print("Approved substitutes:", len(approved_substitutes))

for row in substitutes:
    print(
        row["original_sku_id"],
        "->",
        row["substitute_sku_id"],
        "| Approved:",
        row["is_approved"],
        "| Conversion:",
        row["conversion_factor"]
    )

# 6. Summary of capacity records and PO commitment groups.

print("\n6. PURCHASE ORDER CAPACITY GROUPS")
print("-" * 75)
print("Distinct supplier-SKU-order-week groups:",
      len(existing_commitments))

for key, quantity in list(sorted(existing_commitments.items()))[:10]:
    capacity = capacity_lookup.get(key)

    print(
        key,
        "| Existing ordered quantity:", quantity,
        "| Matching order-week capacity:", capacity
    )

print("\nINSPECTION COMPLETED")
print("No source files modified.")
print("Database changes: NONE")
