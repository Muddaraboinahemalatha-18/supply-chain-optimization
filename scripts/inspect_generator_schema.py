
import sys
from pathlib import Path

# Add the project root to Python's import path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

tables = cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
      AND name NOT LIKE 'sqlite_%'
    ORDER BY name
""").fetchall()

print("=" * 80)
print("MIGRATED DATABASE SCHEMA INSPECTION")
print("=" * 80)

for table_row in tables:
    table_name = table_row["name"]

    print(f"\nTABLE: {table_name}")
    print("-" * 80)

    columns = cursor.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    for column in columns:
        print(
            f"Column: {column['name']} | "
            f"Type: {column['type']} | "
            f"Not Null: {column['notnull']} | "
            f"Primary Key: {column['pk']} | "
            f"Default: {column['dflt_value']}"
        )

    foreign_keys = cursor.execute(
        f'PRAGMA foreign_key_list("{table_name}")'
    ).fetchall()

    if foreign_keys:
        print("Foreign Keys:")

        for fk in foreign_keys:
            print(
                f"  {fk['from']} -> "
                f"{fk['table']}.{fk['to']}"
            )

connection.close()

print("\n" + "=" * 80)
print("SCHEMA INSPECTION COMPLETED")
print("=" * 80)
