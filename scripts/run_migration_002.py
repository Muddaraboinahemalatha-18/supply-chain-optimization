
import sqlite3
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

DB_PATH = BASE_DIR / "data" / "supply_chain.db"

BACKUP_PATH = (
    BASE_DIR / "data" / "supply_chain_pre_migration_002.db"
)

MIGRATION_PATH = (
    BASE_DIR / "database" / "migration_002_add_shortage_events.sql"
)

print("=" * 70)
print("DATABASE MIGRATION 002")
print("=" * 70)

# Check required files
if not DB_PATH.exists():
    raise FileNotFoundError("Database file not found.")

if not MIGRATION_PATH.exists():
    raise FileNotFoundError("Migration SQL file not found.")

# Prevent accidental backup overwrite
if BACKUP_PATH.exists():
    raise FileExistsError(
        "Migration backup already exists. "
        "Do not overwrite it. Inspect the database first."
    )

# Connect to database
connection = sqlite3.connect(DB_PATH)
connection.execute("PRAGMA foreign_keys = ON")

try:
    cursor = connection.cursor()

    # Check whether migration has already been applied
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'shortage_event'
    """)

    if cursor.fetchone():
        raise RuntimeError(
            "shortage_event already exists. Migration not applied."
        )

    # Check original table counts
    original_tables = [
        "sku", "location", "supplier", "sku_location",
        "forecast_demand", "inventory", "supplier_sku",
        "supplier_capacity", "lead_time", "purchase_order",
        "purchase_order_line", "production_plan", "bom",
        "inventory_event", "purchase_order_event", "shortage",
        "mitigation_option", "mitigation_event",
        "inbound_order", "production_capacity", "sku_substitute",
        "supplier_sku_policy", "data_quality_issue",
        "scenario_ground_truth"
    ]

    before_counts = {}

    for table in original_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        before_counts[table] = cursor.fetchone()[0]

    # Create backup
    connection.close()
    shutil.copy2(DB_PATH, BACKUP_PATH)

    print("\nBackup created:")
    print(BACKUP_PATH)

    # Reconnect and apply migration
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    with open(MIGRATION_PATH, "r", encoding="utf-8") as file:
        migration_sql = file.read()

    connection.executescript(migration_sql)
    connection.commit()

    print("\nMigration SQL executed successfully.")

    cursor = connection.cursor()

    # Verify new table
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'shortage_event'
    """)

    if not cursor.fetchone():
        raise RuntimeError("New table verification failed.")

    print("shortage_event table: EXISTS")

    # Verify original record counts
    print("\nORIGINAL TABLE COUNT VERIFICATION")
    print("-" * 55)

    for table, old_count in before_counts.items():
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        new_count = cursor.fetchone()[0]

        print(
            f"{table}: Before={old_count}, After={new_count}"
        )

        if old_count != new_count:
            raise RuntimeError(
                f"Record count changed in table: {table}"
            )

    # Verify database integrity
    cursor.execute("PRAGMA integrity_check")
    integrity = cursor.fetchone()[0]

    print("\nIntegrity check:", integrity)

    if integrity != "ok":
        raise RuntimeError("Database integrity check failed.")

    # Verify foreign keys
    cursor.execute("PRAGMA foreign_key_check")
    foreign_errors = cursor.fetchall()

    if foreign_errors:
        raise RuntimeError(
            f"Foreign key errors found: {foreign_errors}"
        )

    print("Foreign key check: PASSED")

    connection.commit()

    print("\nMIGRATION 002 COMPLETED SUCCESSFULLY")

except Exception:
    connection.rollback()
    raise

finally:
    connection.close()
