
import sqlite3
import json
import base64
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "data" / "supply_chain.db"

EXPORT_DIR = BASE_DIR / "data" / "exports"

JSON_PATH = EXPORT_DIR / "supply_chain_database.json"
SQL_PATH = EXPORT_DIR / "supply_chain_database.sql"


# ============================================================
# JSON VALUE CONVERSION
# ============================================================

def convert_value(value):
    if isinstance(value, bytes):
        return {
            "__type__": "bytes",
            "base64": base64.b64encode(value).decode("ascii")
        }

    return value


# ============================================================
# DATABASE EXPORT
# ============================================================

def main():

    if not DB_PATH.exists():
        print("ERROR: Database file not found.")
        return

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Open the database in READ-ONLY mode.
    connection = sqlite3.connect(
        DB_PATH.resolve().as_uri() + "?mode=ro",
        uri=True
    )

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)

        table_names = [row[0] for row in cursor.fetchall()]

        database_data = {
            "database": "Supply Chain Optimization",
            "source": "data/supply_chain.db",
            "table_count": len(table_names),
            "tables": {}
        }

        print("DATABASE JSON EXPORT")
        print("=" * 60)

        for table_name in table_names:

            cursor.execute(
                f'PRAGMA table_info("{table_name}")'
            )

            columns = [
                row[1] for row in cursor.fetchall()
            ]

            cursor.execute(
                f'SELECT * FROM "{table_name}"'
            )

            records = cursor.fetchall()

            rows = []

            for record in records:

                row_data = {}

                for column, value in zip(columns, record):
                    row_data[column] = convert_value(value)

                rows.append(row_data)

            database_data["tables"][table_name] = {
                "columns": columns,
                "record_count": len(rows),
                "records": rows
            }

            print(
                f"{table_name}: {len(rows)} records"
            )

        # Save JSON export.
        with open(JSON_PATH, "w", encoding="utf-8") as file:
            json.dump(
                database_data,
                file,
                indent=4,
                ensure_ascii=False
            )

        # Save complete SQLite SQL dump.
        with open(SQL_PATH, "w", encoding="utf-8") as file:

            for statement in connection.iterdump():
                file.write(statement + "\n")

        print("\nEXPORT COMPLETED")
        print("=" * 60)

        print("Tables exported:", len(table_names))
        print("JSON file:", JSON_PATH)
        print("SQL file:", SQL_PATH)

    finally:
        connection.close()


if __name__ == "__main__":
    main()
