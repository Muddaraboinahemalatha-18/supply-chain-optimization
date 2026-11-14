
import sqlite3

# Connect to database
connection = sqlite3.connect("data/supply_chain.db")

cursor = connection.cursor()

# Get shortage records
cursor.execute("""
SELECT
    shortage.shortage_id,
    sku.sku_name,
    shortage.demand_quantity,
    shortage.available_quantity,
    shortage.shortage_quantity,
    shortage.priority,
    shortage.status
FROM shortage
JOIN sku
ON shortage.sku_id = sku.sku_id
""")

records = cursor.fetchall()

print("SHORTAGE REPORT")
print("------------------------------------------")

for record in records:
    print("Shortage ID:", record[0])
    print("Product:", record[1])
    print("Demand:", record[2])
    print("Available:", record[3])
    print("Shortage:", record[4])
    print("Priority:", record[5])
    print("Status:", record[6])
    print("------------------------------------------")

print("Total Shortage Records:", len(records))

connection.close()
