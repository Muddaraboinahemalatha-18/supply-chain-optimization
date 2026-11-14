
import sys
import csv
import random
import argparse
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from config.generator_config import get_config


def read_csv(file_path):

    if not file_path.exists():
        raise FileNotFoundError(
            f"Required input file not found: {file_path}"
        )

    with open(file_path, "r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(file_path, records):

    if not records:
        raise ValueError(f"No records available for {file_path}")

    with open(file_path, "w", newline="", encoding="utf-8") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(records[0].keys())
        )

        writer.writeheader()
        writer.writerows(records)


def generate_purchase_inbound(scale="starter"):

    config = get_config(scale)
    rng = random.Random(config["random_seed"] + 3)

    # Scale-specific directories
    scale_dir = BASE_DIR / "data" / "generated" / scale

    master_dir = scale_dir / "master_data"
    transaction_dir = scale_dir / "transactions"

    transaction_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------
    # 1. READ EXISTING GENERATED DATA
    # ------------------------------------------------

    skus = read_csv(master_dir / "sku.csv")
    suppliers = read_csv(master_dir / "supplier.csv")
    supplier_skus = read_csv(master_dir / "supplier_sku.csv")
    sku_locations = read_csv(master_dir / "sku_location.csv")
    locations = read_csv(master_dir / "location.csv")

    capacities = read_csv(
        transaction_dir / "supplier_capacity.csv"
    )

    lead_times = read_csv(
        transaction_dir / "lead_time.csv"
    )

    if not all([
        skus,
        suppliers,
        supplier_skus,
        sku_locations,
        locations,
        capacities,
        lead_times
    ]):
        raise ValueError("Required input CSV files must not be empty.")

    sku_lookup = {
        row["sku_id"]: row for row in skus
    }

    supplier_lookup = {
        row["supplier_id"]: row for row in suppliers
    }

    # ------------------------------------------------
    # 2. GENERATE SUPPLIER-SKU POLICY
    # ------------------------------------------------

    # Synthetic MOQ assumptions:
    # Kg products: 25 units
    # Liter products: 10 units

    policy_records = []
    policy_lookup = {}

    for index, relationship in enumerate(supplier_skus, start=1):

        sku_id = relationship["sku_id"]
        supplier_id = relationship["supplier_id"]

        if sku_id not in sku_lookup:
            raise ValueError(f"Unknown SKU: {sku_id}")

        if supplier_id not in supplier_lookup:
            raise ValueError(f"Unknown supplier: {supplier_id}")

        sku = sku_lookup[sku_id]

        if sku["unit_of_measure"] == "Kg":
            minimum_quantity = 25

        elif sku["unit_of_measure"] == "Liter":
            minimum_quantity = 10

        else:
            raise ValueError(
                f"Unsupported UOM for SKU {sku_id}"
            )

        policy = {
            "policy_id": f"POL-2026-{index:06d}",
            "supplier_id": supplier_id,
            "sku_id": sku_id,
            "minimum_order_quantity": minimum_quantity,
            "unit_cost": relationship["unit_cost"],
            "effective_from": config["inventory_snapshot_date"],
            "effective_to": ""
        }

        policy_records.append(policy)

        policy_lookup[(supplier_id, sku_id)] = policy

    # ------------------------------------------------
    # 3. PREPARE CAPACITY AND LEAD-TIME LOOKUPS
    # ------------------------------------------------

    capacity_lookup = {}

    for row in capacities:

        key = (
            row["supplier_id"],
            row["sku_id"],
            row["capacity_week"]
        )

        capacity_lookup[key] = int(row["maximum_quantity"])

    remaining_capacity = dict(capacity_lookup)

    lead_time_lookup = {}

    for row in lead_times:

        key = (
            row["supplier_id"],
            row["location_id"]
        )

        lead_time_lookup[key] = int(row["lead_time_days"])

    # ------------------------------------------------
    # 4. PREPARE VALID SKU-LOCATION ASSIGNMENTS
    # ------------------------------------------------

    locations_by_sku = {}

    for row in sku_locations:

        locations_by_sku.setdefault(
            row["sku_id"], []
        ).append(row["location_id"])

    # ------------------------------------------------
    # 5. PREPARE CANDIDATE PURCHASE ORDERS
    # ------------------------------------------------

    candidates = []

    for relationship in supplier_skus:

        supplier_id = relationship["supplier_id"]
        sku_id = relationship["sku_id"]

        if int(relationship["is_approved"]) != 1:
            continue

        if sku_id not in locations_by_sku:
            continue

        policy = policy_lookup[(supplier_id, sku_id)]

        minimum_quantity = int(
            policy["minimum_order_quantity"]
        )

        for location_id in locations_by_sku[sku_id]:

            lead_key = (supplier_id, location_id)

            if lead_key not in lead_time_lookup:
                continue

            for week_number in range(
                1, config["demand_weeks"] + 1
            ):

                planning_week = (
                    f"{config['planning_year']}-W{week_number:02d}"
                )

                capacity_key = (
                    supplier_id,
                    sku_id,
                    planning_week
                )

                available_capacity = remaining_capacity.get(
                    capacity_key, 0
                )

                if available_capacity < minimum_quantity:
                    continue

                candidates.append({
                    "supplier_id": supplier_id,
                    "sku_id": sku_id,
                    "location_id": location_id,
                    "planning_week": planning_week,
                    "week_number": week_number,
                    "capacity_key": capacity_key,
                    "minimum_quantity": minimum_quantity,
                    "lead_time_days": lead_time_lookup[lead_key],
                    "policy": policy
                })

    rng.shuffle(candidates)

    # ------------------------------------------------
    # 6. PREPARE PURCHASE ORDER AND INBOUND DATA
    # ------------------------------------------------

    target_count = config["inbound_order_count"]

    purchase_orders = []
    purchase_order_lines = []
    inbound_orders = []

    # Generate status distribution for the requested scale.
    # 10% PLANNED
    # 25% IN_TRANSIT
    # 10% PARTIALLY_RECEIVED
    # 40% RECEIVED
    # Remaining 15% DELAYED

    planned_count = round(target_count * 0.10)
    transit_count = round(target_count * 0.25)
    partial_count = round(target_count * 0.10)
    received_count = round(target_count * 0.40)

    delayed_count = (
        target_count
        - planned_count
        - transit_count
        - partial_count
        - received_count
    )

    status_distribution = (
        ["PLANNED"] * planned_count
        + ["IN_TRANSIT"] * transit_count
        + ["PARTIALLY_RECEIVED"] * partial_count
        + ["RECEIVED"] * received_count
        + ["DELAYED"] * delayed_count
    )

    rng.shuffle(status_distribution)

    snapshot_date = date.fromisoformat(
        config["inventory_snapshot_date"]
    )

    po_counter = 1
    line_counter = 1
    inbound_counter = 1

    # ------------------------------------------------
    # 7. GENERATE PURCHASE ORDERS, LINES AND INBOUND
    # ------------------------------------------------

    for candidate in candidates:

        if len(inbound_orders) >= target_count:
            break

        supplier_id = candidate["supplier_id"]
        sku_id = candidate["sku_id"]
        location_id = candidate["location_id"]

        capacity_key = candidate["capacity_key"]
        minimum_quantity = candidate["minimum_quantity"]

        remaining = remaining_capacity[capacity_key]

        maximum_lots = min(
            3,
            remaining // minimum_quantity
        )

        if maximum_lots < 1:
            continue

        lot_count = rng.randint(1, maximum_lots)

        order_quantity = minimum_quantity * lot_count

        if order_quantity > remaining:
            continue

        # Order date must belong to the allocated planning week.
        week_offset = (
            candidate["week_number"] - 1
        ) * 7

        order_date = snapshot_date + timedelta(
            days=week_offset + rng.randint(0, 3)
        )

        actual_order_week = (
            f"{order_date.isocalendar().year}-"
            f"W{order_date.isocalendar().week:02d}"
        )

        if actual_order_week != candidate["planning_week"]:
            raise ValueError(
                f"Order week mismatch: {actual_order_week} "
                f"!= {candidate['planning_week']}"
            )

        # Allocate capacity after validating the order week.
        remaining_capacity[capacity_key] -= order_quantity

        lead_days = candidate["lead_time_days"]

        expected_arrival = order_date + timedelta(
            days=lead_days
        )

        inbound_status = status_distribution[len(inbound_orders)]

        if inbound_status == "DELAYED":

            expected_arrival += timedelta(
                days=rng.randint(3, 10)
            )

        if inbound_status in (
            "PARTIALLY_RECEIVED",
            "RECEIVED"
        ):

            actual_arrival = expected_arrival + timedelta(
                days=rng.randint(0, 2)
            )

        else:
            actual_arrival = None

        if inbound_status == "PLANNED":

            po_status = "APPROVED"
            received_quantity = 0

        elif inbound_status in ("IN_TRANSIT", "DELAYED"):

            po_status = "SHIPPED"
            received_quantity = 0

        elif inbound_status == "PARTIALLY_RECEIVED":

            po_status = "PARTIALLY_RECEIVED"

            received_quantity = rng.randint(
                1, order_quantity - 1
            )

        else:

            po_status = "RECEIVED"
            received_quantity = order_quantity

        sku = sku_lookup[sku_id]

        po_id = f"PO-2026-{po_counter:06d}"
        po_line_id = f"PO-LINE-2026-{line_counter:06d}"
        inbound_id = f"INB-2026-{inbound_counter:06d}"

        purchase_orders.append({
            "po_id": po_id,
            "supplier_id": supplier_id,
            "order_date": order_date.isoformat(),
            "expected_date": expected_arrival.isoformat(),
            "status": po_status
        })

        purchase_order_lines.append({
            "po_line_id": po_line_id,
            "po_id": po_id,
            "sku_id": sku_id,
            "location_id": location_id,
            "order_quantity": order_quantity,
            "received_quantity": received_quantity,
            "unit_of_measure": sku["unit_of_measure"]
        })

        inbound_orders.append({
            "inbound_id": inbound_id,
            "po_line_id": po_line_id,
            "expected_arrival_date": expected_arrival.isoformat(),
            "actual_arrival_date": (
                actual_arrival.isoformat()
                if actual_arrival else ""
            ),
            "inbound_quantity": order_quantity,
            "received_quantity": received_quantity,
            "status": inbound_status
        })

        po_counter += 1
        line_counter += 1
        inbound_counter += 1

    # ------------------------------------------------
    # 8. CHECK TARGET RECORD COUNT
    # ------------------------------------------------

    if len(inbound_orders) != target_count:

        raise ValueError(
            f"Could generate only {len(inbound_orders)} "
            f"of {target_count} requested inbound orders. "
            "Review capacity and MOQ assumptions."
        )

    # ------------------------------------------------
    # 9. VALIDATION
    # ------------------------------------------------

    assert len(purchase_orders) == target_count
    assert len(purchase_order_lines) == target_count
    assert len(inbound_orders) == target_count

    assert len({
        row["po_id"] for row in purchase_orders
    }) == target_count

    assert len({
        row["po_line_id"] for row in purchase_order_lines
    }) == target_count

    assert len({
        row["inbound_id"] for row in inbound_orders
    }) == target_count

    valid_supplier_ids = {
        row["supplier_id"] for row in suppliers
    }

    valid_sku_ids = set(sku_lookup.keys())

    valid_location_ids = {
        row["location_id"] for row in locations
    }

    po_ids = {
        row["po_id"] for row in purchase_orders
    }

    po_line_ids = {
        row["po_line_id"] for row in purchase_order_lines
    }

    po_lookup = {
        row["po_id"]: row for row in purchase_orders
    }

    assert all(
        row["supplier_id"] in valid_supplier_ids
        for row in purchase_orders
    )

    assert all(
        row["po_id"] in po_ids
        and row["sku_id"] in valid_sku_ids
        and row["location_id"] in valid_location_ids
        for row in purchase_order_lines
    )

    assert all(
        row["po_line_id"] in po_line_ids
        for row in inbound_orders
    )

    assert all(
        int(row["received_quantity"]) <= int(row["order_quantity"])
        for row in purchase_order_lines
    )

    assert all(
        int(row["received_quantity"]) <= int(row["inbound_quantity"])
        for row in inbound_orders
    )

    # Validate minimum order quantities.
    assert all(
        int(line["order_quantity"]) >= int(
            policy_lookup[
                (
                    po_lookup[line["po_id"]]["supplier_id"],
                    line["sku_id"]
                )
            ]["minimum_order_quantity"]
        )
        for line in purchase_order_lines
    )

    # Validate supplier capacity by actual purchase order week.
    allocated_capacity = {}

    for line in purchase_order_lines:

        po = po_lookup[line["po_id"]]

        order_date = date.fromisoformat(po["order_date"])

        order_week = (
            f"{order_date.isocalendar().year}-"
            f"W{order_date.isocalendar().week:02d}"
        )

        key = (
            po["supplier_id"],
            line["sku_id"],
            order_week
        )

        allocated_capacity[key] = (
            allocated_capacity.get(key, 0)
            + int(line["order_quantity"])
        )

    assert all(
        quantity <= capacity_lookup.get(key, 0)
        for key, quantity in allocated_capacity.items()
    )

    assert all(
        row["status"] in (
            "PLANNED",
            "IN_TRANSIT",
            "PARTIALLY_RECEIVED",
            "RECEIVED",
            "DELAYED",
            "CANCELLED"
        )
        for row in inbound_orders
    )

    # Reconcile inbound quantities with purchase-order lines.
    line_lookup = {
        row["po_line_id"]: row
        for row in purchase_order_lines
    }

    assert all(
        int(line_lookup[row["po_line_id"]]["received_quantity"])
        == int(row["received_quantity"])
        for row in inbound_orders
    )

    assert all(
        (
            row["actual_arrival_date"] != ""
            if int(row["received_quantity"]) > 0
            else row["actual_arrival_date"] == ""
        )
        for row in inbound_orders
    )

    # Validate the generated status distribution.
    actual_status_counts = {
        status: sum(
            1 for row in inbound_orders
            if row["status"] == status
        )
        for status in (
            "PLANNED",
            "IN_TRANSIT",
            "PARTIALLY_RECEIVED",
            "RECEIVED",
            "DELAYED"
        )
    }

    expected_status_counts = {
        "PLANNED": planned_count,
        "IN_TRANSIT": transit_count,
        "PARTIALLY_RECEIVED": partial_count,
        "RECEIVED": received_count,
        "DELAYED": delayed_count
    }

    assert actual_status_counts == expected_status_counts

    # ------------------------------------------------
    # 10. EXPORT CSV FILES
    # ------------------------------------------------

    write_csv(
        master_dir / "supplier_sku_policy.csv",
        policy_records
    )

    write_csv(
        transaction_dir / "purchase_order.csv",
        purchase_orders
    )

    write_csv(
        transaction_dir / "purchase_order_line.csv",
        purchase_order_lines
    )

    write_csv(
        transaction_dir / "inbound_order.csv",
        inbound_orders
    )

    # ------------------------------------------------
    # 11. DISPLAY RESULTS
    # ------------------------------------------------

    print("=" * 60)
    print("PURCHASE ORDER AND INBOUND GENERATION COMPLETED")
    print("=" * 60)

    print(f"Scale: {scale}")
    print(f"Random seed: {config['random_seed'] + 3}")

    print("\nGENERATED RECORD COUNTS")
    print("-" * 60)
    print(f"supplier_sku_policy.csv: {len(policy_records)}")
    print(f"purchase_order.csv: {len(purchase_orders)}")
    print(f"purchase_order_line.csv: {len(purchase_order_lines)}")
    print(f"inbound_order.csv: {len(inbound_orders)}")

    print("\nINBOUND STATUS DISTRIBUTION")
    print("-" * 60)

    for status, count in actual_status_counts.items():
        print(f"{status}: {count}")

    print("\nVALIDATION")
    print("Primary key uniqueness: PASSED")
    print("Supplier, SKU and location references: PASSED")
    print("Purchase order line references: PASSED")
    print("MOQ compliance: PASSED")
    print("Supplier capacity limits by order week: PASSED")
    print("Received quantity reconciliation: PASSED")
    print("Inbound lifecycle status checks: PASSED")
    print("Arrival date checks: PASSED")
    print("Inbound status distribution: PASSED")

    print("\nMASTER DATA OUTPUT DIRECTORY")
    print(master_dir)

    print("\nTRANSACTION OUTPUT DIRECTORY")
    print(transaction_dir)

    print("\nDatabase changes: NONE")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Generate purchase orders and inbound records."
    )

    parser.add_argument(
        "--scale",
        choices=["starter", "full"],
        default="starter"
    )

    args = parser.parse_args()

    generate_purchase_inbound(args.scale)
