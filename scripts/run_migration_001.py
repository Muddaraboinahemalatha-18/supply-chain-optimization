
import sqlite3
import shutil
from pathlib import Path

# Project folders
BASE_DIR = Path(__file__).resolve().parents[1]

DB_PATH = BASE_DIR / "data" / "supply_chain.db"

BACKUP_PATH = BASE_DIR / "data" / "supply_chain_pre_migration_001.db"

MIGRATION_PATH = (
    BASE_DIR / "database" / "migration_001_add_planning_tables.sql"
)

# Tables that must be preserved
EXISTING_TABLES = [
    "sku",
    "location",
    "supplier",
    "sku_location",
    "forecast_demand",
    "inventory",
    "supplier_sku",
    "supplier_capacity",
    "lead_time",
    "purchase_order",
    "purchase_order_line",
    "production_plan",
    "bom",
    "inventory_event",
    "purchase_order_event",
    "shortage",
    "mitigation_option",
    "mitigation_event"
]


def get_row_counts(connection):
    counts = {}

    for table in EXISTING_TABLES:
        result = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()

        counts[table] = result[0]

    return counts


def run_migration():

    # Check required files
    if not DB_PATH.exists():
        print("ERROR: Database file not found.")
        return

    if not MIGRATION_PATH.exists():
        print("ERROR: Migration SQL file not found.")
        return

    # Never overwrite an existing backup
    if BACKUP_PATH.exists():
        print("ERROR: Migration backup already exists.")
        print("No changes were made.")
        return

    # Create a consistent backup using SQLite backup API
    source = sqlite3.connect(DB_PATH)
    backup = sqlite3.connect(BACKUP_PATH)

    try:
        source.backup(backup)
    finally:
        backup.close()
        source.close()

    print("Backup created successfully.")

    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        # Record original row counts
        before_counts = get_row_counts(connection)

        # Read migration SQL
        with open(MIGRATION_PATH, "r", encoding="utf-8") as file:
            migration_sql = file.read()

        # Start transaction and apply migration
        connection.executescript(
            "BEGIN IMMEDIATE;\n" + migration_sql + "\n"
        )

        # Verify foreign-key integrity before committing
        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if foreign_key_errors:
            raise Exception(
                f"Foreign-key errors found: {foreign_key_errors}"
            )

        # Verify existing records
        after_counts = get_row_counts(connection)

        if before_counts != after_counts:
            raise Exception(
                "Existing table row counts changed."
            )

        # Verify all six new tables
        new_tables = [
            "inbound_order",
            "production_capacity",
            "sku_substitute",
            "supplier_sku_policy",
            "data_quality_issue",
            "scenario_ground_truth"
        ]

        for table in new_tables:
            result = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name = ?
                """,
                (table,)
            ).fetchone()

            if result is None:
                raise Exception(
                    f"New table not found: {table}"
                )

        # Commit only after successful checks
        connection.commit()

        print("\nMIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 45)

        print("\nNew tables created:")

        for table in new_tables:
            print("-", table)

        print("\nExisting records preserved:")

        for table, count in after_counts.items():
            print(f"{table}: {count}")

        print("\nForeign-key check: PASSED")
        print("Existing row-count check: PASSED")
        print(f"Backup: {BACKUP_PATH.name}")

    except Exception as error:

        connection.rollback()

        print("\nMIGRATION FAILED")
        print("Changes were rolled back.")
        print("Error:", error)
        print("Backup is preserved.")

    finally:
        connection.close()


if __name__ == "__main__":
    run_migration()
