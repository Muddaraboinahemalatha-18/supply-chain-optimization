
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 70)
print("SUPPLY CHAIN EVENT HISTORY INSPECTION")
print("=" * 70)

# Inventory event history
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

inventory_events = cursor.fetchall()

print("\nINVENTORY EVENTS")
print("-" * 70)

if inventory_events:
    for row in inventory_events:
        print(
            f"{row['event_id']} | "
            f"SKU: {row['sku_id']} | "
            f"Location: {row['location_id']} | "
            f"Type: {row['event_type']} | "
            f"Quantity: {row['quantity']} {row['unit_of_measure']} | "
            f"Date: {row['event_date']} | "
            f"Source: {row['source_ref']}"
        )
else:
    print("No inventory events found.")

# Purchase order event history
cursor.execute("""
    SELECT
        po_event_id,
        po_id,
        event_type,
        event_date,
        quantity,
        source_ref
    FROM purchase_order_event
    ORDER BY event_date, po_event_id
""")

po_events = cursor.fetchall()

print("\nPURCHASE ORDER EVENTS")
print("-" * 70)

if po_events:
    for row in po_events:
        print(
            f"{row['po_event_id']} | "
            f"PO: {row['po_id']} | "
            f"Type: {row['event_type']} | "
            f"Quantity: {row['quantity']} | "
            f"Date: {row['event_date']} | "
            f"Source: {row['source_ref']}"
        )
else:
    print("No purchase order events found.")

# Mitigation event history
cursor.execute("""
    SELECT
        mitigation_event_id,
        option_id,
        event_type,
        event_date,
        decision_reason
    FROM mitigation_event
    ORDER BY event_date, mitigation_event_id
""")

mitigation_events = cursor.fetchall()

print("\nMITIGATION EVENTS")
print("-" * 70)

if mitigation_events:
    for row in mitigation_events:
        print(
            f"{row['mitigation_event_id']} | "
            f"Option: {row['option_id']} | "
            f"Type: {row['event_type']} | "
            f"Date: {row['event_date']} | "
            f"Reason: {row['decision_reason']}"
        )
else:
    print("No mitigation events found.")

print("\nEVENT HISTORY COUNTS")
print("-" * 70)
print("Inventory events:", len(inventory_events))
print("Purchase order events:", len(po_events))
print("Mitigation events:", len(mitigation_events))

connection.close()

print("\nEVENT HISTORY INSPECTION COMPLETED")
