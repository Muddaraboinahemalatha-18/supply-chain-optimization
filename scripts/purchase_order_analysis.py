
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("PURCHASE ORDER ANALYSIS")
print("=" * 50)

cursor.execute("""
    SELECT
        po.po_id,
        su.supplier_name,
        po.order_date,
        po.expected_date,
        po.status,
        sk.sku_name,
        pol.order_quantity,
        pol.received_quantity,
        pol.unit_of_measure,
        sk.unit_cost
    FROM purchase_order po
    JOIN supplier su
        ON po.supplier_id = su.supplier_id
    JOIN purchase_order_line pol
        ON po.po_id = pol.po_id
    JOIN sku sk
        ON pol.sku_id = sk.sku_id
    ORDER BY po.order_date DESC
""")

orders = cursor.fetchall()

if not orders:
    print("No purchase orders found.")

else:
    total_orders = 0
    total_cost = 0

    for order in orders:
        cost = order["order_quantity"] * order["unit_cost"]

        print("\nPurchase Order ID:", order["po_id"])
        print("Supplier:", order["supplier_name"])
        print("Product:", order["sku_name"])
        print("Order Date:", order["order_date"])
        print("Expected Date:", order["expected_date"])
        print("Status:", order["status"])
        print("Order Quantity:", order["order_quantity"])
        print("Received Quantity:", order["received_quantity"])
        print("Unit:", order["unit_of_measure"])
        print("Estimated Cost:", cost)

        print("-" * 50)

        total_orders += 1
        total_cost += cost

    print("\nPURCHASE ORDER SUMMARY")
    print("=" * 50)
    print("Total Purchase Orders:", total_orders)
    print("Total Estimated Cost:", total_cost)

connection.close()

print("\nPurchase order analysis completed!")
