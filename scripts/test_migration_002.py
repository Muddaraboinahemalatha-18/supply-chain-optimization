
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
MIGRATION_PATH = (
    BASE_DIR / "database" / "migration_002_add_shortage_events.sql"
)

# Create a temporary in-memory database
connection = sqlite3.connect(":memory:")
connection.execute("PRAGMA foreign_keys = ON")

print("=" * 70)
print("MIGRATION 002 TEST")
print("=" * 70)

# Load original database schema
with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
    schema = file.read()

connection.executescript(schema)

print("\nOriginal schema loaded successfully.")

# Execute migration on temporary database
with open(MIGRATION_PATH, "r", encoding="utf-8") as file:
    migration = file.read()

connection.executescript(migration)

print("Migration 002 executed successfully.")

# Verify table
cursor = connection.cursor()

cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
      AND name = 'shortage_event'
""")

table = cursor.fetchone()

if table:
    print("\nshortage_event table: EXISTS")
else:
    print("\nshortage_event table: MISSING")

# Inspect columns
cursor.execute("PRAGMA table_info(shortage_event)")

print("\nSHORTAGE EVENT COLUMNS")
print("-" * 50)

for column in cursor.fetchall():
    print(
        f"Name: {column[1]} | "
        f"Type: {column[2]} | "
        f"Primary Key: {column[5]}"
    )

# Verify foreign keys
cursor.execute("PRAGMA foreign_key_list(shortage_event)")

print("\nFOREIGN KEY VERIFICATION")
print("-" * 50)

for foreign_key in cursor.fetchall():
    print(
        f"Column: {foreign_key[3]} | "
        f"References: {foreign_key[2]}.{foreign_key[4]}"
    )

# Verify database integrity
cursor.execute("PRAGMA integrity_check")
print("\nIntegrity check:", cursor.fetchone()[0])

cursor.execute("PRAGMA foreign_key_check")
foreign_key_errors = cursor.fetchall()

if not foreign_key_errors:
    print("Foreign key check: PASSED")
else:
    print("Foreign key check: FAILED")
    print(foreign_key_errors)

connection.close()

print("\nMIGRATION 002 TEST COMPLETED")
