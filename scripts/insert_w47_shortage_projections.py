
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

PLANNING_WEEK = "2026-W47"
SNAPSHOT_DATE = "2026-11-12"
PROJECTION_DATE = "2026-11-13"
SCENARIO_ID = "W47-BASELINE-2026-11-12"

ASSUMPTIONS = (
    "Inventory snapshot is 2026-11-12. "
    "No net inventory changes are assumed through 2026-11-15. "
    "Received inbound stock is already included in inventory. "
    "No additional inbound supply is assumed during 2026-W47. "
    "All W47 forecast demand is treated as outstanding. "
    "These are planning estimates, not confirmed actual shortages."
)

CANDIDATES = [
    {
        "forecast_id": "F006",
        "shortage_id": "SHORT-2026-000001",
        "projection_id": "PROJ-2026-000001",
        "event_id": "PEVT-PROJ-2026-000001-CREATE-01",
    },
    {
        "forecast_id": "F008",
        "shortage_id": "SHORT-2026-000002",
        "projection_id": "PROJ-2026-000002",
        "event_id": "PEVT-PROJ-2026-000002-CREATE-01",
    },
    {
        "forecast_id": "F010",
        "shortage_id": "SHORT-2026-000003",
        "projection_id": "PROJ-2026-000003",
        "event_id": "PEVT-PROJ-2026-000003-CREATE-01",
    },
]


def prepare_records(connection):
    prepared = []

    for item in CANDIDATES:
        forecast = connection.execute(
            """
            SELECT
                f.forecast_id,
                f.sku_id,
                f.location_id,
                f.forecast_week,
                f.forecast_quantity,
                s.sku_name,
                s.unit_of_measure
            FROM forecast_demand f
            JOIN sku s ON s.sku_id = f.sku_id
            WHERE f.forecast_id = ?
            """,
            (item["forecast_id"],),
        ).fetchone()

        if forecast is None:
            raise RuntimeError(
                f"Forecast not found: {item['forecast_id']}"
            )

        if forecast["forecast_week"] != PLANNING_WEEK:
            raise RuntimeError("Forecast week mismatch.")

        inventory_rows = connection.execute(
            """
            SELECT
                on_hand_quantity,
                reserved_quantity,
                unit_of_measure
            FROM inventory
            WHERE sku_id = ?
              AND location_id = ?
              AND inventory_date = ?
            """,
            (
                forecast["sku_id"],
                forecast["location_id"],
                SNAPSHOT_DATE,
            ),
        ).fetchall()

        if len(inventory_rows) != 1:
            raise RuntimeError(
                f"Expected one inventory snapshot for "
                f"{item['forecast_id']}"
            )

        inventory = inventory_rows[0]

        if inventory["unit_of_measure"] != forecast["unit_of_measure"]:
            raise RuntimeError("Unit-of-measure mismatch.")

        available = (
            inventory["on_hand_quantity"]
            - inventory["reserved_quantity"]
        )

        shortage_quantity = (
            forecast["forecast_quantity"] - available
        )

        if shortage_quantity <= 0:
            raise RuntimeError("Expected a positive shortage.")

        prepared.append({
            **item,
            "sku_id": forecast["sku_id"],
            "location_id": forecast["location_id"],
            "product": forecast["sku_name"],
            "demand": forecast["forecast_quantity"],
            "available": available,
            "shortage": shortage_quantity,
            "unit": forecast["unit_of_measure"],
        })

    return prepared


