
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

DB_PATH = BASE_DIR / "data" / "supply_chain.db"

MIGRATION_PATH = (
    BASE_DIR / "database" / "migration_001_add_planning_tables.sql"
)

NEW_TABLES = [
    "inbound_order",
    "production_capacity",
    "sku_substitute",
    "supplier_sku_policy",
    "data_quality_issue",
    "scenario_ground_truth"
]


def test_migration():

    if not DB_PATH.exists():
        print("ERROR: Database not found.")
        return

    if not MIGRATION_PATH.exists():
        print("ERROR: Migration SQL file not found.")
        return

    # Create a temporary in-memory database
    source = sqlite3.connect(DB_PATH)
    temporary_db = sqlite3.connect(":memory:")

    try:
        # Copy the existing database into memory
        source.backup(temporary_db)

        print("Temporary database created.")

        # Read migration SQL
        with open(MIGRATION_PATH, "r", encoding="utf-8") as file:
            migration_sql = file.read()

        # Test migration inside a transaction
        temporary_db.execute("PRAGMA foreign_keys = ON")

        temporary_db.executescript(
            "BEGIN IMMEDIATE;\n" + migration_sql + "\n"
        )

        # Check new tables
        for table in NEW_TABLES:

            result = temporary_db.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name = ?
                """,
                (table,)
            ).fetchone()

            if result is None:
                raise Exception(f"Missing table: {table}")

            print(f"PASSED: {table}")

        # Check foreign-key integrity
        errors = temporary_db.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if errors:
            raise Exception(f"Foreign-key errors: {errors}")

        # Roll back the temporary migration
        temporary_db.rollback()

        print("\nMIGRATION TEST PASSED")
        print("All six tables were created in the temporary database.")
        print("Foreign-key check passed.")
        print("Actual database was not modified.")

    except Exception as error:

        temporary_db.rollback()

        print("\nMIGRATION TEST FAILED")
        print("Error:", error)

    finally:
        temporary_db.close()
        source.close()


if __name__ == "__main__":
    test_migration()
