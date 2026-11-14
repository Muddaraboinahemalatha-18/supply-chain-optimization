
import sqlite3

# Connect to database
connection = sqlite3.connect("data/supply_chain.db")

cursor = connection.cursor()

# Get shortage and supplier details
cursor.execute("""
SELECT
    shortage.shortage_id,
    sku.sku_name,
    shortage.shortage_quantity,
    supplier.supplier_id,
    supplier.supplier_name,
    supplier.reliability_score,
    supplier_sku.unit_cost
FROM shortage
JOIN sku
ON shortage.sku_id = sku.sku_id
JOIN supplier_sku
ON shortage.sku_id = supplier_sku.sku_id
JOIN supplier
ON supplier_sku.supplier_id = supplier.supplier_id
WHERE supplier_sku.is_approved = 1
AND supplier.is_active = 1
AND shortage.status = 'OPEN'
ORDER BY shortage.shortage_id, supplier_sku.unit_cost
""")

records = cursor.fetchall()

print("SUPPLIER COST OPTIMIZATION")
print("------------------------------------------")

processed = set()

for record in records:

    shortage_id = record[0]

    # Process each shortage only once
    if shortage_id in processed:
        continue

    processed.add(shortage_id)

    product = record[1]
    quantity = record[2]
    supplier_id = record[3]
    supplier_name = record[4]
    reliability = record[5]
    unit_cost = record[6]

    total_cost = quantity * unit_cost

    print("Product:", product)
    print("Selected Supplier:", supplier_name)
    print("Supplier Reliability:", reliability)
    print("Unit Cost:", unit_cost)
    print("Required Quantity:", quantity)
    print("Total Estimated Cost:", total_cost)

    print("------------------------------------------")

print("Cost optimization completed!")

connection.close()
