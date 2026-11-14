
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

cursor.execute("""
SELECT
    ie.event_id,
    sku.sku_name,
    location.location_name,
    ie.event_type,
    ie.quantity,
    ie.event_date,
    ie.source_ref
FROM inventory_event ie
JOIN sku ON ie.sku_id = sku.sku_id
JOIN location ON ie.location_id = location.location_id
ORDER BY ie.event_date, ie.event_id
""")

records = cursor.fetchall()

print("INVENTORY EVENT HISTORY")
print("=" * 50)

for record in records:
    print("Event ID:", record["event_id"])
    print("Product:", record["sku_name"])
    print("Location:", record["location_name"])
    print("Event Type:", record["event_type"])
    print("Quantity:", record["quantity"])
    print("Event Date:", record["event_date"])
    print("Reference:", record["source_ref"])
    print("-" * 50)

connection.close()
