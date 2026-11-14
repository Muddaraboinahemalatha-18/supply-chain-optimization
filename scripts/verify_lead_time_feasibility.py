
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 80)
print("LEAD TIME FEASIBILITY - SOURCE DATA AUDIT")
print("=" * 80)

# Inspect actual inbound-order table structure
for table in ["purchase_order", "purchase_order_line", "inbound_order"]:
    print("\nTABLE:", table)
    cursor.execute(f"PRAGMA table_info({table})")

    for column in cursor.fetchall():
        print(
            column["name"],
            "| Type:", column["type"],
            "| Required:", bool(column["notnull"]),
            "| Primary key:", bool(column["pk"])
        )

# Display actual purchase and inbound dates
print("\n" + "=" * 80)
print("PURCHASE ORDER AND INBOUND DATE DETAILS")
print("=" * 80)

cursor.execute("""
    SELECT
        sh.shortage_id,
        sh.shortage_week,
        sh.location_id,

        s.sku_name,

        po.po_id,
        po.order_date,
        po.expected_date,
        po.status AS po_status,

        pol.po_line_id,
        pol.order_quantity,
        pol.received_quantity,

        ib.inbound_id,
        ib.expected_arrival_date,
        ib.actual_arrival_date,
        ib.inbound_quantity,
        ib.received_quantity AS inbound_received_quantity,
        ib.status AS inbound_status,

        sup.supplier_name,
        lt.lead_time_days

    FROM shortage sh

    JOIN sku s
        ON sh.sku_id = s.sku_id

    JOIN purchase_order_line pol
        ON sh.sku_id = pol.sku_id
        AND sh.location_id = pol.location_id

    JOIN purchase_order po
        ON pol.po_id = po.po_id

    JOIN inbound_order ib
        ON pol.po_line_id = ib.po_line_id

    JOIN supplier sup
        ON po.supplier_id = sup.supplier_id

    JOIN supplier_sku_policy pol2
        ON pol2.sku_id = sh.sku_id
        AND pol2.supplier_id = sup.supplier_id

    JOIN lead_time lt
        ON lt.supplier_id = sup.supplier_id
        AND lt.location_id = sh.location_id

    WHERE pol2.effective_from <= '2026-11-12'
      AND (
          pol2.effective_to IS NULL
          OR pol2.effective_to >= '2026-11-12'
      )
      AND lt.effective_from <= '2026-11-12'
      AND (
          lt.effective_to IS NULL
          OR lt.effective_to >= '2026-11-12'
      )

    ORDER BY sh.shortage_id
""")

records = cursor.fetchall()

for row in records:
    print("\n" + "-" * 80)

    for key in row.keys():
        print(f"{key}: {row[key]}")

print("\n" + "=" * 80)
print("TOTAL SOURCE RECORDS:", len(records))
print("DATE AUDIT EXTRACTION COMPLETED")
print("No database records were modified.")
print("=" * 80)

connection.close()
