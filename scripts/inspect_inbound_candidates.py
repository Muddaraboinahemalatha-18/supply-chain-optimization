
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "supply_chain.db"

connection = sqlite3.connect(DB_PATH)

print("INBOUND ORDER SOURCE DATA INSPECTION")
print("=" * 55)

try:
    cursor = connection.cursor()

    results = cursor.execute(
        """
        SELECT
            po.po_id,
            po.order_date,
            po.expected_date,
            po.status,
            pol.po_line_id,
            pol.sku_id,
            pol.location_id,
            pol.order_quantity,
            pol.received_quantity,
            pol.unit_of_measure
        FROM purchase_order po
        JOIN purchase_order_line pol
            ON po.po_id = pol.po_id
        ORDER BY po.po_id, pol.po_line_id
        """
    ).fetchall()

    if not results:
        print("No purchase-order lines found.")

    else:
        for row in results:
            print(f"\nPurchase Order: {row[0]}")
            print(f"Order Date: {row[1]}")
            print(f"Expected Date: {row[2]}")
            print(f"PO Status: {row[3]}")
            print(f"PO Line ID: {row[4]}")
            print(f"SKU: {row[5]}")
            print(f"Location: {row[6]}")
            print(f"Ordered Quantity: {row[7]} {row[9]}")
            print(f"Received Quantity: {row[8]} {row[9]}")

    print("\nTOTAL PURCHASE ORDER LINES:", len(results))

finally:
    connection.close()
