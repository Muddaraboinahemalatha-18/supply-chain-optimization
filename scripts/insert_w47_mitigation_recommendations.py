
import sys
import csv
import sqlite3
from pathlib import Path
from datetime import date, timedelta

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

SCENARIO_ID = "SYN-W47-001"
EVENT_DATE = "2026-11-13"
ORDER_DATE = date(2026, 11, 13)

CAPACITY_FILE = (
    BASE_DIR / "data" / "scenarios" /
    "SYN-W47-001_supplier_capacity.csv"
)

connection = get_connection()
cursor = connection.cursor()

print("=" * 85)
print("INSERT W47 MITIGATION RECOMMENDATIONS")
print("=" * 85)

try:
    # 1. Check that the recommendations have not already been inserted
    cursor.execute("""
        SELECT COUNT(*)
        FROM mitigation_option
        WHERE shortage_id IN (
            SELECT shortage_id
            FROM shortage
            WHERE shortage_week = '2026-W47'
        )
    """)

    existing_options = cursor.fetchone()[0]

    if existing_options:
        raise RuntimeError(
            f"{existing_options} W47 mitigation options already exist. "
            "No duplicate insertion allowed."
        )

    # 2. Load synthetic capacity scenario
    if not CAPACITY_FILE.exists():
        raise FileNotFoundError("Synthetic capacity CSV not found.")

    with open(CAPACITY_FILE, "r", encoding="utf-8-sig") as file:
        capacity_rows = list(csv.DictReader(file))

    capacity_lookup = {}

    for row in capacity_rows:
        key = (row["supplier_id"], row["sku_id"])

        if key in capacity_lookup:
            raise ValueError(f"Duplicate capacity entry: {key}")

        if (
            row["scenario_id"] != SCENARIO_ID
            or row["capacity_week"] != "2026-W47"
            or row["source_type"] != "SYNTHETIC"
        ):
            raise ValueError("Invalid synthetic capacity scenario.")

        quantity = float(row["maximum_quantity"])

        if quantity < 0:
            raise ValueError("Negative capacity is not allowed.")

        capacity_lookup[key] = row

    # 3. Confirm actual W47 capacity is still unavailable
    cursor.execute("""
        SELECT COUNT(*)
        FROM supplier_capacity
        WHERE capacity_week = '2026-W47'
    """)

    actual_capacity_count = cursor.fetchone()[0]

    if actual_capacity_count != 0:
        raise RuntimeError(
            "Actual W47 capacity records now exist. "
            "Review the scenario before proceeding."
        )

    # 4. Load W47 shortage and supplier policy data
    cursor.execute("""
        SELECT
            sh.shortage_id,
            sh.sku_id,
            sh.location_id,
            sh.shortage_quantity,
            sh.status,

            sk.sku_name,
            sk.unit_of_measure,

            p.supplier_id,
            p.minimum_order_quantity,
            p.unit_cost,
            p.effective_from AS policy_start,
            p.effective_to AS policy_end,

            su.supplier_name,
            su.is_active,

            ss.is_approved,
            ss.unit_cost AS approved_unit_cost,

            lt.lead_time_days,
            lt.effective_from AS lead_start,
            lt.effective_to AS lead_end

        FROM shortage sh

        JOIN sku sk
            ON sk.sku_id = sh.sku_id

        JOIN supplier_sku_policy p
            ON p.sku_id = sh.sku_id

        JOIN supplier su
            ON su.supplier_id = p.supplier_id

        JOIN supplier_sku ss
            ON ss.supplier_id = p.supplier_id
           AND ss.sku_id = p.sku_id

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
        raise RuntimeError(
            f"Expected exactly 3 W47 options; found {len(source_rows)}."
        )

    # 5. Build and validate recommendations
    recommendations = []

    for row in source_rows:
        if row["is_active"] != 1:
            raise ValueError("Inactive supplier found.")

        if row["is_approved"] != 1:
            raise ValueError("Supplier SKU is not approved.")

        policy_start = date.fromisoformat(row["policy_start"])
        policy_end = (
            date.fromisoformat(row["policy_end"])
            if row["policy_end"] else None
        )

        if not (
            policy_start <= ORDER_DATE
            and (policy_end is None or ORDER_DATE <= policy_end)
        ):
            raise ValueError("Supplier policy is not effective.")

        lead_start = date.fromisoformat(row["lead_start"])
        lead_end = (
            date.fromisoformat(row["lead_end"])
            if row["lead_end"] else None
        )

        if not (
            lead_start <= ORDER_DATE
            and (lead_end is None or ORDER_DATE <= lead_end)
        ):
            raise ValueError("Lead-time record is not effective.")

        if row["unit_of_measure"] not in ("Kg", "Liter"):
            raise ValueError("Unexpected unit of measure.")

        if abs(
            float(row["unit_cost"]) -
            float(row["approved_unit_cost"])
        ) > 0.000001:
            raise ValueError("Supplier price does not match approval.")

        shortage_quantity = float(row["shortage_quantity"])
        moq = float(row["minimum_order_quantity"])
        unit_cost = float(row["unit_cost"])

        if shortage_quantity <= 0 or moq < 0 or unit_cost < 0:
            raise ValueError("Invalid shortage, MOQ or unit cost.")

        proposed_quantity = max(shortage_quantity, moq)

        key = (row["supplier_id"], row["sku_id"])
        capacity_row = capacity_lookup.get(key)

        if capacity_row is None:
            raise ValueError(
                f"Missing synthetic capacity for {key}."
            )

        capacity_quantity = float(
            capacity_row["maximum_quantity"]
        )

        if capacity_row["unit_of_measure"] != row["unit_of_measure"]:
            raise ValueError("Synthetic capacity unit mismatch.")

        if proposed_quantity > capacity_quantity:
            raise ValueError("Synthetic capacity exceeded.")

        lead_days = int(row["lead_time_days"])

        if lead_days < 0:
            raise ValueError("Invalid lead time.")

        estimated_cost = proposed_quantity * unit_cost
        arrival_date = ORDER_DATE + timedelta(days=lead_days)

        option_id = f"MIT-{row['shortage_id']}-01"
        event_id = f"ME-{row['shortage_id']}-CREATE-01"

        description = (
            f"W47 purchase recommendation for {row['sku_name']}. "
            f"Supplier: {row['supplier_name']}. "
            f"Capacity is synthetic under {SCENARIO_ID}; "
            "not an actual supplier commitment."
        )

        recommendations.append({
            "option_id": option_id,
            "event_id": event_id,
            "shortage_id": row["shortage_id"],
            "supplier_id": row["supplier_id"],
            "description": description,
            "unit": row["unit_of_measure"],
            "quantity": proposed_quantity,
            "moq": moq,
            "unit_cost": unit_cost,
            "cost": estimated_cost,
            "capacity": capacity_quantity,
            "lead_days": lead_days,
            "arrival": arrival_date.isoformat(),
        })

    # 6. Check deterministic IDs are unused
    for option in recommendations:
        cursor.execute("""
            SELECT COUNT(*)
            FROM mitigation_option
            WHERE option_id = ?
        """, (option["option_id"],))

        if cursor.fetchone()[0] != 0:
            raise RuntimeError(
                f"Option ID already exists: {option['option_id']}"
            )

        cursor.execute("""
            SELECT COUNT(*)
            FROM mitigation_event
            WHERE mitigation_event_id = ?
        """, (option["event_id"],))

        if cursor.fetchone()[0] != 0:
            raise RuntimeError(
                f"Event ID already exists: {option['event_id']}"
            )

    # 7. Insert options and creation events in one transaction
    cursor.execute("BEGIN IMMEDIATE")

    for option in recommendations:
        cursor.execute("""
            INSERT INTO mitigation_option (
                option_id,
                shortage_id,
                option_type,
                description,
                proposed_quantity,
                estimated_cost,
                policy_compliant,
                supplier_id,
                unit_of_measure,
                minimum_order_quantity,
                unit_cost,
                capacity_quantity,
                capacity_source,
                capacity_scenario_id,
                lead_time_days,
                planned_order_date,
                expected_arrival_date,
                feasibility_status
            )
            VALUES (?, ?, 'PURCHASE', ?, ?, ?, 1, ?, ?, ?, ?, ?,
                    'SYNTHETIC', ?, ?, ?, ?, 'CONDITIONAL')
        """, (
            option["option_id"],
            option["shortage_id"],
            option["description"],
            option["quantity"],
            option["cost"],
            option["supplier_id"],
            option["unit"],
            option["moq"],
            option["unit_cost"],
            option["capacity"],
            SCENARIO_ID,
            option["lead_days"],
            ORDER_DATE.isoformat(),
            option["arrival"],
        ))

        cursor.execute("""
            INSERT INTO mitigation_event (
                mitigation_event_id,
                option_id,
                event_type,
                event_date,
                decision_reason
            )
            VALUES (?, ?, 'OPTION_CREATED', ?, ?)
        """, (
            option["event_id"],
            option["option_id"],
            EVENT_DATE,
            (
                "W47 purchase recommendation created after supplier "
                "approval, MOQ, unit, price and lead-time checks. "
                f"Capacity validation uses synthetic scenario {SCENARIO_ID}. "
                "Actual W47 capacity is unavailable. "
                "This is not a purchase order or supplier commitment."
            ),
        ))

    # 8. Verify inserted counts before commit
    cursor.execute("""
        SELECT COUNT(*)
        FROM mitigation_option
        WHERE shortage_id IN (
            SELECT shortage_id
            FROM shortage
            WHERE shortage_week = '2026-W47'
        )
    """)

    option_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM mitigation_event
        WHERE event_type = 'OPTION_CREATED'
          AND event_date = ?
    """, (EVENT_DATE,))

    event_count = cursor.fetchone()[0]

    if option_count != 3 or event_count != 3:
        raise RuntimeError(
            f"Unexpected inserted counts: options={option_count}, "
            f"events={event_count}"
        )

    # 9. Check foreign keys and integrity before commit
    cursor.execute("PRAGMA foreign_key_check")

    if cursor.fetchall():
        raise RuntimeError("Foreign-key violations detected.")

    cursor.execute("PRAGMA integrity_check")

    if cursor.fetchone()[0] != "ok":
        raise RuntimeError("Database integrity check failed.")

    connection.commit()

    # 10. Display result
    print("\nW47 MITIGATION OPTIONS INSERTED")
    print("-" * 85)

    total_cost = 0

    for option in recommendations:
        total_cost += option["cost"]

        print("Option:", option["option_id"])
        print("Shortage:", option["shortage_id"])
        print("Supplier:", option["supplier_id"])
        print("Quantity:", option["quantity"], option["unit"])
        print("Estimated cost:", option["cost"])
        print("Capacity source: SYNTHETIC")
        print("Feasibility: CONDITIONAL")
        print("Event:", option["event_id"])
        print("-" * 85)

    print("Total recommendations:", option_count)
    print("Creation events:", event_count)
    print("Total estimated cost:", total_cost)
    print("Actual W47 capacity: UNAVAILABLE")
    print("Supplier commitments created: NO")

    print("\nPASS: Foreign-key check.")
    print("PASS: Database integrity check.")

    print("\n" + "=" * 85)
    print("W47 MITIGATION RECOMMENDATIONS INSERTED SUCCESSFULLY")
    print("=" * 85)

except Exception as error:
    connection.rollback()
    print("\nINSERTION FAILED - TRANSACTION ROLLED BACK")
    print("Error:", error)
    raise

finally:
    connection.close()
