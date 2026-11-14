
# Supply Chain Optimization – Data Dictionary

## 1. Purpose

This document defines the database entities, fields, data types, relationships, units, allowed values, uniqueness rules, and validation requirements for the Supply Chain Optimization project.

The system matches forecast demand with available inventory, supplier capacity, lead times, inbound orders, and production constraints to identify shortages and recommend policy-compliant mitigation options.

All normal planning data must be valid. Deliberate anomaly scenarios must be stored separately and clearly labelled.

---

## 2. General Data Standards

| Standard | Rule |
|---|---|
| Database | SQLite |
| Primary keys | TEXT, unique and immutable |
| Foreign keys | Must reference valid parent records |
| Quantities | REAL, non-negative unless explicitly stated |
| Costs | REAL, non-negative, stored in INR |
| Dates | ISO format: YYYY-MM-DD |
| Planning week | YYYY-Www format, e.g. 2026-W46 |
| Boolean values | 0 = False, 1 = True |
| Random seed | 20261022 |
| Missing values | NULL only for optional fields |
| History | Store important state changes as events |

### ID conventions for newly generated full-scale data

- SKU: SKU-000001
- Location: LOC-000001
- Supplier: SUP-000001
- Forecast: DEM-SKU-000001-LOC-000001-2026W01
- Purchase Order: PO-2026-000001
- Shortage: SHORT-2026-000001
- Mitigation: MIT-SHORT-2026-000001-01

IDs must be deterministic and must not change after creation.

Note: Existing starter records use legacy IDs such as SKU001 and LOC001. Preserve them until a planned migration is designed.

---

## 3. Core Entity Data Dictionary

### 3.1 SKU

Purpose: Stores product information.

| Field | Type | Required | Rules / Validation | Unique |
|---|---|---|---|---|
| sku_id | TEXT | Yes | Must follow SKU ID convention for new generated data | Yes, PK |
| sku_name | TEXT | Yes | Non-empty product name | No |
| category | TEXT | No | Valid product category | No |
| unit_of_measure | TEXT | Yes | KG, LITER, UNIT, etc. | No |
| unit_cost | REAL | Yes | Must be >= 0; INR per unit | No |
| is_active | INTEGER | Yes | 0 or 1 | No |

### 3.2 Location

Purpose: Stores warehouse, distribution centre, or production location details.

| Field | Type | Required | Rules / Validation | Unique |
|---|---|---|---|---|
| location_id | TEXT | Yes | LOC-000001 format for new data | Yes, PK |
| location_name | TEXT | Yes | Non-empty | No |
| location_type | TEXT | No | WAREHOUSE, DISTRIBUTION_CENTER, FACTORY | No |
| city | TEXT | No | Valid city name | No |
| state | TEXT | No | Valid state name | No |

### 3.3 ForecastDemand

Purpose: Stores weekly forecast demand for each SKU and location.

| Field | Type | Required | Rules / Validation | Unique |
|---|---|---|---|---|
| forecast_id | TEXT | Yes | DEM-SKU-LOCATION-WEEK format | Yes, PK |
| sku_id | TEXT | Yes | Must exist in SKU | No |
| location_id | TEXT | Yes | Must exist in Location | No |
| forecast_week | TEXT | Yes | YYYY-Www format | No |
| forecast_quantity | REAL | Yes | >= 0, in SKU UOM | No |
| forecast_version | INTEGER | Yes | >= 1 | No |

Business uniqueness: One record per SKU, location, week, and forecast version.

### 3.4 Inventory

Purpose: Stores dated inventory snapshots.

| Field | Type | Required | Rules / Validation | Unique |
|---|---|---|---|---|
| inventory_id | TEXT | Yes | Unique inventory ID | Yes, PK |
| sku_id | TEXT | Yes | Must exist in SKU | No |
| location_id | TEXT | Yes | Must exist in Location | No |
| on_hand_quantity | REAL | Yes | >= 0, in SKU UOM | No |
| reserved_quantity | REAL | Yes | >= 0 and <= on-hand quantity | No |
| unit_of_measure | TEXT | Yes | Must match SKU UOM | No |
| inventory_date | TEXT | Yes | YYYY-MM-DD | No |

