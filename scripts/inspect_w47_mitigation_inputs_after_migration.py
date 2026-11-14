
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

tables = [
    "supplier_sku_policy",
    "supplier_sku",
    "lead_time",
    "supplier_capacity",
    "mitigation_option",
    "mitigation_event",
]

print("=" * 85)
print("W47 MITIGATION INPUTS - POST MIGRATION 004")
print("=" * 85)

for table in tables:
    print(f"\nTABLE: {table}")
    print("-" * 85)

    cursor.execute(f'PRAGMA table_info("{table}")')
    columns = [row["name"] for row in cursor.fetchall()]

    print("COLUMNS:", " | ".join(columns))

    if table == "supplier_capacity":
        cursor.execute("""
            SELECT *
            FROM supplier_capacity
            WHERE capacity_week = '2026-W47'
        """)

    elif table == "mitigation_option":
        cursor.execute("""
            SELECT *
            FROM mitigation_option
            ORDER BY option_id
        """)

    elif table == "mitigation_event":
        cursor.execute("""
            SELECT *
            FROM mitigation_event
            ORDER BY mitigation_event_id
        """)

    else:
        cursor.execute(f'SELECT * FROM "{table}"')

    records = cursor.fetchall()

    if records:
        for record in records:
            print(dict(record))
    else:
        print("No records found.")

    print("TOTAL RECORDS:", len(records))

# Verify current W47 shortage records
print("\nW47 SHORTAGE SUMMARY")
print("-" * 85)

cursor.execute("""
    SELECT
        shortage_id,
        sku_id,
        location_id,
        shortage_week,
        shortage_quantity,
        status
    FROM shortage
    WHERE shortage_week = '2026-W47'
    ORDER BY shortage_id
""")

for record in cursor.fetchall():
    print(dict(record))

# Verify database integrity
print("\nDATABASE CHECKS")
print("-" * 85)

cursor.execute("PRAGMA foreign_key_check")
fk_errors = cursor.fetchall()

print("Foreign key check:", "PASS" if not fk_errors else "FAIL")

cursor.execute("PRAGMA integrity_check")
integrity = cursor.fetchone()[0]

print("Integrity check:", integrity)

connection.close()

print("\n" + "=" * 85)
print("INSPECTION COMPLETED - NO DATABASE CHANGES MADE")
print("=" * 85)
