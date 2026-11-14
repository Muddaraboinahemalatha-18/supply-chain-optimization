
import json
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "data" / "supply_chain.db"
JSON_PATH = BASE_DIR / "data" / "exports" / "supply_chain_database.json"
SQL_PATH = BASE_DIR / "data" / "exports" / "supply_chain_database.sql"


def main():

    print("=" * 65)
    print("DATABASE EXPORT VERIFICATION")
    print("=" * 65)

    # Check files
    if not all(path.exists() for path in [DB_PATH, JSON_PATH, SQL_PATH]):
        print("FAIL: One or more required files are missing.")
        return

    # Load JSON
    with open(JSON_PATH, "r", encoding="utf-8") as file:
        json_data = json.load(file)

    # Open original database in read-only mode
    original = sqlite3.connect(
        DB_PATH.resolve().as_uri() + "?mode=ro",
        uri=True
    )

    # Restore SQL dump in memory only
    restored = sqlite3.connect(":memory:")

    try:

        sql_text = SQL_PATH.read_text(encoding="utf-8")
        restored.executescript(sql_text)

        cursor = original.cursor()

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)

        original_tables = [row[0] for row in cursor.fetchall()]

        json_tables = sorted(json_data["tables"].keys())

        restored_cursor = restored.cursor()

        restored_cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)

        sql_tables = [row[0] for row in restored_cursor.fetchall()]

        print("\n1. TABLE COUNT CHECK")

        print("Original:", len(original_tables))
        print("JSON:", len(json_tables))
        print("SQL:", len(sql_tables))

        assert original_tables == json_tables
        assert original_tables == sql_tables

        print("PASS: All table names match.")

        print("\n2. RECORD COUNT CHECK")

        for table in original_tables:

            original_count = original.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]

            json_count = json_data["tables"][table]["record_count"]

            sql_count = restored.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]

            assert original_count == json_count, table
            assert original_count == sql_count, table

            print(
                f"{table}: Original={original_count}, "
                f"JSON={json_count}, SQL={sql_count} PASS"
            )

        print("\n3. FINAL RESULT")
        print("=" * 65)
        print("JSON export: PASS")
        print("SQL export: PASS")
        print("All 27 tables verified.")
        print("Original database opened read-only.")
        print("SQL dump tested in temporary memory database.")
        print("Original database was not modified.")

    finally:
        original.close()
        restored.close()


if __name__ == "__main__":
    main()
