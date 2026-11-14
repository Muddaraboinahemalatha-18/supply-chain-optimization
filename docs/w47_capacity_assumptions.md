
# W47 Supplier Capacity Planning Assumptions

## 1. Purpose

This document records the supplier capacity information available
for the 2026-W47 planning scenario.

It distinguishes existing supplier capacity records from any
synthetic assumptions used for testing.

## 2. Existing Capacity Data

The database currently contains five supplier capacity records.

All five records belong to 2026-W46.

| Supplier | SKU | Week | Maximum Quantity |
|---|---|---|---:|
| SUP001 | SKU001 - Rice | 2026-W46 | 200 Kg |
| SUP001 | SKU002 - Wheat | 2026-W46 | 300 Kg |
| SUP002 | SKU003 - Sugar | 2026-W46 | 150 Kg |
| SUP002 | SKU004 - Oil | 2026-W46 | 200 Liter |
| SUP003 | SKU005 - Milk | 2026-W46 | 100 Liter |

There are currently no supplier capacity records for 2026-W47.

W46 capacity must not be copied into W47 or treated as a
confirmed commitment for another week.

## 3. W47 Planning Requirements

The current W47 projection identifies these estimated shortages:

| SKU | Product | Location | Shortage | Unit |
|---|---|---|---:|---|
| SKU001 | Rice | LOC001 | 20 | Kg |
| SKU003 | Sugar | LOC002 | 20 | Kg |
| SKU005 | Milk | LOC003 | 10 | Liter |

Existing supplier relationships:

| Supplier | Product | MOQ | Unit Cost |
|---|---|---:|---:|
| SUP001 | Rice | 50 Kg | 48 |
| SUP002 | Sugar | 25 Kg | 43 |
| SUP003 | Milk | 10 Liter | 58 |

## 4. Capacity Data Limitation

Actual W47 supplier capacity has not been provided.

Therefore:

- W47 capacity is currently unverified.
- W46 capacity cannot establish W47 availability.
- Purchase options cannot be marked capacity-feasible.
- No actual purchase commitment can be inferred.

## 5. Synthetic Scenario Policy

If synthetic W47 capacity is introduced for testing:

1. It must be explicitly identified as synthetic.
2. It must have a documented scenario identifier.
3. It must not be represented as actual supplier capacity.
4. It must not overwrite W46 records.
5. It must be used only for the documented planning scenario.
6. Capacity validation must compare proposed quantities with
   the capacity for the exact supplier, SKU and planning week.
7. Reports must distinguish synthetic test results from
   verified supplier commitments.

## 6. Current Decision

No W47 supplier capacity records have been inserted.

The W47 purchase options remain conditional.

Capacity feasibility is unverified until valid capacity information
or an explicitly approved synthetic scenario is available.
