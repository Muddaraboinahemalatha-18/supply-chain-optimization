
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "supply_chain.db"

# Synthetic MOQ assumptions for the starter dataset
MOQ_DATA = {
    "SKU001": 50,   # Rice - Kg
    "SKU002": 50,   # Wheat - Kg
    "SKU003": 25,   # Sugar - Kg
    "SKU004": 20,   # Oil - Liter
    "SKU005": 10    # Milk - Liter
}

EFFECTIVE_FROM = "2026-01-01"
EFFECTIVE_TO = None


def seed_supplier_sku_policy():

    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        cursor = connection.cursor()

        # Prevent duplicate policy insertion
        existing_count = cursor.execute(
            "SELECT COUNT(*) FROM supplier_sku_policy"
        ).fetchone()[0]

        if existing_count > 0:
            print("Supplier SKU policies already exist.")
            print("No records were inserted.")
            print("Existing records:", existing_count)
            return

        # Read existing supplier-SKU relationships
        supplier_skus = cursor.execute(
            """
            SELECT supplier_id, sku_id, is_approved, unit_cost
            FROM supplier_sku
            ORDER BY supplier_id, sku_id
            """
        ).fetchall()

        if len(supplier_skus) != len(MOQ_DATA):
            raise Exception(
                "Expected 5 supplier-SKU relationships. "
                "Please inspect the existing data first."
            )

        # Verify every SKU has a configured MOQ
        for supplier_id, sku_id, approved, unit_cost in supplier_skus:

            if sku_id not in MOQ_DATA:
                raise Exception(
                    f"No MOQ configured for SKU: {sku_id}"
                )

            if approved != 1:
                raise Exception(
                    f"Supplier {supplier_id} is not approved "
                    f"for SKU {sku_id}."
                )

            if unit_cost is None or unit_cost < 0:
                raise Exception(
                    f"Invalid supplier unit cost for {sku_id}."
                )

        # Insert policies using existing supplier-specific costs
        for index, record in enumerate(supplier_skus, start=1):

            supplier_id, sku_id, approved, unit_cost = record

            policy_id = f"POLICY-{index:06d}"
            minimum_quantity = MOQ_DATA[sku_id]

            cursor.execute(
                """
                INSERT INTO supplier_sku_policy (
                    policy_id,
                    supplier_id,
                    sku_id,
                    minimum_order_quantity,
                    unit_cost,
                    effective_from,
                    effective_to
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    policy_id,
                    supplier_id,
                    sku_id,
                    minimum_quantity,
                    unit_cost,
                    EFFECTIVE_FROM,
                    EFFECTIVE_TO
                )
            )

        connection.commit()

        print("SUPPLIER SKU POLICIES INSERTED SUCCESSFULLY")
        print("=" * 50)
        print("Total records inserted:", len(supplier_skus))

        print("\nSUPPLIER SKU POLICY DETAILS")
        print("-" * 50)

        results = cursor.execute(
            """
            SELECT
                p.policy_id,
                p.supplier_id,
                p.sku_id,
                p.minimum_order_quantity,
                p.unit_cost,
                s.unit_of_measure
            FROM supplier_sku_policy p
            JOIN sku s ON p.sku_id = s.sku_id
            ORDER BY p.policy_id
            """
        ).fetchall()

        for row in results:
            print(
                f"Policy: {row[0]} | "
                f"Supplier: {row[1]} | "
                f"SKU: {row[2]} | "
                f"MOQ: {row[3]} {row[5]} | "
                f"Unit Cost: Rs.{row[4]}"
            )

        print("\nEffective from:", EFFECTIVE_FROM)
        print("Effective to: Currently active")

    except Exception as error:
        connection.rollback()
        print("\nERROR: Policy insertion failed.")
        print(error)

    finally:
        connection.close()


if __name__ == "__main__":
    seed_supplier_sku_policy()
