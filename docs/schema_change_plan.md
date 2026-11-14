
# Database Schema Change Plan

## 1. Objective

Enhance the existing Supply Chain Optimization database to support the complete business workflow while preserving all existing records.

## 2. Existing Database

- Database: SQLite
- Existing tables: 18
- Existing working records: Must be preserved
- Backup: supply_chain_backup_20261112.db

## 3. New Tables

### 3.1 inbound_order

Tracks expected and actual incoming deliveries.

- inbound_id: Primary key
- po_line_id: Foreign key to purchase_order_line
- expected_arrival_date
- actual_arrival_date
- inbound_quantity
- received_quantity
- status

### 3.2 production_capacity

Stores weekly production limits.

- production_capacity_id: Primary key
- sku_id: Foreign key to sku
- location_id: Foreign key to location
- production_week
- maximum_quantity

Unique business key: SKU + location + production week.

### 3.3 sku_substitute

Stores substitute product relationships.

- substitute_id: Primary key
- original_sku_id: Foreign key to sku
- substitute_sku_id: Foreign key to sku
- is_approved
- conversion_factor
- effective_from
- effective_to

Original and substitute SKUs must be different.

### 3.4 supplier_sku_policy

Stores effective-dated supplier purchasing policies.

- policy_id: Primary key
- supplier_id: Foreign key to supplier
- sku_id: Foreign key to sku
- minimum_order_quantity
- unit_cost
- effective_from
- effective_to

Only approved supplier-SKU relationships may be used for purchasing recommendations.

### 3.5 data_quality_issue

Tracks detected data-quality issues.

- issue_id: Primary key
- issue_type
- affected_entity
- affected_record_id
- severity
- description
- detected_at
- status

### 3.6 scenario_ground_truth

Stores expected labels for testing and evaluation.

- ground_truth_id: Primary key
- scenario_id
- issue_type
- expected_label
- expected_decision
- explanation

This table must never be used as input to the planning engine.

## 4. Existing Table Enhancements

Review and improve:

1. supplier_sku: preserve supplier approval relationships.
2. lead_time: validate effective date ranges.
3. production_plan: validate planned quantity against production capacity.
4. inventory: validate reserved quantity against on-hand quantity.
5. purchase_order_line: reconcile ordered and received quantities.
6. purchase_order: validate lifecycle transitions.
7. shortage: validate calculated shortage quantity.
8. mitigation_option: validate policy compliance.

## 5. Data Integrity Rules

- All primary keys must be unique.
- All foreign keys must reference existing records.
- Quantities must use compatible units.
- Inbound quantities must not be counted twice.
- Supplier capacity must not be exceeded.
- Production must not exceed production capacity.
- Unapproved substitutes must be rejected.
- Historical events must not be overwritten.
- Ground-truth data must remain separate from planning inputs.

## 6. Migration Safety

1. Preserve the existing database.
2. Use a controlled migration script.
3. Do not delete existing tables or records.
4. Do not rerun completed inventory correction scripts.
5. Verify table definitions after migration.
6. Verify existing row counts after migration.
7. Run foreign-key integrity checks.
8. Verify all new tables and relationships.

## 7. Implementation Status

- [x] Data dictionary documented.
- [x] Existing schema gaps documented.
- [x] Database change plan documented.
- [x] Proposed SQL reviewed.
- [x] Migration 001 created and executed.
- [x] Migration 001 database integrity verified.
- [x] Migration 002 created and executed.
- [x] Migration 002 database integrity verified.

### Remaining Implementation Work

- [x] Lead-time records populated.
- [x] Supplier-SKU purchasing policies populated.
- [x] Inbound order history populated.
- [x] W47 forecast records inserted and verified.
- [x] Historical shortage resolution events verified.
- [x] W47 inventory projection preview verified.
- [x] W47 conditional purchase options preview verified.
- [ ] W47 supplier capacity source established.
- [ ] Production and BOM applicability reviewed.
- [ ] W47 projected shortages persisted with traceable events.
- [ ] Feasible mitigation recommendations implemented.
- [ ] Five anomaly scenarios implemented and tested.
- [ ] Evaluation metrics and acceptance criteria verified.
- [ ] Full-scale deterministic data generator implemented.
- [ ] CSV, JSON, SQL exports and README completed.
- [ ] Reproducibility checksums verified.