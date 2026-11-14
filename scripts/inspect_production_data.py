
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "supply_chain.db"

connection = sqlite3.connect(DB_PATH)

print("PRODUCTION DATA INSPECTION")
print("=" * 50)

try:
    cursor = connection.cursor()

    # Inspect existing products
    print("\n1. SKU MASTER DATA")
    print("-" * 50)

    skus = cursor.execute(
        """
        SELECT sku_id, sku_name, category, unit_of_measure
        FROM sku
        ORDER BY sku_id
        """
    ).fetchall()

    for row in skus:
        print(
            f"SKU: {row[0]} | "
            f"Name: {row[1]} | "
            f"Category: {row[2]} | "
            f"Unit: {row[3]}"
        )

    # Inspect production capacity
    print("\n2. PRODUCTION CAPACITY")
    print("-" * 50)

    capacities = cursor.execute(
        "SELECT * FROM production_capacity"
    ).fetchall()

    if capacities:
        for row in capacities:
            print(row)
    else:
        print("No production capacity records found.")

    # Inspect production plans
    print("\n3. PRODUCTION PLANS")
    print("-" * 50)

    plans = cursor.execute(
        "SELECT * FROM production_plan"
    ).fetchall()

    if plans:
        for row in plans:
            print(row)
    else:
        print("No production plans found.")

    # Inspect BOM
    print("\n4. BILL OF MATERIALS")
    print("-" * 50)

    bom_records = cursor.execute(
        "SELECT * FROM bom"
    ).fetchall()

    if bom_records:
        for row in bom_records:
            print(row)
    else:
        print("No BOM records found.")

finally:
    connection.close()
