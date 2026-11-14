
-- ==========================================
-- SUPPLY CHAIN DATABASE
-- ==========================================

PRAGMA foreign_keys = ON;

-- 1. SKU MASTER
CREATE TABLE IF NOT EXISTS sku (
    sku_id TEXT PRIMARY KEY,
    sku_name TEXT NOT NULL,
    category TEXT,
    unit_of_measure TEXT NOT NULL,
    unit_cost REAL DEFAULT 0 CHECK(unit_cost >= 0),
    is_active INTEGER DEFAULT 1
);

-- 2. LOCATION MASTER
CREATE TABLE IF NOT EXISTS location (
    location_id TEXT PRIMARY KEY,
    location_name TEXT NOT NULL,
    location_type TEXT,
    city TEXT,
    state TEXT
);

-- 3. SUPPLIER MASTER
CREATE TABLE IF NOT EXISTS supplier (
    supplier_id TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    supplier_type TEXT,
    reliability_score REAL,
    is_active INTEGER DEFAULT 1
);

-- 4. SKU AND LOCATION RELATIONSHIP
CREATE TABLE IF NOT EXISTS sku_location (
    sku_id TEXT,
    location_id TEXT,
    PRIMARY KEY (sku_id, location_id),
    FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
    FOREIGN KEY (location_id) REFERENCES location(location_id)
);

-- 5. WEEKLY FORECAST DEMAND
CREATE TABLE IF NOT EXISTS forecast_demand (
    forecast_id TEXT PRIMARY KEY,
    sku_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    forecast_week TEXT NOT NULL,
    forecast_quantity REAL NOT NULL CHECK(forecast_quantity >= 0),
    forecast_version TEXT,
    FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
    FOREIGN KEY (location_id) REFERENCES location(location_id)
);

-- 6. INVENTORY
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id TEXT PRIMARY KEY,
    sku_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    on_hand_quantity REAL NOT NULL DEFAULT 0,
    reserved_quantity REAL DEFAULT 0,
    unit_of_measure TEXT NOT NULL,
    inventory_date TEXT,
    FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
    FOREIGN KEY (location_id) REFERENCES location(location_id),
    CHECK(on_hand_quantity >= 0),
    CHECK(reserved_quantity >= 0)
);

-- 7. SUPPLIER AND SKU RELATIONSHIP
CREATE TABLE IF NOT EXISTS supplier_sku (
    supplier_id TEXT,
    sku_id TEXT,
    is_approved INTEGER DEFAULT 1,
    unit_cost REAL,
    PRIMARY KEY (supplier_id, sku_id),
    FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id),
    FOREIGN KEY (sku_id) REFERENCES sku(sku_id)
);

-- 8. SUPPLIER CAPACITY
CREATE TABLE IF NOT EXISTS supplier_capacity (
    capacity_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    capacity_week TEXT NOT NULL,
    maximum_quantity REAL NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id),
    FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
    CHECK(maximum_quantity >= 0)
);

-- 9. LEAD TIME
CREATE TABLE IF NOT EXISTS lead_time (
    lead_time_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    lead_time_days INTEGER NOT NULL,
    effective_from TEXT,
    effective_to TEXT,
    FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id),
    FOREIGN KEY (location_id) REFERENCES location(location_id),
    CHECK(lead_time_days >= 0)
);

-- 10. PURCHASE ORDER HEADER
CREATE TABLE IF NOT EXISTS purchase_order (
    po_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    order_date TEXT NOT NULL,
    expected_date TEXT,
    status TEXT NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id)
);

-- 11. PURCHASE ORDER LINES
CREATE TABLE IF NOT EXISTS purchase_order_line (
    po_line_id TEXT PRIMARY KEY,
    po_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    order_quantity REAL NOT NULL,
    received_quantity REAL DEFAULT 0,
    unit_of_measure TEXT NOT NULL,
    FOREIGN KEY (po_id) REFERENCES purchase_order(po_id),
    FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
    FOREIGN KEY (location_id) REFERENCES location(location_id),
    CHECK(order_quantity >= 0),
    CHECK(received_quantity >= 0)
);

-- 12. PRODUCTION PLAN
CREATE TABLE IF NOT EXISTS production_plan (
    production_id TEXT PRIMARY KEY,
    sku_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    production_week TEXT NOT NULL,
    planned_quantity REAL NOT NULL,
    FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
    FOREIGN KEY (location_id) REFERENCES location(location_id),
    CHECK(planned_quantity >= 0)
);

-- 13. BILL OF MATERIALS
CREATE TABLE IF NOT EXISTS bom (
    bom_id TEXT PRIMARY KEY,
    parent_sku_id TEXT NOT NULL,
    component_sku_id TEXT NOT NULL,
    component_quantity REAL NOT NULL,
    FOREIGN KEY (parent_sku_id) REFERENCES sku(sku_id),
    FOREIGN KEY (component_sku_id) REFERENCES sku(sku_id),
    CHECK(component_quantity > 0)
);

-- 14. INVENTORY EVENT HISTORY
CREATE TABLE IF NOT EXISTS inventory_event (
    event_id TEXT PRIMARY KEY,
    sku_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    quantity REAL NOT NULL,
    event_date TEXT NOT NULL,
    source_ref TEXT,
    unit_of_measure TEXT,
    FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
    FOREIGN KEY (location_id) REFERENCES location(location_id)
);

-- 15. PURCHASE ORDER EVENT HISTORY
CREATE TABLE IF NOT EXISTS purchase_order_event (
    po_event_id TEXT PRIMARY KEY,
    po_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_date TEXT NOT NULL,
    quantity REAL DEFAULT 0,
    source_ref TEXT,
    FOREIGN KEY (po_id) REFERENCES purchase_order(po_id)
);

-- 16. SHORTAGE RECORDS
CREATE TABLE IF NOT EXISTS shortage (
    shortage_id TEXT PRIMARY KEY,
    sku_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    shortage_week TEXT NOT NULL,
    demand_quantity REAL NOT NULL,
    available_quantity REAL NOT NULL,
    shortage_quantity REAL NOT NULL,
    priority TEXT,
    status TEXT DEFAULT 'OPEN',
    FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
    FOREIGN KEY (location_id) REFERENCES location(location_id)
);

-- 17. MITIGATION OPTIONS
CREATE TABLE IF NOT EXISTS mitigation_option (
    option_id TEXT PRIMARY KEY,
    shortage_id TEXT NOT NULL,
    option_type TEXT NOT NULL,
    description TEXT,
    proposed_quantity REAL,
    estimated_cost REAL,
    policy_compliant INTEGER DEFAULT 0,
    FOREIGN KEY (shortage_id) REFERENCES shortage(shortage_id)
);

-- 18. MITIGATION EVENT HISTORY
CREATE TABLE IF NOT EXISTS mitigation_event (
    mitigation_event_id TEXT PRIMARY KEY,
    option_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_date TEXT NOT NULL,
    decision_reason TEXT,
    FOREIGN KEY (option_id) REFERENCES mitigation_option(option_id)
);

-- ==========================================
-- INDEXES FOR FASTER DATA RETRIEVAL
-- ==========================================

CREATE INDEX IF NOT EXISTS idx_forecast_sku_week
ON forecast_demand(sku_id, forecast_week);

CREATE INDEX IF NOT EXISTS idx_inventory_sku_location
ON inventory(sku_id, location_id);

CREATE INDEX IF NOT EXISTS idx_po_supplier
ON purchase_order(supplier_id);

CREATE INDEX IF NOT EXISTS idx_shortage_week
ON shortage(shortage_week);

-- DATABASE SCHEMA COMPLETED
