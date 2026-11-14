
# Exception Scenarios Design

## 1. Purpose

Define controlled synthetic exception scenarios to test the
Supply Chain Optimization workflow.

The scenarios will verify whether invalid or inconsistent supply
chain inputs are detected and handled correctly.

Existing W46 historical records and W47 planning records must
remain unchanged.

## 2. Testing Principles

1. Use separate synthetic test records.
2. Do not corrupt existing valid database records.
3. Assign deterministic scenario IDs.
4. Define expected outcomes using documented business rules.
5. Keep ground-truth labels separate from input features.
6. Record detected issues with their issue types.
7. Preserve traceability between scenarios, detected issues
   and expected decisions.

## 3. Planned Exception Scenarios

| Scenario ID | Issue Type | Description | Expected Label | Expected Decision |
|---|---|---|---|---|
| EXC-001 | INBOUND_DOUBLE_COUNT | Received inbound stock is added to inventory a second time | INVALID | REJECT |
| EXC-002 | UNAPPROVED_SUBSTITUTE | An unapproved substitute SKU is proposed to cover a shortage | INVALID | REJECT |
| EXC-003 | CAPACITY_EXCEEDED | Proposed supplier quantity exceeds available supplier capacity | INVALID | REJECT |
| EXC-004 | MISSING_LEAD_TIME | A purchase recommendation has no applicable lead-time record | INVALID | FLAG |
| EXC-005 | UOM_MISMATCH | Demand, inventory or proposed supply quantities use incompatible units | INVALID | REJECT |

## 4. Scenario Details

### EXC-001: Inbound Stock Counted Twice

- Issue type: INBOUND_DOUBLE_COUNT
- Test condition: Received inbound quantity is already included
  in the inventory snapshot but is added again.
- Expected detection: Duplicate inbound contribution.
- Expected decision: Reject the double-counted calculation.
- Existing inventory must not be modified.

### EXC-002: Unapproved Substitute

- Issue type: UNAPPROVED_SUBSTITUTE
- Test condition: A substitute SKU is proposed without an
  approved substitution relationship.
- Expected detection: Substitute approval is missing.
- Expected decision: Reject the proposed substitution.
- Do not create an actual substitute relationship.

### EXC-003: Supplier Capacity Exceeded

- Issue type: CAPACITY_EXCEEDED
- Test condition: Proposed purchase quantity exceeds the
  supplier's available capacity for the planning week.
- Expected detection: Capacity constraint violation.
- Expected decision: Reject the infeasible recommendation.
- Use a separate synthetic capacity fixture.

### EXC-004: Missing Lead Time

- Issue type: MISSING_LEAD_TIME
- Test condition: No effective lead-time record exists for
  the selected supplier and destination location.
- Expected detection: Lead-time information is unavailable.
- Expected decision: Flag the recommendation for review.
- Do not classify an existing valid lead-time record as missing.

### EXC-005: Unit-of-Measure Mismatch

- Issue type: UOM_MISMATCH
- Test condition: Quantities from incompatible units are
  compared or reconciled without a valid conversion.
- Expected detection: Unit-of-measure inconsistency.
- Expected decision: Reject the invalid calculation.
- Do not silently convert incompatible units.

## 5. Ground-Truth Separation

Ground-truth labels must not be included in scenario input features.

Maintain separate files:

- data/scenarios/exception_scenarios.csv
- data/scenarios/exception_ground_truth.csv

The scenario input file contains only test inputs.

The ground-truth file contains:
- Scenario ID
- Issue type
- Expected label
- Expected decision
- Explanation

## 6. Validation Requirements

Each scenario must be tested independently.

The test process must verify:

1. Scenario input is loaded correctly.
2. The expected issue is detected.
3. The detected issue type matches ground truth.
4. The expected decision is produced.
5. No unrelated valid records are modified.
6. Database foreign-key and integrity checks pass.
7. Ground-truth labels are not used as input features.

## 7. Preservation Requirements

- Preserve all W46 resolved shortages.
- Preserve all W46 mitigation records and events.
- Preserve all W47 projected shortages.
- Preserve all W47 mitigation recommendations and events.
- Do not insert synthetic supplier capacity as actual capacity.
- Do not create purchase orders or supplier commitments
  during exception testing.

## 8. Completion Criteria

The exception-testing stage is complete only when:

- All five scenarios have deterministic inputs.
- All five expected outcomes are documented.
- All five scenarios are tested.
- Detection results match ground truth.
- No existing business records are unintentionally changed.
- Database integrity checks pass.
