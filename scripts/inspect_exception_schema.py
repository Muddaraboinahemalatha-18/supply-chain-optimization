
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

tables = [
    "inbound_order",
    "sku_substitute",
    "supplier_capacity",
    "lead_time",
    "data_quality_issue",
    "scenario_ground_truth"
]

connection = get_connection()
cursor = connection.cursor()

try:
    print("=" * 85)
    print("EXCEPTION SCENARIO SCHEMA INSPECTION")
    print("=" * 85)

    for table in tables:
        print(f"\nTABLE: {table}")
        print("-" * 85)

        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()

        if not columns:
            print("WARNING: Table not found or has no columns.")
            continue

        for column in columns:
            print(
                f"Column: {column['name']} | "
                f"Type: {column['type']} | "
                f"Required: {bool(column['notnull'])} | "
                f"Primary Key: {bool(column['pk'])}"
            )

    print("\n" + "=" * 85)
    print("FOREIGN KEY VALIDATION")
    print("=" * 85)

    cursor.execute("PRAGMA foreign_key_check")
    errors = cursor.fetchall()

    if errors:
        print("FAIL: Foreign-key errors found.")
        for error in errors:
            print(tuple(error))
    else:
        print("PASS: No foreign-key errors.")

    cursor.execute("PRAGMA integrity_check")
    result = cursor.fetchone()[0]
    print(f"Database integrity: {result}")

finally:
    connection.close()

print("\nREAD-ONLY INSPECTION COMPLETED.")
