
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

FORECAST_WEEK = "2026-W47"
FORECAST_VERSION = "SYNTHETIC_V1"

W47_FORECASTS = [
    ("F006", "SKU001", "LOC001", 620.0),
    ("F007", "SKU002", "LOC001", 260.0),
    ("F008", "SKU003", "LOC002", 320.0),
    ("F009", "SKU004", "LOC002", 110.0),
    ("F010", "SKU005", "LOC003", 160.0),
]

connection = get_connection()
cursor = connection.cursor()

try:
    # Validate the complete batch before inserting anything.
    for forecast_id, sku_id, location_id, quantity in W47_FORECASTS:

        cursor.execute("""
            SELECT COUNT(*)
            FROM forecast_demand
            WHERE forecast_id = ?
        """, (forecast_id,))

        if cursor.fetchone()[0] > 0:
            raise ValueError(f"Duplicate forecast ID: {forecast_id}")

        cursor.execute("""
            SELECT COUNT(*)
            FROM forecast_demand
            WHERE sku_id = ?
              AND location_id = ?
              AND forecast_week = ?
        """, (sku_id, location_id, FORECAST_WEEK))

        if cursor.fetchone()[0] > 0:
            raise ValueError(
                f"Duplicate forecast for {sku_id}, "
                f"{location_id}, {FORECAST_WEEK}"
            )

        if quantity < 0:
            raise ValueError(f"Invalid quantity for {forecast_id}")

    # Insert all five records together.
    cursor.executemany("""
        INSERT INTO forecast_demand (
            forecast_id,
            sku_id,
            location_id,
            forecast_week,
            forecast_quantity,
            forecast_version
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        (
            forecast_id,
            sku_id,
            location_id,
            FORECAST_WEEK,
            quantity,
            FORECAST_VERSION
        )
        for forecast_id, sku_id, location_id, quantity
        in W47_FORECASTS
    ])

    connection.commit()

    print("=" * 75)
    print("W47 FORECAST INSERTION SUCCESSFUL")
    print("=" * 75)
    print("Records inserted:", len(W47_FORECASTS))
    print("Forecast week:", FORECAST_WEEK)
    print("Forecast version:", FORECAST_VERSION)

except Exception as error:
    connection.rollback()
    print("INSERTION FAILED:", error)
    print("All changes were rolled back.")

finally:
    connection.close()
