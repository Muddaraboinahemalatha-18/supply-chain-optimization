
import sqlite3

connection = sqlite3.connect("data/supply_chain.db")
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
    print("Product:", record[0])
    print("On Hand:", record[1])
    print("Reserved:", record[2])
    print("Available:", record[3])
    print("-" * 40)

connection.close()
