
import sqlite3

# Connect to database
connection = sqlite3.connect("data/supply_chain.db")

cursor = connection.cursor()

# Get approved suppliers for shortage products
cursor.execute("""
SELECT
    shortage.shortage_id,
    sku.sku_name,
    shortage.shortage_quantity,
    supplier.supplier_id,
    supplier.supplier_name,
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
ORDER BY supplier_sku.unit_cost ASC
""")

records = cursor.fetchall()

print("SUPPLIER REPLENISHMENT ANALYSIS")
print("------------------------------------------")

processed = set()

for record in records:

    shortage_id = record[0]

    # Select only the lowest-cost supplier
    if shortage_id in processed:
        continue

    processed.add(shortage_id)

    product = record[1]
    quantity = record[2]
    supplier_id = record[3]
    supplier_name = record[4]
    unit_cost = record[5]

    estimated_cost = quantity * unit_cost

    option_id = "OPT_" + shortage_id

    # Save replenishment recommendation
    cursor.execute("""
    INSERT OR IGNORE INTO mitigation_option
    (option_id, shortage_id, option_type,
    description, proposed_quantity,
    estimated_cost, policy_compliant)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        option_id,
        shortage_id,
        "PURCHASE",
        "Supplier: " + supplier_name,
        quantity,
        estimated_cost,
        1
    ))

    print("Product:", product)
    print("Supplier:", supplier_name)
    print("Shortage Quantity:", quantity)
    print("Unit Cost:", unit_cost)
    print("Estimated Cost:", estimated_cost)
    print("------------------------------------------")

connection.commit()
connection.close()

print("Supplier replenishment analysis completed!")
