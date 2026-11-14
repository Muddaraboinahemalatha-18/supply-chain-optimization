
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 85)
print("W47 PROJECTED INVENTORY BALANCE PREVIEW")
print("=" * 85)

print("\nPLANNING ASSUMPTIONS")
print("1. Starting inventory snapshot: 2026-11-12")
print("2. No net inventory changes assumed through 2026-11-15.")
print("3. Already received inbound orders are included in inventory.")
print("4. No additional inbound supply is assumed during W47.")
print("5. All W47 forecast demand is treated as outstanding demand.")

print("\nPROJECTED INVENTORY")

cursor.execute("""
    SELECT
        f.forecast_id,
        s.sku_name,
        f.sku_id,
        f.location_id,
        i.inventory_date,
        i.on_hand_quantity,
        i.reserved_quantity,
        i.on_hand_quantity - i.reserved_quantity
            AS opening_available,
        f.forecast_quantity AS forecast_demand,
        s.unit_of_measure
    FROM forecast_demand f
    JOIN sku s
        ON f.sku_id = s.sku_id
    JOIN inventory i
        ON i.sku_id = f.sku_id
       AND i.location_id = f.location_id
    WHERE f.forecast_week = '2026-W47'
    ORDER BY f.forecast_id
""")

records = cursor.fetchall()

print("-" * 85)

for row in records:
    opening = row["opening_available"]
    demand = row["forecast_demand"]
    ending = opening - demand

    shortage = max(0, -ending)
    surplus = max(0, ending)

    status = "SHORTAGE" if shortage > 0 else "SUFFICIENT"

    print(f"\nProduct: {row['sku_name']}")
    print(f"SKU: {row['sku_id']}")
    print(f"Location: {row['location_id']}")
    print(f"Inventory snapshot: {row['inventory_date']}")
    print(f"Opening available: {opening} {row['unit_of_measure']}")
    print(f"W47 forecast demand: {demand} {row['unit_of_measure']}")
    print(f"Projected ending balance: {ending} {row['unit_of_measure']}")
    print(f"Shortage quantity: {shortage} {row['unit_of_measure']}")
    print(f"Remaining surplus: {surplus} {row['unit_of_measure']}")
    print(f"Status: {status}")

print("\n" + "-" * 85)
print("SUMMARY")

shortage_count = 0
sufficient_count = 0

for row in records:
    ending = row["opening_available"] - row["forecast_demand"]

    if ending < 0:
        shortage_count += 1
    else:
        sufficient_count += 1

print("Total forecast records:", len(records))
print("Products with shortage:", shortage_count)
print("Products with sufficient inventory:", sufficient_count)

if len(records) != 5:
    print("WARNING: Expected 5 forecast records but found", len(records))

connection.close()

print("\nNo database records were modified.")
print("=" * 85)