def main():
    connection = get_connection()

    try:
        print("=" * 70)
        print("INSERT W47 SHORTAGE PROJECTIONS")
        print("=" * 70)

        connection.execute("BEGIN IMMEDIATE")

        # Protect against accidental duplicate execution.
        for table in [
            "shortage_projection",
            "shortage_projection_event",
        ]:
            count = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            if count != 0:
                raise RuntimeError(
                    f"{table} is not empty. Insertion stopped."
                )

        # Preserve a comparison of historical W46 records.
        old_shortages = connection.execute(
            """
            SELECT *
            FROM shortage
            ORDER BY shortage_id
            """
        ).fetchall()

        old_events = connection.execute(
            """
            SELECT *
            FROM shortage_event
            ORDER BY shortage_event_id
            """
        ).fetchall()

        prepared = prepare_records(connection)

        # Check all proposed IDs before inserting anything.
        for item in prepared:
            checks = [
                ("shortage", "shortage_id", item["shortage_id"]),
                (
                    "shortage_projection",
                    "projection_id",
                    item["projection_id"],
                ),
                (
                    "shortage_projection_event",
                    "projection_event_id",
                    item["event_id"],
                ),
            ]

            for table, column, value in checks:
                exists = connection.execute(
                    f"SELECT 1 FROM {table} WHERE {column} = ?",
                    (value,),
                ).fetchone()

                if exists:
                    raise RuntimeError(
                        f"Duplicate ID detected: {value}"
                    )

        # Insert each projected shortage and its traceability records.
        for item in prepared:
            connection.execute(
                """
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
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 'PROJECTED')
                """,
                (
                    item["shortage_id"],
                    item["sku_id"],
                    item["location_id"],
                    PLANNING_WEEK,
                    item["demand"],
                    item["available"],
                    item["shortage"],
                ),
            )

            connection.execute(
                """
                INSERT INTO shortage_projection (
                    projection_id,
                    shortage_id,
                    forecast_id,
                    planning_scenario_id,
                    inventory_snapshot_date,
                    projection_date,
                    assumptions,
                    projection_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'PROJECTED')
                """,
                (
                    item["projection_id"],
                    item["shortage_id"],
                    item["forecast_id"],
                    SCENARIO_ID,
                    SNAPSHOT_DATE,
                    PROJECTION_DATE,
                    ASSUMPTIONS,
                ),
            )

            connection.execute(
                """
                INSERT INTO shortage_projection_event (
                    projection_event_id,
                    projection_id,
                    event_type,
                    event_date,
                    source_ref,
                    reason
                )
                VALUES (?, ?, 'PROJECTION_CREATED', ?, ?, ?)
                """,
                (
                    item["event_id"],
                    item["projection_id"],
                    PROJECTION_DATE,
                    item["forecast_id"],
                    "Initial W47 shortage estimate created from "
                    "the documented forecast and inventory snapshot.",
                ),
            )

        # Verify inserted records before committing.
        projection_count = connection.execute(
            "SELECT COUNT(*) FROM shortage_projection"
        ).fetchone()[0]

        event_count = connection.execute(
            "SELECT COUNT(*) FROM shortage_projection_event"
        ).fetchone()[0]

        w47_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM shortage
            WHERE shortage_week = ?
              AND status = 'PROJECTED'
            """,
            (PLANNING_WEEK,),
        ).fetchone()[0]

        if (
            projection_count != 3
            or event_count != 3
            or w47_count != 3
        ):
            raise RuntimeError(
                "Inserted record counts do not match expectations."
            )

        # Verify historical records were not modified.
        new_shortages = connection.execute(
            """
            SELECT *
            FROM shortage
            WHERE shortage_week = '2026-W46'
            ORDER BY shortage_id
            """
        ).fetchall()

        new_events = connection.execute(
            """
            SELECT *
            FROM shortage_event
            ORDER BY shortage_event_id
            """
        ).fetchall()

        old_w46 = [
            tuple(row) for row in old_shortages
            if row["shortage_week"] == "2026-W46"
        ]

        if old_w46 != [tuple(row) for row in new_shortages]:
            raise RuntimeError("W46 shortage history changed.")

        if [tuple(row) for row in old_events] != [
            tuple(row) for row in new_events
        ]:
            raise RuntimeError("Actual shortage events changed.")

        fk_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if fk_errors:
            raise RuntimeError(f"Foreign-key errors: {fk_errors}")

        connection.commit()

        print("\nINSERTION SUCCESSFUL")
        print("-" * 50)

        for item in prepared:
            print(
                f"{item['product']}: "
                f"{item['shortage']} {item['unit']} "
                f"| {item['shortage_id']}"
            )

        print("\nProjection records inserted:", projection_count)
        print("Projection creation events inserted:", event_count)
        print("W47 projected shortage records:", w47_count)
        print("W46 shortage history: PRESERVED")
        print("Actual shortage events: PRESERVED")
        print("Foreign-key check: PASS")
        print("Business inventory quantities changed: NO")

    except Exception:
        if connection.in_transaction:
            connection.rollback()

        print("\nINSERTION FAILED. Transaction rolled back.")
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()
