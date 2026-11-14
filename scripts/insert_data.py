
import sqlite3

# Connect to the database
connection = sqlite3.connect("data/supply_chain.db")

cursor = connection.cursor()

# 1. Insert SKU data
cursor.executemany("""
INSERT OR IGNORE INTO sku
(sku_id, sku_name, category, unit_of_measure, unit_cost)
VALUES (?, ?, ?, ?, ?)
""", [
    ("SKU001", "Rice", "Food", "Kg", 50),
    ("SKU002", "Wheat", "Food", "Kg", 40),
    ("SKU003", "Sugar", "Food", "Kg", 45),
    ("SKU004", "Oil", "Food", "Liter", 120),
    ("SKU005", "Milk", "Dairy", "Liter", 60)
])

# 2. Insert location data
cursor.executemany("""
INSERT OR IGNORE INTO location
(location_id, location_name, location_type, city, state)
VALUES (?, ?, ?, ?, ?)
""", [
    ("LOC001", "Warehouse 1", "Warehouse", "Vijayawada", "Andhra Pradesh"),
    ("LOC002", "Warehouse 2", "Warehouse", "Hyderabad", "Telangana"),
    ("LOC003", "Warehouse 3", "Warehouse", "Chennai", "Tamil Nadu")
])

# 3. Insert supplier data
cursor.executemany("""
INSERT OR IGNORE INTO supplier
(supplier_id, supplier_name, supplier_type, reliability_score)
VALUES (?, ?, ?, ?)
""", [
    ("SUP001", "ABC Suppliers", "Food Supplier", 0.95),
    ("SUP002", "Global Traders", "Wholesale Supplier", 0.90),
    ("SUP003", "Fresh Products", "Dairy Supplier", 0.98)
])

# 4. Insert SKU and location relationship
cursor.executemany("""
INSERT OR IGNORE INTO sku_location (sku_id, location_id)
VALUES (?, ?)
""", [
    ("SKU001", "LOC001"),
    ("SKU002", "LOC001"),
    ("SKU003", "LOC002"),
    ("SKU004", "LOC002"),
    ("SKU005", "LOC003")
])

# 5. Insert inventory data
cursor.executemany("""
INSERT OR IGNORE INTO inventory
(inventory_id, sku_id, location_id, on_hand_quantity,
reserved_quantity, unit_of_measure, inventory_date)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", [
    ("INV001", "SKU001", "LOC001", 500, 50, "Kg", "2026-11-12"),
    ("INV002", "SKU002", "LOC001", 300, 20, "Kg", "2026-11-12"),
    ("INV003", "SKU003", "LOC002", 200, 30, "Kg", "2026-11-12"),
    ("INV004", "SKU004", "LOC002", 150, 10, "Liter", "2026-11-12"),
    ("INV005", "SKU005", "LOC003", 100, 15, "Liter", "2026-11-12")
])

# 6. Insert forecast demand
cursor.executemany("""
INSERT OR IGNORE INTO forecast_demand
(forecast_id, sku_id, location_id, forecast_week,
forecast_quantity, forecast_version)
VALUES (?, ?, ?, ?, ?, ?)
""", [
    ("F001", "SKU001", "LOC001", "2026-W46", 600, "V1"),
    ("F002", "SKU002", "LOC001", "2026-W46", 250, "V1"),
    ("F003", "SKU003", "LOC002", "2026-W46", 300, "V1"),
    ("F004", "SKU004", "LOC002", "2026-W46", 100, "V1"),
    ("F005", "SKU005", "LOC003", "2026-W46", 150, "V1")
])

# 7. Insert supplier and SKU relationship
cursor.executemany("""
INSERT OR IGNORE INTO supplier_sku
(supplier_id, sku_id, is_approved, unit_cost)
VALUES (?, ?, ?, ?)
""", [
    ("SUP001", "SKU001", 1, 48),
    ("SUP001", "SKU002", 1, 38),
    ("SUP002", "SKU003", 1, 43),
    ("SUP002", "SKU004", 1, 115),
    ("SUP003", "SKU005", 1, 58)
])

# Save all changes
connection.commit()

print("Sample data inserted successfully!")

connection.close()
