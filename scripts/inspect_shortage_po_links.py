
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 75)
print("SHORTAGE AND PURCHASE ORDER LINK VERIFICATION")
print("=" * 75)

cursor.execute("""
    SELECT
        sh.shortage_id,
        s.sku_name,
        sh.shortage_quantity,
        sh.status AS shortage_status,
        po.po_id,
        po.status AS po_status,
        pol.po_line_id,
        pol.order_quantity,
        pol.received_quantity,
        ib.inbound_id,
        ib.inbound_quantity,
        ib.received_quantity AS inbound_received,
        ib.status AS inbound_status,
        ib.actual_arrival_date

    FROM shortage sh

    JOIN sku s
        ON sh.sku_id = s.sku_id

    LEFT JOIN purchase_order_line pol
        ON sh.sku_id = pol.sku_id
        AND sh.location_id = pol.location_id

    LEFT JOIN purchase_order po
        ON pol.po_id = po.po_id

    LEFT JOIN inbound_order ib
        ON pol.po_line_id = ib.po_line_id

    ORDER BY sh.shortage_id
""")

records = cursor.fetchall()

for row in records:
    print("\nShortage ID:", row["shortage_id"])
    print("Product:", row["sku_name"])
    print("Shortage quantity:", row["shortage_quantity"])
    print("Shortage status:", row["shortage_status"])

    print("\nPurchase Order ID:", row["po_id"])
    print("PO status:", row["po_status"])
    print("PO line ID:", row["po_line_id"])
    print("Ordered quantity:", row["order_quantity"])
    print("PO received quantity:", row["received_quantity"])

    print("\nInbound ID:", row["inbound_id"])
    print("Inbound quantity:", row["inbound_quantity"])
    print("Inbound received:", row["inbound_received"])
    print("Inbound status:", row["inbound_status"])
    print("Actual arrival date:", row["actual_arrival_date"])

    print("-" * 75)

print("\nTOTAL RELATIONSHIP RECORDS:", len(records))

connection.close()

print("\nLINK VERIFICATION COMPLETED")
