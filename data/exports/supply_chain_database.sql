BEGIN TRANSACTION;
CREATE TABLE bom (
    bom_id TEXT PRIMARY KEY,
    parent_sku_id TEXT NOT NULL,
    component_sku_id TEXT NOT NULL,
    component_quantity REAL NOT NULL,
    FOREIGN KEY (parent_sku_id) REFERENCES sku(sku_id),
    FOREIGN KEY (component_sku_id) REFERENCES sku(sku_id),
    CHECK(component_quantity > 0)
);
CREATE TABLE data_quality_issue (
    issue_id TEXT PRIMARY KEY,
    issue_type TEXT NOT NULL
        CHECK (
            issue_type IN (
                'INBOUND_DOUBLE_COUNT',
                'UNAPPROVED_SUBSTITUTE',
                'CAPACITY_EXCEEDED',
                'MISSING_LEAD_TIME',
                'UOM_MISMATCH'
            )
        ),
    affected_entity TEXT NOT NULL,
    affected_record_id TEXT NOT NULL,
    severity TEXT NOT NULL
        CHECK (
            severity IN (
                'LOW',
                'MEDIUM',
                'HIGH',
                'CRITICAL'
            )
        ),
    description TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN'
        CHECK (
            status IN (
                'OPEN',
                'DETECTED',
                'RESOLVED'
            )
        )
);
CREATE TABLE forecast_demand (
    forecast_id TEXT PRIMARY KEY,
    sku_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    forecast_week TEXT NOT NULL,
    forecast_quantity REAL NOT NULL CHECK(forecast_quantity >= 0),
    forecast_version TEXT,
    FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
    FOREIGN KEY (location_id) REFERENCES location(location_id)
);
INSERT INTO "forecast_demand" VALUES('F001','SKU001','LOC001','2026-W46',600.0,'V1');
INSERT INTO "forecast_demand" VALUES('F002','SKU002','LOC001','2026-W46',250.0,'V1');
INSERT INTO "forecast_demand" VALUES('F003','SKU003','LOC002','2026-W46',300.0,'V1');
INSERT INTO "forecast_demand" VALUES('F004','SKU004','LOC002','2026-W46',100.0,'V1');
INSERT INTO "forecast_demand" VALUES('F005','SKU005','LOC003','2026-W46',150.0,'V1');
INSERT INTO "forecast_demand" VALUES('F006','SKU001','LOC001','2026-W47',620.0,'SYNTHETIC_V1');
INSERT INTO "forecast_demand" VALUES('F007','SKU002','LOC001','2026-W47',260.0,'SYNTHETIC_V1');
INSERT INTO "forecast_demand" VALUES('F008','SKU003','LOC002','2026-W47',320.0,'SYNTHETIC_V1');
INSERT INTO "forecast_demand" VALUES('F009','SKU004','LOC002','2026-W47',110.0,'SYNTHETIC_V1');
INSERT INTO "forecast_demand" VALUES('F010','SKU005','LOC003','2026-W47',160.0,'SYNTHETIC_V1');
CREATE TABLE inbound_order (
    inbound_id TEXT PRIMARY KEY,
    po_line_id TEXT NOT NULL,
    expected_arrival_date TEXT NOT NULL,
    actual_arrival_date TEXT,
    inbound_quantity REAL NOT NULL CHECK (inbound_quantity > 0),
    received_quantity REAL NOT NULL DEFAULT 0
        CHECK (received_quantity >= 0),
    status TEXT NOT NULL DEFAULT 'PLANNED'
        CHECK (
            status IN (
                'PLANNED',
                'IN_TRANSIT',
                'PARTIALLY_RECEIVED',
                'RECEIVED',
                'DELAYED',
                'CANCELLED'
            )
        ),

    FOREIGN KEY (po_line_id)
        REFERENCES purchase_order_line(po_line_id),

    CHECK (received_quantity <= inbound_quantity)
);
INSERT INTO "inbound_order" VALUES('INB-2026-000001','LINE_SH_F001','2026-11-19','2026-11-12',150.0,150.0,'RECEIVED');
INSERT INTO "inbound_order" VALUES('INB-2026-000002','LINE_SH_F003','2026-11-19','2026-11-12',130.0,130.0,'RECEIVED');
INSERT INTO "inbound_order" VALUES('INB-2026-000003','LINE_SH_F005','2026-11-19','2026-11-12',65.0,65.0,'RECEIVED');
CREATE TABLE inventory (
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
INSERT INTO "inventory" VALUES('INV001','SKU001','LOC001',650.0,50.0,'Kg','2026-11-12');
INSERT INTO "inventory" VALUES('INV002','SKU002','LOC001',300.0,20.0,'Kg','2026-11-12');
INSERT INTO "inventory" VALUES('INV003','SKU003','LOC002',330.0,30.0,'Kg','2026-11-12');
INSERT INTO "inventory" VALUES('INV004','SKU004','LOC002',150.0,10.0,'Liter','2026-11-12');
INSERT INTO "inventory" VALUES('INV005','SKU005','LOC003',165.0,15.0,'Liter','2026-11-12');
CREATE TABLE inventory_event (
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
INSERT INTO "inventory_event" VALUES('EVT_PO_SH_F001','SKU001','LOC001','PURCHASE_RECEIVED',150.0,'2026-11-12','PO_SH_F001','Kg');
INSERT INTO "inventory_event" VALUES('EVT_PO_SH_F003','SKU003','LOC002','PURCHASE_RECEIVED',130.0,'2026-11-12','PO_SH_F003','Kg');
INSERT INTO "inventory_event" VALUES('EVT_PO_SH_F005','SKU005','LOC003','PURCHASE_RECEIVED',65.0,'2026-11-12','PO_SH_F005','Liter');
CREATE TABLE lead_time (
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
INSERT INTO "lead_time" VALUES('LT-000001','SUP001','LOC001',2,'2026-01-01',NULL);
INSERT INTO "lead_time" VALUES('LT-000002','SUP001','LOC002',4,'2026-01-01',NULL);
INSERT INTO "lead_time" VALUES('LT-000003','SUP001','LOC003',5,'2026-01-01',NULL);
INSERT INTO "lead_time" VALUES('LT-000004','SUP002','LOC001',3,'2026-01-01',NULL);
INSERT INTO "lead_time" VALUES('LT-000005','SUP002','LOC002',3,'2026-01-01',NULL);
INSERT INTO "lead_time" VALUES('LT-000006','SUP002','LOC003',4,'2026-01-01',NULL);
INSERT INTO "lead_time" VALUES('LT-000007','SUP003','LOC001',1,'2026-01-01',NULL);
INSERT INTO "lead_time" VALUES('LT-000008','SUP003','LOC002',2,'2026-01-01',NULL);
INSERT INTO "lead_time" VALUES('LT-000009','SUP003','LOC003',3,'2026-01-01',NULL);
CREATE TABLE location (
    location_id TEXT PRIMARY KEY,
    location_name TEXT NOT NULL,
    location_type TEXT,
    city TEXT,
    state TEXT
);
INSERT INTO "location" VALUES('LOC001','Warehouse 1','Warehouse','Vijayawada','Andhra Pradesh');
INSERT INTO "location" VALUES('LOC002','Warehouse 2','Warehouse','Hyderabad','Telangana');
INSERT INTO "location" VALUES('LOC003','Warehouse 3','Warehouse','Chennai','Tamil Nadu');
CREATE TABLE mitigation_event (
    mitigation_event_id TEXT PRIMARY KEY,
    option_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_date TEXT NOT NULL,
    decision_reason TEXT,
    FOREIGN KEY (option_id) REFERENCES mitigation_option(option_id)
);
INSERT INTO "mitigation_event" VALUES('ME-SHORT-2026-000001-CREATE-01','MIT-SHORT-2026-000001-01','OPTION_CREATED','2026-11-13','W47 purchase recommendation created after supplier approval, MOQ, unit, price and lead-time checks. Capacity validation uses synthetic scenario SYN-W47-001. Actual W47 capacity is unavailable. This is not a purchase order or supplier commitment.');
INSERT INTO "mitigation_event" VALUES('ME-SHORT-2026-000002-CREATE-01','MIT-SHORT-2026-000002-01','OPTION_CREATED','2026-11-13','W47 purchase recommendation created after supplier approval, MOQ, unit, price and lead-time checks. Capacity validation uses synthetic scenario SYN-W47-001. Actual W47 capacity is unavailable. This is not a purchase order or supplier commitment.');
INSERT INTO "mitigation_event" VALUES('ME-SHORT-2026-000003-CREATE-01','MIT-SHORT-2026-000003-01','OPTION_CREATED','2026-11-13','W47 purchase recommendation created after supplier approval, MOQ, unit, price and lead-time checks. Capacity validation uses synthetic scenario SYN-W47-001. Actual W47 capacity is unavailable. This is not a purchase order or supplier commitment.');
CREATE TABLE mitigation_option (
    option_id TEXT PRIMARY KEY,
    shortage_id TEXT NOT NULL,
    option_type TEXT NOT NULL,
    description TEXT,
    proposed_quantity REAL,
    estimated_cost REAL,
    policy_compliant INTEGER DEFAULT 0, supplier_id TEXT
REFERENCES supplier(supplier_id), unit_of_measure TEXT, minimum_order_quantity REAL
CHECK (minimum_order_quantity IS NULL OR minimum_order_quantity >= 0), unit_cost REAL
CHECK (unit_cost IS NULL OR unit_cost >= 0), capacity_quantity REAL
CHECK (capacity_quantity IS NULL OR capacity_quantity >= 0), capacity_source TEXT
CHECK (
    capacity_source IS NULL OR
    capacity_source IN ('ACTUAL', 'SYNTHETIC', 'UNAVAILABLE')
), capacity_scenario_id TEXT, lead_time_days INTEGER
CHECK (lead_time_days IS NULL OR lead_time_days >= 0), planned_order_date TEXT, expected_arrival_date TEXT, feasibility_status TEXT
CHECK (
    feasibility_status IS NULL OR
    feasibility_status IN ('FEASIBLE', 'CONDITIONAL', 'BLOCKED')
),
    FOREIGN KEY (shortage_id) REFERENCES shortage(shortage_id)
);
INSERT INTO "mitigation_option" VALUES('OPT_SH_F003','SH_F003','PURCHASE','Supplier: Global Traders',130.0,5590.0,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL);
INSERT INTO "mitigation_option" VALUES('OPT_SH_F001','SH_F001','PURCHASE','Supplier: ABC Suppliers',150.0,7200.0,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL);
INSERT INTO "mitigation_option" VALUES('OPT_SH_F005','SH_F005','PURCHASE','Supplier: Fresh Products',65.0,3770.0,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL);
INSERT INTO "mitigation_option" VALUES('MIT-SHORT-2026-000001-01','SHORT-2026-000001','PURCHASE','W47 purchase recommendation for Rice. Supplier: ABC Suppliers. Capacity is synthetic under SYN-W47-001; not an actual supplier commitment.',50.0,2400.0,1,'SUP001','Kg',50.0,48.0,100.0,'SYNTHETIC','SYN-W47-001',2,'2026-11-13','2026-11-15','CONDITIONAL');
INSERT INTO "mitigation_option" VALUES('MIT-SHORT-2026-000002-01','SHORT-2026-000002','PURCHASE','W47 purchase recommendation for Sugar. Supplier: Global Traders. Capacity is synthetic under SYN-W47-001; not an actual supplier commitment.',25.0,1075.0,1,'SUP002','Kg',25.0,43.0,100.0,'SYNTHETIC','SYN-W47-001',3,'2026-11-13','2026-11-16','CONDITIONAL');
INSERT INTO "mitigation_option" VALUES('MIT-SHORT-2026-000003-01','SHORT-2026-000003','PURCHASE','W47 purchase recommendation for Milk. Supplier: Fresh Products. Capacity is synthetic under SYN-W47-001; not an actual supplier commitment.',10.0,580.0,1,'SUP003','Liter',10.0,58.0,50.0,'SYNTHETIC','SYN-W47-001',3,'2026-11-13','2026-11-16','CONDITIONAL');
CREATE TABLE production_capacity (
    production_capacity_id TEXT PRIMARY KEY,
    sku_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    production_week TEXT NOT NULL,
    maximum_quantity REAL NOT NULL
        CHECK (maximum_quantity >= 0),

    FOREIGN KEY (sku_id)
        REFERENCES sku(sku_id),

    FOREIGN KEY (location_id)
        REFERENCES location(location_id),

    UNIQUE (sku_id, location_id, production_week)
);
CREATE TABLE production_plan (
    production_id TEXT PRIMARY KEY,
    sku_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    production_week TEXT NOT NULL,
    planned_quantity REAL NOT NULL,
    FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
    FOREIGN KEY (location_id) REFERENCES location(location_id),
    CHECK(planned_quantity >= 0)
);
CREATE TABLE purchase_order (
    po_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    order_date TEXT NOT NULL,
    expected_date TEXT,
    status TEXT NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id)
);
INSERT INTO "purchase_order" VALUES('PO_SH_F001','SUP001','2026-11-12','2026-11-19','RECEIVED');
INSERT INTO "purchase_order" VALUES('PO_SH_F003','SUP002','2026-11-12','2026-11-19','RECEIVED');
INSERT INTO "purchase_order" VALUES('PO_SH_F005','SUP003','2026-11-12','2026-11-19','RECEIVED');
CREATE TABLE purchase_order_event (
    po_event_id TEXT PRIMARY KEY,
    po_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_date TEXT NOT NULL,
    quantity REAL DEFAULT 0,
    source_ref TEXT,
    FOREIGN KEY (po_id) REFERENCES purchase_order(po_id)
);
CREATE TABLE purchase_order_line (
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
INSERT INTO "purchase_order_line" VALUES('LINE_SH_F001','PO_SH_F001','SKU001','LOC001',150.0,150.0,'Kg');
INSERT INTO "purchase_order_line" VALUES('LINE_SH_F003','PO_SH_F003','SKU003','LOC002',130.0,130.0,'Kg');
INSERT INTO "purchase_order_line" VALUES('LINE_SH_F005','PO_SH_F005','SKU005','LOC003',65.0,65.0,'Liter');
CREATE TABLE scenario_ground_truth (
    ground_truth_id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL UNIQUE,
    issue_type TEXT NOT NULL
        CHECK (
            issue_type IN (
                'INBOUND_DOUBLE_COUNT',
                'UNAPPROVED_SUBSTITUTE',
                'CAPACITY_EXCEEDED',
                'MISSING_LEAD_TIME',
                'UOM_MISMATCH'
            )
        ),
    expected_label TEXT NOT NULL
        CHECK (
            expected_label IN (
                'VALID',
                'INVALID',
                'REJECT',
                'FLAG'
            )
        ),
    expected_decision TEXT NOT NULL,
    explanation TEXT NOT NULL
);
CREATE TABLE shortage (
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
INSERT INTO "shortage" VALUES('SH_F001','SKU001','LOC001','2026-W46',600.0,450.0,150.0,'HIGH','RESOLVED');
INSERT INTO "shortage" VALUES('SH_F003','SKU003','LOC002','2026-W46',300.0,170.0,130.0,'HIGH','RESOLVED');
INSERT INTO "shortage" VALUES('SH_F005','SKU005','LOC003','2026-W46',150.0,85.0,65.0,'HIGH','RESOLVED');
INSERT INTO "shortage" VALUES('SHORT-2026-000001','SKU001','LOC001','2026-W47',620.0,600.0,20.0,NULL,'PROJECTED');
INSERT INTO "shortage" VALUES('SHORT-2026-000002','SKU003','LOC002','2026-W47',320.0,300.0,20.0,NULL,'PROJECTED');
INSERT INTO "shortage" VALUES('SHORT-2026-000003','SKU005','LOC003','2026-W47',160.0,150.0,10.0,NULL,'PROJECTED');
CREATE TABLE shortage_event (
    shortage_event_id TEXT PRIMARY KEY,

    shortage_id TEXT NOT NULL,

    event_type TEXT NOT NULL
        CHECK (
            event_type IN (
                'SHORTAGE_DETECTED',
                'SHORTAGE_RESOLVED',
                'SHORTAGE_REOPENED'
            )
        ),

    event_date TEXT NOT NULL,

    resolved_quantity REAL NOT NULL DEFAULT 0
        CHECK (resolved_quantity >= 0),

    source_ref TEXT,

    reason TEXT,

    FOREIGN KEY (shortage_id)
        REFERENCES shortage(shortage_id)
);
INSERT INTO "shortage_event" VALUES('SEVT-SH_F001-RES-01','SH_F001','SHORTAGE_RESOLVED','2026-11-12',150.0,'INB-2026-000001','Inbound receipt INB-2026-000001 was fully received; current available inventory covers recorded demand.');
INSERT INTO "shortage_event" VALUES('SEVT-SH_F003-RES-01','SH_F003','SHORTAGE_RESOLVED','2026-11-12',130.0,'INB-2026-000002','Inbound receipt INB-2026-000002 was fully received; current available inventory covers recorded demand.');
INSERT INTO "shortage_event" VALUES('SEVT-SH_F005-RES-01','SH_F005','SHORTAGE_RESOLVED','2026-11-12',65.0,'INB-2026-000003','Inbound receipt INB-2026-000003 was fully received; current available inventory covers recorded demand.');
CREATE TABLE shortage_projection (
    projection_id TEXT PRIMARY KEY,
    shortage_id TEXT NOT NULL UNIQUE,
    forecast_id TEXT NOT NULL,
    planning_scenario_id TEXT NOT NULL,
    inventory_snapshot_date TEXT NOT NULL,
    projection_date TEXT NOT NULL,
    assumptions TEXT NOT NULL,
    projection_status TEXT NOT NULL DEFAULT 'PROJECTED'
        CHECK (
            projection_status IN (
                'PROJECTED',
                'CONFIRMED',
                'CANCELLED'
            )
        ),

    FOREIGN KEY (shortage_id)
        REFERENCES shortage(shortage_id),

    FOREIGN KEY (forecast_id)
        REFERENCES forecast_demand(forecast_id),

    UNIQUE (
        forecast_id,
        planning_scenario_id,
        inventory_snapshot_date
    )
);
INSERT INTO "shortage_projection" VALUES('PROJ-2026-000001','SHORT-2026-000001','F006','W47-BASELINE-2026-11-12','2026-11-12','2026-11-13','Inventory snapshot is 2026-11-12. No net inventory changes are assumed through 2026-11-15. Received inbound stock is already included in inventory. No additional inbound supply is assumed during 2026-W47. All W47 forecast demand is treated as outstanding. These are planning estimates, not confirmed actual shortages.','PROJECTED');
INSERT INTO "shortage_projection" VALUES('PROJ-2026-000002','SHORT-2026-000002','F008','W47-BASELINE-2026-11-12','2026-11-12','2026-11-13','Inventory snapshot is 2026-11-12. No net inventory changes are assumed through 2026-11-15. Received inbound stock is already included in inventory. No additional inbound supply is assumed during 2026-W47. All W47 forecast demand is treated as outstanding. These are planning estimates, not confirmed actual shortages.','PROJECTED');
INSERT INTO "shortage_projection" VALUES('PROJ-2026-000003','SHORT-2026-000003','F010','W47-BASELINE-2026-11-12','2026-11-12','2026-11-13','Inventory snapshot is 2026-11-12. No net inventory changes are assumed through 2026-11-15. Received inbound stock is already included in inventory. No additional inbound supply is assumed during 2026-W47. All W47 forecast demand is treated as outstanding. These are planning estimates, not confirmed actual shortages.','PROJECTED');
CREATE TABLE shortage_projection_event (
    projection_event_id TEXT PRIMARY KEY,
    projection_id TEXT NOT NULL,
    event_type TEXT NOT NULL
        CHECK (
            event_type IN (
                'PROJECTION_CREATED',
                'PROJECTION_REVISED',
                'PROJECTION_CONFIRMED',
                'PROJECTION_CANCELLED'
            )
        ),
    event_date TEXT NOT NULL,
    source_ref TEXT,
    reason TEXT NOT NULL,

    FOREIGN KEY (projection_id)
        REFERENCES shortage_projection(projection_id)
);
INSERT INTO "shortage_projection_event" VALUES('PEVT-PROJ-2026-000001-CREATE-01','PROJ-2026-000001','PROJECTION_CREATED','2026-11-13','F006','Initial W47 shortage estimate created from the documented forecast and inventory snapshot.');
INSERT INTO "shortage_projection_event" VALUES('PEVT-PROJ-2026-000002-CREATE-01','PROJ-2026-000002','PROJECTION_CREATED','2026-11-13','F008','Initial W47 shortage estimate created from the documented forecast and inventory snapshot.');
INSERT INTO "shortage_projection_event" VALUES('PEVT-PROJ-2026-000003-CREATE-01','PROJ-2026-000003','PROJECTION_CREATED','2026-11-13','F010','Initial W47 shortage estimate created from the documented forecast and inventory snapshot.');
CREATE TABLE sku (
    sku_id TEXT PRIMARY KEY,
    sku_name TEXT NOT NULL,
    category TEXT,
    unit_of_measure TEXT NOT NULL,
    unit_cost REAL DEFAULT 0 CHECK(unit_cost >= 0),
    is_active INTEGER DEFAULT 1
);
INSERT INTO "sku" VALUES('SKU001','Rice','Food','Kg',50.0,1);
INSERT INTO "sku" VALUES('SKU002','Wheat','Food','Kg',40.0,1);
INSERT INTO "sku" VALUES('SKU003','Sugar','Food','Kg',45.0,1);
INSERT INTO "sku" VALUES('SKU004','Oil','Food','Liter',120.0,1);
INSERT INTO "sku" VALUES('SKU005','Milk','Dairy','Liter',60.0,1);
CREATE TABLE sku_location (
    sku_id TEXT,
    location_id TEXT,
    PRIMARY KEY (sku_id, location_id),
    FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
    FOREIGN KEY (location_id) REFERENCES location(location_id)
);
INSERT INTO "sku_location" VALUES('SKU001','LOC001');
INSERT INTO "sku_location" VALUES('SKU002','LOC001');
INSERT INTO "sku_location" VALUES('SKU003','LOC002');
INSERT INTO "sku_location" VALUES('SKU004','LOC002');
INSERT INTO "sku_location" VALUES('SKU005','LOC003');
CREATE TABLE sku_substitute (
    substitute_id TEXT PRIMARY KEY,
    original_sku_id TEXT NOT NULL,
    substitute_sku_id TEXT NOT NULL,
    is_approved INTEGER NOT NULL DEFAULT 0
        CHECK (is_approved IN (0, 1)),
    conversion_factor REAL NOT NULL
        CHECK (conversion_factor > 0),
    effective_from TEXT NOT NULL,
    effective_to TEXT,

    FOREIGN KEY (original_sku_id)
        REFERENCES sku(sku_id),

    FOREIGN KEY (substitute_sku_id)
        REFERENCES sku(sku_id),

    CHECK (original_sku_id <> substitute_sku_id),

    CHECK (
        effective_to IS NULL
        OR effective_to >= effective_from
    ),

    UNIQUE (
        original_sku_id,
        substitute_sku_id,
        effective_from
    )
);
CREATE TABLE supplier (
    supplier_id TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    supplier_type TEXT,
    reliability_score REAL,
    is_active INTEGER DEFAULT 1
);
INSERT INTO "supplier" VALUES('SUP001','ABC Suppliers','Food Supplier',0.95,1);
INSERT INTO "supplier" VALUES('SUP002','Global Traders','Wholesale Supplier',0.9,1);
INSERT INTO "supplier" VALUES('SUP003','Fresh Products','Dairy Supplier',0.98,1);
CREATE TABLE supplier_capacity (
    capacity_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    capacity_week TEXT NOT NULL,
    maximum_quantity REAL NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id),
    FOREIGN KEY (sku_id) REFERENCES sku(sku_id),
    CHECK(maximum_quantity >= 0)
);
INSERT INTO "supplier_capacity" VALUES('CAP001','SUP001','SKU001','2026-W46',200.0);
INSERT INTO "supplier_capacity" VALUES('CAP002','SUP001','SKU002','2026-W46',300.0);
INSERT INTO "supplier_capacity" VALUES('CAP003','SUP002','SKU003','2026-W46',150.0);
INSERT INTO "supplier_capacity" VALUES('CAP004','SUP002','SKU004','2026-W46',200.0);
INSERT INTO "supplier_capacity" VALUES('CAP005','SUP003','SKU005','2026-W46',100.0);
CREATE TABLE supplier_sku (
    supplier_id TEXT,
    sku_id TEXT,
    is_approved INTEGER DEFAULT 1,
    unit_cost REAL,
    PRIMARY KEY (supplier_id, sku_id),
    FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id),
    FOREIGN KEY (sku_id) REFERENCES sku(sku_id)
);
INSERT INTO "supplier_sku" VALUES('SUP001','SKU001',1,48.0);
INSERT INTO "supplier_sku" VALUES('SUP001','SKU002',1,38.0);
INSERT INTO "supplier_sku" VALUES('SUP002','SKU003',1,43.0);
INSERT INTO "supplier_sku" VALUES('SUP002','SKU004',1,115.0);
INSERT INTO "supplier_sku" VALUES('SUP003','SKU005',1,58.0);
CREATE TABLE supplier_sku_policy (
    policy_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    minimum_order_quantity REAL NOT NULL
        CHECK (minimum_order_quantity >= 0),
    unit_cost REAL NOT NULL
        CHECK (unit_cost >= 0),
    effective_from TEXT NOT NULL,
    effective_to TEXT,

    FOREIGN KEY (supplier_id, sku_id)
        REFERENCES supplier_sku(supplier_id, sku_id),

    CHECK (
        effective_to IS NULL
        OR effective_to >= effective_from
    ),

    UNIQUE (supplier_id, sku_id, effective_from)
);
INSERT INTO "supplier_sku_policy" VALUES('POLICY-000001','SUP001','SKU001',50.0,48.0,'2026-01-01',NULL);
INSERT INTO "supplier_sku_policy" VALUES('POLICY-000002','SUP001','SKU002',50.0,38.0,'2026-01-01',NULL);
INSERT INTO "supplier_sku_policy" VALUES('POLICY-000003','SUP002','SKU003',25.0,43.0,'2026-01-01',NULL);
INSERT INTO "supplier_sku_policy" VALUES('POLICY-000004','SUP002','SKU004',20.0,115.0,'2026-01-01',NULL);
INSERT INTO "supplier_sku_policy" VALUES('POLICY-000005','SUP003','SKU005',10.0,58.0,'2026-01-01',NULL);
CREATE INDEX idx_forecast_sku_week
ON forecast_demand(sku_id, forecast_week);
CREATE INDEX idx_inventory_sku_location
ON inventory(sku_id, location_id);
CREATE INDEX idx_po_supplier
ON purchase_order(supplier_id);
CREATE INDEX idx_shortage_week
ON shortage(shortage_week);
CREATE INDEX idx_inbound_po_line
ON inbound_order(po_line_id);
CREATE INDEX idx_inbound_expected_date
ON inbound_order(expected_arrival_date);
CREATE INDEX idx_production_capacity_week
ON production_capacity(production_week);
CREATE INDEX idx_sku_substitute_original
ON sku_substitute(original_sku_id);
CREATE INDEX idx_supplier_policy_lookup
ON supplier_sku_policy(supplier_id, sku_id);
CREATE INDEX idx_quality_issue_type
ON data_quality_issue(issue_type);
CREATE INDEX idx_ground_truth_type
ON scenario_ground_truth(issue_type);
CREATE INDEX idx_shortage_event_shortage
ON shortage_event(shortage_id);
CREATE INDEX idx_shortage_event_date
ON shortage_event(event_date);
CREATE INDEX idx_shortage_projection_forecast
ON shortage_projection(forecast_id);
CREATE INDEX idx_shortage_projection_scenario
ON shortage_projection(planning_scenario_id);
CREATE INDEX idx_shortage_projection_event_projection
ON shortage_projection_event(projection_id);
CREATE INDEX idx_mitigation_option_supplier
ON mitigation_option(supplier_id);
CREATE INDEX idx_mitigation_option_feasibility
ON mitigation_option(feasibility_status);
COMMIT;
