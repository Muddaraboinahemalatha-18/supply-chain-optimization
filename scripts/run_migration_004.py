
import sqlite3
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

DB_PATH = BASE_DIR / "data" / "supply_chain.db"
BACKUP_PATH = BASE_DIR / "data" / "supply_chain_pre_migration_004.db"
MIGRATION_PATH = (
    BASE_DIR / "database" /
    "migration_004_enhance_mitigation_options.sql"
)

print("=" * 80)
print("MIGRATION 004 - ACTUAL DATABASE")
print("=" * 80)

if not DB_PATH.exists():
    raise FileNotFoundError("Project database not found.")

if not MIGRATION_PATH.exists():
    raise FileNotFoundError("Migration SQL file not found.")

if BACKUP_PATH.exists():
    raise FileExistsError(
        f"Backup already exists: {BACKUP_PATH}\n"
        "No files were overwritten. Inspect the existing backup first."
    )

connection = sqlite3.connect(DB_PATH)
connection.row_factory = sqlite3.Row
connection.execute("PRAGMA foreign_keys = ON")

try:
    cursor = connection.cursor()

    # 1. Check database before migration
    cursor.execute("PRAGMA integrity_check")
    integrity = cursor.fetchone()[0]

    if integrity != "ok":
        raise RuntimeError(
            f"Database integrity failed before migration: {integrity}"
        )

    cursor.execute("PRAGMA foreign_key_check")
    if cursor.fetchall():
        raise RuntimeError("Foreign key errors exist before migration.")

    print("\nPASS: Existing database integrity check.")

    # 2. Capture all existing table counts
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)

    table_names = [row["name"] for row in cursor.fetchall()]

    original_counts = {}

    for table in table_names:
        cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
        original_counts[table] = cursor.fetchone()[0]

    # 3. Capture historical mitigation records
    cursor.execute("""
        SELECT
            option_id,
            shortage_id,
            option_type,
            description,
            proposed_quantity,
            estimated_cost,
            policy_compliant
        FROM mitigation_option
        ORDER BY option_id
    """)

    original_options = [
        tuple(row) for row in cursor.fetchall()
    ]

    # 4. Create a separate backup
    backup_connection = sqlite3.connect(BACKUP_PATH)

    try:
        connection.backup(backup_connection)
    finally:
        backup_connection.close()

    print(f"PASS: Backup created: {BACKUP_PATH.name}")

    # 5. Apply migration inside a transaction
    migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")

    cursor.executescript(
        "BEGIN IMMEDIATE;\n" + migration_sql
    )

    print("PASS: Migration SQL executed.")

    # 6. Verify all new columns
    cursor.execute("PRAGMA table_info(mitigation_option)")
    columns = {row["name"] for row in cursor.fetchall()}

    expected_columns = {
        "supplier_id",
        "unit_of_measure",
        "minimum_order_quantity",
        "unit_cost",
        "capacity_quantity",
        "capacity_source",
        "capacity_scenario_id",
        "lead_time_days",
        "planned_order_date",
        "expected_arrival_date",
        "feasibility_status",
    }

    missing = expected_columns - columns

    if missing:
        raise RuntimeError(
            f"Missing columns: {sorted(missing)}"
        )

    print("PASS: All 11 new columns exist.")

    # 7. Verify historical mitigation values
    cursor.execute("""
        SELECT
            option_id,
            shortage_id,
            option_type,
            description,
            proposed_quantity,
            estimated_cost,
            policy_compliant
        FROM mitigation_option
        ORDER BY option_id
    """)

    current_options = [
        tuple(row) for row in cursor.fetchall()
    ]

    if current_options != original_options:
        raise RuntimeError(
            "Historical mitigation records changed."
        )

    print("PASS: Historical mitigation records preserved.")

    # 8. Verify every original table count
    for table, original_count in original_counts.items():
        cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
        current_count = cursor.fetchone()[0]

        if current_count != original_count:
            raise RuntimeError(
                f"Table count changed: {table} "
                f"({original_count} -> {current_count})"
            )

    print("PASS: All existing table counts preserved.")

    # 9. Verify indexes
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'index'
          AND name IN (
              'idx_mitigation_option_supplier',
              'idx_mitigation_option_feasibility'
          )
    """)

    indexes = {row["name"] for row in cursor.fetchall()}

    if len(indexes) != 2:
        raise RuntimeError("Expected migration indexes are missing.")

    print("PASS: Both new indexes exist.")

    # 10. Verify foreign keys
    cursor.execute("PRAGMA foreign_key_check")

    if cursor.fetchall():
        raise RuntimeError("Foreign key violations detected.")

    print("PASS: Foreign key check.")

    # 11. Verify database integrity
    cursor.execute("PRAGMA integrity_check")
    integrity = cursor.fetchone()[0]

    if integrity != "ok":
        raise RuntimeError(
            f"Database integrity failed: {integrity}"
        )

    print("PASS: Database integrity check.")

    # Commit only after every verification succeeds
    connection.commit()

    print("\n" + "=" * 80)
    print("MIGRATION 004 APPLIED SUCCESSFULLY")
    print("Historical records preserved.")
    print("Existing table counts preserved.")
    print("Backup retained.")
    print("=" * 80)

except Exception as error:
    connection.rollback()

    print("\nMIGRATION 004 FAILED")
    print("Transaction rolled back.")
    print("Backup, if created, has been retained.")
    print("Error:", error)

    raise

finally:
    connection.close()
