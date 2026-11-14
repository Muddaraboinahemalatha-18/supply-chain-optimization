
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 75)
print("INVENTORY TIMELINE INSPECTION")
print("=" * 75)

print("\n1. CURRENT INVENTORY")

cursor.execute("""
    SELECT
        i.inventory_id,
        s.sku_name,
        i.location_id,
        i.on_hand_quantity,
        i.reserved_quantity,
        i.on_hand_quantity - i.reserved_quantity AS available_quantity,
        i.unit_of_measure,
        i.inventory_date
    FROM inventory i
    JOIN sku s ON i.sku_id = s.sku_id
    ORDER BY s.sku_name
""")

for row in cursor.fetchall():
    print("\n", dict(row))

print("\n2. INVENTORY EVENT HISTORY")

cursor.execute("""
    SELECT
        event_id,
        sku_id,
        location_id,
        event_type,
        quantity,
        event_date,
        source_ref,
        unit_of_measure
    FROM inventory_event
    ORDER BY event_date, event_id
""")

events = cursor.fetchall()

for row in events:
    print("\n", dict(row))

print("\nTOTAL INVENTORY EVENTS:", len(events))

print("\n3. INBOUND RECEIPT HISTORY")

cursor.execute("""
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
""")

for row in cursor.fetchall():
    print("\n", dict(row))

connection.close()

print("\n" + "=" * 75)
print("INSPECTION COMPLETED")
print("No database records were modified.")
print("=" * 75)
