
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

cursor.execute("""
SELECT
    po.po_id,
    s.supplier_name,
    sku.sku_name,
    pol.order_quantity,
    pol.received_quantity,
    pol.order_quantity - pol.received_quantity AS pending_quantity,
    po.status
FROM purchase_order po
JOIN supplier s ON po.supplier_id = s.supplier_id
JOIN purchase_order_line pol ON po.po_id = pol.po_id
JOIN sku ON pol.sku_id = sku.sku_id
ORDER BY po.po_id
""")

records = cursor.fetchall()

print("PURCHASE ORDER STATUS REPORT")
print("=" * 55)

for record in records:
    print("Purchase Order:", record["po_id"])
    print("Supplier:", record["supplier_name"])
    print("Product:", record["sku_name"])
    print("Ordered Quantity:", record["order_quantity"])
    print("Received Quantity:", record["received_quantity"])
    print("Pending Quantity:", record["pending_quantity"])
    print("Status:", record["status"])
    print("-" * 55)

connection.close()
