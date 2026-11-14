
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "supply_chain.db"

TABLES = [
    "supplier_sku",
    "lead_time",
    "supplier_sku_policy",
    "supplier_capacity",
    "production_capacity",
    "production_plan",
    "bom",
    "inbound_order"
]

connection = sqlite3.connect(DB_PATH)

print("PLANNING TABLE STRUCTURE")
print("=" * 50)

try:
    for table in TABLES:
        print(f"\nTable: {table}")
        print("-" * 40)

        columns = connection.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()

        for column in columns:
            print(
                f"Column: {column[1]} | "
                f"Type: {column[2]} | "
                f"Required: {'Yes' if column[3] else 'No'} | "
                f"Primary Key: {'Yes' if column[5] else 'No'}"
            )

finally:
    connection.close()