Business uniqueness: SKU + location + inventory date.

Available stock = on-hand quantity - reserved quantity.

Inbound quantities must be calculated from eligible inbound records, not added again to the inventory snapshot.

### 3.5 Supplier

Purpose: Stores supplier information.

| Field | Type | Required | Rules / Validation | Unique |
|---|---|---|---|---|
| supplier_id | TEXT | Yes | SUP-000001 format for new data | Yes, PK |
| supplier_name | TEXT | Yes | Non-empty | No |
| supplier_type | TEXT | No | Valid supplier category | No |
| reliability_score | REAL | No | Between 0 and 1 | No |
| is_active | INTEGER | Yes | 0 or 1 | No |

### 3.6 SupplierCapacity

Purpose: Defines the maximum quantity a supplier can provide for a SKU during a particular week.

| Field | Type | Required | Rules / Validation | Unique |
|---|---|---|---|---|
| capacity_id | TEXT | Yes | Unique capacity ID | Yes, PK |
| supplier_id | TEXT | Yes | Must exist in Supplier | No |
| sku_id | TEXT | Yes | Must exist in SKU | No |
| capacity_week | TEXT | Yes | YYYY-Www | No |
| maximum_quantity | REAL | Yes | >= 0, in SKU UOM | No |

Business uniqueness: Supplier + SKU + capacity week.

Committed capacity must be derived from valid purchase-order allocations. Available capacity = maximum quantity - committed quantity.

### 3.7 LeadTime

Purpose: Stores supplier-to-location delivery lead times.

| Field | Type | Required | Rules / Validation | Unique |
|---|---|---|---|---|
| lead_time_id | TEXT | Yes | Unique lead-time ID | Yes, PK |
| supplier_id | TEXT | Yes | Must exist in Supplier | No |
| location_id | TEXT | Yes | Must exist in Location | No |
| lead_time_days | INTEGER | Yes | >= 0, days | No |
| effective_from | TEXT | Yes | YYYY-MM-DD | No |
| effective_to | TEXT | No | YYYY-MM-DD, >= effective_from | No |

Effective date ranges for the same supplier and location must not overlap.

### 3.8 PurchaseOrder

Purpose: Stores purchase-order header information.

| Field | Type | Required | Rules / Validation | Unique |
|---|---|---|---|---|
| po_id | TEXT | Yes | PO-YYYY-000001 format | Yes, PK |
| supplier_id | TEXT | Yes | Must exist in Supplier | No |
| order_date | TEXT | Yes | YYYY-MM-DD | No |
| expected_date | TEXT | Yes | >= order_date | No |
| status | TEXT | Yes | DRAFT, CREATED, APPROVED, SHIPPED, PARTIALLY_RECEIVED, RECEIVED, CANCELLED | No |

A purchase order can contain multiple purchase-order lines.

### 3.9 ProductionPlan

Purpose: Stores planned production for a SKU and location by week.

| Field | Type | Required | Rules / Validation | Unique |
|---|---|---|---|---|
| production_id | TEXT | Yes | Unique production ID | Yes, PK |
| sku_id | TEXT | Yes | Must exist in SKU | No |
| location_id | TEXT | Yes | Must exist in Location | No |
| production_week | TEXT | Yes | YYYY-Www | No |
| planned_quantity | REAL | Yes | >= 0, in SKU UOM | No |

Business uniqueness: SKU + location + production week.

Planned production must not exceed available production capacity.

### 3.10 Shortage

Purpose: Stores calculated shortages after considering demand, inventory, inbound supply, lead times, and production.

