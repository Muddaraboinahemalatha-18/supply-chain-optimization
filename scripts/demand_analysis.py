
import sqlite3

# Connect to database
connection = sqlite3.connect("data/supply_chain.db")

cursor = connection.cursor()

# Compare demand with available inventory
cursor.execute("""
SELECT
    sku.sku_name,
    forecast_demand.forecast_quantity,
    inventory.on_hand_quantity - inventory.reserved_quantity
FROM forecast_demand
JOIN sku
ON forecast_demand.sku_id = sku.sku_id
JOIN inventory
ON forecast_demand.sku_id = inventory.sku_id
AND forecast_demand.location_id = inventory.location_id
""")

records = cursor.fetchall()

print("DEMAND VS INVENTORY ANALYSIS")
print("------------------------------------------")

for record in records:

    product = record[0]
    demand = record[1]
    available = record[2]

    print("Product:", product)
    print("Forecast Demand:", demand)
    print("Available Inventory:", available)

    if available >= demand:
        print("Status: Sufficient Stock")
    else:
        shortage = demand - available
        print("Status: Stock Shortage")
        print("Shortage Quantity:", shortage)

    print("------------------------------------------")

connection.close()
