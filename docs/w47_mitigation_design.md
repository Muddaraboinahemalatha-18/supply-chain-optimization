
# W47 Mitigation Recommendation Design

## 1. Purpose

Design traceable purchase mitigation recommendations for the three
W47 projected shortages while preserving W46 mitigation history.

These recommendations are planning options, not confirmed supplier orders.

## 2. W47 Shortage Inputs

| Shortage ID | Product | Shortage | Unit |
|---|---|---:|---|
| SHORT-2026-000001 | Rice | 20 | Kg |
| SHORT-2026-000002 | Sugar | 20 | Kg |
| SHORT-2026-000003 | Milk | 10 | Liter |

Inventory snapshot date: 2026-11-12

Planning scenario: W47-BASELINE-2026-11-12

## 3. Proposed Purchase Options

| Product | Supplier | Shortage | MOQ | Proposed Qty | Unit Cost | Estimated Cost |
|---|---|---:|---:|---:|---:|---:|
| Rice | SUP001 | 20 | 50 | 50 Kg | 48 | 2400 |
| Sugar | SUP002 | 20 | 25 | 25 Kg | 43 | 1075 |
| Milk | SUP003 | 10 | 10 | 10 Liter | 58 | 580 |

Total estimated purchase cost: 4055

Costs are based on existing supplier-SKU policy records.

## 4. Supplier and Policy Validation

Each proposed option must satisfy:

- Supplier exists and is active.
- Supplier is approved for the SKU.
- Proposed quantity meets the minimum order quantity.
- Unit of measure matches the SKU and supplier policy.
- Estimated cost equals proposed quantity multiplied by unit cost.
- Applicable lead-time information exists.

## 5. Capacity Validation

No actual W47 supplier capacity records currently exist.

The synthetic scenario SYN-W47-001 proposes:

| Supplier | SKU | Synthetic Capacity | Proposed Qty |
|---|---|---:|---:|
| SUP001 | SKU001 | 100 Kg | 50 Kg |
| SUP002 | SKU003 | 100 Kg | 25 Kg |
| SUP003 | SKU005 | 50 Liter | 10 Liter |

All three proposed quantities pass the synthetic capacity checks.

These results are conditional on SYN-W47-001.
They must not be represented as actual supplier commitments.

## 6. Lead-Time Assumptions

Hypothetical order date: 2026-11-13

| Product | Lead Time | Estimated Arrival |
|---|---:|---|
| Rice | 2 days | 2026-11-15 |
| Sugar | 3 days | 2026-11-16 |
| Milk | 3 days | 2026-11-16 |

Lead times are illustrative assumptions, not confirmed supplier commitments.

Estimated arrival dates do not guarantee delivery or service.

## 7. Existing Schema Gap

The existing mitigation_option table contains:

- option_id
- shortage_id
- option_type
- description
- proposed_quantity
- estimated_cost
- policy_compliant

It does not independently store supplier, unit, MOQ, capacity scenario,
capacity source, lead time or expected arrival date.

Storing all these values only in description would reduce traceability.

## 8. Proposed Schema Enhancement

Evaluate adding nullable structured fields to mitigation_option:

- supplier_id
- unit_of_measure
- minimum_order_quantity
- unit_cost
- capacity_quantity
- capacity_source
- capacity_scenario_id
- lead_time_days
- planned_order_date
- expected_arrival_date
- feasibility_status

Suggested capacity sources:

- ACTUAL
- SYNTHETIC
- UNAVAILABLE

Suggested feasibility statuses:

- FEASIBLE
- CONDITIONAL
- BLOCKED

Historical W46 rows must remain unchanged.
New fields must not require fabricated values for historical records.

## 9. Mitigation Event History

Record option creation and subsequent review decisions in mitigation_event.

Each event should retain:

- Event ID
- Option ID
- Event type
- Event date
- Decision reason

Do not overwrite previous event history.

## 10. Acceptance Checks

- Three W47 shortage records are linked to their mitigation options.
- Supplier approval and MOQ checks pass.
- Unit and cost calculations reconcile.
- Synthetic capacity is clearly identified.
- Missing actual W47 capacity is not treated as actual feasibility.
- Lead-time assumptions remain identifiable.
- W46 mitigation records remain unchanged.
- Foreign-key and database integrity checks pass.

## 11. Current Status

Design document prepared.
No database changes made by this design document.
No new purchase orders or supplier commitments created.