| Field | Type | Required | Rules / Validation | Unique |
|---|---|---|---|---|
| shortage_id | TEXT | Yes | SHORT-YYYY-000001 format | Yes, PK |
| sku_id | TEXT | Yes | Must exist in SKU | No |
| location_id | TEXT | Yes | Must exist in Location | No |
| shortage_week | TEXT | Yes | YYYY-Www | No |
| demand_quantity | REAL | Yes | >= 0, in SKU UOM | No |
| available_quantity | REAL | Yes | >= 0, in SKU UOM | No |
| shortage_quantity | REAL | Yes | >= 0, in SKU UOM | No |
| priority | TEXT | Yes | P1, P2, P3 | No |
| status | TEXT | Yes | OPEN, UNDER_REVIEW, MITIGATED, CLOSED | No |

Calculation:

Projected balance = opening available inventory + eligible inbound receipts + eligible production - forecast demand.

Shortage quantity = MAX(0, -projected balance).

The shortage record must have an explainable cause.

### 3.11 MitigationOption

Purpose: Stores possible actions to reduce or resolve shortages.

| Field | Type | Required | Rules / Validation | Unique |
|---|---|---|---|---|
| option_id | TEXT | Yes | MIT-SHORTAGE-01 format | Yes, PK |
| shortage_id | TEXT | Yes | Must exist in Shortage | No |
| option_type | TEXT | Yes | PURCHASE, EXPEDITE, PRODUCTION, TRANSFER, SUBSTITUTE | No |
| description | TEXT | Yes | Non-empty explanation | No |
| proposed_quantity | REAL | Yes | >= 0, in SKU UOM | No |
| estimated_cost | REAL | Yes | >= 0, INR | No |
| policy_compliant | INTEGER | Yes | 0 or 1 | No |

Only policy-compliant options may be selected as recommended actions.

---

## 4. Supporting Entity Data Dictionary

These supporting entities are required to represent the complete workflow accurately.

### 4.1 SKU-Location

Purpose: Defines which SKUs are handled at which locations.

| Field | Type | Required | Rules |
|---|---|---|---|
| sku_id | TEXT | Yes | FK to SKU |
| location_id | TEXT | Yes | FK to Location |

Primary key: sku_id + location_id.

Relationship: SKU and Location have a many-to-many relationship through this table.

### 4.2 Supplier-SKU

Purpose: Defines which suppliers are approved to supply each SKU and their purchasing policies.

| Field | Type | Required | Rules |
|---|---|---|---|
| supplier_id | TEXT | Yes | FK to Supplier |
| sku_id | TEXT | Yes | FK to SKU |
| is_approved | INTEGER | Yes | 0 or 1 |
| unit_cost | REAL | Yes | >= 0, INR per SKU unit |
| minimum_order_quantity | REAL | Yes | >= 0, in SKU UOM |
| effective_from | TEXT | Yes | YYYY-MM-DD |
| effective_to | TEXT | No | >= effective_from |

Primary key: supplier_id + sku_id + effective_from.

An unapproved supplier-SKU combination must not be selected for a recommended purchase.

### 4.3 PurchaseOrderLine

Purpose: Stores individual products and destinations within a purchase order.

| Field | Type | Required | Rules |
|---|---|---|---|
| po_line_id | TEXT | Yes | Unique line ID |
| po_id | TEXT | Yes | FK to PurchaseOrder |
| sku_id | TEXT | Yes | FK to SKU |
| location_id | TEXT | Yes | FK to Location |
| order_quantity | REAL | Yes | >= 0, in SKU UOM |
| received_quantity | REAL | Yes | >= 0 and <= order quantity |
| unit_of_measure | TEXT | Yes | Must match SKU UOM |

One purchase order can have many purchase-order lines.

### 4.4 InboundOrder

Purpose: Tracks expected incoming supply and delivery status.

