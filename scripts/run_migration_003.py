
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "supply_chain.db"
BACKUP_PATH = BASE_DIR / "data" / "supply_chain_pre_migration_003.db"
MIGRATION_PATH = (
    BASE_DIR / "database" / "migration_003_add_shortage_projections.sql"
)

NEW_TABLES = {
    "shortage_projection",
    "shortage_projection_event",
}


def get_table_names(connection):
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()

    return {row[0] for row in rows}


def get_table_counts(connection, table_names):
    counts = {}

    for table_name in sorted(table_names):
        # Table names come from sqlite_master, not user input.
        counts[table_name] = connection.execute(
            f'SELECT COUNT(*) FROM "{table_name}"'
        ).fetchone()[0]

    return counts


def main():
    print("=" * 65)
    print("MIGRATION 003 - SHORTAGE PROJECTION TABLES")
    print("=" * 65)

    # Safety checks.
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    if not MIGRATION_PATH.exists():
        raise FileNotFoundError(
            f"Migration SQL not found: {MIGRATION_PATH}"
        )

    if BACKUP_PATH.exists():
        raise FileExistsError(
            "Backup already exists. Migration stopped to protect it:\n"
            f"{BACKUP_PATH}"
        )

    migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")

    source = sqlite3.connect(DB_PATH)
    source.execute("PRAGMA foreign_keys = ON")

    try:
        existing_tables = get_table_names(source)

        if NEW_TABLES.intersection(existing_tables):
            raise RuntimeError(
                "One or both Migration 003 tables already exist. "
                "No migration was applied."
            )

        # Save original table counts and W46 history.
        original_counts = get_table_counts(
            source, existing_tables
        )

        original_shortages = source.execute(
            """
            SELECT *
            FROM shortage
            ORDER BY shortage_id
            """
        ).fetchall()

        original_events = source.execute(
            """
            SELECT *
            FROM shortage_event
            ORDER BY shortage_event_id
            """
        ).fetchall()

        # Create a separate backup without overwriting anything.
        backup = sqlite3.connect(BACKUP_PATH)

        try:
            source.backup(backup)
            backup_integrity = backup.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
        finally:
            backup.close()

        if backup_integrity != "ok":
            raise RuntimeError(
                f"Backup integrity check failed: {backup_integrity}"
            )

        print("\nBackup created:")
        print(BACKUP_PATH.name)
        print("Backup integrity:", backup_integrity)

        # Begin the migration transaction.
        source.executescript(
            "BEGIN IMMEDIATE;\n" + migration_sql
        )

        updated_tables = get_table_names(source)

        if not NEW_TABLES.issubset(updated_tables):
            raise RuntimeError(
                "Required projection tables were not created."
            )

        # Confirm all original table counts are unchanged.
        updated_counts = get_table_counts(
            source, existing_tables
        )

        if original_counts != updated_counts:
            raise RuntimeError(
                "An existing table count changed."
            )

        # Confirm historical shortage records are unchanged.
        updated_shortages = source.execute(
            """
            SELECT *
            FROM shortage
            ORDER BY shortage_id
            """
        ).fetchall()

        if original_shortages != updated_shortages:
            raise RuntimeError(
                "Existing shortage records changed."
            )

        # Confirm actual shortage events are unchanged.
        updated_events = source.execute(
            """
            SELECT *
            FROM shortage_event
            ORDER BY shortage_event_id
            """
        ).fetchall()

        if original_events != updated_events:
            raise RuntimeError(
                "Existing shortage events changed."
            )

        # Verify foreign keys before committing.
        fk_errors = source.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if fk_errors:
            raise RuntimeError(
                f"Foreign-key errors found: {fk_errors}"
            )

        source.commit()

        # Final database integrity check.
        integrity = source.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise RuntimeError(
                f"Database integrity check failed: {integrity}"
            )

        print("\nMIGRATION 003 SUCCESSFUL")
        print("-" * 45)
        print("New table: shortage_projection")
        print("New table: shortage_projection_event")
        print("Original table counts: PRESERVED")
        print("Historical shortage records: PRESERVED")
        print("Historical shortage events: PRESERVED")
        print("Foreign-key check: PASS")
        print("Integrity check:", integrity)
        print("Business records inserted: 0")
        print("\nMigration completed successfully.")

    except Exception:
        if source.in_transaction:
            source.rollback()

        print("\nMIGRATION FAILED.")
        print("Any uncommitted migration changes were rolled back.")
        print("The backup, if already created, has been preserved.")
        raise

    finally:
        source.close()


if __name__ == "__main__":
    main()
