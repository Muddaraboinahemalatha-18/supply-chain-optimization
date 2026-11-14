
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()

try:
    print("=" * 75)
    print("W47 SHORTAGE PROJECTION VERIFICATION")
    print("=" * 75)

    rows = connection.execute(
        """
        SELECT
            s.shortage_id,
            s.sku_id,
            sku.sku_name,
            s.location_id,
            s.shortage_week,
            s.demand_quantity,
            s.available_quantity,
            s.shortage_quantity,
            s.status,
            p.projection_id,
            p.forecast_id,
            p.planning_scenario_id,
            p.inventory_snapshot_date,
            p.projection_date,
            p.projection_status,
            e.projection_event_id,
            e.event_type,
            e.event_date
        FROM shortage s
        JOIN sku
            ON sku.sku_id = s.sku_id
        JOIN shortage_projection p
            ON p.shortage_id = s.shortage_id
        JOIN shortage_projection_event e
            ON e.projection_id = p.projection_id
        WHERE s.shortage_week = '2026-W47'
        ORDER BY s.shortage_id
        """
    ).fetchall()

    print("\nW47 PROJECTION RECORDS")
    print("-" * 75)

    for row in rows:
        print(dict(row))

    print("\nRECORD COUNTS")
    print("-" * 75)

    for table in [
        "shortage",
        "shortage_projection",
        "shortage_projection_event",
    ]:
        if table == "shortage":
            count = connection.execute(
                """
                SELECT COUNT(*)
                FROM shortage
                WHERE shortage_week = '2026-W47'
                """
            ).fetchone()[0]
        else:
            count = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

        print(f"{table}: {count}")

    print("\nW46 HISTORICAL SHORTAGES")
    print("-" * 75)

    historical = connection.execute(
        """
        SELECT shortage_id, shortage_week,
               shortage_quantity, status
        FROM shortage
        WHERE shortage_week = '2026-W46'
        ORDER BY shortage_id
        """
    ).fetchall()

    for row in historical:
        print(dict(row))

    print("\nACTUAL SHORTAGE EVENTS")
    print("-" * 75)

    actual_events = connection.execute(
        """
        SELECT shortage_event_id, shortage_id,
               event_type, resolved_quantity
        FROM shortage_event
        ORDER BY shortage_event_id
        """
    ).fetchall()

    for row in actual_events:
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

    if len(rows) != 3:
        raise RuntimeError("Expected exactly three W47 projection rows.")

    if any(
        row["status"] != "PROJECTED"
        or row["projection_status"] != "PROJECTED"
        or row["event_type"] != "PROJECTION_CREATED"
        for row in rows
    ):
        raise RuntimeError("Unexpected W47 projection lifecycle status.")

    if len(historical) != 3 or len(actual_events) != 3:
        raise RuntimeError("Historical W46 record count mismatch.")

    if fk_errors:
        raise RuntimeError("Foreign-key validation failed.")

    print("\nFINAL RESULT: ALL VERIFICATION CHECKS PASSED")

finally:
    connection.close()
