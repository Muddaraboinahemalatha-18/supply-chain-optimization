
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 80)
print("MITIGATION OPTION COMPLIANCE AUDIT")
print("=" * 80)

cursor.execute("""
    SELECT
        sh.shortage_id,
        sh.location_id,
        sh.shortage_week,
        sh.status AS shortage_status,
        sh.shortage_quantity,

        s.sku_name,
        s.unit_of_measure,

        mo.option_id,
        mo.option_type,
        mo.description,
        mo.proposed_quantity,
        mo.estimated_cost,
        mo.policy_compliant,

        sup.supplier_id,
        sup.supplier_name,
        sup.is_active AS supplier_active,

        ss.is_approved,
        ss.unit_cost,

        pol.minimum_order_quantity,
        pol.effective_from AS policy_effective_from,
        pol.effective_to AS policy_effective_to,

        sc.maximum_quantity,
        sc.capacity_week,

        lt.lead_time_days,
        lt.effective_from AS lead_effective_from,
        lt.effective_to AS lead_effective_to

    FROM mitigation_option mo

    JOIN shortage sh
        ON mo.shortage_id = sh.shortage_id

    JOIN sku s
        ON sh.sku_id = s.sku_id

    JOIN supplier sup
        ON sup.supplier_name =
           TRIM(REPLACE(mo.description, 'Supplier: ', ''))

    LEFT JOIN supplier_sku ss
        ON ss.supplier_id = sup.supplier_id
        AND ss.sku_id = sh.sku_id

    LEFT JOIN supplier_sku_policy pol
        ON pol.supplier_id = sup.supplier_id
        AND pol.sku_id = sh.sku_id

    LEFT JOIN supplier_capacity sc
        ON sc.supplier_id = sup.supplier_id
        AND sc.sku_id = sh.sku_id
        AND sc.capacity_week = sh.shortage_week

    LEFT JOIN lead_time lt
        ON lt.supplier_id = sup.supplier_id
        AND lt.location_id = sh.location_id

    WHERE mo.option_type = 'PURCHASE'

    ORDER BY sh.shortage_id, mo.option_id
""")

records = cursor.fetchall()

print("\nTOTAL PURCHASE MITIGATION RECORDS:", len(records))

for row in records:
    print("\n" + "-" * 80)

    print("Shortage ID:", row["shortage_id"])
    print("Location ID:", row["location_id"])
    print("Shortage week:", row["shortage_week"])
    print("Product:", row["sku_name"])
    print("Unit:", row["unit_of_measure"])
    print("Shortage status:", row["shortage_status"])
    print("Historical shortage:", row["shortage_quantity"])

    print("\nMITIGATION DETAILS")
    print("Option ID:", row["option_id"])
    print("Option type:", row["option_type"])
    print("Description:", row["description"])
    print("Proposed quantity:", row["proposed_quantity"])
    print("Estimated cost:", row["estimated_cost"])
    print("Stored policy compliant:", row["policy_compliant"])

    print("\nSUPPLIER DETAILS")
    print("Supplier ID:", row["supplier_id"])
    print("Supplier:", row["supplier_name"])
    print("Supplier active:", row["supplier_active"])
    print("Supplier SKU approved:", row["is_approved"])
    print("Supplier unit cost:", row["unit_cost"])

    print("\nPOLICY DETAILS")
    print("Minimum order quantity:", row["minimum_order_quantity"])
    print("Policy effective from:", row["policy_effective_from"])
    print("Policy effective to:", row["policy_effective_to"])

    print("\nCAPACITY DETAILS")
    print("Capacity week:", row["capacity_week"])
    print("Maximum quantity:", row["maximum_quantity"])

    print("\nLOCATION-SPECIFIC LEAD TIME")
    print("Lead time days:", row["lead_time_days"])
    print("Lead time effective from:", row["lead_effective_from"])
    print("Lead time effective to:", row["lead_effective_to"])

    print("\nBASIC COMPLIANCE CHECKS")

    checks = {
        "Supplier active":
            row["supplier_active"] == 1,

        "Supplier SKU approved":
            row["is_approved"] == 1,

        "MOQ satisfied":
            row["minimum_order_quantity"] is not None
            and row["proposed_quantity"] >= row["minimum_order_quantity"],

        "Supplier capacity available":
            row["maximum_quantity"] is not None
            and row["proposed_quantity"] <= row["maximum_quantity"],

        "Lead time available":
            row["lead_time_days"] is not None,

        "Supplier unit cost available":
            row["unit_cost"] is not None,

        "Estimated cost matches":
            row["unit_cost"] is not None
            and abs(
                row["estimated_cost"]
                - row["proposed_quantity"] * row["unit_cost"]
            ) < 0.01
    }

    for check_name, passed in checks.items():
        print(check_name + ":", "PASSED" if passed else "FAILED")

    print("Basic checks passed:", sum(checks.values()), "/", len(checks))

print("\n" + "=" * 80)
print("MITIGATION AUDIT EXTRACTION COMPLETED")
print("No database records were modified.")
print("=" * 80)

connection.close()
