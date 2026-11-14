
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 65)
print("FORECAST DEMAND COVERAGE INSPECTION")
print("=" * 65)

# Weekly demand summary
cursor.execute("""
    SELECT
        forecast_week,
        COUNT(*) AS total_records,
        SUM(forecast_quantity) AS total_demand
    FROM forecast_demand
    GROUP BY forecast_week
    ORDER BY forecast_week
""")

weekly_data = cursor.fetchall()

print("\nWEEKLY FORECAST SUMMARY")
print("-" * 65)

for row in weekly_data:
    print(
        f"Week: {row['forecast_week']} | "
        f"Records: {row['total_records']} | "
        f"Total demand: {row['total_demand']}"
    )

# SKU and location coverage
cursor.execute("""
    SELECT
        f.sku_id,
        s.sku_name,
        f.location_id,
        l.location_name,
        COUNT(*) AS forecast_records,
        SUM(f.forecast_quantity) AS total_demand,
        MIN(f.forecast_week) AS first_week,
        MAX(f.forecast_week) AS last_week
    FROM forecast_demand f
    JOIN sku s ON f.sku_id = s.sku_id
    JOIN location l ON f.location_id = l.location_id
    GROUP BY
        f.sku_id,
        s.sku_name,
        f.location_id,
        l.location_name
    ORDER BY f.sku_id, f.location_id
""")

coverage = cursor.fetchall()

print("\nSKU-LOCATION FORECAST COVERAGE")
print("-" * 65)

for row in coverage:
    print(
        f"{row['sku_name']} | "
        f"{row['location_name']} | "
        f"Records: {row['forecast_records']} | "
        f"Demand: {row['total_demand']} | "
        f"From: {row['first_week']} | "
        f"To: {row['last_week']}"
    )

print("\nTOTAL FORECAST RECORDS:", sum(
    row["total_records"] for row in weekly_data
))

print("TOTAL WEEKS:", len(weekly_data))
print("TOTAL SKU-LOCATION COMBINATIONS:", len(coverage))

connection.close()

print("\nINSPECTION COMPLETED")
