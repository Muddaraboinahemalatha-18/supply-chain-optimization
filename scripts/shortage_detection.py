
import sqlite3

# Connect to database
connection = sqlite3.connect("data/supply_chain.db")

cursor = connection.cursor()

# Get demand and inventory details
cursor.execute("""
SELECT
    forecast_demand.forecast_id,
    forecast_demand.sku_id,
    forecast_demand.location_id,
    forecast_demand.forecast_week,
    forecast_demand.forecast_quantity,
    inventory.on_hand_quantity - inventory.reserved_quantity
FROM forecast_demand
JOIN inventory
ON forecast_demand.sku_id = inventory.sku_id
AND forecast_demand.location_id = inventory.location_id
""")

records = cursor.fetchall()

print("SHORTAGE DETECTION")
print("--------------------------------")

for record in records:

    forecast_id = record[0]
    sku_id = record[1]
    location_id = record[2]
    week = record[3]
    demand = record[4]
    available = record[5]

    shortage = demand - available

    if shortage > 0:

        shortage_id = "SH_" + forecast_id

        cursor.execute("""
        INSERT OR IGNORE INTO shortage
        (shortage_id, sku_id, location_id,
        shortage_week, demand_quantity,
        available_quantity, shortage_quantity,
        priority, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            shortage_id,
            sku_id,
            location_id,
            week,
            demand,
            available,
            shortage,
            "HIGH",
            "OPEN"
        ))

        print("SKU:", sku_id)
        print("Shortage Quantity:", shortage)
        print("Status: Shortage Recorded")
        print("--------------------------------")

connection.commit()
connection.close()

print("Shortage detection completed!")
