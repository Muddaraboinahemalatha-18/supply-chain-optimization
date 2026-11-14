
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

cursor.execute("""
UPDATE inventory
SET on_hand_quantity = on_hand_quantity - (
    SELECT SUM(pol.received_quantity)
    FROM purchase_order_line pol
    JOIN purchase_order po ON po.po_id = pol.po_id
    WHERE pol.sku_id = inventory.sku_id
    AND pol.location_id = inventory.location_id
    AND po.status = 'RECEIVED'
)
WHERE EXISTS (
    SELECT 1
    FROM purchase_order_line pol
    JOIN purchase_order po ON po.po_id = pol.po_id
    WHERE pol.sku_id = inventory.sku_id
    AND pol.location_id = inventory.location_id
    AND po.status = 'RECEIVED'
)
""")

connection.commit()
connection.close()

print("Duplicate inventory quantities corrected!")
