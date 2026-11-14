
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

connection = get_connection()
cursor = connection.cursor()

print("=" * 90)
print("W47 MITIGATION RECOMMENDATION VERIFICATION")
print("=" * 90)

try:
    # 1. Verify W47 mitigation options and their events
    print("\n1. W47 MITIGATION OPTIONS")
    print("-" * 90)

    cursor.execute("""
        SELECT
            mo.option_id,
            mo.shortage_id,
            s.shortage_week,
            s.status AS shortage_status,
            mo.supplier_id,
            su.supplier_name,
            mo.proposed_quantity,
            mo.unit_of_measure,
            mo.minimum_order_quantity,
            mo.unit_cost,
            mo.estimated_cost,
            mo.policy_compliant,
            mo.capacity_quantity,
            mo.capacity_source,
            mo.capacity_scenario_id,
            mo.lead_time_days,
            mo.planned_order_date,
            mo.expected_arrival_date,
            mo.feasibility_status,
            me.mitigation_event_id,
            me.event_type,
            me.event_date
        FROM mitigation_option mo
        JOIN shortage s
            ON s.shortage_id = mo.shortage_id
        JOIN supplier su
            ON su.supplier_id = mo.supplier_id
        LEFT JOIN mitigation_event me
            ON me.option_id = mo.option_id
        WHERE s.shortage_week = '2026-W47'
        ORDER BY mo.option_id
    """)

    options = cursor.fetchall()

    for option in options:
        print(dict(option))

    assert len(options) == 3, (
        f"Expected 3 W47 options, found {len(options)}"
    )

    print("\nPASS: Exactly 3 W47 mitigation options found.")

    # 2. Verify quantities and cost calculations
    print("\n2. QUANTITY AND COST RECONCILIATION")
    print("-" * 90)

    expected = {
        "MIT-SHORT-2026-000001-01": {
            "supplier_id": "SUP001",
            "quantity": 50,
            "unit": "Kg",
            "moq": 50,
            "unit_cost": 48,
            "cost": 2400,
            "capacity": 100,
            "lead_days": 2,
            "arrival": "2026-11-15",
        },
        "MIT-SHORT-2026-000002-01": {
            "supplier_id": "SUP002",
            "quantity": 25,
            "unit": "Kg",
            "moq": 25,
            "unit_cost": 43,
            "cost": 1075,
            "capacity": 100,
            "lead_days": 3,
            "arrival": "2026-11-16",
        },
        "MIT-SHORT-2026-000003-01": {
            "supplier_id": "SUP003",
            "quantity": 10,
            "unit": "Liter",
            "moq": 10,
            "unit_cost": 58,
            "cost": 580,
            "capacity": 50,
            "lead_days": 3,
            "arrival": "2026-11-16",
        },
    }

    total_cost = 0

    for option in options:
        option_id = option["option_id"]
        assert option_id in expected, f"Unexpected option: {option_id}"

        target = expected[option_id]

        assert option["supplier_id"] == target["supplier_id"]
        assert option["proposed_quantity"] == target["quantity"]
        assert option["unit_of_measure"] == target["unit"]
        assert option["minimum_order_quantity"] == target["moq"]
        assert option["unit_cost"] == target["unit_cost"]
        assert option["estimated_cost"] == target["cost"]
        assert option["capacity_quantity"] == target["capacity"]
        assert option["lead_time_days"] == target["lead_days"]
        assert option["expected_arrival_date"] == target["arrival"]

        calculated_cost = (
            option["proposed_quantity"] * option["unit_cost"]
        )

        assert abs(calculated_cost - option["estimated_cost"]) < 0.000001

        assert option["proposed_quantity"] >= (
            option["minimum_order_quantity"]
        )

        total_cost += option["estimated_cost"]

        print(
            f"PASS: {option_id} | "
            f"Quantity={option['proposed_quantity']} | "
            f"Cost={calculated_cost}"
        )

    assert total_cost == 4055

    print("PASS: Total estimated cost = 4055.")

    # 3. Verify conditional feasibility and synthetic source
    print("\n3. CAPACITY AND FEASIBILITY")
    print("-" * 90)

    for option in options:
        assert option["capacity_source"] == "SYNTHETIC"
        assert option["capacity_scenario_id"] == "SYN-W47-001"
        assert option["feasibility_status"] == "CONDITIONAL"
        assert option["policy_compliant"] == 1

        print(
            f"PASS: {option['option_id']} | "
            "SYNTHETIC | CONDITIONAL"
        )

    cursor.execute("""
        SELECT COUNT(*)
        FROM supplier_capacity
        WHERE capacity_week = '2026-W47'
    """)

    actual_capacity_count = cursor.fetchone()[0]

    assert actual_capacity_count == 0

    print("PASS: No synthetic capacity was inserted as actual capacity.")

    # 4. Verify creation events
    print("\n4. MITIGATION CREATION EVENTS")
    print("-" * 90)

    cursor.execute("""
        SELECT
            me.mitigation_event_id,
            me.option_id,
            me.event_type,
            me.event_date,
            me.decision_reason
        FROM mitigation_event me
        JOIN mitigation_option mo
            ON mo.option_id = me.option_id
        JOIN shortage s
            ON s.shortage_id = mo.shortage_id
        WHERE s.shortage_week = '2026-W47'
        ORDER BY me.mitigation_event_id
    """)

    events = cursor.fetchall()

    for event in events:
        print(dict(event))
        assert event["event_type"] == "OPTION_CREATED"
        assert event["event_date"] == "2026-11-13"

    assert len(events) == 3

    print("PASS: Exactly 3 creation events found.")

    # 5. Verify W46 historical options
    print("\n5. W46 HISTORICAL MITIGATION PRESERVATION")
    print("-" * 90)

    cursor.execute("""
        SELECT
            mo.option_id,
            mo.shortage_id,
            mo.proposed_quantity,
            mo.estimated_cost,
            mo.policy_compliant,
            s.status
        FROM mitigation_option mo
        JOIN shortage s
            ON s.shortage_id = mo.shortage_id
        WHERE s.shortage_week = '2026-W46'
        ORDER BY mo.option_id
    """)

    historical = cursor.fetchall()

    for record in historical:
        print(dict(record))

    assert len(historical) == 3

    expected_historical_ids = {
        "OPT_SH_F001",
        "OPT_SH_F003",
        "OPT_SH_F005",
    }

    assert {row["option_id"] for row in historical} == (
        expected_historical_ids
    )

    assert all(row["status"] == "RESOLVED" for row in historical)

    print("PASS: All 3 W46 historical options preserved.")

    # 6. Verify W46 shortage events
    cursor.execute("""
        SELECT COUNT(*)
        FROM shortage_event
        WHERE event_type = 'SHORTAGE_RESOLVED'
    """)

    resolved_events = cursor.fetchone()[0]

    assert resolved_events == 3

    print("PASS: All 3 W46 shortage resolution events preserved.")

    # 7. Database integrity
    print("\n6. DATABASE INTEGRITY")
    print("-" * 90)

    cursor.execute("PRAGMA foreign_key_check")
    fk_errors = cursor.fetchall()

    assert not fk_errors, f"Foreign key errors: {fk_errors}"

    cursor.execute("PRAGMA integrity_check")
    integrity = cursor.fetchone()[0]

    assert integrity == "ok"

    print("PASS: Foreign key check.")
    print("PASS: Integrity check:", integrity)

    print("\n" + "=" * 90)
    print("W47 MITIGATION VERIFICATION PASSED")
    print("3 recommendations verified.")
    print("3 creation events verified.")
    print("W46 history preserved.")
    print("No actual W47 capacity invented.")
    print("=" * 90)

except Exception as error:
    print("\nVERIFICATION FAILED")
    print("Error:", error)
    raise

finally:
    connection.close()