| Field | Type | Required | Rules |
|---|---|---|---|
| inbound_id | TEXT | Yes | Unique inbound ID |
| po_line_id | TEXT | Yes | FK to PurchaseOrderLine |
| expected_arrival_date | TEXT | Yes | >= order date |
| actual_arrival_date | TEXT | No | Must be >= order date |
| inbound_quantity | REAL | Yes | >= 0, in SKU UOM |
| status | TEXT | Yes | PLANNED, IN_TRANSIT, PARTIALLY_RECEIVED, RECEIVED, DELAYED, CANCELLED |

Inbound supply must be counted only once. Received quantities must reconcile with purchase-order line and inventory events.

### 4.5 ProductionCapacity

Purpose: Defines production limits for each SKU and location per week.

| Field | Type | Required | Rules |
|---|---|---|---|
| production_capacity_id | TEXT | Yes | Unique ID |
| sku_id | TEXT | Yes | FK to SKU |
| location_id | TEXT | Yes | FK to Location |
| production_week | TEXT | Yes | YYYY-Www |
| maximum_quantity | REAL | Yes | >= 0, in SKU UOM |

Business uniqueness: SKU + location + production week.

### 4.6 BillOfMaterials (BOM)

Purpose: Defines component requirements for producing a parent SKU.

| Field | Type | Required | Rules |
|---|---|---|---|
| bom_id | TEXT | Yes | Unique BOM ID |
| parent_sku_id | TEXT | Yes | FK to SKU |
| component_sku_id | TEXT | Yes | FK to SKU |
| component_quantity | REAL | Yes | > 0, component units per parent unit |

A SKU cannot be its own component. BOM cycles must be rejected.

### 4.7 SKU Substitute

Purpose: Defines approved substitute products.

| Field | Type | Required | Rules |
|---|---|---|---|
| substitute_id | TEXT | Yes | Unique ID |
| original_sku_id | TEXT | Yes | FK to SKU |
| substitute_sku_id | TEXT | Yes | FK to SKU |
| is_approved | INTEGER | Yes | 0 or 1 |
| conversion_factor | REAL | Yes | > 0 |
| effective_from | TEXT | Yes | YYYY-MM-DD |
| effective_to | TEXT | No | >= effective_from |

Original SKU and substitute SKU must be different. Only approved, effective substitutions are eligible for mitigation.

Conversion factor must be explicitly defined and validated. Do not compare incompatible units without a valid conversion rule.

### 4.8 InventoryEvent

Purpose: Maintains a history of inventory changes.

| Field | Type | Required | Rules |
|---|---|---|---|
| event_id | TEXT | Yes | Unique event ID |
| sku_id | TEXT | Yes | FK to SKU |
| location_id | TEXT | Yes | FK to Location |
| event_type | TEXT | Yes | RECEIPT, ISSUE, RESERVATION, RELEASE, ADJUSTMENT, TRANSFER |
| quantity | REAL | Yes | > 0, in SKU UOM |
| event_date | TEXT | Yes | YYYY-MM-DD |
| source_ref | TEXT | No | Related PO, transfer, or source ID |
| unit_of_measure | TEXT | Yes | Must match SKU UOM |

Events are append-only. Corrections must be recorded as new events.

### 4.9 PurchaseOrderEvent

Purpose: Maintains the lifecycle history of purchase orders.

| Field | Type | Required | Rules |
|---|---|---|---|
| po_event_id | TEXT | Yes | Unique event ID |
| po_id | TEXT | Yes | FK to PurchaseOrder |
| event_type | TEXT | Yes | CREATED, APPROVED, SHIPPED, RECEIVED, CANCELLED |
| event_date | TEXT | Yes | YYYY-MM-DD |
| quantity | REAL | Yes | >= 0 |
| source_ref | TEXT | No | Related document or event ID |

Events are append-only. Valid status transitions must be checked.

### 4.10 MitigationEvent

Purpose: Records decisions and outcomes for mitigation options.

