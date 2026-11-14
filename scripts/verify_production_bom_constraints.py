
import csv
import math
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "generated" / "full"
TOLERANCE = 0.00001


def read_csv(relative_path):
    path = DATA_DIR / relative_path
    with open(path, encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def close(a, b):
    return math.isclose(
        float(a), float(b),
        rel_tol=0,
        abs_tol=TOLERANCE
    )


def main():
    print("=" * 72)
    print("INDEPENDENT PRODUCTION AND BOM CONSTRAINT VERIFICATION")
    print("=" * 72)

    bom_rows = read_csv("master_data/bom.csv")
    capacity_rows = read_csv("transactions/production_capacity.csv")
    plan_rows = read_csv("transactions/production_plan.csv")
    projection_rows = read_csv(
        "transactions/weekly_inventory_projection.csv"
    )

    bom_by_parent = defaultdict(list)

    for row in bom_rows:
        ratio = float(row["component_quantity"])
        if ratio <= 0:
            raise ValueError("Invalid BOM component quantity.")
        bom_by_parent[row["parent_sku_id"]].append(row)

    capacity_lookup = {}

    for row in capacity_rows:
        key = (
            row["sku_id"],
            row["location_id"],
            row["production_week"]
        )

        if key in capacity_lookup:
            raise ValueError(f"Duplicate capacity record: {key}")

        capacity = float(row["maximum_quantity"])

        if capacity < 0:
            raise ValueError(f"Negative capacity: {key}")

        capacity_lookup[key] = capacity

    projection_lookup = {}
    projections_by_week = defaultdict(list)

    for row in projection_rows:
        key = (
            row["sku_id"],
            row["location_id"],
            row["forecast_week"]
        )

        if key in projection_lookup:
            raise ValueError(f"Duplicate projection: {key}")

        projection_lookup[key] = row
        projections_by_week[key[2]].append(row)

    plans_by_week = defaultdict(list)
    plan_keys = set()

    for row in plan_rows:
        key = (
            row["sku_id"],
            row["location_id"],
            row["production_week"]
        )

        if key in plan_keys:
            raise ValueError(f"Duplicate production plan: {key}")

        plan_keys.add(key)

        if key not in capacity_lookup:
            raise ValueError(f"Missing production capacity: {key}")

        if key[0] not in bom_by_parent:
            raise ValueError(f"Missing BOM: {key}")

        planned = float(row["planned_quantity"])
        capacity = capacity_lookup[key]

        if planned < 0 or planned > capacity + TOLERANCE:
            raise ValueError(f"Plan exceeds capacity: {key}")

        plans_by_week[key[2]].append({
            "key": key,
            "planned": planned
        })

    # Independently recalculate expected results.
    expected = defaultdict(lambda: {
        "planned": 0.0,
        "capacity": 0.0,
        "output": 0.0,
        "consumption": 0.0
    })

    component_calculations = 0
    negative_surplus_errors = 0

    for week in sorted(projections_by_week):

        component_surplus = {}

        # Reserve current-week forecast demand first.
        for row in projections_by_week[week]:
            key = (row["sku_id"], row["location_id"])

            available = float(row["available_after_inbound"])
            demand = float(row["forecast_demand"])

            component_surplus[key] = max(
                0.0, available - demand
            )

        # Same deterministic plan order as the generator.
        week_plans = sorted(
            plans_by_week.get(week, []),
            key=lambda item: item["key"]
        )

        for plan in week_plans:
            sku, location, production_week = plan["key"]
            planned = plan["planned"]
            capacity = capacity_lookup[plan["key"]]

            feasible = min(planned, capacity)
            parent_bom = bom_by_parent[sku]

            # Determine production supported by every component.
            for component in parent_bom:
                component_sku = component["component_sku_id"]
                ratio = float(component["component_quantity"])
                component_key = (component_sku, location)

                if component_key not in component_surplus:
                    raise ValueError(
                        f"Missing component projection: "
                        f"{component_key}, {week}"
                    )

                supported = math.floor(
                    (component_surplus[component_key] + 0.0000001)
                    / ratio
                )

                feasible = min(feasible, supported)
                component_calculations += 1

            feasible = max(0.0, feasible)

            # Correct flat tuple keys: SKU, location, week.
            expected[sku, location, week]["planned"] += planned
            expected[sku, location, week]["capacity"] += capacity
            expected[sku, location, week]["output"] += feasible

            # Independently calculate and deduct BOM consumption.
            for component in parent_bom:
                component_sku = component["component_sku_id"]
                ratio = float(component["component_quantity"])
                component_key = (component_sku, location)

                consumption = round(feasible * ratio, 6)

                component_surplus[component_key] -= consumption

                expected[component_sku, location, week][
                    "consumption"
                ] += consumption

                if component_surplus[component_key] < -TOLERANCE:
                    negative_surplus_errors += 1

    # Compare every projection record.
    comparison_errors = 0

    for row in projection_rows:
        sku = row["sku_id"]
        location = row["location_id"]
        week = row["forecast_week"]

        values = expected[sku, location, week]

        comparisons = {
            "planned": row["production_planned_quantity"],
            "capacity": row["production_capacity_quantity"],
            "output": row["production_output_quantity"],
            "consumption": row["production_component_consumption"]
        }

        for field, actual in comparisons.items():
            if not close(actual, values[field]):
                comparison_errors += 1

                if comparison_errors <= 10:
                    print(
                        "MISMATCH:", (sku, location, week),
                        field,
                        "Expected:", values[field],
                        "Actual:", actual
                    )

        output = float(row["production_output_quantity"])
        planned = float(row["production_planned_quantity"])
        capacity = float(row["production_capacity_quantity"])

        if output > planned + TOLERANCE:
            comparison_errors += 1

        if output > capacity + TOLERANCE:
            comparison_errors += 1

    print("\nVERIFICATION RESULTS")
    print("-" * 72)
    print("BOM records:", len(bom_rows))
    print("Capacity records:", len(capacity_rows))
    print("Production plans:", len(plan_rows))
    print("Projection records:", len(projection_rows))
    print("BOM component calculations:", component_calculations)
    print("Independent comparison errors:", comparison_errors)
    print("Negative component surplus errors:", negative_surplus_errors)

    if comparison_errors == 0 and negative_surplus_errors == 0:
        print("\nPASS: Production and BOM constraints independently verified.")
    else:
        print("\nFAIL: Production/BOM verification found discrepancies.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
