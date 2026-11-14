
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

tables = [
    "supplier_capacity",
    "supplier_sku_policy",
    "sku_substitute",
    "production_capacity",
    "lead_time"
]

print("=" * 85)
print("W47 MITIGATION INPUT INSPECTION")
print("=" * 85)

for table in tables:

    print("\n" + "-" * 85)
    print("TABLE:", table)
    print("-" * 85)

    # Read actual table columns
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()

    print("\nCOLUMNS:")
    for column in columns:
        print(
            f"{column['name']} | "
            f"Type: {column['type']} | "
            f"Required: {bool(column['notnull'])} | "
            f"Primary Key: {bool(column['pk'])}"
        )

    # Read all records without assuming column names
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()

    print("\nTOTAL RECORDS:", len(rows))
    print("\nRECORD DETAILS:")

    if not rows:
        print("No records found.")

    for row in rows:
        print(dict(row))

    # Specifically report W47 capacity availability
    if table == "supplier_capacity":
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM supplier_capacity
            WHERE capacity_week = '2026-W47'
        """)
        count = cursor.fetchone()["total"]

        print("\nW47 CAPACITY RECORD COUNT:", count)

print("\n" + "=" * 85)
print("INSPECTION COMPLETED")
print("No database records were modified.")
print("=" * 85)

connection.close()
