
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

# Synthetic forecast data for testing only.
W47_FORECASTS = [
    ("F006", "SKU001", "LOC001", "Rice", 620.0, "Kg"),
    ("F007", "SKU002", "LOC001", "Wheat", 260.0, "Kg"),
    ("F008", "SKU003", "LOC002", "Sugar", 320.0, "Kg"),
    ("F009", "SKU004", "LOC002", "Oil", 110.0, "Liter"),
    ("F010", "SKU005", "LOC003", "Milk", 160.0, "Liter"),
]

FORECAST_WEEK = "2026-W47"
FORECAST_VERSION = "SYNTHETIC_V1"

connection = get_connection()
cursor = connection.cursor()

print("=" * 75)
print("W47 SYNTHETIC FORECAST PREVIEW")
print("=" * 75)

valid = True

print("\n1. VALIDATING PROPOSED FORECASTS")

for forecast_id, sku_id, location_id, name, quantity, unit in W47_FORECASTS:

    cursor.execute("""
        SELECT COUNT(*)
        FROM sku
        WHERE sku_id = ?
    """, (sku_id,))
    sku_exists = cursor.fetchone()[0] == 1

    cursor.execute("""
        SELECT COUNT(*)
        FROM location
        WHERE location_id = ?
    """, (location_id,))
    location_exists = cursor.fetchone()[0] == 1

    cursor.execute("""
        SELECT COUNT(*)
        FROM forecast_demand
        WHERE forecast_id = ?
    """, (forecast_id,))
    id_exists = cursor.fetchone()[0] > 0

    cursor.execute("""
        SELECT COUNT(*)
        FROM forecast_demand
        WHERE sku_id = ?
          AND location_id = ?
          AND forecast_week = ?
    """, (sku_id, location_id, FORECAST_WEEK))
    duplicate_exists = cursor.fetchone()[0] > 0

    row_valid = (
        sku_exists
        and location_exists
        and not id_exists
        and not duplicate_exists
        and quantity >= 0
    )

    if not row_valid:
        valid = False

    print(
        f"{name}: "
        f"SKU exists={sku_exists}, "
        f"Location exists={location_exists}, "
        f"ID available={not id_exists}, "
        f"No duplicate={not duplicate_exists}, "
        f"Valid={row_valid}"
    )

print("\n2. PROPOSED FORECAST RECORDS")

for forecast_id, sku_id, location_id, name, quantity, unit in W47_FORECASTS:
    print(
        f"{forecast_id} | {name} | {location_id} | "
        f"{FORECAST_WEEK} | {quantity} {unit} | "
        f"{FORECAST_VERSION}"
    )

print("\n3. FORECAST SUMMARY")

print("Number of proposed records:", len(W47_FORECASTS))
print("Total quantity (mixed units):",
      sum(record[4] for record in W47_FORECASTS))

print("\n4. FINAL VALIDATION")

if valid:
    print("RESULT: ALL FORECAST RECORDS ARE VALID.")
    print("READY FOR REVIEW BEFORE INSERTION.")
else:
    print("RESULT: VALIDATION FAILED.")
    print("DO NOT INSERT THESE RECORDS.")

connection.close()

print("\nNo database records were modified.")
print("=" * 75)
