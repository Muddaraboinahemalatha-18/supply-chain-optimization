
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("PURCHASE ORDER RECEIVING")
print("=" * 50)

# Get all purchase orders
cursor.execute("""
    SELECT
        po.po_id,
        pol.po_line_id,
        pol.sku_id,
        pol.location_id,
        pol.order_quantity,
        pol.received_quantity,
        pol.unit_of_measure,
        sk.sku_name
    FROM purchase_order po
    JOIN purchase_order_line pol
        ON po.po_id = pol.po_id
    JOIN sku sk
        ON pol.sku_id = sk.sku_id
    WHERE po.status IN ('CREATED', 'PARTIALLY_RECEIVED')
""")

orders = cursor.fetchall()

if not orders:
    print("No pending purchase orders found.")

else:
    for order in orders:

        po_id = order["po_id"]
        po_line_id = order["po_line_id"]
        sku_id = order["sku_id"]
        location_id = order["location_id"]
        product = order["sku_name"]

        ordered = order["order_quantity"]
        already_received = order["received_quantity"]

        remaining = ordered - already_received

        # Receive remaining quantity
        received_now = remaining

        new_received = already_received + received_now

        # Update purchase order line
        cursor.execute("""
            UPDATE purchase_order_line
            SET received_quantity = ?
            WHERE po_line_id = ?
        """, (new_received, po_line_id))

        # Update inventory
        cursor.execute("""
            UPDATE inventory
            SET on_hand_quantity = on_hand_quantity + ?
            WHERE sku_id = ? AND location_id = ?
        """, (received_now, sku_id, location_id))

        # Record inventory event
        cursor.execute("""
            INSERT INTO inventory_event
            (event_id, sku_id, location_id, event_type,
             quantity, event_date, source_ref, unit_of_measure)
            VALUES (?, ?, ?, ?, ?, DATE('now'), ?, ?)
        """, (
            "EVT_" + po_id,
            sku_id,
            location_id,
            "PURCHASE_RECEIVED",
            received_now,
            po_id,
            order["unit_of_measure"]
        ))

        print("\nProduct:", product)
        print("Purchase Order:", po_id)
        print("Ordered Quantity:", ordered)
        print("Received Quantity:", received_now)
        print("New Total Received:", new_received)

        print("-" * 50)

        # Update purchase order status
        cursor.execute("""
            SELECT SUM(order_quantity),
                   SUM(received_quantity)
            FROM purchase_order_line
            WHERE po_id = ?
        """, (po_id,))

        totals = cursor.fetchone()

        if totals[0] == totals[1]:
            status = "RECEIVED"
        else:
            status = "PARTIALLY_RECEIVED"

        cursor.execute("""
            UPDATE purchase_order
            SET status = ?
            WHERE po_id = ?
        """, (status, po_id))

        print("Updated Status:", status)

    connection.commit()

connection.close()

print("\nPurchase order receiving completed!")
