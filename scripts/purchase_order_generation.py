
import sys
from pathlib import Path

# Get the main project folder
BASE_DIR = Path(__file__).resolve().parents[1]

# Add project folder to Python path
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("PURCHASE ORDER GENERATION")
print("=" * 45)

# Get products with shortages
cursor.execute("""
    SELECT 
        s.shortage_id,
        s.sku_id,
        s.location_id,
        s.shortage_quantity,
        sk.sku_name
    FROM shortage s
    JOIN sku sk ON s.sku_id = sk.sku_id
    WHERE s.status = 'OPEN'
""")

shortages = cursor.fetchall()

for shortage in shortages:

    shortage_id = shortage["shortage_id"]
    sku_id = shortage["sku_id"]
    location_id = shortage["location_id"]
    required_quantity = shortage["shortage_quantity"]
    product = shortage["sku_name"]

    # Find a suitable supplier
    cursor.execute("""
        SELECT 
            su.supplier_id,
            su.supplier_name,
            su.reliability_score,
            ss.unit_cost,
            sc.maximum_quantity
        FROM supplier_sku ss
        JOIN supplier su
            ON ss.supplier_id = su.supplier_id
        JOIN supplier_capacity sc
            ON sc.supplier_id = su.supplier_id
            AND sc.sku_id = ss.sku_id
        WHERE ss.sku_id = ?
        AND ss.is_approved = 1
        AND su.is_active = 1
        ORDER BY su.reliability_score DESC, ss.unit_cost ASC
        LIMIT 1
    """, (sku_id,))

    supplier = cursor.fetchone()

    if supplier is None:
        print(f"\nProduct: {product}")
        print("No suitable supplier found!")
        continue

    supplier_id = supplier["supplier_id"]
    supplier_name = supplier["supplier_name"]
    unit_cost = supplier["unit_cost"]
    capacity = supplier["maximum_quantity"]

    order_quantity = min(required_quantity, capacity)
    total_cost = order_quantity * unit_cost

    # Generate purchase order ID
    po_id = "PO_" + shortage_id

    # Insert purchase order
    cursor.execute("""
        INSERT INTO purchase_order
        (po_id, supplier_id, order_date, expected_date, status)
        VALUES (?, ?, DATE('now'), DATE('now', '+7 days'), 'CREATED')
    """, (po_id, supplier_id))

    # Insert purchase order line
    cursor.execute("""
        INSERT INTO purchase_order_line
        (po_line_id, po_id, sku_id, location_id,
         order_quantity, received_quantity, unit_of_measure)
        SELECT ?, ?, ?, ?, ?, 0, unit_of_measure
        FROM sku
        WHERE sku_id = ?
    """, (
        "LINE_" + shortage_id,
        po_id,
        sku_id,
        location_id,
        order_quantity,
        sku_id
    ))

    print(f"\nProduct: {product}")
    print(f"Selected Supplier: {supplier_name}")
    print(f"Required Quantity: {required_quantity}")
    print(f"Order Quantity: {order_quantity}")
    print(f"Unit Cost: {unit_cost}")
    print(f"Total Estimated Cost: {total_cost}")

    if order_quantity < required_quantity:
        print("Status: Partially Covered - Capacity Limited")
    else:
        print("Status: Purchase Order Generated")

connection.commit()
connection.close()

print("\nPurchase order generation completed!")
