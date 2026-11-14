
-- =====================================================
-- SUPPLY CHAIN OPTIMIZATION
-- Migration 001: Add Supporting Planning Tables
-- Database: SQLite
-- =====================================================

PRAGMA foreign_keys = ON;

-- 1. INBOUND ORDER
-- Tracks incoming deliveries against purchase order lines.

CREATE TABLE IF NOT EXISTS inbound_order (
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


-- 2. PRODUCTION CAPACITY
-- Defines weekly production limits for each SKU and location.

CREATE TABLE IF NOT EXISTS production_capacity (
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


-- 3. SKU SUBSTITUTE
-- Defines approved alternative products.

CREATE TABLE IF NOT EXISTS sku_substitute (
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


-- 4. SUPPLIER SKU POLICY
-- Stores effective-dated purchasing policies and prices.
-- References the existing supplier_sku relationship.

CREATE TABLE IF NOT EXISTS supplier_sku_policy (
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


-- 5. DATA QUALITY ISSUE
-- Records detected data-quality exceptions.

CREATE TABLE IF NOT EXISTS data_quality_issue (
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


-- 6. SCENARIO GROUND TRUTH
-- Stores expected labels for testing.
-- This table must not be used by the planning engine.

CREATE TABLE IF NOT EXISTS scenario_ground_truth (
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


-- =====================================================
-- INDEXES
-- Improve frequently used joins and lookups.
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_inbound_po_line
ON inbound_order(po_line_id);

CREATE INDEX IF NOT EXISTS idx_inbound_expected_date
ON inbound_order(expected_arrival_date);

CREATE INDEX IF NOT EXISTS idx_production_capacity_week
ON production_capacity(production_week);

CREATE INDEX IF NOT EXISTS idx_sku_substitute_original
ON sku_substitute(original_sku_id);

CREATE INDEX IF NOT EXISTS idx_supplier_policy_lookup
ON supplier_sku_policy(supplier_id, sku_id);

CREATE INDEX IF NOT EXISTS idx_quality_issue_type
ON data_quality_issue(issue_type);

CREATE INDEX IF NOT EXISTS idx_ground_truth_type
ON scenario_ground_truth(issue_type);

-- End of Migration 001
