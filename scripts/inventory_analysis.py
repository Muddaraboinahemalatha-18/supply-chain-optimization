
import sqlite3

# Connect to database
connection = sqlite3.connect("data/supply_chain.db")

cursor = connection.cursor()

# Get inventory details
cursor.execute("""
SELECT
    sku.sku_name,
    location.location_name,
    inventory.on_hand_quantity,
    inventory.reserved_quantity,
    (inventory.on_hand_quantity - inventory.reserved_quantity)
    AS available_quantity
FROM inventory
JOIN sku
ON inventory.sku_id = sku.sku_id
JOIN location
ON inventory.location_id = location.location_id
""")

records = cursor.fetchall()

print("SUPPLY CHAIN INVENTORY ANALYSIS")
print("------------------------------------------")

for record in records:
    print("Product:", record[0])
    print("Location:", record[1])
    print("On Hand:", record[2])
    print("Reserved:", record[3])
    print("Available Inventory:", record[4])
    print("------------------------------------------")

connection.close()
