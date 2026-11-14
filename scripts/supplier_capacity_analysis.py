
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("SUPPLIER CAPACITY ANALYSIS")
print("=" * 50)

query = """
SELECT
    s.sku_name,
    sc.capacity_week,
    sc.maximum_quantity
FROM supplier_capacity sc
JOIN sku s ON sc.sku_id = s.sku_id
WHERE sc.capacity_week = '2026-W46'
ORDER BY s.sku_name
"""

cursor.execute(query)
records = cursor.fetchall()

for record in records:
    print(f"Product: {record['sku_name']}")
    print(f"Week: {record['capacity_week']}")
    print(f"Maximum Quantity: {record['maximum_quantity']}")
    print("-" * 40)

connection.close()
