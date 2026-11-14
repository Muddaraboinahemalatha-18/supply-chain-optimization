
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

DB_SCHEMA = BASE_DIR / "database" / "schema.sql"

MIGRATIONS = [
    BASE_DIR / "database" / "migration_001_add_planning_tables.sql",
    BASE_DIR / "database" / "migration_002_add_shortage_events.sql",
    BASE_DIR / "database" / "migration_003_add_shortage_projections.sql",
    BASE_DIR / "database" / "migration_004_enhance_mitigation_options.sql",
]

connection = sqlite3.connect(":memory:")
connection.row_factory = sqlite3.Row
connection.execute("PRAGMA foreign_keys = ON")

cursor = connection.cursor()

print("=" * 80)
print("MIGRATION 004 TEST")
print("=" * 80)

try:
    # 1. Create original database schema
    cursor.executescript(DB_SCHEMA.read_text(encoding="utf-8"))
    print("\nPASS: Original database schema created.")

    # 2. Apply migrations 001, 002 and 003
    for migration_path in MIGRATIONS[:3]:
        cursor.executescript(
            migration_path.read_text(encoding="utf-8")
        )
        print(f"PASS: {migration_path.name} applied.")

    # 3. Insert temporary parent records
    cursor.execute("""
        INSERT INTO sku (
            sku_id, sku_name, unit_of_measure
        )
        VALUES ('SKU-TEST', 'Test Product', 'Kg')
    """)

    cursor.execute("""
        INSERT INTO location (
            location_id, location_name
        )
        VALUES ('LOC-TEST', 'Test Location')
    """)

    cursor.execute("""
        INSERT INTO supplier (
            supplier_id, supplier_name
        )
        VALUES ('SUP-TEST', 'Test Supplier')
    """)

    # 4. Insert a historical shortage and mitigation option
    cursor.execute("""
        INSERT INTO shortage (
            shortage_id,
            sku_id,
            location_id,
            shortage_week,
            demand_quantity,
            available_quantity,
            shortage_quantity,
            priority,
            status
        )
        VALUES (
            'SH-TEST',
            'SKU-TEST',
            'LOC-TEST',
            '2026-W46',
            100,
            80,
            20,
            'HIGH',
            'RESOLVED'
        )
    """)

    cursor.execute("""
        INSERT INTO mitigation_option (
            option_id,
            shortage_id,
            option_type,
            description,
            proposed_quantity,
            estimated_cost,
            policy_compliant
        )
        VALUES (
            'OPT-TEST',
            'SH-TEST',
            'PURCHASE',
            'Historical test option',
            20,
            1000,
            1
        )
    """)

    connection.commit()
    print("\nPASS: Temporary historical mitigation record created.")

    # 5. Apply Migration 004
    migration_004 = MIGRATIONS[3]

    cursor.executescript(
        migration_004.read_text(encoding="utf-8")
    )

    print("PASS: Migration 004 applied.")

    # 6. Verify new columns
    cursor.execute("PRAGMA table_info(mitigation_option)")
    columns = {
        row["name"] for row in cursor.fetchall()
    }

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

    missing_columns = expected_columns - columns

    if missing_columns:
        raise AssertionError(
            f"Missing columns: {sorted(missing_columns)}"
        )

    print(
        f"PASS: All {len(expected_columns)} new columns exist."
    )

    # 7. Verify historical record was preserved
    cursor.execute("""
        SELECT *
        FROM mitigation_option
        WHERE option_id = 'OPT-TEST'
    """)

    historical = cursor.fetchone()

    assert historical is not None
    assert historical["shortage_id"] == "SH-TEST"
    assert historical["proposed_quantity"] == 20
    assert historical["estimated_cost"] == 1000
    assert historical["policy_compliant"] == 1
    assert historical["supplier_id"] is None

    print("PASS: Historical mitigation values preserved.")

    # 8. Verify supplier foreign key
    cursor.execute("""
        UPDATE mitigation_option
        SET supplier_id = 'SUP-TEST'
        WHERE option_id = 'OPT-TEST'
    """)

    print("PASS: Valid supplier foreign key accepted.")

    try:
        cursor.execute("""
            UPDATE mitigation_option
            SET supplier_id = 'SUP-INVALID'
            WHERE option_id = 'OPT-TEST'
        """)

        raise AssertionError(
            "Invalid supplier ID was unexpectedly accepted."
        )

    except sqlite3.IntegrityError:
        print("PASS: Invalid supplier foreign key rejected.")

    # 9. Verify capacity source constraint
    try:
        cursor.execute("""
            UPDATE mitigation_option
            SET capacity_source = 'INVALID'
            WHERE option_id = 'OPT-TEST'
        """)

        raise AssertionError(
            "Invalid capacity source was unexpectedly accepted."
        )

    except sqlite3.IntegrityError:
        print("PASS: Invalid capacity source rejected.")

    # 10. Verify feasibility status constraint
    try:
        cursor.execute("""
            UPDATE mitigation_option
            SET feasibility_status = 'INVALID'
            WHERE option_id = 'OPT-TEST'
        """)

        raise AssertionError(
            "Invalid feasibility status was unexpectedly accepted."
        )

    except sqlite3.IntegrityError:
        print("PASS: Invalid feasibility status rejected.")

    # 11. Verify indexes
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

    assert len(indexes) == 2

    print("PASS: Both mitigation indexes exist.")

    # 12. Verify foreign keys and database integrity
    cursor.execute("PRAGMA foreign_key_check")
    fk_errors = cursor.fetchall()

    assert not fk_errors, f"Foreign key errors: {fk_errors}"

    cursor.execute("PRAGMA integrity_check")
    integrity = cursor.fetchone()[0]

    assert integrity == "ok", integrity

    print("PASS: Foreign key check.")
    print("PASS: Database integrity check.")

    print("\n" + "=" * 80)
    print("MIGRATION 004 TEST PASSED")
    print("All tests completed using a temporary in-memory database.")
    print("The actual project database was not modified.")
    print("=" * 80)

except Exception as error:
    print("\nMIGRATION 004 TEST FAILED")
    print("Error:", error)
    raise

finally:
    connection.close()
