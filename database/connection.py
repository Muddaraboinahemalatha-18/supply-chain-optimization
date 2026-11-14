
import sqlite3
from pathlib import Path

# Get the main project folder
BASE_DIR = Path(__file__).resolve().parents[1]

# Create data folder
DB_FOLDER = BASE_DIR / "data"
DB_FOLDER.mkdir(exist_ok=True)

# Database file path
DB_PATH = DB_FOLDER / "supply_chain.db"


# Connect to the database
def get_connection():
    connection = sqlite3.connect(DB_PATH)

    # Enable foreign key relationships
    connection.execute("PRAGMA foreign_keys = ON")

    # Return results as dictionary-like rows
    connection.row_factory = sqlite3.Row

    return connection


# Create database tables
def create_database():
    connection = get_connection()

    schema_path = BASE_DIR / "database" / "schema.sql"

    with open(schema_path, "r", encoding="utf-8") as file:
        schema = file.read()

    connection.executescript(schema)
    connection.commit()
    connection.close()

    print("Database created successfully!")


if __name__ == "__main__":
    create_database()
