
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "supply_chain.db"

# Synthetic sample lead-time assumptions
LEAD_TIME_DATA = [
    ("LT-000001", "SUP001", "LOC001", 2),
    ("LT-000002", "SUP001", "LOC002", 4),
    ("LT-000003", "SUP001", "LOC003", 5),

    ("LT-000004", "SUP002", "LOC001", 3),
    ("LT-000005", "SUP002", "LOC002", 3),
    ("LT-000006", "SUP002", "LOC003", 4),

    ("LT-000007", "SUP003", "LOC001", 1),
    ("LT-000008", "SUP003", "LOC002", 2),
    ("LT-000009", "SUP003", "LOC003", 3)
]

EFFECTIVE_FROM = "2026-01-01"
EFFECTIVE_TO = None


def seed_lead_time():

    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        cursor = connection.cursor()

        # Check whether records already exist
        existing_count = cursor.execute(
            "SELECT COUNT(*) FROM lead_time"
        ).fetchone()[0]

        if existing_count > 0:
            print("Lead-time records already exist.")
            print("No records were inserted.")
            print("Existing records:", existing_count)
            return

        # Insert lead-time records
        for record in LEAD_TIME_DATA:

            lead_time_id, supplier_id, location_id, days = record

            cursor.execute(
                """
                INSERT INTO lead_time (
                    lead_time_id,
                    supplier_id,
                    location_id,
                    lead_time_days,
                    effective_from,
                    effective_to
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    lead_time_id,
                    supplier_id,
                    location_id,
                    days,
                    EFFECTIVE_FROM,
                    EFFECTIVE_TO
                )
            )

        connection.commit()

        print("LEAD-TIME DATA INSERTED SUCCESSFULLY")
        print("=" * 45)

        print("Total records inserted:", len(LEAD_TIME_DATA))
        print("Effective from:", EFFECTIVE_FROM)
        print("Effective to: Currently active")

        print("\nLEAD-TIME RECORDS")
        print("-" * 45)

        results = cursor.execute(
            """
            SELECT
                lead_time_id,
                supplier_id,
                location_id,
                lead_time_days
            FROM lead_time
            ORDER BY lead_time_id
            """
        ).fetchall()

        for row in results:
            print(
                f"ID: {row[0]} | "
                f"Supplier: {row[1]} | "
                f"Location: {row[2]} | "
                f"Lead Time: {row[3]} days"
            )

    except Exception as error:
        connection.rollback()
        print("ERROR: Lead-time insertion failed.")
        print(error)

    finally:
        connection.close()


if __name__ == "__main__":
    seed_lead_time()
