
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 75)
print("FORECAST SCHEMA INSPECTION")
print("=" * 75)

print("\n1. FORECAST TABLE STRUCTURE")

cursor.execute("PRAGMA table_info(forecast_demand)")

for row in cursor.fetchall():
    print(dict(row))

print("\n2. FORECAST TABLE SQL")

cursor.execute("""
    SELECT sql
    FROM sqlite_master
    WHERE type = 'table'
      AND name = 'forecast_demand'
""")

row = cursor.fetchone()
print(row["sql"] if row else "Table definition not found")

print("\n3. EXISTING FORECAST IDs")

cursor.execute("""
    SELECT forecast_id, sku_id, location_id,
           forecast_week, forecast_quantity, forecast_version
    FROM forecast_demand
    ORDER BY forecast_id
""")

for row in cursor.fetchall():
    print(dict(row))

connection.close()

print("\n" + "=" * 75)
print("INSPECTION COMPLETED")
print("No database records were modified.")
print("=" * 75)
