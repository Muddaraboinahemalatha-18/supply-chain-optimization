
# W47 Shortage Projection Persistence Design

## 1. Purpose

Persist W47 estimated shortages while preserving W46 historical
shortage records and maintaining traceability.

## 2. W47 Projection Inputs

| Forecast ID | Product | Demand | Available | Projected Shortage | Unit |
|---|---|---:|---:|---:|---|
| F006 | Rice | 620 | 600 | 20 | Kg |
| F008 | Sugar | 320 | 300 | 20 | Kg |
| F010 | Milk | 160 | 150 | 10 | Liter |

Inventory snapshot: 2026-11-12.

Planning week: 2026-W47.

## 3. Data Integrity Requirements

1. Existing W46 shortage records must not be modified.
2. Existing W46 resolution events must be preserved.
3. W47 projections must be distinguishable from actual shortages.
4. Each projection must reference its original forecast ID.
5. Each projection must record its inventory snapshot date.
6. Projection assumptions must be documented.
7. Synthetic capacity scenario SYN-W47-001 must remain separate
   from the shortage projection assumptions.
8. No received inbound quantity may be counted twice.

## 4. Proposed Schema Enhancement

Introduce a separate shortage projection history structure.

It must preserve:

- Projection ID
- Shortage ID
- Forecast ID
- Planning scenario ID
- Inventory snapshot date
- Projection creation date
- Projection assumptions
- Projection lifecycle status

A separate projection event history must record
projection creation, revision, confirmation and cancellation.

Actual shortage events must retain their existing meanings.

## 5. Proposed W47 Identifiers

Use deterministic IDs:

- SHORT-2026-000001 - Rice
- SHORT-2026-000002 - Sugar
- SHORT-2026-000003 - Milk

These IDs are proposed and must be checked for uniqueness
before insertion.

## 6. Current Status

No W47 shortage records or projection events have been inserted.

Schema enhancement and read-only preview must be completed
before database insertion.
