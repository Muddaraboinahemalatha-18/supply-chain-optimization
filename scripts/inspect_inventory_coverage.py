
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 65)
print("INVENTORY COVERAGE INSPECTION")
print("=" * 65)

# Inventory details
cursor.execute("""
    SELECT
        i.inventory_id,
        i.sku_id,
        s.sku_name,
        i.location_id,
        l.location_name,
        i.on_hand_quantity,
        i.reserved_quantity,
        (i.on_hand_quantity - i.reserved_quantity) AS available_quantity,
        i.unit_of_measure,
        i.inventory_date
    FROM inventory i
    JOIN sku s ON i.sku_id = s.sku_id
    JOIN location l ON i.location_id = l.location_id
    ORDER BY i.sku_id, i.location_id
""")

inventory_records = cursor.fetchall()

print("\nINVENTORY DETAILS")
print("-" * 65)

for row in inventory_records:
    print(
        f"ID: {row['inventory_id']} | "
        f"Product: {row['sku_name']} | "
        f"Location: {row['location_name']} | "
        f"On hand: {row['on_hand_quantity']} | "
        f"Reserved: {row['reserved_quantity']} | "
        f"Available: {row['available_quantity']} | "
        f"UOM: {row['unit_of_measure']} | "
        f"Date: {row['inventory_date']}"
    )

# Inventory summary by product
cursor.execute("""
    SELECT
        sku_id,
        SUM(on_hand_quantity) AS total_on_hand,
        SUM(reserved_quantity) AS total_reserved,
        SUM(on_hand_quantity - reserved_quantity) AS total_available,
        COUNT(*) AS record_count
    FROM inventory
    GROUP BY sku_id
    ORDER BY sku_id
""")

summary = cursor.fetchall()

print("\nINVENTORY SUMMARY BY SKU")
print("-" * 65)

for row in summary:
    print(
        f"SKU: {row['sku_id']} | "
        f"Records: {row['record_count']} | "
        f"On hand: {row['total_on_hand']} | "
        f"Reserved: {row['total_reserved']} | "
        f"Available: {row['total_available']}"
    )

# Check forecast combinations missing inventory
cursor.execute("""
    SELECT
        f.sku_id,
        f.location_id
    FROM forecast_demand f
    LEFT JOIN inventory i
        ON f.sku_id = i.sku_id
        AND f.location_id = i.location_id
    WHERE i.inventory_id IS NULL
    GROUP BY f.sku_id, f.location_id
""")

missing = cursor.fetchall()

print("\nFORECAST COMBINATIONS WITHOUT INVENTORY")
print("-" * 65)

if missing:
    for row in missing:
        print(
            f"SKU: {row['sku_id']} | "
            f"Location: {row['location_id']}"
        )
else:
    print("All forecast combinations have inventory records.")

print("\nTOTAL INVENTORY RECORDS:", len(inventory_records))
print("MISSING INVENTORY COMBINATIONS:", len(missing))

connection.close()

print("\nINSPECTION COMPLETED")
