
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

PLANNING_WEEK = "2026-W47"
SNAPSHOT_DATE = "2026-11-12"
PROJECTION_DATE = "2026-11-13"

SCENARIO_ID = "W47-BASELINE-2026-11-12"

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

ASSUMPTIONS = (
    "Inventory snapshot is 2026-11-12. "
    "No net inventory changes are assumed through 2026-11-15. "
    "Received inbound stock is already included in inventory. "
    "No additional inbound supply is assumed during 2026-W47. "
    "All W47 forecast demand is treated as outstanding. "
    "These are planning estimates, not confirmed actual shortages."
)


def main():
    connection = get_connection()

    try:
        print("=" * 75)
        print("W47 SHORTAGE PROJECTION PERSISTENCE PREVIEW")
        print("=" * 75)

        print("Planning week:", PLANNING_WEEK)
        print("Inventory snapshot:", SNAPSHOT_DATE)
        print("Projection date:", PROJECTION_DATE)
        print("Planning scenario:", SCENARIO_ID)

        # Ensure the projection tables are empty.
        projection_count = connection.execute(
            "SELECT COUNT(*) FROM shortage_projection"
        ).fetchone()[0]

        event_count = connection.execute(
            "SELECT COUNT(*) FROM shortage_projection_event"
        ).fetchone()[0]

        if projection_count != 0 or event_count != 0:
            raise RuntimeError(
                "Projection tables are not empty. "
                "Stop and inspect existing records."
            )

        print("\nProjection tables are empty: PASS")

        # Check the planning scenario is distinct from the
        # synthetic supplier-capacity scenario.
        if SCENARIO_ID == "SYN-W47-001":
            raise RuntimeError("Planning scenario ID conflict.")

        print("Capacity scenario kept separate: PASS")

        print("\nPROJECTION CANDIDATES")
        print("-" * 75)

        prepared = []

        for candidate in CANDIDATES:
            forecast_id = candidate["forecast_id"]

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
                JOIN sku s
                    ON s.sku_id = f.sku_id
                WHERE f.forecast_id = ?
                """,
                (forecast_id,),
            ).fetchone()

            if forecast is None:
                raise RuntimeError(
                    f"Forecast not found: {forecast_id}"
                )

            if forecast["forecast_week"] != PLANNING_WEEK:
                raise RuntimeError(
                    f"Incorrect planning week for {forecast_id}"
                )

            inventory_rows = connection.execute(
                """
                SELECT
                    inventory_id,
                    on_hand_quantity,
                    reserved_quantity,
                    unit_of_measure,
                    inventory_date
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
                    f"Expected exactly one inventory snapshot for "
                    f"{forecast_id}; found {len(inventory_rows)}"
                )

            inventory = inventory_rows[0]

            if (
                inventory["unit_of_measure"]
                != forecast["unit_of_measure"]
            ):
                raise RuntimeError(
                    f"Unit mismatch for {forecast_id}"
                )

            available = (
                inventory["on_hand_quantity"]
                - inventory["reserved_quantity"]
            )

            shortage_quantity = (
                forecast["forecast_quantity"] - available
            )

            if shortage_quantity <= 0:
                raise RuntimeError(
                    f"{forecast_id} does not have a positive shortage."
                )

            prepared.append({
                **candidate,
                "forecast_id": forecast["forecast_id"],
                "sku_id": forecast["sku_id"],
                "location_id": forecast["location_id"],
                "product": forecast["sku_name"],
                "demand": forecast["forecast_quantity"],
                "available": available,
                "shortage": shortage_quantity,
                "unit": forecast["unit_of_measure"],
            })

        # Check all proposed IDs are unused.
        for item in prepared:
            for table, column, value in [
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
            ]:
                exists = connection.execute(
                    f"SELECT 1 FROM {table} WHERE {column} = ?",
                    (value,),
                ).fetchone()

                if exists:
                    raise RuntimeError(
                        f"ID already exists: {value} in {table}"
                    )

        for item in prepared:
            print(f"\nForecast: {item['forecast_id']}")
            print("Product:", item["product"])
            print("SKU:", item["sku_id"])
            print("Location:", item["location_id"])
            print("Demand:", item["demand"], item["unit"])
            print("Available:", item["available"], item["unit"])
            print("Projected shortage:", item["shortage"], item["unit"])
            print("Shortage ID:", item["shortage_id"])
            print("Projection ID:", item["projection_id"])
            print("Projection event ID:", item["event_id"])
            print("Validation: PASS")

        print("\nSUMMARY")
        print("-" * 75)
        print("Candidate projections:", len(prepared))
        print("Forecast relationship checks: PASS")
        print("Inventory snapshot checks: PASS")
        print("Unit-of-measure checks: PASS")
        print("Shortage ID uniqueness checks: PASS")
        print("Projection ID uniqueness checks: PASS")
        print("Event ID uniqueness checks: PASS")
        print("Planning scenario separation: PASS")

        print("\nASSUMPTIONS")
        print(ASSUMPTIONS)

        print("\nDATABASE CHANGES: NONE")
        print("This script is read-only.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
