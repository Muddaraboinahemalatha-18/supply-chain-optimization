
# Supply Chain Optimization – Schema Gap Analysis

## 1. Purpose

This document compares the existing SQLite database schema with the original Supply Chain Optimization problem statement.

The goal is to identify missing entities, fields, relationships, validation rules, and data requirements before making database changes.

Existing working data must be preserved.

## 2. Existing Database Summary

The current database contains 25 tables.

### 2.1 Original Tables

1. sku
2. location
3. supplier
4. sku_location
5. forecast_demand
6. inventory
7. supplier_sku
8. supplier_capacity
9. lead_time
10. purchase_order
11. purchase_order_line
12. production_plan
13. bom
14. inventory_event
15. purchase_order_event
16. shortage
17. mitigation_option
18. mitigation_event

### 2.2 Tables Added Through Migrations

19. inbound_order
20. production_capacity
21. sku_substitute
22. supplier_sku_policy
23. data_quality_issue
24. scenario_ground_truth
25. shortage_event

The six supporting tables were added through Migration 001.
The shortage_event table was added through Migration 002.

Both migrations were executed and their database integrity checks passed.

## 3. Existing Data Status

| Table | Current Records | Status |
|---|---:|---|
| sku | 5 | Available |
| location | 3 | Available |
| supplier | 3 | Available |
| sku_location | 5 | Available |
| forecast_demand | 10 | Available - W46 and W47 |
| inventory | 5 | Available |
| supplier_sku | 5 | Available |
| supplier_capacity | 5 | W46 only |
| lead_time | 9 | Available - illustrative assumptions |
| purchase_order | 3 | Available |
| purchase_order_line | 3 | Available |
| production_plan | 0 | Not populated |
| bom | 0 | Not populated |
| inventory_event | 3 | Available |
| purchase_order_event | 0 | Not populated |
| shortage | 3 | Historical shortages resolved |
| mitigation_option | 3 | Historical options available |
| mitigation_event | 0 | Not populated |
| inbound_order | 3 | Received inbound records |
| production_capacity | 0 | Not populated |
| sku_substitute | 0 | Not populated |
| supplier_sku_policy | 5 | Available |
| data_quality_issue | 0 | Not populated |
| scenario_ground_truth | 0 | Not populated |
| shortage_event | 3 | Historical resolution events |

Note:

- W46 and W47 refer to forecast weeks 2026-W46 and 2026-W47.
- Lead-time values are illustrative assumptions, not confirmed supplier commitments.
- W47 forecast and inventory projection results are planning estimates, not confirmed actual business demand or future inventory.
- Existing historical shortage records and their resolution events must be preserved.

## 4. Supporting Entities Added Through Migrations

The following supporting entities have been created and verified.

| Entity | Purpose | Current Records |
|---|---|---:|
| inbound_order | Track expected and actual incoming deliveries | 3 |
| production_capacity | Define weekly production limits | 0 |
| sku_substitute | Maintain approved substitute relationships | 0 |
| supplier_sku_policy | Store supplier purchasing policies | 5 |
| data_quality_issue | Track detected data-quality exceptions | 0 |
| scenario_ground_truth | Store expected labels and decisions separately | 0 |
| shortage_event | Preserve shortage detection and resolution history | 3 |

The tables exist, but empty tables still require appropriate data population or scenario-based testing where applicable.

All entities must maintain appropriate primary keys, foreign keys, constraints, indexes, and traceability.

## 5. Required Schema Enhancements

### 5.1 Supplier-SKU

Support the following:

- Minimum order quantity.
- Effective-from date.
- Effective-to date.
- Approved supplier validation.
- Supplier-specific unit price.
- Supplier and SKU relationship validation.

Only approved and effective supplier-SKU relationships may be used for purchasing recommendations.

### 5.2 Inventory

- Preserve dated inventory snapshots.
- Validate reserved quantity against on-hand quantity.
- Calculate available inventory as on-hand minus reserved.
- Do not duplicate inbound quantities in inventory snapshots.
- Maintain inventory changes through explicit events.
- Validate inventory quantities using compatible units of measurement.

### 5.3 Supplier Capacity

- Maintain capacity for each supplier, SKU, and planning week.
- Calculate committed capacity from purchase-order allocations.
- Prevent valid purchase allocations from exceeding capacity.
- Validate capacity for the correct planning week.
- Do not use capacity from one week as a substitute for another week without documented justification.