| Field | Type | Required | Rules |
|---|---|---|---|
| mitigation_event_id | TEXT | Yes | Unique event ID |
| option_id | TEXT | Yes | FK to MitigationOption |
| event_type | TEXT | Yes | PROPOSED, APPROVED, REJECTED, EXECUTED, COMPLETED |
| event_date | TEXT | Yes | YYYY-MM-DD |
| decision_reason | TEXT | Yes | Explanation of decision |

### 4.11 DataQualityIssue

Purpose: Records deliberately constructed or detected data-quality exceptions.

| Field | Type | Required | Rules |
|---|---|---|---|
| issue_id | TEXT | Yes | Unique issue ID |
| issue_type | TEXT | Yes | INBOUND_DOUBLE_COUNT, UNAPPROVED_SUBSTITUTE, CAPACITY_EXCEEDED, MISSING_LEAD_TIME, UOM_MISMATCH |
| affected_entity | TEXT | Yes | Entity/table name |
| affected_record_id | TEXT | Yes | ID of affected scenario record |
| severity | TEXT | Yes | LOW, MEDIUM, HIGH, CRITICAL |
| description | TEXT | Yes | Explanation |
| detected_at | TEXT | Yes | Fixed scenario timestamp or YYYY-MM-DD HH:MM:SS |
| status | TEXT | Yes | OPEN, DETECTED, RESOLVED |

Do not silently corrupt normal baseline records to create anomalies.

### 4.12 ScenarioGroundTruth

Purpose: Stores expected labels and decisions for evaluation. This table must never be used as an input to the planning or mitigation engine.

| Field | Type | Required | Rules |
|---|---|---|---|
| ground_truth_id | TEXT | Yes | Unique ID |
| scenario_id | TEXT | Yes | Unique scenario reference |
| issue_type | TEXT | Yes | Documented anomaly type |
| expected_label | TEXT | Yes | Expected result, such as VALID, INVALID, REJECT, FLAG |
| expected_decision | TEXT | Yes | Expected system action |
| explanation | TEXT | Yes | Rule-based reason |

Ground-truth data is used only for testing and evaluation.

---

## 5. Relationship and Cardinality Rules

| Parent | Child | Relationship | Rule |
|---|---|---|---|
| SKU | ForecastDemand | 1:N | One SKU can have many forecasts |
| Location | ForecastDemand | 1:N | One location can have many forecasts |
| SKU | Inventory | 1:N | One SKU can have multiple dated snapshots |
| Location | Inventory | 1:N | One location can store many SKUs |
| SKU | SupplierSKU | 1:N | One SKU can have multiple suppliers |
| Supplier | SupplierSKU | 1:N | One supplier can supply multiple SKUs |
| Supplier | SupplierCapacity | 1:N | One supplier has many capacity records |
| SKU | SupplierCapacity | 1:N | Capacity is SKU-specific |
| Supplier | LeadTime | 1:N | Supplier can serve multiple locations |
| Location | LeadTime | 1:N | Location can receive from multiple suppliers |
| Supplier | PurchaseOrder | 1:N | One supplier can receive many POs |
| PurchaseOrder | PurchaseOrderLine | 1:N | One PO has multiple lines |
| PurchaseOrderLine | InboundOrder | 1:N | A line may have multiple delivery records |
| SKU | ProductionPlan | 1:N | One SKU can have multiple plans |
| SKU | BOM | 1:N | A SKU may be a parent or component |
| SKU | Shortage | 1:N | One SKU can have shortages across weeks |
| Location | Shortage | 1:N | One location can have many shortages |
| Shortage | MitigationOption | 1:N | One shortage can have multiple options |
| MitigationOption | MitigationEvent | 1:N | An option can have multiple decision events |

Optional relationships:
- A SKU may have no BOM if it is not manufactured.
- A SKU may have no substitute.
- A supplier may have no capacity record for a week.
- A shortage may have no feasible mitigation option.
- A purchase order may have no inbound record until shipment planning.

