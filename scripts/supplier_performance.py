
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

cursor.execute("""
SELECT
    s.supplier_name,
    s.reliability_score,
    COUNT(DISTINCT po.po_id) AS total_orders,
    COALESCE(SUM(pol.received_quantity), 0) AS total_quantity_supplied,
    COALESCE(SUM(pol.received_quantity * ss.unit_cost), 0) AS total_order_value
FROM supplier s
LEFT JOIN purchase_order po
    ON s.supplier_id = po.supplier_id
LEFT JOIN purchase_order_line pol
    ON po.po_id = pol.po_id
LEFT JOIN supplier_sku ss
    ON ss.supplier_id = po.supplier_id
    AND ss.sku_id = pol.sku_id
GROUP BY s.supplier_id, s.supplier_name, s.reliability_score
ORDER BY s.reliability_score DESC
""")

records = cursor.fetchall()

print("SUPPLIER PERFORMANCE REPORT")
print("=" * 55)

for record in records:
    print("Supplier:", record["supplier_name"])
    print("Reliability Score:", record["reliability_score"])
    print("Total Orders:", record["total_orders"])
    print("Total Quantity Supplied:", record["total_quantity_supplied"])
    print("Total Order Value: Rs.", record["total_order_value"])
    print("-" * 55)

connection.close()