### 5.4 Lead Time

- Maintain supplier-to-location lead-time records.
- Support effective dates.
- Prevent overlapping effective periods for the same supplier and location.
- Calculate estimated arrival dates using order dates and applicable lead times.
- Distinguish illustrative lead-time assumptions from confirmed supplier commitments.

### 5.5 Production and BOM

- Maintain weekly production capacity.
- Populate production plans where applicable.
- Define component requirements using BOM.
- Validate production against available capacity and component inventory.
- Reject circular BOM relationships.
- Prevent planned production from exceeding available production capacity.

### 5.6 Substitutes

- Maintain original and substitute SKU relationships.
- Record approval status and conversion factor.
- Support effective-from and effective-to dates.
- Reject unapproved or ineffective substitutions.
- Validate unit compatibility and conversion factors.

### 5.7 Inbound Orders

- Track planned, shipped, delayed, partially received, and received quantities.
- Connect inbound records to purchase-order lines.
- Reconcile ordered, inbound, and received quantities.
- Prevent double-counting of incoming and received quantities.
- Preserve actual arrival dates and receipt history.

## 6. Data Quality and Exception Scenarios

The project must test these five deliberate anomaly scenarios.

| Scenario | Expected System Behaviour |
|---|---|
| Inbound counted twice | Detect duplicate inventory impact |
| Substitute not approved | Reject substitute recommendation |
| Supplier capacity exceeded | Flag infeasible allocation |
| Shortage calculated without lead time | Detect incorrect planning result |
| UOM mismatch | Reject invalid quantity comparison |

These scenarios must be labelled and kept separate from normal baseline data.

They must not silently corrupt valid production records.

Each scenario must have:

- A unique scenario identifier.
- A documented issue type.
- An expected ground-truth label.
- An expected system decision.
- An explanation of the expected outcome.

Ground-truth labels must not be used as planning-engine input features.

## 7. Data Generation Gaps

Current starter data is much smaller than the required full-scale dataset.

| Requirement | Target |
|---|---:|
| SKUs | 3,000 |
| Locations | 50 |
| Suppliers | 500 |
| Forecast horizon | 52 weeks |
| Inbound orders | 10,000 |

The generator must support both starter and full configurations.

Both configurations must use the same deterministic generation rules and fixed seed:

20261022

The generator must:

- Create parent/master records before dependent records.
- Generate valid foreign-key relationships.
- Generate SKU-location demand by week.
- Generate inventory and inbound supply.
- Generate supplier capacity, minimum quantities, and lead times.
- Generate production and BOM data where applicable.
- Calculate projected available balances.
- Generate shortages and candidate mitigations from documented rules.
- Create labelled anomaly scenarios separately from baseline data.
- Support reproducible CSV, JSON, and SQL exports.

## 8. Identifier Gaps

Existing starter records use legacy identifiers such as:

- SKU001
- LOC001
- SUP001

New full-scale generated records must follow the documented conventions:

- SKU-000001
- LOC-000001
- SUP-000001
- DEM-<sku>-<location>-2026W01
- PO-2026-000001
- SHORT-2026-000001
- MIT-<shortage-id>-01

Counters must be zero-padded.

Identifiers must be immutable and consistent across database records and exported files.

Existing identifiers must not be changed without a documented migration plan and foreign-key verification.

## 9. Required Validation Enhancements

The final database and workflow must validate:

1. Primary-key uniqueness.
2. Foreign-key integrity.
3. Required fields and allowed values.
4. Quantity and cost constraints.
5. UOM consistency.
6. Lead-time effective dates.
7. Supplier minimum-order quantities.
8. Supplier capacity constraints.
9. Production capacity constraints.
10. BOM validity and cycle prevention.
11. Inbound receipt reconciliation.
12. Purchase-order lifecycle transitions.
13. Inventory event history.
14. Weekly projected balance reconciliation.
15. Shortage calculation accuracy.
16. Mitigation policy compliance.
17. Ground-truth isolation.
18. Reproducible data generation.
19. Duplicate forecast detection.
20. Valid parent-child relationships.
21. Effective-date validation for supplier policies.
22. Correct shortage lifecycle transitions.
23. Correct mitigation quantity and cost calculations.

