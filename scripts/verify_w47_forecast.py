
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 75)
print("W46 AND W47 FORECAST VERIFICATION")
print("=" * 75)

print("\n1. FORECAST COUNTS BY WEEK")

cursor.execute("""
    SELECT
        forecast_week,
        COUNT(*) AS record_count,
        SUM(forecast_quantity) AS total_quantity
    FROM forecast_demand
    GROUP BY forecast_week
    ORDER BY forecast_week
""")

for row in cursor.fetchall():
    print(dict(row))

print("\n2. W46 HISTORICAL FORECASTS")

cursor.execute("""
    SELECT forecast_id, sku_id, location_id,
           forecast_week, forecast_quantity, forecast_version
    FROM forecast_demand
    WHERE forecast_week = '2026-W46'
    ORDER BY forecast_id
""")

w46_records = cursor.fetchall()

for row in w46_records:
    print(dict(row))

expected_w46 = {
    "F001": 600.0,
    "F002": 250.0,
    "F003": 300.0,
    "F004": 100.0,
    "F005": 150.0
}

w46_valid = (
    len(w46_records) == 5
    and {
        row["forecast_id"]: row["forecast_quantity"]
        for row in w46_records
    } == expected_w46
)

print("\nW46 historical data preserved:", w46_valid)

print("\n3. W47 SYNTHETIC FORECASTS")

cursor.execute("""
    SELECT forecast_id, sku_id, location_id,
           forecast_week, forecast_quantity, forecast_version
    FROM forecast_demand
    WHERE forecast_week = '2026-W47'
    ORDER BY forecast_id
""")

w47_records = cursor.fetchall()

for row in w47_records:
    print(dict(row))

expected_w47 = {
    "F006": 620.0,
    "F007": 260.0,
    "F008": 320.0,
    "F009": 110.0,
    "F010": 160.0
}

w47_valid = (
    len(w47_records) == 5
    and {
        row["forecast_id"]: row["forecast_quantity"]
        for row in w47_records
    } == expected_w47
    and all(
        row["forecast_version"] == "SYNTHETIC_V1"
        for row in w47_records
    )
)

print("\nW47 records verified:", w47_valid)

print("\n4. FINAL RESULT")

if w46_valid and w47_valid:
    print("PASS: W46 historical forecasts are preserved.")
    print("PASS: All five W47 synthetic forecasts are verified.")
else:
    print("FAIL: Please inspect the forecast records.")

connection.close()

print("\nNo database records were modified.")
print("=" * 75)