---

## 6. Core Business Calculations

### Available inventory

Available inventory = On-hand quantity - Reserved quantity.

### Available supplier capacity

Available supplier capacity = Maximum supplier capacity - Committed purchase quantity.

### Projected available balance

Projected balance for a SKU-location-week must consider:

- Opening available inventory
- Eligible inbound receipts arriving by the required week
- Eligible production completed by the required week
- Forecast demand
- Component consumption from BOM, where applicable

Projected balance = Opening available inventory + Eligible inbound + Eligible production - Forecast demand - Component consumption.

### Shortage quantity

Shortage quantity = MAX(0, -Projected balance).

### Mitigation evaluation

Each mitigation option must include:

- Proposed quantity
- Estimated cost in INR
- Expected service impact
- Supplier or production feasibility
- Lead-time feasibility
- Policy compliance
- Final recommendation status

A mitigation is not feasible if it violates supplier capacity, minimum order quantity, approved-supplier policy, lead-time requirements, production capacity, or substitute approval rules.

---

## 7. Lifecycle States

### Purchase Order
DRAFT → CREATED → APPROVED → SHIPPED → PARTIALLY_RECEIVED → RECEIVED

A purchase order may move to CANCELLED only through a valid cancellation action.

### Inbound Order
PLANNED → IN_TRANSIT → PARTIALLY_RECEIVED → RECEIVED

A delivery may be marked DELAYED when the expected arrival date is missed.

### Shortage
OPEN → UNDER_REVIEW → MITIGATED → CLOSED

### Mitigation Option
PROPOSED → APPROVED or REJECTED → EXECUTED → COMPLETED

State transitions must be recorded in event history.

---

## 8. Required Data Validation

1. Primary keys must be unique and non-null.
2. Every foreign key must reference an existing parent.
3. SKU-location combinations must exist before demand or inventory is generated.
4. Quantities must be non-negative.
5. Reserved quantity cannot exceed on-hand quantity.
6. Received quantity cannot exceed ordered quantity.
7. Purchase-order expected date cannot be earlier than order date.
8. Lead-time effective dates must be valid and non-overlapping for the same supplier and location.
9. Supplier capacity cannot be exceeded by valid committed allocations.
10. Production quantity cannot exceed production capacity.
11. BOM component quantity must be greater than zero.
12. BOM cycles must not exist.
13. Unapproved substitutes must not be recommended.
14. UOM values must match or have a valid conversion rule.
15. Inbound receipts must not be counted more than once.
16. Projected inventory must reconcile week by week.
17. Shortage quantity must match the calculated projected balance.
18. Lifecycle transitions must be valid.
19. Event records must preserve historical changes.
20. Ground-truth labels must not be used as planning-engine input.

---

## 9. Data Generation Requirements

Baseline synthetic dataset:

| Entity / Dimension | Target |
|---|---:|
| SKUs | 3,000 |
| Locations | 50 |
| Suppliers | 500 |
| Demand horizon | 52 weeks |
| Inbound orders | 10,000 |

The generator must also support a smaller starter dataset using the same generation rules.

Use fixed random seed: 20261022.

Required scenarios:
- Demand spikes
- Constrained suppliers
- Approved substitute SKUs
- Transport delays
- Inbound quantity double-counting anomaly
- Unapproved substitute anomaly
- Supplier capacity exceeded anomaly
- Missing lead-time anomaly
- UOM mismatch anomaly

Generate valid baseline data first. Add labelled anomaly scenarios separately.

---

## 10. Reproducibility and Exports

The project must export:

- CSV files
- JSON files
- SQL seed data
- Data dictionary
- Database schema
- README with setup and execution instructions
- Source manifest
- Validation summary
- Separate ground-truth file

Generating data twice with the same seed and configuration must produce identical row counts and checksums.

Ground-truth records must remain separate from planning-engine input data.