Validation must report detected issues without silently changing valid historical records.

## 10. Preservation and Migration Rules

- Keep the existing database backups.
- Do not delete existing working records.
- Do not rerun database-modifying scripts unnecessarily.
- Do not rerun inventory correction scripts.
- Review every schema modification before executing it.
- Use a database migration or controlled schema update for new entities and fields.
- Verify row counts and foreign-key integrity after every migration.
- Maintain event history rather than overwriting historical records.
- Use transactions for database modifications.
- Keep historical and future planning scenarios separate.
- Preserve the original W46 forecast and historical shortage records.
- Do not count already received inbound quantities twice.

## 11. Implementation Order

The planned implementation order is:

1. Complete and verify the data dictionary.
2. Review the existing schema and document gaps.
3. Design the additional tables and field changes.
4. Review the proposed schema before migration.
5. Apply controlled database changes.
6. Populate and verify missing planning data.
7. Build the deterministic synthetic data generator.
8. Develop the planning and shortage calculation engine.
9. Develop mitigation recommendations.
10. Test all five anomaly scenarios.
11. Validate evaluation metrics and acceptance criteria.
12. Export CSV, JSON, SQL, documentation, and validation reports.
13. Verify reproducibility using identical seed and configuration.
14. Produce a final validation summary and source manifest.

## 12. Acceptance Criteria

The completed project must:

- Reconcile projected inventory balances week by week.
- Explain why each shortage occurs.
- Respect supplier capacity, minimum order quantity, and lead times.
- Respect production capacity and BOM requirements where applicable.
- Reject unapproved substitutes.
- Compare feasible mitigation alternatives using cost and service impact.
- Preserve historical state changes.
- Detect all five documented anomaly scenarios.
- Keep ground-truth labels separate from planning inputs.
- Reproduce identical outputs with the same seed and configuration.
- Maintain referential integrity across related entities.
- Produce traceable and explainable planning decisions.
- Report measurable evaluation metrics.

## 13. Production and Substitute Applicability Review

The starter dataset contains five finished-product SKUs assigned to three warehouse locations.

Inspection results:

| Table | Records |
|---|---:|
| production_capacity | 0 |
| production_plan | 0 |
| bom | 0 |
| sku_substitute | 0 |

### Decision

- Production planning is not currently demonstrated by the starter data.
- No BOM component relationships will be invented.
- No production capacity or production plans will be inserted without a documented synthetic scenario or valid source.
- Production-related tables remain available for future manufacturing scenarios.
- Substitute relationships will not be invented.
- Substitute-based mitigation will remain unavailable until approved relationships and conversion factors are defined.

This decision applies to the current starter dataset.

It does not remove production or substitute planning from the overall project requirements.

## 14. Current Implementation Status

### Completed and Verified

- [x] Original database schema inspected.
- [x] Data dictionary documented.
- [x] Schema gap analysis documented.
- [x] Schema change plan documented.
- [x] Migration 001 executed and verified.
- [x] Migration 002 executed and verified.
- [x] Lead-time records populated.
- [x] Supplier-SKU purchasing policies populated.
- [x] Inbound order history populated.
- [x] W47 forecast records inserted and verified.
- [x] Historical shortage resolution events verified.
- [x] W47 inventory projection preview verified.
- [x] W47 conditional purchase options preview verified.
- [x] Production and BOM applicability inspected.
- [x] Substitute applicability inspected.

### Remaining Implementation Work

- [ ] Establish a documented W47 supplier capacity source.
- [ ] Review and document synthetic planning assumptions.
- [ ] Persist W47 projected shortages with traceable events.
- [ ] Implement feasible mitigation recommendations.
- [ ] Implement and test all five anomaly scenarios.
- [ ] Verify evaluation metrics and acceptance criteria.
- [ ] Implement the full-scale deterministic data generator.
- [ ] Generate starter and full-scale datasets.
- [ ] Complete CSV, JSON, and SQL exports.
- [ ] Complete README and source manifest.
- [ ] Run data integrity and reconciliation validations.
- [ ] Verify reproducibility using checksums.
- [ ] Produce the final validation report.

Note: A completed preview or inspection does not mean that the corresponding planning records have been persisted or that the complete workflow has passed acceptance testing.
