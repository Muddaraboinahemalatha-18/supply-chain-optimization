
import sys
from pathlib import Path
from datetime import date, timedelta

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection

# Planning configuration
ORDER_DATE = date(2026, 11, 13)
FORECAST_WEEK = "2026-W47"

connection = get_connection()
cursor = connection.cursor()

print("=" * 95)
print("W47 CONDITIONAL PURCHASE OPTION PREVIEW")
print("=" * 95)

print("\nPLANNING ASSUMPTIONS")
print("1. Forecast week:", FORECAST_WEEK)
print("2. Proposed order date:", ORDER_DATE)
print("3. Inventory snapshot date: 2026-11-12")
print("4. Already received inbound quantities are included in inventory.")
print("5. No additional inbound supply is assumed.")
print("6. Supplier capacity must be verified before approving an order.")
print("7. Lead-time values are illustrative assumptions, not confirmed commitments.")

# Retrieve W47 forecast and supplier information
cursor.execute("""
    SELECT
        f.forecast_id,
        f.sku_id,
        s.sku_name,
        f.location_id,
        f.forecast_quantity,
        s.unit_of_measure,

        i.inventory_date,
        i.on_hand_quantity - i.reserved_quantity
            AS available_quantity,

        sp.supplier_id,
        sp.supplier_name,
        sp.is_active,

        ss.is_approved,

        p.minimum_order_quantity,
        p.unit_cost,
        p.effective_from,
        p.effective_to,

        lt.lead_time_id,
        lt.lead_time_days,
        lt.effective_from AS lead_effective_from,
        lt.effective_to AS lead_effective_to,

        sc.capacity_id,
        sc.maximum_quantity AS w47_capacity

    FROM forecast_demand f

    JOIN sku s
        ON f.sku_id = s.sku_id

    JOIN inventory i
        ON i.sku_id = f.sku_id
       AND i.location_id = f.location_id

    LEFT JOIN supplier_sku ss
        ON ss.sku_id = f.sku_id

    LEFT JOIN supplier sp
        ON sp.supplier_id = ss.supplier_id

    LEFT JOIN supplier_sku_policy p
        ON p.supplier_id = ss.supplier_id
       AND p.sku_id = ss.sku_id

    LEFT JOIN lead_time lt
        ON lt.supplier_id = ss.supplier_id
       AND lt.location_id = f.location_id

    LEFT JOIN supplier_capacity sc
        ON sc.supplier_id = ss.supplier_id
       AND sc.sku_id = f.sku_id
       AND sc.capacity_week = f.forecast_week

    WHERE f.forecast_week = ?

    ORDER BY f.forecast_id, sp.supplier_id
""", (FORECAST_WEEK,))

records = cursor.fetchall()

print("\n" + "=" * 95)
print("PURCHASE OPTION DETAILS")
print("=" * 95)

total_options = 0
capacity_missing = 0
policy_missing = 0
lead_time_missing = 0
approved_options = 0
estimated_total_cost = 0.0

