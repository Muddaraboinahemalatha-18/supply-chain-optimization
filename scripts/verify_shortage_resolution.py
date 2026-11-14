
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 75)
print("SHORTAGE RESOLUTION VERIFICATION")
print("=" * 75)

cursor.execute("""
    SELECT
        sh.shortage_id,
        s.sku_name,
        sh.location_id,
        sh.demand_quantity,
        sh.shortage_quantity,
        sh.available_quantity AS historical_available,
        i.on_hand_quantity,
        i.reserved_quantity,
        (i.on_hand_quantity - i.reserved_quantity)
            AS current_available,
        COALESCE(receipts.received_quantity, 0)
            AS recorded_receipts,
        sh.status

    FROM shortage sh

    JOIN sku s
        ON sh.sku_id = s.sku_id

    LEFT JOIN inventory i
        ON sh.sku_id = i.sku_id
        AND sh.location_id = i.location_id

    LEFT JOIN (
        SELECT
            pol.sku_id,
            pol.location_id,
            SUM(ib.received_quantity) AS received_quantity
        FROM inbound_order ib
        JOIN purchase_order_line pol
            ON ib.po_line_id = pol.po_line_id
        WHERE ib.status = 'RECEIVED'
        GROUP BY pol.sku_id, pol.location_id
    ) receipts
        ON sh.sku_id = receipts.sku_id
        AND sh.location_id = receipts.location_id

    ORDER BY sh.shortage_id
""")

records = cursor.fetchall()

print("\nSHORTAGE RECONCILIATION")
print("-" * 75)

for row in records:
    print(f"\nShortage ID: {row['shortage_id']}")
    print(f"Product: {row['sku_name']}")
    print(f"Demand quantity: {row['demand_quantity']}")
    print(f"Historical available: {row['historical_available']}")
    print(f"Historical shortage: {row['shortage_quantity']}")
    print(f"Recorded receipts: {row['recorded_receipts']}")

    current_available = row['current_available']

    if current_available is None:
        print("Inventory check: INVENTORY RECORD MISSING")
        continue

    reconstructed_available = (
        current_available - row['recorded_receipts']
    )

    print(f"Reconstructed historical available: {reconstructed_available}")
    print(f"Current available inventory: {current_available}")

    if abs(reconstructed_available - row['historical_available']) < 0.001:
        print("Historical reconciliation: MATCH")
    else:
        print("Historical reconciliation: MISMATCH")

    remaining_shortage = max(
        0,
        row['demand_quantity'] - current_available
    )

    print(f"Remaining shortage against recorded demand: {remaining_shortage}")
    print(f"Current database status: {row['status']}")

    if remaining_shortage == 0 and row['status'] == 'OPEN':
        print("Status review: Inventory covers recorded demand, but shortage is still OPEN.")
    elif remaining_shortage > 0:
        print("Status review: A shortage remains against recorded demand.")
    else:
        print("Status review: No immediate status inconsistency identified.")

print("\nTOTAL SHORTAGES CHECKED:", len(records))

connection.close()

print("\nVERIFICATION COMPLETED")
