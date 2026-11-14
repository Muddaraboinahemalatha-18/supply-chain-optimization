
import sys
from pathlib import Path

# Add the project root directory to Python's import path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 60)
print("SKU SUBSTITUTE DATA INSPECTION")
print("=" * 60)

cursor.execute("""
    SELECT
        substitute_id,
        original_sku_id,
        substitute_sku_id,
        is_approved,
        conversion_factor,
        effective_from,
        effective_to
    FROM sku_substitute
    ORDER BY substitute_id
""")

substitutes = cursor.fetchall()

if substitutes:
    print("\nEXISTING SUBSTITUTE RELATIONSHIPS")
    print("-" * 60)

    for row in substitutes:
        print(
            f"ID: {row['substitute_id']} | "
            f"Original SKU: {row['original_sku_id']} | "
            f"Substitute SKU: {row['substitute_sku_id']} | "
            f"Approved: {row['is_approved']} | "
            f"Conversion: {row['conversion_factor']} | "
            f"From: {row['effective_from']} | "
            f"To: {row['effective_to']}"
        )
else:
    print("\nNo substitute relationships found.")

cursor.execute("""
    SELECT sku_id, sku_name, category, unit_of_measure
    FROM sku
    ORDER BY sku_id
""")

skus = cursor.fetchall()

print("\nAVAILABLE SKUs")
print("-" * 60)

for sku in skus:
    print(
        f"{sku['sku_id']} | "
        f"{sku['sku_name']} | "
        f"Category: {sku['category']} | "
        f"UOM: {sku['unit_of_measure']}"
    )

print("\nTOTAL SUBSTITUTE RELATIONSHIPS:", len(substitutes))
print("TOTAL SKUs:", len(skus))

connection.close()

print("\nINSPECTION COMPLETED")
