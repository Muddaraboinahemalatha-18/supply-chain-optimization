
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

cursor.execute("""
SELECT
    sku.sku_name,
    inventory.on_hand_quantity,
    inventory.reserved_quantity,
    inventory.on_hand_quantity - inventory.reserved_quantity
FROM inventory
JOIN sku ON inventory.sku_id = sku.sku_id
""")

records = cursor.fetchall()

print("UPDATED INVENTORY REPORT")
print("=" * 40)

for record in records:
    print("Product:", record["sku_name"])
    print("On Hand:", record["on_hand_quantity"])
    print("Reserved:", record["reserved_quantity"])
    print("Available:", record[3])
    print("-" * 40)

connection.close()
