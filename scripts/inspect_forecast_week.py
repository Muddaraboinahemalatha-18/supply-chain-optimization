
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 70)
print("FORECAST WEEK DATE INSPECTION")
print("=" * 70)

cursor.execute("""
    SELECT
        forecast_id,
        sku_id,
        location_id,
        forecast_week,
        forecast_quantity,
        forecast_version
    FROM forecast_demand
    ORDER BY forecast_week, forecast_id
""")

records = cursor.fetchall()

for row in records:
    print("\nForecast ID:", row["forecast_id"])
    print("SKU:", row["sku_id"])
    print("Location:", row["location_id"])
    print("Forecast week:", row["forecast_week"])
    print("Demand:", row["forecast_quantity"])
    print("Version:", row["forecast_version"])

print("\nTOTAL FORECAST RECORDS:", len(records))

connection.close()

print("\nINSPECTION COMPLETED")
print("No database records were modified.")