for row in records:

    available = row["available_quantity"]
    demand = row["forecast_quantity"]

    projected_balance = available - demand
    shortage = max(0, -projected_balance)

    # No purchase is needed for sufficient inventory.
    if shortage <= 0:
        continue

    total_options += 1

    print("\n" + "-" * 95)
    print("PRODUCT:", row["sku_name"])
    print("Forecast ID:", row["forecast_id"])
    print("SKU:", row["sku_id"])
    print("Location:", row["location_id"])
    print("Inventory snapshot:", row["inventory_date"])
    print("Available inventory:", available, row["unit_of_measure"])
    print("Forecast demand:", demand, row["unit_of_measure"])
    print("Projected balance:", projected_balance, row["unit_of_measure"])
    print("Shortage:", shortage, row["unit_of_measure"])

    print("\nSUPPLIER DETAILS")
    print("Supplier:", row["supplier_name"])
    print("Supplier ID:", row["supplier_id"])

    supplier_active = row["is_active"] == 1
    sku_approved = row["is_approved"] == 1

    print("Supplier active:", supplier_active)
    print("SKU approved:", sku_approved)

    # Validate supplier policy
    policy_available = row["minimum_order_quantity"] is not None

    if policy_available:
        moq = row["minimum_order_quantity"]
        unit_cost = row["unit_cost"]

        policy_date_valid = (
            row["effective_from"] <= ORDER_DATE.isoformat()
            and (
                row["effective_to"] is None
                or row["effective_to"] >= ORDER_DATE.isoformat()
            )
        )

        order_quantity = max(shortage, moq)
        estimated_cost = order_quantity * unit_cost

        print("Minimum order quantity:", moq, row["unit_of_measure"])
        print("Unit cost: Rs.", unit_cost)
        print("Conditional order quantity:", order_quantity, row["unit_of_measure"])
        print("Estimated purchase cost: Rs.", estimated_cost)
        print("Policy effective on order date:", policy_date_valid)

        if not policy_date_valid:
            policy_missing += 1

    else:
        moq = None
        unit_cost = None
        order_quantity = None
        estimated_cost = None
        policy_date_valid = False

        policy_missing += 1
        print("Supplier policy: MISSING")

    # Validate supplier lead-time information
    lead_time_available = row["lead_time_days"] is not None

    if lead_time_available:
        lead_days = row["lead_time_days"]

        lead_policy_valid = (
            row["lead_effective_from"] is None
            or row["lead_effective_from"] <= ORDER_DATE.isoformat()
        ) and (
            row["lead_effective_to"] is None
            or row["lead_effective_to"] >= ORDER_DATE.isoformat()
        )

        estimated_arrival = ORDER_DATE + timedelta(days=lead_days)

        print("Lead time:", lead_days, "days")
        print("Illustrative estimated arrival:", estimated_arrival)
        print("Lead-time record effective:", lead_policy_valid)
        print("Lead-time reliability: NOT CONFIRMED")

        if not lead_policy_valid:
            lead_time_missing += 1

    else:
        lead_policy_valid = False
        estimated_arrival = None
        lead_time_missing += 1

        print("Lead time: MISSING")

    # Validate W47 supplier capacity
    capacity_available = row["w47_capacity"] is not None

    if capacity_available:
        capacity = row["w47_capacity"]

        print("W47 supplier capacity:", capacity, row["unit_of_measure"])

        if order_quantity is not None:
            capacity_sufficient = order_quantity <= capacity
        else:
            capacity_sufficient = False

    else:
        capacity = None
        capacity_sufficient = False
        capacity_missing += 1

        print("W47 supplier capacity: MISSING")

    # Overall conditional checks
    basic_checks_pass = (
        supplier_active
        and sku_approved
        and policy_available
        and policy_date_valid
        and lead_time_available
        and lead_policy_valid
        and order_quantity is not None
    )

    if basic_checks_pass:
        approved_options += 1

    if estimated_cost is not None:
        estimated_total_cost += estimated_cost

    print("\nMITIGATION ASSESSMENT")

    print("Supplier active:", "PASS" if supplier_active else "FAIL")
    print("SKU approved:", "PASS" if sku_approved else "FAIL")
    print("Supplier policy:", "PASS" if policy_available and policy_date_valid else "FAIL")
    print("Lead-time record:", "PASS" if lead_time_available and lead_policy_valid else "FAIL")
    print("W47 capacity:", "PASS" if capacity_available and capacity_sufficient else "NOT VERIFIED")

    if basic_checks_pass and capacity_available and capacity_sufficient:
        print("Conditional assessment: ALL DATA CHECKS PASS")
    else:
        print("Conditional assessment: NOT READY FOR APPROVAL")

    print("Estimated arrival is not a confirmed delivery date.")

# Summary
print("\n" + "=" * 95)
print("W47 PURCHASE OPTION SUMMARY")
print("=" * 95)

print("Purchase options inspected:", total_options)
print("Options passing basic supplier and policy checks:", approved_options)
print("Missing W47 capacity records:", capacity_missing)
print("Missing or invalid supplier policies:", policy_missing)
print("Missing or invalid lead-time records:", lead_time_missing)

print("Conditional estimated purchase cost: Rs.", round(estimated_total_cost, 2))

print("\nIMPORTANT LIMITATIONS")
print("1. No W47 supplier capacity records currently exist.")
print("2. Lead-time values are illustrative, not confirmed commitments.")
print("3. Delivery feasibility has not been established.")
print("4. Cost estimates are conditional on the listed MOQ and unit prices.")
print("5. No purchase orders or mitigation records were created.")
print("6. Historical W46 purchase orders and receipts were not modified.")

print("\nNo database records were modified.")
print("=" * 95)

connection.close()
