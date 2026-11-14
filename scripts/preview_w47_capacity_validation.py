
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection


def main():
    connection = get_connection()

    try:
        print("=" * 85)
        print("W47 SUPPLIER CAPACITY VALIDATION PREVIEW")
        print("=" * 85)

        print("\nPLANNING ASSUMPTIONS")
        print("-" * 85)
        print("Forecast week: W47")
        print("Inventory snapshot: 2026-11-12")
        print("Received inbound stock is already included in inventory.")
        print("No additional inbound supply is assumed.")
        print("Only exact W47 supplier capacity can establish capacity feasibility.")
        print("This script is READ-ONLY. No database records will be changed.")

        forecasts = connection.execute("""
            SELECT
                f.forecast_id,
                f.sku_id,
                s.sku_name,
                f.location_id,
                f.forecast_quantity,
                s.unit_of_measure,
                i.on_hand_quantity,
                i.reserved_quantity,
                (i.on_hand_quantity - i.reserved_quantity)
                    AS available_quantity
            FROM forecast_demand f
            JOIN sku s
                ON f.sku_id = s.sku_id
            LEFT JOIN inventory i
                ON f.sku_id = i.sku_id
                AND f.location_id = i.location_id
            WHERE f.forecast_week = '2026-W47'
            ORDER BY f.forecast_id
        """).fetchall()

        if not forecasts:
            print("\nNo W47 forecast records found.")
            return

        policy_columns = [
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(supplier_sku_policy)"
            ).fetchall()
        ]

        capacity_rows = connection.execute("""
            SELECT
                sc.supplier_id,
                sc.sku_id,
                sc.capacity_week,
                sc.maximum_quantity
            FROM supplier_capacity sc
            WHERE sc.capacity_week = '2026-W47'
        """).fetchall()

        print("\nW47 CAPACITY RECORD COUNT:", len(capacity_rows))

        print("\nSHORTAGE AND CAPACITY VALIDATION")
        print("-" * 85)

        shortage_count = 0
        feasible_count = 0
        unverified_count = 0

        for item in forecasts:
            print("\nForecast ID:", item["forecast_id"])
            print("Product:", item["sku_name"])
            print("SKU:", item["sku_id"])
            print("Location:", item["location_id"])
            print("Demand:", item["forecast_quantity"], item["unit_of_measure"])

            if item["available_quantity"] is None:
                print("Inventory: MISSING")
                print("Result: CANNOT CALCULATE SHORTAGE")
                continue

            available = item["available_quantity"]
            shortage = max(0, item["forecast_quantity"] - available)

            print("Available inventory:", available)
            print("Estimated shortage:", shortage, item["unit_of_measure"])

            if shortage <= 0:
                print("Result: SUFFICIENT INVENTORY")
                continue

            shortage_count += 1

            suppliers = connection.execute("""
                SELECT
                    ss.supplier_id,
                    s.supplier_name,
                    s.is_active,
                    ss.is_approved
                FROM supplier_sku ss
                JOIN supplier s
                    ON ss.supplier_id = s.supplier_id
                WHERE ss.sku_id = ?
                ORDER BY ss.supplier_id
            """, (item["sku_id"],)).fetchall()

            if not suppliers:
                print("Result: NO SUPPLIER RELATIONSHIP FOUND")
                unverified_count += 1
                continue

            eligible_suppliers = []

            for supplier in suppliers:
                if supplier["is_active"] != 1:
                    continue
                if supplier["is_approved"] != 1:
                    continue

                eligible_suppliers.append(supplier)

            if not eligible_suppliers:
                print("Result: NO ACTIVE APPROVED SUPPLIER")
                unverified_count += 1
                continue

            for supplier in eligible_suppliers:
                print("\nSupplier:", supplier["supplier_name"])
                print("Supplier ID:", supplier["supplier_id"])
                print("Supplier status: ACTIVE")
                print("SKU approval: APPROVED")

                policy = connection.execute("""
                    SELECT *
                    FROM supplier_sku_policy
                    WHERE supplier_id = ?
                      AND sku_id = ?
                      AND effective_from <= '2026-11-13'
                      AND (
                          effective_to IS NULL
                          OR effective_to >= '2026-11-13'
                      )
                """, (
                    supplier["supplier_id"],
                    item["sku_id"]
                )).fetchall()

                if policy:
                    for policy_record in policy:
                        print("Applicable supplier policy:")
                        for column in policy_columns:
                            print(
                                " ", column, ":",
                                policy_record[column]
                            )
                else:
                    print("Applicable supplier policy: NOT FOUND")

                capacity = connection.execute("""
                    SELECT maximum_quantity
                    FROM supplier_capacity
                    WHERE supplier_id = ?
                      AND sku_id = ?
                      AND capacity_week = '2026-W47'
                """, (
                    supplier["supplier_id"],
                    item["sku_id"]
                )).fetchone()

                if capacity is None:
                    print("W47 capacity: NOT AVAILABLE")
                    print("Capacity feasibility: UNVERIFIED")
                    unverified_count += 1
                else:
                    maximum = capacity["maximum_quantity"]
                    print("W47 maximum capacity:", maximum)

                    if shortage <= maximum:
                        print("Capacity feasibility: PASS")
                        feasible_count += 1
                    else:
                        print("Capacity feasibility: FAIL")

        print("\n" + "=" * 85)
        print("VALIDATION SUMMARY")
        print("=" * 85)
        print("W47 forecast records:", len(forecasts))
        print("Estimated shortage cases:", shortage_count)
        print("Capacity-feasible supplier matches:", feasible_count)
        print("Unverified supplier matches:", unverified_count)

        print("\nIMPORTANT:")
        print("Missing W47 capacity is not treated as zero capacity.")
        print("W46 capacity is not reused for W47.")
        print("No synthetic capacity or purchase commitment is created.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
