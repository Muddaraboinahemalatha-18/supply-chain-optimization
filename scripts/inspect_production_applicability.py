
import sys
from pathlib import Path

# Add the project root folder to Python's import path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 75)
print("PRODUCTION AND BOM APPLICABILITY INSPECTION")
print("=" * 75)

tables = [
    "sku",
    "sku_location",
    "production_capacity",
    "production_plan",
    "bom",
    "sku_substitute"
]

for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]

    print(f"\nTABLE: {table}")
    print("-" * 50)
    print("Record count:", count)

    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()

    print("Columns:")
    for column in columns:
        print(f"  {column[1]} ({column[2]})")

    if count > 0:
        cursor.execute(f"SELECT * FROM {table} LIMIT 10")
        records = cursor.fetchall()

        print("Sample records:")
        for record in records:
            print(" ", dict(record))

connection.close()

print("\nInspection completed. No database records were modified.")
