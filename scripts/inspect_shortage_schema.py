
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

tables = [
    "shortage",
    "mitigation_event",
    "inventory_event",
    "purchase_order_event"
]

for table in tables:
    print("\n" + "=" * 65)
    print("TABLE:", table)
    print("=" * 65)

    cursor.execute(f"PRAGMA table_info({table})")

    for column in cursor.fetchall():
        print(
            f"Column: {column['name']} | "
            f"Type: {column['type']} | "
            f"Not Null: {column['notnull']} | "
            f"Primary Key: {column['pk']}"
        )

connection.close()

print("\nSCHEMA INSPECTION COMPLETED")
