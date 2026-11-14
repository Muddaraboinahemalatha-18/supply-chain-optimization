
import sys
import csv
from pathlib import Path
from datetime import date, timedelta

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

SCENARIO_ID = "SYN-W47-001"
PLANNED_ORDER_DATE = date(2026, 11, 13)
CAPACITY_FILE = (
    BASE_DIR / "data" / "scenarios" /
    "SYN-W47-001_supplier_capacity.csv"
)

connection = get_connection()
cursor = connection.cursor()

print("=" * 90)
print("W47 MITIGATION RECOMMENDATION PREVIEW")
print("=" * 90)

try:
    # 1. Load synthetic capacity scenario
    if not CAPACITY_FILE.exists():
        raise FileNotFoundError(
            f"Synthetic capacity file not found: {CAPACITY_FILE}"
        )

    with open(CAPACITY_FILE, "r", encoding="utf-8-sig") as file:
        capacity_rows = list(csv.DictReader(file))

    capacity_lookup = {}

    for row in capacity_rows:
        key = (row["supplier_id"], row["sku_id"])

        if key in capacity_lookup:
            raise ValueError(
                f"Duplicate synthetic capacity entry: {key}"
            )

        if row["scenario_id"] != SCENARIO_ID:
            raise ValueError("Unexpected scenario ID.")

        if row["capacity_week"] != "2026-W47":
            raise ValueError("Unexpected capacity week.")

        if row["source_type"] != "SYNTHETIC":
            raise ValueError("Capacity source must be SYNTHETIC.")

        capacity_lookup[key] = row

    print("\n1. SYNTHETIC CAPACITY SCENARIO")
    print("-" * 90)
    print("Scenario:", SCENARIO_ID)
    print("Capacity records:", len(capacity_rows))

    # 2. Load W47 shortages and approved supplier policies
    cursor.execute("""
        SELECT
            sh.shortage_id,
            sh.sku_id,
            sk.sku_name,
            sk.unit_of_measure,
            sh.location_id,
            sh.shortage_quantity,
            sh.status,

            p.supplier_id,
            su.supplier_name,
            su.is_active,

            p.minimum_order_quantity,
            p.unit_cost,
            p.effective_from AS policy_effective_from,
            p.effective_to AS policy_effective_to,

            ss.is_approved,
            ss.unit_cost AS approved_unit_cost,

            lt.lead_time_days,
            lt.effective_from AS lead_effective_from,
            lt.effective_to AS lead_effective_to

        FROM shortage sh

        JOIN sku sk
            ON sh.sku_id = sk.sku_id

        JOIN supplier_sku_policy p
            ON p.sku_id = sh.sku_id

        JOIN supplier su
            ON su.supplier_id = p.supplier_id

        JOIN supplier_sku ss
            ON ss.supplier_id = p.supplier_id
           AND ss.sku_id = sh.sku_id

        JOIN lead_time lt
            ON lt.supplier_id = p.supplier_id
           AND lt.location_id = sh.location_id

        WHERE sh.shortage_week = '2026-W47'
          AND sh.status = 'PROJECTED'
          AND ss.is_approved = 1

        ORDER BY sh.shortage_id
    """)

    source_rows = cursor.fetchall()

    if len(source_rows) != 3:
        raise ValueError(
            f"Expected 3 W47 recommendations, found {len(source_rows)}."
        )

    # 3. Prepare recommendations
    recommendations = []
    errors = []

    print("\n2. RECOMMENDATION VALIDATION")
    print("-" * 90)

    for row in source_rows:
        shortage_id = row["shortage_id"]
        supplier_id = row["supplier_id"]
        sku_id = row["sku_id"]

        checks = []

        # Supplier status
        checks.append(
            ("Supplier active", row["is_active"] == 1)
        )

        # Supplier approval
        checks.append(
            ("SKU approved", row["is_approved"] == 1)
        )

        # Policy effective date
        policy_start = date.fromisoformat(
            row["policy_effective_from"]
        )

        policy_end = (
            date.fromisoformat(row["policy_effective_to"])
            if row["policy_effective_to"] else None
        )

        policy_valid = (
            policy_start <= PLANNED_ORDER_DATE
            and (
                policy_end is None
                or PLANNED_ORDER_DATE <= policy_end
            )
        )

        checks.append(("Policy effective", policy_valid))

        # Lead-time effective date
        lead_start = date.fromisoformat(
            row["lead_effective_from"]
        )

        lead_end = (
            date.fromisoformat(row["lead_effective_to"])
            if row["lead_effective_to"] else None
        )

        lead_valid = (
            lead_start <= PLANNED_ORDER_DATE
            and (
                lead_end is None
                or PLANNED_ORDER_DATE <= lead_end
            )
        )

        checks.append(("Lead time effective", lead_valid))

        # Unit and price consistency
        unit_valid = row["unit_of_measure"] in ("Kg", "Liter")

        checks.append(("Unit of measure", unit_valid))

        cost_valid = (
            abs(
                float(row["unit_cost"])
                - float(row["approved_unit_cost"])
            ) < 0.000001
        )

        checks.append(("Supplier price matches policy", cost_valid))

        # Proposed quantity meets MOQ
        shortage_quantity = float(row["shortage_quantity"])
        moq = float(row["minimum_order_quantity"])
        proposed_quantity = max(shortage_quantity, moq)

        moq_valid = proposed_quantity >= moq

        checks.append(("Minimum order quantity", moq_valid))

        # Synthetic capacity validation
        capacity_key = (supplier_id, sku_id)
        capacity_row = capacity_lookup.get(capacity_key)

        if capacity_row is None:
            capacity_quantity = None
            capacity_valid = False
        else:
            capacity_quantity = float(
                capacity_row["maximum_quantity"]
            )

            capacity_unit_valid = (
                capacity_row["unit_of_measure"]
                == row["unit_of_measure"]
            )

            capacity_valid = (
                capacity_unit_valid
                and proposed_quantity <= capacity_quantity
            )

        checks.append(
            ("Synthetic capacity", capacity_valid)
        )

        for check_name, passed in checks:
            print(
                f"{shortage_id} | {check_name}: "
                f"{'PASS' if passed else 'FAIL'}"
            )

            if not passed:
                errors.append(
                    f"{shortage_id}: {check_name} failed"
                )

        estimated_cost = proposed_quantity * float(row["unit_cost"])

        lead_days = int(row["lead_time_days"])

        expected_arrival = (
            PLANNED_ORDER_DATE + timedelta(days=lead_days)
        )

        # Real capacity is unavailable, so recommendations
        # remain conditional even when synthetic checks pass.
        feasibility_status = "CONDITIONAL"

        option = {
            "option_id": f"MIT-{shortage_id}-01",
            "shortage_id": shortage_id,
            "product": row["sku_name"],
            "sku_id": sku_id,
            "supplier_id": supplier_id,
            "supplier_name": row["supplier_name"],
            "unit": row["unit_of_measure"],
            "shortage_quantity": shortage_quantity,
            "minimum_order_quantity": moq,
            "proposed_quantity": proposed_quantity,
            "unit_cost": float(row["unit_cost"]),
            "estimated_cost": estimated_cost,
            "capacity_quantity": capacity_quantity,
            "capacity_source": "SYNTHETIC",
            "capacity_scenario_id": SCENARIO_ID,
            "lead_time_days": lead_days,
            "planned_order_date": PLANNED_ORDER_DATE.isoformat(),
            "expected_arrival_date": expected_arrival.isoformat(),
            "feasibility_status": feasibility_status,
            "policy_compliant": 1,
        }

        recommendations.append(option)

    if errors:
        raise ValueError(
            "Recommendation validation failed:\n"
            + "\n".join(errors)
        )

    # 4. Display recommendation details
    print("\n3. W47 PURCHASE RECOMMENDATIONS")
    print("-" * 90)

    total_cost = 0

    for option in recommendations:
        total_cost += option["estimated_cost"]

        print("\nOption ID:", option["option_id"])
        print("Product:", option["product"])
        print("Shortage:", option["shortage_quantity"], option["unit"])
        print("Supplier:", option["supplier_name"])
        print("Proposed quantity:", option["proposed_quantity"], option["unit"])
        print("MOQ:", option["minimum_order_quantity"])
        print("Unit cost:", option["unit_cost"])
        print("Estimated cost:", option["estimated_cost"])
        print("Synthetic capacity:", option["capacity_quantity"])
        print("Capacity source:", option["capacity_source"])
        print("Capacity scenario:", option["capacity_scenario_id"])
        print("Lead time:", option["lead_time_days"], "days")
        print("Planned order date:", option["planned_order_date"])
        print("Estimated arrival:", option["expected_arrival_date"])
        print("Policy compliant:", option["policy_compliant"])
        print("Feasibility:", option["feasibility_status"])

    # 5. Summary
    print("\n4. SUMMARY")
    print("-" * 90)

    print("Recommendations:", len(recommendations))
    print("Validation failures:", len(errors))
    print("Total estimated cost:", total_cost)
    print("Actual W47 supplier capacity: UNAVAILABLE")
    print("Synthetic capacity checks: 3 passed")
    print("Overall feasibility: CONDITIONAL")
    print("Supplier commitments created: NO")

    # 6. Confirm no database changes
    cursor.execute("PRAGMA foreign_key_check")
    fk_errors = cursor.fetchall()

    cursor.execute("PRAGMA integrity_check")
    integrity = cursor.fetchone()[0]

    print("\n5. DATABASE CHECKS")
    print("-" * 90)
    print("Foreign key check:", "PASS" if not fk_errors else "FAIL")
    print("Integrity check:", integrity)

    if fk_errors or integrity != "ok":
        raise RuntimeError("Database verification failed.")

    print("\n" + "=" * 90)
    print("W47 MITIGATION PREVIEW COMPLETED")
    print("READ-ONLY: NO DATABASE RECORDS INSERTED OR UPDATED")
    print("=" * 90)

finally:
    connection.close()
