
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "supply_chain.db"

TABLES = [
    "inventory_event",
    "purchase_order_event"
]

connection = sqlite3.connect(DB_PATH)

print("EXISTING RECEIPT EVENT INSPECTION")
print("=" * 50)

try:
    cursor = connection.cursor()

    for table in TABLES:

        print(f"\nTABLE: {table}")
        print("-" * 50)

        columns = cursor.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()

        column_names = [column[1] for column in columns]

        print("Columns:", column_names)

        records = cursor.execute(
            f"SELECT * FROM {table}"
        ).fetchall()

        if not records:
            print("No records found.")
        else:
            for record in records:
                for name, value in zip(column_names, record):
                    print(f"{name}: {value}")
                print("-" * 30)

            print("Total records:", len(records))

finally:
    connection.close()
