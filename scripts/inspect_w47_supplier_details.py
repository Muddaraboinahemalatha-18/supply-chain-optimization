
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 85)
print("W47 SUPPLIER AND PURCHASE ORDER INSPECTION")
print("=" * 85)

# 1. Supplier details
print("\n1. SUPPLIERS")

cursor.execute("""
    SELECT supplier_id, supplier_name, supplier_type,
           reliability_score, is_active
    FROM supplier
    ORDER BY supplier_id
""")

for row in cursor.fetchall():
    print(dict(row))

# 2. Approved supplier-SKU relationships
print("\n2. SUPPLIER SKU APPROVAL")

cursor.execute("""
    SELECT ss.supplier_id, s.supplier_name,
           ss.sku_id, k.sku_name,
           ss.is_approved, ss.unit_cost
    FROM supplier_sku ss
    JOIN supplier s ON ss.supplier_id = s.supplier_id
    JOIN sku k ON ss.sku_id = k.sku_id
    ORDER BY ss.supplier_id, ss.sku_id
""")

for row in cursor.fetchall():
    print(dict(row))

# 3. Existing purchase orders
print("\n3. PURCHASE ORDERS")

cursor.execute("""
    SELECT *
    FROM purchase_order
    ORDER BY po_id
""")

for row in cursor.fetchall():
    print(dict(row))

# 4. Existing purchase order lines
print("\n4. PURCHASE ORDER LINES")

cursor.execute("""
    SELECT *
    FROM purchase_order_line
    ORDER BY po_line_id
""")

for row in cursor.fetchall():
    print(dict(row))

# 5. Existing inbound orders
print("\n5. INBOUND ORDERS")

cursor.execute("""
    SELECT *
    FROM inbound_order
    ORDER BY inbound_id
""")

for row in cursor.fetchall():
    print(dict(row))

# 6. Supplier capacity by week
print("\n6. SUPPLIER CAPACITY BY WEEK")

cursor.execute("""
    SELECT capacity_week, COUNT(*) AS record_count,
           SUM(maximum_quantity) AS total_capacity
    FROM supplier_capacity
    GROUP BY capacity_week
    ORDER BY capacity_week
""")

for row in cursor.fetchall():
    print(dict(row))

print("\n" + "=" * 85)
print("INSPECTION COMPLETED")
print("No database records were modified.")
print("=" * 85)

connection.close()
