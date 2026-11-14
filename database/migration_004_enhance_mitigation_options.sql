
-- Migration 004: Enhance mitigation option traceability
-- Existing historical mitigation records must remain unchanged.

ALTER TABLE mitigation_option
ADD COLUMN supplier_id TEXT
REFERENCES supplier(supplier_id);

ALTER TABLE mitigation_option
ADD COLUMN unit_of_measure TEXT;

ALTER TABLE mitigation_option
ADD COLUMN minimum_order_quantity REAL
CHECK (minimum_order_quantity IS NULL OR minimum_order_quantity >= 0);

ALTER TABLE mitigation_option
ADD COLUMN unit_cost REAL
CHECK (unit_cost IS NULL OR unit_cost >= 0);

ALTER TABLE mitigation_option
ADD COLUMN capacity_quantity REAL
CHECK (capacity_quantity IS NULL OR capacity_quantity >= 0);

ALTER TABLE mitigation_option
ADD COLUMN capacity_source TEXT
CHECK (
    capacity_source IS NULL OR
    capacity_source IN ('ACTUAL', 'SYNTHETIC', 'UNAVAILABLE')
);

ALTER TABLE mitigation_option
ADD COLUMN capacity_scenario_id TEXT;

ALTER TABLE mitigation_option
ADD COLUMN lead_time_days INTEGER
CHECK (lead_time_days IS NULL OR lead_time_days >= 0);

ALTER TABLE mitigation_option
ADD COLUMN planned_order_date TEXT;

ALTER TABLE mitigation_option
ADD COLUMN expected_arrival_date TEXT;

ALTER TABLE mitigation_option
ADD COLUMN feasibility_status TEXT
CHECK (
    feasibility_status IS NULL OR
    feasibility_status IN ('FEASIBLE', 'CONDITIONAL', 'BLOCKED')
);

CREATE INDEX IF NOT EXISTS idx_mitigation_option_supplier
ON mitigation_option(supplier_id);

CREATE INDEX IF NOT EXISTS idx_mitigation_option_feasibility
ON mitigation_option(feasibility_status);
