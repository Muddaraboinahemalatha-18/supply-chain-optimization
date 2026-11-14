
import sqlite3

connection = sqlite3.connect("data/supply_chain.db")

cursor = connection.cursor()

# Display SKU data
cursor.execute("SELECT * FROM sku")

records = cursor.fetchall()

print("PRODUCT DETAILS")
print("--------------------------")

for record in records:
    print(record)

print("\nTotal Products:", len(records))

connection.close()
