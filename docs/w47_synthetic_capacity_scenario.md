
# W47 Synthetic Supplier Capacity Scenario

## 1. Purpose

This document defines illustrative supplier capacity values
for testing the W47 supply chain planning workflow.

These values are synthetic and are not actual supplier commitments.

## 2. Scenario Identifier

Scenario ID: SYN-W47-001

Planning week: 2026-W47

Scenario type: Synthetic test data

## 3. Proposed Capacity Values

| Supplier | SKU | Product | Capacity | Unit |
|---|---|---|---:|---|
| SUP001 | SKU001 | Rice | 100 | Kg |
| SUP002 | SKU003 | Sugar | 100 | Kg |
| SUP003 | SKU005 | Milk | 50 | Liter |

## 4. Validation Purpose

The scenario will test:

- Supplier and SKU matching
- Exact planning-week matching
- Capacity limit validation
- Purchase quantity versus available capacity
- Mitigation feasibility decisions

## 5. Data Integrity Rules

1. Existing W46 capacity records must remain unchanged.
2. Synthetic values must never be presented as actual commitments.
3. The scenario ID must remain associated with test results.
4. Synthetic capacity must not silently enter actual planning outputs.
5. Capacity must be checked for the exact supplier, SKU and week.

## 6. Approval Status

Status: Proposed for testing

No synthetic capacity records have been inserted.
