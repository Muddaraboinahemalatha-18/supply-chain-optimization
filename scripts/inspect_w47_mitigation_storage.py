
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 85)
print("W47 MITIGATION STORAGE INSPECTION")
print("=" * 85)

# 1. Inspect mitigation_option schema
print("\n1. MITIGATION_OPTION TABLE COLUMNS")
print("-" * 85)

cursor.execute("PRAGMA table_info(mitigation_option)")

for column in cursor.fetchall():
    print(dict(column))

# 2. Inspect existing mitigation options
print("\n2. EXISTING MITIGATION OPTIONS")
print("-" * 85)

cursor.execute("""
    SELECT
        mo.option_id,
        mo.shortage_id,
        s.shortage_week,
        s.status AS shortage_status,
        mo.option_type,
        mo.description,
        mo.proposed_quantity,
        mo.estimated_cost,
        mo.policy_compliant
    FROM mitigation_option mo
    LEFT JOIN shortage s
        ON mo.shortage_id = s.shortage_id
    ORDER BY mo.option_id
""")

options = cursor.fetchall()

if options:
    for option in options:
        print(dict(option))
else:
    print("No mitigation options found.")

print("\nTotal mitigation options:", len(options))

# 3. Inspect mitigation_event schema
print("\n3. MITIGATION_EVENT TABLE COLUMNS")
print("-" * 85)

cursor.execute("PRAGMA table_info(mitigation_event)")

for column in cursor.fetchall():
    print(dict(column))

# 4. Inspect existing mitigation events
print("\n4. EXISTING MITIGATION EVENTS")
print("-" * 85)

cursor.execute("""
    SELECT
        me.mitigation_event_id,
        me.option_id,
        me.event_type,
        me.event_date,
        me.decision_reason
    FROM mitigation_event me
    ORDER BY me.mitigation_event_id
""")

events = cursor.fetchall()

if events:
    for event in events:
        print(dict(event))
else:
    print("No mitigation events found.")

print("\nTotal mitigation events:", len(events))

# 5. Inspect W47 projected shortages
print("\n5. W47 PROJECTED SHORTAGES")
print("-" * 85)

cursor.execute("""
    SELECT
        shortage_id,
        sku_id,
        location_id,
        shortage_week,
        demand_quantity,
        available_quantity,
        shortage_quantity,
        status
    FROM shortage
    WHERE shortage_week = '2026-W47'
    ORDER BY shortage_id
""")

shortages = cursor.fetchall()

for shortage in shortages:
    print(dict(shortage))

print("\nTotal W47 shortages:", len(shortages))

# 6. Foreign key check
print("\n6. FOREIGN KEY CHECK")
print("-" * 85)

cursor.execute("PRAGMA foreign_key_check")
foreign_key_errors = cursor.fetchall()

if foreign_key_errors:
    for error in foreign_key_errors:
        print(dict(error))
else:
    print("PASS: No foreign key violations.")

connection.close()

print("\n" + "=" * 85)
print("INSPECTION COMPLETED - NO DATABASE CHANGES MADE")
print("=" * 85)
