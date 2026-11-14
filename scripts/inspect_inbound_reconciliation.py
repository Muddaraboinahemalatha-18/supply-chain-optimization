
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 70)
print("INBOUND ORDER RECONCILIATION")
print("=" * 70)

cursor.execute("""
    SELECT
        ib.inbound_id,
        ib.po_line_id,
        po.po_id,
        pol.sku_id,
        s.sku_name,
        pol.location_id,
        ib.expected_arrival_date,
        ib.actual_arrival_date,
        pol.order_quantity,
        ib.inbound_quantity,
        pol.received_quantity AS po_received_quantity,
        ib.received_quantity AS inbound_received_quantity,
        ib.status,
        pol.unit_of_measure
    FROM inbound_order ib
    JOIN purchase_order_line pol
        ON ib.po_line_id = pol.po_line_id
    JOIN purchase_order po
        ON pol.po_id = po.po_id
    JOIN sku s
        ON pol.sku_id = s.sku_id
    ORDER BY ib.inbound_id
""")

records = cursor.fetchall()

print("\nINBOUND ORDER DETAILS")
print("-" * 70)

for row in records:
    print(f"\nInbound ID: {row['inbound_id']}")
    print(f"PO ID: {row['po_id']}")
    print(f"PO Line ID: {row['po_line_id']}")
    print(f"Product: {row['sku_name']}")
    print(f"Location: {row['location_id']}")
    print(f"Expected arrival: {row['expected_arrival_date']}")
    print(f"Actual arrival: {row['actual_arrival_date']}")
    print(f"Ordered quantity: {row['order_quantity']} {row['unit_of_measure']}")
    print(f"Inbound quantity: {row['inbound_quantity']} {row['unit_of_measure']}")
    print(f"PO received quantity: {row['po_received_quantity']}")
    print(f"Inbound received quantity: {row['inbound_received_quantity']}")
    print(f"Status: {row['status']}")

    if row['order_quantity'] == row['inbound_quantity']:
        print("Ordered vs inbound quantity: MATCH")
    else:
        print("Ordered vs inbound quantity: MISMATCH")

    if row['po_received_quantity'] == row['inbound_received_quantity']:
        print("Received quantity: MATCH")
    else:
        print("Received quantity: MISMATCH")

# Check purchase order lines without inbound records
cursor.execute("""
    SELECT
        pol.po_line_id,
        pol.po_id,
        pol.sku_id,
        pol.order_quantity
    FROM purchase_order_line pol
    LEFT JOIN inbound_order ib
        ON pol.po_line_id = ib.po_line_id
    WHERE ib.inbound_id IS NULL
""")

missing = cursor.fetchall()

print("\nPURCHASE ORDER LINES WITHOUT INBOUND RECORDS")
print("-" * 70)

if missing:
    for row in missing:
        print(
            f"PO Line: {row['po_line_id']} | "
            f"PO: {row['po_id']} | "
            f"SKU: {row['sku_id']} | "
            f"Quantity: {row['order_quantity']}"
        )
else:
    print("All purchase order lines have inbound records.")

print("\nTOTAL INBOUND RECORDS:", len(records))
print("PO LINES WITHOUT INBOUND RECORDS:", len(missing))

connection.close()

print("\nRECONCILIATION INSPECTION COMPLETED")
