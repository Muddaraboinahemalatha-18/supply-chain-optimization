
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 70)
print("SHORTAGE AND MITIGATION INSPECTION")
print("=" * 70)

# Shortage records
cursor.execute("""
    SELECT
        sh.shortage_id,
        sh.sku_id,
        s.sku_name,
        sh.location_id,
        l.location_name,
        sh.shortage_week,
        sh.demand_quantity,
        sh.available_quantity,
        sh.shortage_quantity,
        sh.priority,
        sh.status
    FROM shortage sh
    JOIN sku s ON sh.sku_id = s.sku_id
    JOIN location l ON sh.location_id = l.location_id
    ORDER BY sh.shortage_id
""")

shortages = cursor.fetchall()

print("\nSHORTAGE DETAILS")
print("-" * 70)

for row in shortages:
    print(
        f"\nShortage ID: {row['shortage_id']}\n"
        f"Product: {row['sku_name']}\n"
        f"Location: {row['location_name']}\n"
        f"Week: {row['shortage_week']}\n"
        f"Demand: {row['demand_quantity']}\n"
        f"Available: {row['available_quantity']}\n"
        f"Shortage quantity: {row['shortage_quantity']}\n"
        f"Priority: {row['priority']}\n"
        f"Status: {row['status']}"
    )

# Mitigation options
cursor.execute("""
    SELECT
        mo.option_id,
        mo.shortage_id,
        mo.option_type,
        mo.description,
        mo.proposed_quantity,
        mo.estimated_cost,
        mo.policy_compliant
    FROM mitigation_option mo
    ORDER BY mo.shortage_id, mo.option_id
""")

options = cursor.fetchall()

print("\nMITIGATION OPTIONS")
print("-" * 70)

if options:
    for row in options:
        print(
            f"\nOption ID: {row['option_id']}\n"
            f"Shortage ID: {row['shortage_id']}\n"
            f"Type: {row['option_type']}\n"
            f"Description: {row['description']}\n"
            f"Proposed quantity: {row['proposed_quantity']}\n"
            f"Estimated cost: {row['estimated_cost']}\n"
            f"Policy compliant: {row['policy_compliant']}"
        )
else:
    print("No mitigation options found.")

# Shortages without mitigation options
cursor.execute("""
    SELECT
        sh.shortage_id,
        sh.sku_id,
        sh.location_id,
        sh.shortage_quantity
    FROM shortage sh
    LEFT JOIN mitigation_option mo
        ON sh.shortage_id = mo.shortage_id
    WHERE mo.option_id IS NULL
""")

missing_options = cursor.fetchall()

print("\nSHORTAGES WITHOUT MITIGATION OPTIONS")
print("-" * 70)

if missing_options:
    for row in missing_options:
        print(
            f"{row['shortage_id']} | "
            f"SKU: {row['sku_id']} | "
            f"Location: {row['location_id']} | "
            f"Shortage: {row['shortage_quantity']}"
        )
else:
    print("Every shortage has at least one mitigation option.")

print("\nSUMMARY")
print("-" * 70)
print("Total shortages:", len(shortages))
print("Total mitigation options:", len(options))
print("Shortages without options:", len(missing_options))

connection.close()

print("\nINSPECTION COMPLETED")
