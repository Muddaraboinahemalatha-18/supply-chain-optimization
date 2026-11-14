
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "supply_chain.db"

NEW_TABLES = [
    "inbound_order",
    "production_capacity",
    "sku_substitute",
    "supplier_sku_policy",
    "data_quality_issue",
    "scenario_ground_truth"
]

connection = sqlite3.connect(DB_PATH)
connection.execute("PRAGMA foreign_keys = ON")

print("DATABASE MIGRATION VERIFICATION")
print("=" * 45)

try:
    for table in NEW_TABLES:

        result = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (table,)
        ).fetchone()

        if result:
            count = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            print(f"{table}: EXISTS | Records: {count}")
        else:
            print(f"{table}: MISSING")

    print("\nFOREIGN KEY CHECK")
    errors = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if errors:
        print("FAILED:", errors)
    else:
        print("PASSED: No foreign-key errors")

    print("\nDATABASE INTEGRITY CHECK")
    result = connection.execute(
        "PRAGMA integrity_check"
    ).fetchone()

    print(result[0])

    print("\nMIGRATION VERIFICATION COMPLETED")

finally:
    connection.close()
