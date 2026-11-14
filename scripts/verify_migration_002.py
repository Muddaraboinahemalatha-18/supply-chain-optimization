
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 70)
print("MIGRATION 002 VERIFICATION")
print("=" * 70)

# Check table existence
cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
      AND name = 'shortage_event'
""")

table = cursor.fetchone()

if table:
    print("\nshortage_event: EXISTS")
else:
    print("\nshortage_event: MISSING")

# Check columns
cursor.execute("PRAGMA table_info(shortage_event)")

print("\nTABLE COLUMNS")
print("-" * 50)

for column in cursor.fetchall():
    print(
        f"{column['name']} | "
        f"{column['type']} | "
        f"Primary Key: {column['pk']}"
    )

# Check existing shortage records
cursor.execute("""
    SELECT shortage_id, shortage_quantity, status
    FROM shortage
    ORDER BY shortage_id
""")

print("\nEXISTING SHORTAGES")
print("-" * 50)

for row in cursor.fetchall():
    print(
        row["shortage_id"],
        "| Quantity:", row["shortage_quantity"],
        "| Status:", row["status"]
    )

# Check event records
cursor.execute("SELECT COUNT(*) FROM shortage_event")

print("\nExisting shortage events:", cursor.fetchone()[0])

# Integrity check
cursor.execute("PRAGMA integrity_check")
print("Integrity check:", cursor.fetchone()[0])

# Foreign key check
cursor.execute("PRAGMA foreign_key_check")

if not cursor.fetchall():
    print("Foreign key check: PASSED")
else:
    print("Foreign key check: FAILED")

connection.close()

print("\nVERIFICATION COMPLETED")
