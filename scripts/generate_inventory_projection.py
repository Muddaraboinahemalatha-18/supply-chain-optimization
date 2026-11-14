
import argparse
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from config.generator_config import get_config


SNAPSHOT_DATE = "2026-01-01"

ASSUMPTIONS = (
    "Opening available = on_hand - reserved; "
    "inbound is counted by arrival week; "
    "partial receipts are split into received and outstanding quantities; "
    "partial outstanding ETA is max(expected date, actual date); "
    "production consumes components after reserving current-week forecast demand; "
    "production is limited by plan, capacity and component availability; "
    "unfulfilled demand is recorded as shortage and is not carried as backorder."
)


def read_csv(file_path):
    if not file_path.exists():
        raise FileNotFoundError(f"Required input file not found: {file_path}")

    with open(file_path, "r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(file_path, records, fieldnames):
    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def week_key(date_value):
    iso = date_value.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def week_start(week_value):
    year_text, week_text = week_value.split("-W")
    return date.fromisocalendar(int(year_text), int(week_text), 1)


def add_inbound(schedule, key, received, outstanding, inbound_id):
    if key not in schedule:
        schedule[key] = {
            "received": 0.0,
            "outstanding": 0.0,
            "inbound_ids": []
        }

    schedule[key]["received"] += received
    schedule[key]["outstanding"] += outstanding
    schedule[key]["inbound_ids"].append(inbound_id)


def generate_inventory_projection(scale="starter"):

    config = get_config(scale)

    # Use the selected scale-specific folders.
    scale_dir = BASE_DIR / "data" / "generated" / scale
    master_dir = scale_dir / "master_data"
    transaction_dir = scale_dir / "transactions"

    print("=" * 70)
    print("STARTING WEEKLY INVENTORY PROJECTION")
    print("=" * 70)
    print(f"Scale: {scale}")
    print(f"Input directory: {scale_dir}")

    # --------------------------------------------------
    # 1. Read source CSV files
    # --------------------------------------------------

    skus = read_csv(master_dir / "sku.csv")
    sku_locations = read_csv(master_dir / "sku_location.csv")
    bom = read_csv(master_dir / "bom.csv")

    forecasts = read_csv(transaction_dir / "forecast_demand.csv")
    inventories = read_csv(transaction_dir / "inventory.csv")

    inbound_orders = read_csv(transaction_dir / "inbound_order.csv")
    po_lines = read_csv(transaction_dir / "purchase_order_line.csv")
    purchase_orders = read_csv(transaction_dir / "purchase_order.csv")

    production_plans = read_csv(transaction_dir / "production_plan.csv")
    production_capacities = read_csv(
        transaction_dir / "production_capacity.csv"
    )

    required_inputs = [
        skus,
        sku_locations,
        bom,
        forecasts,
        inventories,
        inbound_orders,
        po_lines,
        purchase_orders,
        production_plans,
        production_capacities
    ]

    if any(not records for records in required_inputs):
        raise ValueError("One or more required input CSV files are empty.")

    # --------------------------------------------------
    # 2. Validate SKU master data
    # --------------------------------------------------

    sku_lookup = {row["sku_id"]: row for row in skus}

    if len(sku_lookup) != len(skus):
        raise ValueError("Duplicate SKU IDs found.")

    valid_skus = set(sku_lookup)

    # --------------------------------------------------
    # 3. Validate SKU-location relationships
    # --------------------------------------------------

    valid_locations = set()
    locations_by_sku = defaultdict(set)

    for row in sku_locations:
        key = (row["sku_id"], row["location_id"])

        if row["sku_id"] not in valid_skus:
            raise ValueError(f"Unknown SKU-location reference: {key}")

        if key in valid_locations:
            raise ValueError(f"Duplicate SKU-location relationship: {key}")

        valid_locations.add(key)
        locations_by_sku[row["sku_id"]].add(row["location_id"])

    # --------------------------------------------------
    # 4. Validate and prepare opening inventory
    # --------------------------------------------------

    opening_inventory = {}

    for row in inventories:
        key = (row["sku_id"], row["location_id"])

        if key not in valid_locations:
            raise ValueError(f"Invalid inventory SKU-location: {key}")

        if key in opening_inventory:
            raise ValueError(f"Duplicate inventory record: {key}")

        if row["unit_of_measure"] != sku_lookup[key[0]]["unit_of_measure"]:
            raise ValueError(f"Inventory UOM mismatch: {key}")

        on_hand = float(row["on_hand_quantity"])
        reserved = float(row["reserved_quantity"])

        if on_hand < 0 or reserved < 0 or reserved > on_hand:
            raise ValueError(f"Invalid inventory quantities: {key}")

        if row["inventory_date"] != SNAPSHOT_DATE:
            raise ValueError(
                f"Unexpected inventory snapshot date: {row['inventory_date']}"
            )

        opening_inventory[key] = on_hand - reserved

    # --------------------------------------------------
    # 5. Validate and group weekly forecasts
    # --------------------------------------------------

    forecast_lookup = {}
    forecast_ids = {}
    forecasts_by_week = defaultdict(dict)

    for row in forecasts:
        sku_id = row["sku_id"]
        location_id = row["location_id"]
        forecast_week = row["forecast_week"]

        key = (sku_id, location_id, forecast_week)
        sku_location = (sku_id, location_id)

        if sku_location not in valid_locations:
            raise ValueError(f"Invalid forecast SKU-location: {key}")

        if key in forecast_lookup:
            raise ValueError(f"Duplicate forecast: {key}")

        quantity = float(row["forecast_quantity"])

        if quantity < 0:
            raise ValueError(f"Negative forecast quantity: {key}")

        # Validate the ISO week format.
        week_start(forecast_week)

        forecast_lookup[key] = quantity
        forecast_ids[key] = row["forecast_id"]
        forecasts_by_week[forecast_week][sku_location] = quantity

    forecast_combinations = {
        (sku_id, location_id)
        for sku_id, location_id, _ in forecast_lookup
    }

    if set(opening_inventory) != forecast_combinations:
        raise ValueError(
            "Inventory and forecast SKU-location combinations do not match."
        )

    weeks = sorted(forecasts_by_week)

    # --------------------------------------------------
    # 6. Prepare purchase order relationships
    # --------------------------------------------------

    po_line_lookup = {
        row["po_line_id"]: row
        for row in po_lines
    }

    po_lookup = {
        row["po_id"]: row
        for row in purchase_orders
    }

    if len(po_line_lookup) != len(po_lines):
        raise ValueError("Duplicate purchase order line IDs.")

    if len(po_lookup) != len(purchase_orders):
        raise ValueError("Duplicate purchase order IDs.")

    # --------------------------------------------------
    # 7. Schedule inbound quantities by arrival week
    # --------------------------------------------------

    inbound_schedule = defaultdict(
        lambda: {
            "received": 0.0,
            "outstanding": 0.0,
            "inbound_ids": []
        }
    )

    inbound_ids = set()

    expected_po_status = {
        "PLANNED": "APPROVED",
        "IN_TRANSIT": "SHIPPED",
        "DELAYED": "SHIPPED",
        "PARTIALLY_RECEIVED": "PARTIALLY_RECEIVED",
        "RECEIVED": "RECEIVED"
    }

    snapshot = date.fromisoformat(SNAPSHOT_DATE)

    for inbound in inbound_orders:

        inbound_id = inbound["inbound_id"]

        if inbound_id in inbound_ids:
            raise ValueError(f"Duplicate inbound ID: {inbound_id}")

        inbound_ids.add(inbound_id)

        po_line_id = inbound["po_line_id"]

        if po_line_id not in po_line_lookup:
            raise ValueError(
                f"Unknown purchase order line: {po_line_id}"
            )

        line = po_line_lookup[po_line_id]

        if line["po_id"] not in po_lookup:
            raise ValueError(f"Unknown purchase order: {line['po_id']}")

        po = po_lookup[line["po_id"]]

        sku_id = line["sku_id"]
        location_id = line["location_id"]
        sku_location = (sku_id, location_id)

        if sku_location not in valid_locations:
            raise ValueError(
                f"Invalid inbound SKU-location: {sku_location}"
            )

        if line["unit_of_measure"] != sku_lookup[sku_id]["unit_of_measure"]:
            raise ValueError(f"Inbound UOM mismatch: {inbound_id}")

        status = inbound["status"]

        if status not in expected_po_status:
            raise ValueError(f"Unknown inbound status: {status}")

        if po["status"] != expected_po_status[status]:
            raise ValueError(
                f"PO/inbound status mismatch: {inbound_id}"
            )

        quantity = float(inbound["inbound_quantity"])
        received = float(inbound["received_quantity"])

        if quantity < 0 or received < 0 or received > quantity:
            raise ValueError(
                f"Invalid inbound quantities: {inbound_id}"
            )

        if abs(float(line["order_quantity"]) - quantity) > 0.000001:
            raise ValueError(
                f"Inbound and PO line quantity mismatch: {inbound_id}"
            )

        expected_date = date.fromisoformat(
            inbound["expected_arrival_date"]
        )

        if expected_date < snapshot:
            raise ValueError(
                f"Inbound expected date precedes snapshot: {inbound_id}"
            )

        actual_date = None

        if inbound["actual_arrival_date"]:
            actual_date = date.fromisoformat(
                inbound["actual_arrival_date"]
            )

            if actual_date < snapshot:
                raise ValueError(
                    f"Inbound actual date precedes snapshot: {inbound_id}"
                )

        if status in ("RECEIVED", "PARTIALLY_RECEIVED"):

            if actual_date is None:
                raise ValueError(
                    f"Missing actual arrival date: {inbound_id}"
                )

            if received <= 0:
                raise ValueError(
                    f"Missing received quantity: {inbound_id}"
                )

            add_inbound(
                inbound_schedule,
                (sku_id, location_id, week_key(actual_date)),
                received,
                0.0,
                inbound_id
            )

            outstanding = quantity - received

            if status == "RECEIVED" and outstanding > 0.000001:
                raise ValueError(
                    f"Received order has outstanding quantity: {inbound_id}"
                )

            if status == "PARTIALLY_RECEIVED" and outstanding <= 0:
                raise ValueError(
                    f"Partial receipt has no outstanding quantity: {inbound_id}"
                )

            if outstanding > 0:
                remaining_date = max(expected_date, actual_date)

                add_inbound(
                    inbound_schedule,
                    (
                        sku_id,
                        location_id,
                        week_key(remaining_date)
                    ),
                    0.0,
                    outstanding,
                    inbound_id
                )

        else:

            if received != 0:
                raise ValueError(
                    f"Unexpected received quantity for {status}: {inbound_id}"
                )

            add_inbound(
                inbound_schedule,
                (
                    sku_id,
                    location_id,
                    week_key(expected_date)
                ),
                0.0,
                quantity,
                inbound_id
            )

    # --------------------------------------------------
    # 8. Validate BOM and production data
    # --------------------------------------------------

    bom_by_parent = defaultdict(list)

    for row in bom:
        parent = row["parent_sku_id"]
        component = row["component_sku_id"]
        quantity = float(row["component_quantity"])

        if parent not in valid_skus or component not in valid_skus:
            raise ValueError("Invalid BOM SKU reference.")

        if parent == component or quantity <= 0:
            raise ValueError("Invalid BOM relationship or quantity.")

        if (
            sku_lookup[parent]["unit_of_measure"]
            != sku_lookup[component]["unit_of_measure"]
        ):
            raise ValueError("BOM component UOM mismatch.")

        if not locations_by_sku[parent].issubset(
            locations_by_sku[component]
        ):
            raise ValueError(
                f"BOM component location coverage failed: {parent}, {component}"
            )

        bom_by_parent[parent].append(row)

    if any(len(rows) < 2 for rows in bom_by_parent.values()):
        raise ValueError(
            "Each manufactured SKU must have at least two BOM components."
        )

    capacity_lookup = {}
    plans_by_week = defaultdict(list)

    for row in production_capacities:
        key = (
            row["sku_id"],
            row["location_id"],
            row["production_week"]
        )

        if key in capacity_lookup:
            raise ValueError(f"Duplicate production capacity: {key}")

        if (key[0], key[1]) not in valid_locations:
            raise ValueError(f"Invalid production capacity location: {key}")

        capacity = float(row["maximum_quantity"])

        if capacity < 0:
            raise ValueError(f"Negative production capacity: {key}")

        capacity_lookup[key] = capacity

    plan_lookup = {}

    for row in production_plans:
        key = (
            row["sku_id"],
            row["location_id"],
            row["production_week"]
        )

        if key in plan_lookup:
            raise ValueError(f"Duplicate production plan: {key}")

        if key not in capacity_lookup:
            raise ValueError(f"Production plan has no capacity: {key}")

        planned = float(row["planned_quantity"])

        if planned < 0 or planned > capacity_lookup[key]:
            raise ValueError(f"Production plan exceeds capacity: {key}")

        if key[0] not in bom_by_parent:
            raise ValueError(
                f"Production plan SKU has no BOM: {key[0]}"
            )

        week_start(key[2])

        plan = {
            "quantity": planned,
            "production_id": row["production_id"],
            "key": key
        }

        plan_lookup[key] = plan
        plans_by_week[key[2]].append(plan)

    # Sort plans once for deterministic component allocation.
    for production_week in plans_by_week:
        plans_by_week[production_week].sort(
            key=lambda item: item["key"]
        )

    # --------------------------------------------------
    # 9. Calculate weekly inventory projections
    # --------------------------------------------------

    current_balance = dict(opening_inventory)

    projection_records = []
    shortage_records = []

    projection_counter = 1
    shortage_counter = 1

    for current_week in weeks:

        week_date = week_start(current_week)
        week_forecasts = forecasts_by_week[current_week]

        week_state = {}

        # Prepare opening balance and inbound supply.
        for sku_location, demand in week_forecasts.items():

            inbound = inbound_schedule.get(
                (
                    sku_location[0],
                    sku_location[1],
                    current_week
                ),
                {
                    "received": 0.0,
                    "outstanding": 0.0,
                    "inbound_ids": []
                }
            )

            opening = current_balance[sku_location]

            inbound_received = inbound["received"]
            inbound_outstanding = inbound["outstanding"]

            available_after_inbound = (
                opening
                + inbound_received
                + inbound_outstanding
            )

            week_state[sku_location] = {
                "opening": opening,
                "demand": demand,
                "inbound_received": inbound_received,
                "inbound_outstanding": inbound_outstanding,
                "inbound_ids": sorted(set(inbound["inbound_ids"])),
                "available_after_inbound": available_after_inbound,
                "component_consumption": 0.0,
                "production_output": 0.0,
                "production_ids": [],
                "bom_ids": [],
                "planned_production": 0.0,
                "feasible_production": 0.0,
                "production_capacity": 0.0
            }

        # Reserve current-week forecast demand before using
        # component stock for production.
        component_surplus = {}

        for sku_location, state in week_state.items():
            component_surplus[sku_location] = max(
                0.0,
                state["available_after_inbound"] - state["demand"]
            )

        # Process only production plans belonging to this week.
        for plan in plans_by_week.get(current_week, []):

            parent_sku, location_id, production_week = plan["key"]
            parent_key = (parent_sku, location_id)

            if parent_key not in week_state:
                raise ValueError(
                    f"Production plan has no forecast row: "
                    f"{parent_key}, {current_week}"
                )

            planned_quantity = plan["quantity"]

            capacity = capacity_lookup[
                (parent_sku, location_id, production_week)
            ]

            feasible_quantity = min(planned_quantity, capacity)

            parent_bom = bom_by_parent[parent_sku]

            # Determine the quantity supported by every component.
            for component_row in parent_bom:

                component_sku = component_row["component_sku_id"]
                component_ratio = float(
                    component_row["component_quantity"]
                )

                component_key = (component_sku, location_id)

                if component_key not in component_surplus:
                    raise ValueError(
                        f"Missing component projection row: {component_key}"
                    )

                component_available = component_surplus[component_key]

                component_supported_quantity = math.floor(
                    (component_available + 0.0000001)
                    / component_ratio
                )

                feasible_quantity = min(
                    feasible_quantity,
                    component_supported_quantity
                )

            feasible_quantity = max(0.0, feasible_quantity)

            # Consume components for feasible production.
            for component_row in parent_bom:

                component_sku = component_row["component_sku_id"]
                component_ratio = float(
                    component_row["component_quantity"]
                )

                component_key = (component_sku, location_id)

                consumption = round(
                    feasible_quantity * component_ratio,
                    6
                )

                component_surplus[component_key] -= consumption

                week_state[component_key][
                    "component_consumption"
                ] += consumption

                week_state[component_key]["bom_ids"].append(
                    component_row["bom_id"]
                )

            # Add finished production output.
            parent_state = week_state[parent_key]

            parent_state["production_output"] += feasible_quantity
            parent_state["planned_production"] += planned_quantity
            parent_state["feasible_production"] += feasible_quantity
            parent_state["production_capacity"] += capacity

            parent_state["production_ids"].append(
                plan["production_id"]
            )

            parent_state["bom_ids"].extend(
                row["bom_id"] for row in parent_bom
            )

        # Calculate final weekly balance and shortage.
        for sku_location in sorted(week_state):

            state = week_state[sku_location]

            available_before_demand = (
                state["available_after_inbound"]
                - state["component_consumption"]
                + state["production_output"]
            )

            demand = state["demand"]

            shortage_quantity = max(
                0.0,
                demand - available_before_demand
            )

            ending_balance = max(
                0.0,
                available_before_demand - demand
            )

            values = {
                "opening_available_quantity": state["opening"],
                "inbound_received_quantity": state["inbound_received"],
                "inbound_outstanding_quantity": state["inbound_outstanding"],
                "available_after_inbound": state["available_after_inbound"],
                "production_planned_quantity": state["planned_production"],
                "production_capacity_quantity": state["production_capacity"],
                "production_output_quantity": state["production_output"],
                "production_component_consumption": state["component_consumption"],
                "available_before_demand": available_before_demand,
                "forecast_demand": demand,
                "projected_shortage_quantity": shortage_quantity,
                "ending_available_balance": ending_balance
            }

            values = {
                key: round(value, 6)
                for key, value in values.items()
            }

            sku_id, location_id = sku_location

            forecast_key = (
                sku_id,
                location_id,
                current_week
            )

            projection_id = (
                f"PROJ-GEN-2026-{projection_counter:06d}"
            )

            projection_counter += 1

            projection_records.append({
                "projection_id": projection_id,
                "forecast_id": forecast_ids[forecast_key],
                "sku_id": sku_id,
                "location_id": location_id,
                "forecast_week": current_week,
                "inventory_snapshot_date": SNAPSHOT_DATE,
                "projection_date": week_date.isoformat(),
                "unit_of_measure": sku_lookup[sku_id]["unit_of_measure"],
                **values,
                "inbound_source_refs": ";".join(state["inbound_ids"]),
                "production_source_refs": ";".join(
                    sorted(set(state["production_ids"]))
                ),
                "bom_source_refs": ";".join(
                    sorted(set(state["bom_ids"]))
                ),
                "projection_status": (
                    "SHORTAGE"
                    if shortage_quantity > 0.000001
                    else "SUFFICIENT"
                ),
                "assumptions": ASSUMPTIONS
            })

            if shortage_quantity > 0.000001:

                shortage_id = (
                    f"SHORT-GEN-2026-{shortage_counter:06d}"
                )

                shortage_counter += 1

                shortage_records.append({
                    "shortage_id": shortage_id,
                    "projection_id": projection_id,
                    "forecast_id": forecast_ids[forecast_key],
                    "sku_id": sku_id,
                    "location_id": location_id,
                    "shortage_week": current_week,
                    "demand_quantity": round(demand, 6),
                    "available_quantity": round(
                        available_before_demand, 6
                    ),
                    "shortage_quantity": round(
                        shortage_quantity, 6
                    ),
                    "unit_of_measure": sku_lookup[sku_id]["unit_of_measure"],
                    "status": "PROJECTED",
                    "cause": (
                        "INSUFFICIENT_AVAILABLE_INVENTORY"
                        if state["production_output"] == 0
                        else "DEMAND_EXCEEDS_AVAILABLE_SUPPLY"
                    )
                })

            # No backorder is carried into the next week.
            current_balance[sku_location] = ending_balance

    # --------------------------------------------------
    # 10. Validate projection output
    # --------------------------------------------------

    expected_projection_count = len(forecast_lookup)

    if len(projection_records) != expected_projection_count:
        raise ValueError(
            "Projection row count does not match forecast row count."
        )

    projection_ids = {
        row["projection_id"] for row in projection_records
    }

    if len(projection_ids) != len(projection_records):
        raise ValueError("Duplicate projection IDs.")

    shortage_ids = {
        row["shortage_id"] for row in shortage_records
    }

    if len(shortage_ids) != len(shortage_records):
        raise ValueError("Duplicate shortage IDs.")

    for row in projection_records:

        if abs(
            row["opening_available_quantity"]
            + row["inbound_received_quantity"]
            + row["inbound_outstanding_quantity"]
            - row["available_after_inbound"]
        ) > 0.00001:
            raise ValueError("Inbound balance reconciliation failed.")

        if abs(
            row["available_after_inbound"]
            - row["production_component_consumption"]
            + row["production_output_quantity"]
            - row["available_before_demand"]
        ) > 0.00001:
            raise ValueError("Production balance reconciliation failed.")

        if abs(
            max(
                0.0,
                row["available_before_demand"]
                - row["forecast_demand"]
            )
            - row["ending_available_balance"]
        ) > 0.00001:
            raise ValueError("Ending inventory reconciliation failed.")

        if abs(
            max(
                0.0,
                row["forecast_demand"]
                - row["available_before_demand"]
            )
            - row["projected_shortage_quantity"]
        ) > 0.00001:
            raise ValueError("Shortage quantity reconciliation failed.")

    # --------------------------------------------------
    # 11. Export CSV files
    # --------------------------------------------------

    projection_fields = list(projection_records[0].keys())

    shortage_fields = [
        "shortage_id",
        "projection_id",
        "forecast_id",
        "sku_id",
        "location_id",
        "shortage_week",
        "demand_quantity",
        "available_quantity",
        "shortage_quantity",
        "unit_of_measure",
        "status",
        "cause"
    ]

    write_csv(
        transaction_dir / "weekly_inventory_projection.csv",
        projection_records,
        projection_fields
    )

    write_csv(
        transaction_dir / "projected_shortages.csv",
        shortage_records,
        shortage_fields
    )

    # --------------------------------------------------
    # 12. Display results
    # --------------------------------------------------

    total_demand = sum(
        row["forecast_demand"]
        for row in projection_records
    )

    total_shortage = sum(
        row["shortage_quantity"]
        for row in shortage_records
    )

    total_production = sum(
        row["production_output_quantity"]
        for row in projection_records
    )

    print("\n" + "=" * 70)
    print("WEEKLY INVENTORY PROJECTION COMPLETED")
    print("=" * 70)

    print(f"Scale: {scale}")
    print(f"Inventory snapshot: {SNAPSHOT_DATE}")
    print(f"Forecast weeks: {len(weeks)}")

    print("\nGENERATED RECORD COUNTS")
    print("-" * 70)
    print(f"Forecast rows: {len(forecast_lookup)}")
    print(f"Projection rows: {len(projection_records)}")
    print(f"Projected shortage rows: {len(shortage_records)}")

    print("\nPROJECTION TOTALS")
    print("-" * 70)
    print(f"Forecast demand: {round(total_demand, 2)}")
    print(f"Feasible production output: {round(total_production, 2)}")
    print(f"Projected shortage quantity: {round(total_shortage, 2)}")

    print("\nVALIDATION")
    print("-" * 70)
    print("Required input checks: PASSED")
    print("Inventory snapshot checks: PASSED")
    print("SKU-location references: PASSED")
    print("Forecast uniqueness: PASSED")
    print("Inbound lifecycle checks: PASSED")
    print("Inbound quantity reconciliation: PASSED")
    print("BOM component location coverage: PASSED")
    print("Production capacity checks: PASSED")
    print("Production component availability checks: PASSED")
    print("Weekly inventory arithmetic: PASSED")
    print("Shortage quantity reconciliation: PASSED")
    print("Projection ID uniqueness: PASSED")
    print("Shortage ID uniqueness: PASSED")

    print("\nOUTPUT FILES")
    print(transaction_dir / "weekly_inventory_projection.csv")
    print(transaction_dir / "projected_shortages.csv")

    print("\nDatabase changes: NONE")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Generate weekly inventory projections and shortages."
    )

    parser.add_argument(
        "--scale",
        choices=["starter", "full"],
        default="starter",
        help="Dataset scale to process."
    )

    args = parser.parse_args()

    generate_inventory_projection(args.scale)
