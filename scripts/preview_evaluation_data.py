
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection


def show_records(connection, title, query, parameters=()):
    print("\n" + "=" * 85)
    print(title)
    print("=" * 85)

    cursor = connection.execute(query, parameters)
    rows = cursor.fetchall()

    print("Records found:", len(rows))

    for row in rows:
        print(dict(row))

    if not rows:
        print("No records found.")


def main():
    print("=" * 85)
    print("SUPPLY CHAIN EVALUATION DATA PREVIEW")
    print("Planning week: 2026-W47")
    print("Database changes: NONE")
    print("=" * 85)

    connection = get_connection()

    try:
        show_records(
            connection,
            "1. W47 FORECAST DEMAND",
            """
            SELECT forecast_id, sku_id, location_id,
                   forecast_week, forecast_quantity, forecast_version
            FROM forecast_demand
            WHERE forecast_week = ?
            ORDER BY forecast_id
            """,
            ("2026-W47",)
        )

        show_records(
            connection,
            "2. CURRENT INVENTORY",
            """
            SELECT inventory_id, sku_id, location_id,
                   on_hand_quantity, reserved_quantity,
                   unit_of_measure, inventory_date
            FROM inventory
            ORDER BY sku_id, location_id
            """
        )

        show_records(
            connection,
            "3. W47 SHORTAGE RECORDS",
            """
            SELECT shortage_id, sku_id, location_id,
                   shortage_week, demand_quantity,
                   available_quantity, shortage_quantity, status
            FROM shortage
            WHERE shortage_week = ?
            ORDER BY shortage_id
            """,
            ("2026-W47",)
        )

        show_records(
            connection,
            "4. W47 SHORTAGE PROJECTIONS",
            """
            SELECT projection_id, shortage_id, forecast_id,
                   planning_scenario_id, inventory_snapshot_date,
                   projection_date, projection_status
            FROM shortage_projection
            ORDER BY projection_id
            """
        )

        show_records(
            connection,
            "5. W47 MITIGATION OPTIONS",
            """
            SELECT option_id, shortage_id, supplier_id,
                   proposed_quantity, unit_of_measure,
                   estimated_cost, policy_compliant,
                   capacity_quantity, capacity_source,
                   lead_time_days, expected_arrival_date,
                   feasibility_status
            FROM mitigation_option
            WHERE shortage_id IN (
                SELECT shortage_id
                FROM shortage
                WHERE shortage_week = ?
            )
            ORDER BY option_id
            """,
            ("2026-W47",)
        )

        show_records(
            connection,
            "6. ACTUAL W47 SUPPLIER CAPACITY",
            """
            SELECT capacity_id, supplier_id, sku_id,
                   capacity_week, maximum_quantity
            FROM supplier_capacity
            WHERE capacity_week = ?
            ORDER BY supplier_id, sku_id
            """,
            ("2026-W47",)
        )

        show_records(
            connection,
            "7. LEAD-TIME RECORDS",
            """
            SELECT lead_time_id, supplier_id, location_id,
                   lead_time_days, effective_from, effective_to
            FROM lead_time
            ORDER BY supplier_id, location_id
            """
        )

        show_records(
            connection,
            "8. PRODUCTION AND BOM RECORD COUNTS",
            """
            SELECT
                (SELECT COUNT(*) FROM production_plan) AS production_plan_count,
                (SELECT COUNT(*) FROM bom) AS bom_count,
                (SELECT COUNT(*) FROM production_capacity) AS production_capacity_count
            """
        )

    finally:
        connection.close()

    print("\n" + "=" * 85)
    print("DATA PREVIEW COMPLETED")
    print("Database changes: NONE")
    print("=" * 85)


if __name__ == "__main__":
    main()
