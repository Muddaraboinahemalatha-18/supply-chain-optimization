
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 75)
print("SHORTAGE RESOLUTION PREVIEW")
print("=" * 75)

cursor.execute("""
    SELECT
        sh.shortage_id,
        s.sku_name,
        sh.demand_quantity,
        sh.shortage_quantity,
        sh.status AS shortage_status,

        i.on_hand_quantity - i.reserved_quantity
            AS current_available,

        po.status AS po_status,
        ib.inbound_id,
        ib.received_quantity,
        ib.status AS inbound_status,
        ib.actual_arrival_date,

        (
            SELECT COUNT(*)
            FROM shortage_event se
            WHERE se.shortage_id = sh.shortage_id
              AND se.event_type = 'SHORTAGE_RESOLVED'
        ) AS existing_resolution_events

    FROM shortage sh

    JOIN sku s
        ON sh.sku_id = s.sku_id

    JOIN inventory i
        ON sh.sku_id = i.sku_id
        AND sh.location_id = i.location_id

    JOIN purchase_order_line pol
        ON sh.sku_id = pol.sku_id
        AND sh.location_id = pol.location_id

    JOIN purchase_order po
        ON pol.po_id = po.po_id

    JOIN inbound_order ib
        ON pol.po_line_id = ib.po_line_id

    ORDER BY sh.shortage_id
""")

records = cursor.fetchall()

eligible_count = 0

for row in records:
    print("\nShortage:", row["shortage_id"])
    print("Product:", row["sku_name"])
    print("Historical shortage:", row["shortage_quantity"])
    print("Current available:", row["current_available"])
    print("Demand:", row["demand_quantity"])
    print("Purchase order status:", row["po_status"])
    print("Inbound ID:", row["inbound_id"])
    print("Received quantity:", row["received_quantity"])
    print("Inbound status:", row["inbound_status"])
    print("Actual arrival date:", row["actual_arrival_date"])
    print("Existing resolution events:", row["existing_resolution_events"])

    checks = [
        row["shortage_status"] == "OPEN",
        row["po_status"] == "RECEIVED",
        row["inbound_status"] == "RECEIVED",
        row["received_quantity"] >= row["shortage_quantity"],
        row["current_available"] >= row["demand_quantity"],
        row["existing_resolution_events"] == 0
    ]

    if all(checks):
        print("Resolution eligibility: ELIGIBLE")
        eligible_count += 1
    else:
        print("Resolution eligibility: NOT ELIGIBLE")

    print("-" * 75)

print("\nTOTAL RECORDS:", len(records))
print("ELIGIBLE SHORTAGES:", eligible_count)

connection.close()

print("\nPREVIEW COMPLETED")
print("No database records were modified.")
