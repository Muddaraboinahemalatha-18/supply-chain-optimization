
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

supplier_capacities = [
    ("SUP001", "SKU001", "2026-W46", 200),
    ("SUP001", "SKU002", "2026-W46", 300),
    ("SUP002", "SKU003", "2026-W46", 150),
    ("SUP002", "SKU004", "2026-W46", 200),
    ("SUP003", "SKU005", "2026-W46", 100)
]

for record in supplier_capacities:
    cursor.execute("""
        INSERT OR IGNORE INTO supplier_capacity
        (supplier_id, sku_id, capacity_week, max_quantity)
        VALUES (?, ?, ?, ?)
    """, record)

connection.commit()
connection.close()

print("Supplier capacity data inserted successfully!")
