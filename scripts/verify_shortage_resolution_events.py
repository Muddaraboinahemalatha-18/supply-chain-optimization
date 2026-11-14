
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 75)
print("SHORTAGE RESOLUTION EVENT VERIFICATION")
print("=" * 75)

cursor.execute("""
    SELECT
        sh.shortage_id,
        s.sku_name,
        sh.shortage_quantity,
        sh.status,
        se.shortage_event_id,
        se.event_type,
        se.resolved_quantity,
        se.event_date,
        se.source_ref,
        se.reason
    FROM shortage sh
    JOIN sku s
        ON sh.sku_id = s.sku_id
    LEFT JOIN shortage_event se
        ON sh.shortage_id = se.shortage_id
        AND se.event_type = 'SHORTAGE_RESOLVED'
    ORDER BY sh.shortage_id
""")

records = cursor.fetchall()
verified = 0

for row in records:
    print("\nShortage ID:", row["shortage_id"])
    print("Product:", row["sku_name"])
    print("Historical shortage:", row["shortage_quantity"])
    print("Current status:", row["status"])
    print("Event ID:", row["shortage_event_id"])
    print("Event type:", row["event_type"])
    print("Resolved quantity:", row["resolved_quantity"])
    print("Event date:", row["event_date"])
    print("Source inbound:", row["source_ref"])
    print("Reason:", row["reason"])

    if (
        row["status"] == "RESOLVED"
        and row["event_type"] == "SHORTAGE_RESOLVED"
        and row["resolved_quantity"] == row["shortage_quantity"]
        and row["source_ref"] is not None
    ):
        print("Verification: PASSED")
        verified += 1
    else:
        print("Verification: FAILED")

print("\n" + "=" * 75)
print("TOTAL SHORTAGES:", len(records))
print("SUCCESSFULLY VERIFIED:", verified)

connection.close()

print("\nVERIFICATION COMPLETED")
print("No database records were modified.")
