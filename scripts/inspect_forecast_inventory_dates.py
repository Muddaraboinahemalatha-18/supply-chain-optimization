
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 75)
print("FORECAST AND INVENTORY DATE INSPECTION")
print("=" * 75)

print("\n1. FORECAST RECORDS")

cursor.execute("""
    SELECT
        f.forecast_id,
        s.sku_name,
        f.location_id,
        f.forecast_week,
        f.forecast_quantity,
        s.unit_of_measure
    FROM forecast_demand f
    JOIN sku s ON f.sku_id = s.sku_id
    ORDER BY f.forecast_id
""")

for row in cursor.fetchall():
    print(dict(row))

print("\n2. INVENTORY SNAPSHOT DATES")

cursor.execute("""
    SELECT
        s.sku_name,
        i.location_id,
        i.inventory_date,
        i.on_hand_quantity,
        i.reserved_quantity,
        i.on_hand_quantity - i.reserved_quantity
            AS available_quantity,
        i.unit_of_measure
    FROM inventory i
    JOIN sku s ON i.sku_id = s.sku_id
    ORDER BY s.sku_name
""")

for row in cursor.fetchall():
    print(dict(row))

print("\n3. INVENTORY EVENT TYPES")

cursor.execute("""
    SELECT
        event_type,
        COUNT(*) AS event_count
    FROM inventory_event
    GROUP BY event_type
    ORDER BY event_type
""")

for row in cursor.fetchall():
    print(dict(row))

connection.close()

print("\n" + "=" * 75)
print("INSPECTION COMPLETED")
print("No database records were modified.")
print("=" * 75)
