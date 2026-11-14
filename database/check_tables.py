
import sqlite3

connection = sqlite3.connect("data/supply_chain.db")

cursor = connection.cursor()

cursor.execute("""
SELECT name FROM sqlite_master
WHERE type='table'
""")

tables = cursor.fetchall()

print("Database Tables:")

for table in tables:
    print(table[0])

print("\nTotal Tables:", len(tables))

connection.close()
