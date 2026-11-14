
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

tables = [
    "data_quality_issue",
    "scenario_ground_truth"
]

for table in tables:
    print("\n" + "=" * 75)
    print("TABLE DEFINITION:", table)
    print("=" * 75)

    cursor.execute("""
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table'
        AND name = ?
    """, (table,))

    result = cursor.fetchone()

    if result:
        print(result["sql"])
    else:
        print("Table definition not found.")

connection.close()

print("\nINSPECTION COMPLETED")
print("No database records were modified.")
