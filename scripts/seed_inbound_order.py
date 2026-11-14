
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "supply_chain.db"

# Inbound history derived from existing received PO records
INBOUND_DATA = [
    (
        "INB-2026-000001",
        "LINE_SH_F001",
        "2026-11-19",
        "2026-11-12",
        150.0,
        150.0,
        "RECEIVED"
    ),
    (
        "INB-2026-000002",
        "LINE_SH_F003",
        "2026-11-19",
        "2026-11-12",
        130.0,
        130.0,
        "RECEIVED"
    ),
    (
        "INB-2026-000003",
        "LINE_SH_F005",
        "2026-11-19",
        "2026-11-12",
        65.0,
        65.0,
        "RECEIVED"
    )
]


def seed_inbound_orders():

    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        cursor = connection.cursor()

        # Prevent duplicate insertion
        existing_count = cursor.execute(
            "SELECT COUNT(*) FROM inbound_order"
        ).fetchone()[0]

        if existing_count > 0:
            print("Inbound records already exist.")
            print("No records were inserted.")
            print("Existing records:", existing_count)
            return

        # Verify source purchase-order lines and quantities
        for record in INBOUND_DATA:

            inbound_id = record[0]
            po_line_id = record[1]
            inbound_quantity = record[4]
            received_quantity = record[5]

            source = cursor.execute(
                """
                SELECT order_quantity, received_quantity
                FROM purchase_order_line
                WHERE po_line_id = ?
                """,
                (po_line_id,)
            ).fetchone()

            if source is None:
                raise Exception(
                    f"Purchase order line not found: {po_line_id}"
                )

            if source[0] != inbound_quantity:
                raise Exception(
                    f"Inbound quantity mismatch: {inbound_id}"
                )

            if source[1] != received_quantity:
                raise Exception(
                    f"Received quantity mismatch: {inbound_id}"
                )

        # Insert inbound history records
        for record in INBOUND_DATA:

            cursor.execute(
                """
                INSERT INTO inbound_order (
                    inbound_id,
                    po_line_id,
                    expected_arrival_date,
                    actual_arrival_date,
                    inbound_quantity,
                    received_quantity,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                record
            )

        connection.commit()

        print("INBOUND ORDER HISTORY INSERTED SUCCESSFULLY")
        print("=" * 55)
        print("Total records inserted:", len(INBOUND_DATA))
        print("Inventory quantities were not changed.")

        print("\nINBOUND ORDER DETAILS")
        print("-" * 55)

        results = cursor.execute(
            """
            SELECT
                inbound_id,
                po_line_id,
                expected_arrival_date,
                actual_arrival_date,
                inbound_quantity,
                received_quantity,
                status
            FROM inbound_order
            ORDER BY inbound_id
            """
        ).fetchall()

        for row in results:
            print(
                f"ID: {row[0]} | "
                f"PO Line: {row[1]} | "
                f"Expected: {row[2]} | "
                f"Actual: {row[3]} | "
                f"Quantity: {row[4]} | "
                f"Received: {row[5]} | "
                f"Status: {row[6]}"
            )

    except Exception as error:
        connection.rollback()
        print("\nERROR: Inbound insertion failed.")
        print(error)

    finally:
        connection.close()


if __name__ == "__main__":
    seed_inbound_orders()
