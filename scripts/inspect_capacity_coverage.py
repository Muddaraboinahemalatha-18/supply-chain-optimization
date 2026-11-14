
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 65)
print("SUPPLIER CAPACITY COVERAGE INSPECTION")
print("=" * 65)

# Show capacity records grouped by week
cursor.execute("""
    SELECT
        capacity_week,
        COUNT(*) AS total_records,
        SUM(maximum_quantity) AS total_capacity
    FROM supplier_capacity
    GROUP BY capacity_week
    ORDER BY capacity_week
""")

weekly_records = cursor.fetchall()

print("\nWEEKLY CAPACITY SUMMARY")
print("-" * 65)

if weekly_records:
    for row in weekly_records:
        print(
            f"Week: {row['capacity_week']} | "
            f"Records: {row['total_records']} | "
            f"Total capacity: {row['total_capacity']}"
        )
else:
    print("No supplier capacity records found.")

# Show individual supplier capacity records
cursor.execute("""
    SELECT
        sc.capacity_id,
        sc.supplier_id,
        s.supplier_name,
        sc.sku_id,
        sk.sku_name,
        sc.capacity_week,
        sc.maximum_quantity,
        sk.unit_of_measure
    FROM supplier_capacity sc
    JOIN supplier s
        ON sc.supplier_id = s.supplier_id
    JOIN sku sk
        ON sc.sku_id = sk.sku_id
    ORDER BY sc.capacity_week, sc.supplier_id, sc.sku_id
""")

records = cursor.fetchall()

print("\nINDIVIDUAL CAPACITY RECORDS")
print("-" * 65)

for row in records:
    print(
        f"{row['capacity_id']} | "
        f"{row['supplier_name']} | "
        f"{row['sku_name']} | "
        f"Week: {row['capacity_week']} | "
        f"Capacity: {row['maximum_quantity']} "
        f"{row['unit_of_measure']}"
    )

print("\nTOTAL CAPACITY RECORDS:", len(records))

# Check approved supplier-SKU relationships
cursor.execute("""
    SELECT
        sku_id,
        COUNT(*) AS approved_supplier_count
    FROM supplier_sku
    WHERE is_approved = 1
    GROUP BY sku_id
    ORDER BY sku_id
""")

approved_records = cursor.fetchall()

print("\nAPPROVED SUPPLIERS PER SKU")
print("-" * 65)

for row in approved_records:
    print(
        f"SKU: {row['sku_id']} | "
        f"Approved suppliers: {row['approved_supplier_count']}"
    )

connection.close()

print("\nINSPECTION COMPLETED")
