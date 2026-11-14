
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 75)
print("W47 SUPPLY INPUT INSPECTION")
print("=" * 75)

print("\n1. CURRENT INVENTORY SNAPSHOT")

cursor.execute("""
    SELECT
        s.sku_name,
        i.sku_id,
        i.location_id,
        i.on_hand_quantity,
        i.reserved_quantity,
        i.on_hand_quantity - i.reserved_quantity
            AS available_quantity,
        i.unit_of_measure,
        i.inventory_date
    FROM inventory i
    JOIN sku s ON i.sku_id = s.sku_id
    ORDER BY s.sku_name
""")

for row in cursor.fetchall():
    print(dict(row))

print("\n2. ALL INBOUND ORDERS")

cursor.execute("""
    SELECT
        io.inbound_id,
        pol.sku_id,
        s.sku_name,
        pol.location_id,
        io.expected_arrival_date,
        io.actual_arrival_date,
        io.inbound_quantity,
        io.received_quantity,
        io.status,
        pol.unit_of_measure
    FROM inbound_order io
    JOIN purchase_order_line pol
        ON io.po_line_id = pol.po_line_id
    JOIN sku s
        ON pol.sku_id = s.sku_id
    ORDER BY io.expected_arrival_date, io.inbound_id
""")

inbound_records = cursor.fetchall()

for row in inbound_records:
    print(dict(row))

print("\nTOTAL INBOUND RECORDS:", len(inbound_records))

print("\n3. OUTSTANDING INBOUND ORDERS")

outstanding = [
    row for row in inbound_records
    if row["status"] != "RECEIVED"
]

if outstanding:
    for row in outstanding:
        print(dict(row))
else:
    print("No outstanding inbound orders found.")

print("\n4. FINAL INSPECTION")

print("Inventory snapshot date: 2026-11-12")
print("Next planning week: 2026-W47")
print("W47 start date: 2026-11-16")

connection.close()

print("\nNo database records were modified.")
print("=" * 75)
