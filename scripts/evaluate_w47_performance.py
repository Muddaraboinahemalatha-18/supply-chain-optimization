
import sys
import csv
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

OUTPUT_FILE = (
    BASE_DIR / "data" / "scenarios" / "w47_performance_evaluation.csv"
)


def main():
    print("=" * 85)
    print("W47 SUPPLY CHAIN PERFORMANCE EVALUATION")
    print("=" * 85)

    connection = get_connection()

    try:
        forecasts = connection.execute(
            """
            SELECT forecast_id, sku_id, location_id,
                   forecast_week, forecast_quantity
            FROM forecast_demand
            WHERE forecast_week = '2026-W47'
            ORDER BY forecast_id
            """
        ).fetchall()

        inventory_rows = connection.execute(
            """
            SELECT sku_id, location_id, on_hand_quantity,
                   reserved_quantity, unit_of_measure
            FROM inventory
            """
        ).fetchall()

        shortage_rows = connection.execute(
            """
            SELECT shortage_id, sku_id, location_id,
                   demand_quantity, available_quantity,
                   shortage_quantity, status
            FROM shortage
            WHERE shortage_week = '2026-W47'
            """
        ).fetchall()

        mitigation_rows = connection.execute(
            """
            SELECT option_id, shortage_id, proposed_quantity,
                   estimated_cost, capacity_source,
                   feasibility_status, minimum_order_quantity
            FROM mitigation_option
            WHERE shortage_id IN (
                SELECT shortage_id
                FROM shortage
                WHERE shortage_week = '2026-W47'
            )
            """
        ).fetchall()

        actual_capacity_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM supplier_capacity
            WHERE capacity_week = '2026-W47'
            """
        ).fetchone()[0]

        lead_time_count = connection.execute(
            "SELECT COUNT(*) FROM lead_time"
        ).fetchone()[0]

        production_counts = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM production_plan),
                (SELECT COUNT(*) FROM bom),
                (SELECT COUNT(*) FROM production_capacity)
            """
        ).fetchone()

    finally:
        connection.close()

    inventory_lookup = {}

    for row in inventory_rows:
        key = (row["sku_id"], row["location_id"])

        if key in inventory_lookup:
            raise ValueError(f"Multiple inventory records found for {key}")

        inventory_lookup[key] = row

    shortage_lookup = {}

    for row in shortage_rows:
        key = (row["sku_id"], row["location_id"])

        if key in shortage_lookup:
            raise ValueError(f"Multiple W47 shortages found for {key}")

        shortage_lookup[key] = row

    mitigation_lookup = defaultdict(list)

    for row in mitigation_rows:
        mitigation_lookup[row["shortage_id"]].append(row)

    evaluation_rows = []
    demand_by_unit = defaultdict(float)
    available_by_unit = defaultdict(float)
    shortage_by_unit = defaultdict(float)
    proposed_by_unit = defaultdict(float)
    excess_by_unit = defaultdict(float)

    shortage_line_count = 0
    sufficient_line_count = 0
    reconciliation_errors = 0
    covered_shortage_count = 0
    total_mitigation_cost = 0.0
    conditional_option_count = 0
    synthetic_option_count = 0

    print("\nSKU-LEVEL EVALUATION")
    print("-" * 85)

    for forecast in forecasts:
        key = (forecast["sku_id"], forecast["location_id"])

        inventory = inventory_lookup.get(key)

        if inventory is None:
            raise ValueError(f"Inventory missing for {key}")

        unit = inventory["unit_of_measure"]
        demand = float(forecast["forecast_quantity"])

        available = (
            float(inventory["on_hand_quantity"])
            - float(inventory["reserved_quantity"])
        )

        projected_balance = available - demand
        calculated_shortage = max(0, -projected_balance)

        demand_by_unit[unit] += demand
        available_by_unit[unit] += available
        shortage_by_unit[unit] += calculated_shortage

        shortage = shortage_lookup.get(key)

        if calculated_shortage > 0:
            shortage_line_count += 1
        else:
            sufficient_line_count += 1

        if calculated_shortage > 0:
            if shortage is None:
                reconciliation_errors += 1
                raise ValueError(
                    f"Missing shortage record for {forecast['sku_id']}"
                )

            if (
                abs(float(shortage["shortage_quantity"]) - calculated_shortage) > 0.000001
                or abs(float(shortage["available_quantity"]) - available) > 0.000001
                or abs(float(shortage["demand_quantity"]) - demand) > 0.000001
            ):
                reconciliation_errors += 1
                raise ValueError(
                    f"Shortage reconciliation failed for {forecast['sku_id']}"
                )

            options = mitigation_lookup.get(shortage["shortage_id"], [])

            proposed_quantity = sum(
                float(option["proposed_quantity"])
                for option in options
            )

            proposed_by_unit[unit] += proposed_quantity

            if proposed_quantity >= calculated_shortage:
                covered_shortage_count += 1

            excess_quantity = max(
                0, proposed_quantity - calculated_shortage
            )
            excess_by_unit[unit] += excess_quantity

            for option in options:
                total_mitigation_cost += float(option["estimated_cost"])

                if option["feasibility_status"] == "CONDITIONAL":
                    conditional_option_count += 1

                if option["capacity_source"] == "SYNTHETIC":
                    synthetic_option_count += 1

            shortage_id = shortage["shortage_id"]
            shortage_status = shortage["status"]

        else:
            proposed_quantity = 0
            excess_quantity = 0
            shortage_id = "NONE"
            shortage_status = "NO_SHORTAGE"

        evaluation_rows.append({
            "forecast_id": forecast["forecast_id"],
            "sku_id": forecast["sku_id"],
            "location_id": forecast["location_id"],
            "unit": unit,
            "demand": demand,
            "available_stock": available,
            "projected_balance": projected_balance,
            "calculated_shortage": calculated_shortage,
            "shortage_id": shortage_id,
            "shortage_status": shortage_status,
            "recommended_quantity": proposed_quantity,
            "excess_recommended_quantity": excess_quantity
        })

        print(
            f'{forecast["sku_id"]} | '
            f'Demand: {demand:g} {unit} | '
            f'Available: {available:g} {unit} | '
            f'Balance: {projected_balance:g} {unit} | '
            f'Shortage: {calculated_shortage:g} {unit}'
        )

    if len(evaluation_rows) != 5:
        raise ValueError("Expected exactly five W47 forecast records.")

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=evaluation_rows[0].keys()
        )
        writer.writeheader()
        writer.writerows(evaluation_rows)

    print("\nINVENTORY COVERAGE")
    print("-" * 85)

    for unit in sorted(demand_by_unit):
        demand = demand_by_unit[unit]
        available = available_by_unit[unit]
        coverage = (available / demand * 100) if demand else 0

        print(f"{unit}:")
        print(f"  Forecast demand: {demand:g}")
        print(f"  Available stock: {available:g}")
        print(f"  Availability-to-demand ratio: {coverage:.2f}%")
        print(f"  Projected shortage: {shortage_by_unit[unit]:g}")

    total_forecast_lines = len(forecasts)
    shortage_rate = (
        shortage_line_count / total_forecast_lines * 100
    )

    mitigation_coverage = (
        covered_shortage_count / shortage_line_count * 100
        if shortage_line_count else 0
    )

    print("\nSHORTAGE METRICS")
    print("-" * 85)
    print("Forecast lines evaluated:", total_forecast_lines)
    print("Shortage lines:", shortage_line_count)
    print("Sufficient-stock lines:", sufficient_line_count)
    print(f"Shortage incidence: {shortage_rate:.2f}%")
    print("Shortage reconciliation errors:", reconciliation_errors)

    print("\nMITIGATION METRICS")
    print("-" * 85)
    print("Shortages covered by recommendations:",
          f"{covered_shortage_count}/{shortage_line_count}")
    print(f"Recommendation coverage: {mitigation_coverage:.2f}%")

    for unit in sorted(proposed_by_unit):
        print(
            f"Recommended quantity ({unit}): "
            f"{proposed_by_unit[unit]:g}"
        )
        print(
            f"Excess over projected shortage ({unit}): "
            f"{excess_by_unit[unit]:g}"
        )

    print(f"Total estimated mitigation cost: Rs. {total_mitigation_cost:.2f}")
    print("Conditional options:", conditional_option_count)
    print("Options using synthetic capacity:", synthetic_option_count)

    print("\nSUPPLY CONSTRAINT EVIDENCE")
    print("-" * 85)
    print("Actual W47 supplier capacity records:", actual_capacity_count)
    print("Lead-time records available:", lead_time_count)
    print("Production plan records:", production_counts[0])
    print("BOM records:", production_counts[1])
    print("Production capacity records:", production_counts[2])

    print("\nEVALUATION LIMITATIONS")
    print("-" * 85)
    print("Forecast accuracy: NOT CALCULATED (actual demand unavailable).")
    print("Supplier capacity feasibility: CONDITIONAL (synthetic capacity).")
    print("Production evaluation: NOT APPLICABLE TO CURRENT STARTER DATA.")

    print("\nSUMMARY")
    print("-" * 85)
    print("Performance evaluation rows:", len(evaluation_rows))
    print("Results saved:", OUTPUT_FILE.name)
    print("Database changes: NONE")
    print("EVALUATION STATUS: COMPLETED")
    print("=" * 85)


if __name__ == "__main__":
    main()
