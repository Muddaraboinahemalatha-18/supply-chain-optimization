
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE_DIR = BASE_DIR / "database"

connection = sqlite3.connect(":memory:")
connection.execute("PRAGMA foreign_keys = ON")

try:
    # Load the original database schema.
    schema = (DATABASE_DIR / "schema.sql").read_text(encoding="utf-8")
    connection.executescript(schema)

    # Apply migrations in order.
    for migration_name in [
        "migration_001_add_planning_tables.sql",
        "migration_002_add_shortage_events.sql",
        "migration_003_add_shortage_projections.sql",
    ]:
        migration_path = DATABASE_DIR / migration_name
        migration_sql = migration_path.read_text(encoding="utf-8")
        connection.executescript(migration_sql)
        print(f"PASS: {migration_name}")

    # Confirm both new tables exist.
    tables = {
        row[0]
        for row in connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        )
    }

    required_tables = {
        "shortage_projection",
        "shortage_projection_event",
    }

    assert required_tables.issubset(tables)

    # Check projection table columns.
    projection_columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(shortage_projection)"
        )
    }

    expected_projection_columns = {
        "projection_id",
        "shortage_id",
        "forecast_id",
        "planning_scenario_id",
        "inventory_snapshot_date",
        "projection_date",
        "assumptions",
        "projection_status",
    }

    assert expected_projection_columns.issubset(projection_columns)

    # Check projection event columns.
    event_columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(shortage_projection_event)"
        )
    }

    expected_event_columns = {
        "projection_event_id",
        "projection_id",
        "event_type",
        "event_date",
        "source_ref",
        "reason",
    }

    assert expected_event_columns.issubset(event_columns)

    # Verify foreign-key definitions.
    projection_fks = connection.execute(
        "PRAGMA foreign_key_list(shortage_projection)"
    ).fetchall()

    assert len(projection_fks) == 2

    event_fks = connection.execute(
        "PRAGMA foreign_key_list(shortage_projection_event)"
    ).fetchall()

    assert len(event_fks) == 1

    # Confirm the original shortage-event table remains present.
    assert "shortage_event" in tables

    # Confirm foreign-key integrity.
    fk_errors = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    assert not fk_errors, fk_errors

    # Confirm database integrity.
    integrity = connection.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    assert integrity == "ok", integrity

    print("\nMIGRATION 003 TEST SUMMARY")
    print("----------------------------------------")
    print("Projection table: PASS")
    print("Projection event table: PASS")
    print("Required columns: PASS")
    print("Foreign keys: PASS")
    print("Existing shortage event table: PRESERVED")
    print("Foreign key check: PASS")
    print("Integrity check:", integrity)
    print("\nAll Migration 003 structural tests passed.")

finally:
    connection.close()
