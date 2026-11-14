
import sys
from pathlib import Path

# Add the project root to Python's import path.
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()

try:
    print("=" * 65)
    print("MIGRATION 003 DATABASE VERIFICATION")
    print("=" * 65)

    for table in [
        "shortage_projection",
        "shortage_projection_event",
    ]:
        columns = connection.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()

        count = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(f"\nTABLE: {table}")
        print("-" * 45)

        for column in columns:
            print(
                f"{column['name']} | "
                f"Type: {column['type']} | "
                f"Primary Key: {column['pk']}"
            )

        print("Record count:", count)

    print("\nEXISTING W46 SHORTAGE HISTORY")
    print("-" * 45)

    shortages = connection.execute(
        """
        SELECT shortage_id, shortage_week,
               shortage_quantity, status
        FROM shortage
        ORDER BY shortage_id
        """
    ).fetchall()

    for row in shortages:
        print(dict(row))

    print("\nEXISTING SHORTAGE EVENTS")
    print("-" * 45)

    events = connection.execute(
        """
        SELECT shortage_event_id, shortage_id, event_type,
               resolved_quantity, source_ref
        FROM shortage_event
        ORDER BY shortage_event_id
        """
    ).fetchall()

    for row in events:
        print(dict(row))

    print("\nFOREIGN KEY CHECK")
    fk_errors = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    print("PASS" if not fk_errors else [tuple(r) for r in fk_errors])

    print("\nDATABASE INTEGRITY")
    print(
        connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]
    )

finally:
    connection.close()
