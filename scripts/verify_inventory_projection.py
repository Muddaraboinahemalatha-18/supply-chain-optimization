
import argparse
import csv
import math
import sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from config.generator_config import get_config

SNAPSHOT_DATE = "2026-01-01"
TOLERANCE = 0.00001


def read_csv(data_dir, filename):
    path = data_dir / filename

    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with open(path, "r", newline="", encoding="utf-8") as file:
        records = list(csv.DictReader(file))

    if not records:
        raise ValueError(f"File is empty: {path}")

    return records


def close(a, b):
    return math.isclose(
        float(a),
        float(b),
        rel_tol=0,
        abs_tol=TOLERANCE
    )


def verify_inventory_projection(scale="starter"):

    get_config(scale)

    scale_dir = BASE_DIR / "data" / "generated" / scale
    master_dir = scale_dir / "master_data"
    transaction_dir = scale_dir / "transactions"

    projection = read_csv(
        transaction_dir, "weekly_inventory_projection.csv"
    )
    shortages = read_csv(
        transaction_dir, "projected_shortages.csv"
    )
    forecasts = read_csv(
        transaction_dir, "forecast_demand.csv"
    )
    inventories = read_csv(
        transaction_dir, "inventory.csv"
    )

    skus = read_csv(master_dir, "sku.csv")

    errors = []

    print("=" * 70)
    print("INVENTORY PROJECTION INDEPENDENT VERIFICATION")
    print("=" * 70)
    print("Scale:", scale)
    print("Input directory:", scale_dir)

    # --------------------------------------------------
    # 1. Record counts
    # --------------------------------------------------

    print("\n1. RECORD COUNTS")
    print("-" * 70)

    print("Forecast records:", len(forecasts))
    print("Projection records:", len(projection))
    print("Shortage records:", len(shortages))

    if len(projection) != len(forecasts):
        errors.append("Projection count does not match forecast count.")

    # --------------------------------------------------
    # 2. Build independent source lookups
    # --------------------------------------------------

    sku_lookup = {r["sku_id"]: r for r in skus}

    if len(sku_lookup) != len(skus):
        errors.append("Duplicate SKU master IDs.")

    forecast_lookup = {}

    for row in forecasts:
        key = (
            row["sku_id"],
            row["location_id"],
            row["forecast_week"]
        )

        if key in forecast_lookup:
            errors.append(f"Duplicate source forecast: {key}")
            continue

        forecast_lookup[key] = row

    inventory_lookup = {}

    for row in inventories:
        key = (row["sku_id"], row["location_id"])

        if key in inventory_lookup:
            errors.append(f"Duplicate opening inventory: {key}")
            continue

        inventory_lookup[key] = row

    # --------------------------------------------------
    # 3. Uniqueness and source-reference checks
    # --------------------------------------------------

    projection_keys = [
        (
            r["sku_id"],
            r["location_id"],
            r["forecast_week"]
        )
        for r in projection
    ]

    projection_ids = [r["projection_id"] for r in projection]
    shortage_ids = [r["shortage_id"] for r in shortages]

    projection_key_set = set(projection_keys)
    projection_id_set = set(projection_ids)

    print("\n2. UNIQUENESS AND SOURCE REFERENCES")
    print("-" * 70)

    checks = {
        "SKU-location-week uniqueness":
            len(projection_keys) == len(projection_key_set),

        "Projection ID uniqueness":
            len(projection_ids) == len(projection_id_set),

        "Shortage ID uniqueness":
            len(shortage_ids) == len(set(shortage_ids)),

        "Forecast reference coverage":
            projection_key_set == set(forecast_lookup)
    }

    for name, passed in checks.items():
        print(f"{name}: {'PASSED' if passed else 'FAILED'}")

        if not passed:
            errors.append(name + " failed.")

    # Verify each projection refers to its source forecast.
    for row in projection:

        key = (
            row["sku_id"],
            row["location_id"],
            row["forecast_week"]
        )

        source = forecast_lookup.get(key)

        if source is None:
            continue

        if row["forecast_id"] != source["forecast_id"]:
            errors.append(
                f"Forecast ID mismatch: {row['projection_id']}"
            )

        if not close(
            row["forecast_demand"],
            source["forecast_quantity"]
        ):
            errors.append(
                f"Forecast quantity mismatch: {row['projection_id']}"
            )

        sku = sku_lookup.get(row["sku_id"])

        if sku is None:
            errors.append(
                f"Unknown SKU in projection: {row['projection_id']}"
            )
        elif row["unit_of_measure"] != sku["unit_of_measure"]:
            errors.append(
                f"Projection UOM mismatch: {row['projection_id']}"
            )

    # --------------------------------------------------
    # 4. Inventory arithmetic reconciliation
    # --------------------------------------------------

    print("\n3. ARITHMETIC RECONCILIATION")
    print("-" * 70)

    arithmetic_errors = 0

    for row in projection:

        opening = float(row["opening_available_quantity"])
        received = float(row["inbound_received_quantity"])
        outstanding = float(row["inbound_outstanding_quantity"])
        demand = float(row["forecast_demand"])
        production = float(row["production_output_quantity"])
        consumption = float(row["production_component_consumption"])
        available_after_inbound = float(
            row["available_after_inbound"]
        )
        available = float(row["available_before_demand"])
        ending = float(row["ending_available_balance"])
        shortage = float(row["projected_shortage_quantity"])

        expected_after_inbound = (
            opening + received + outstanding
        )

        expected_available = (
            expected_after_inbound + production - consumption
        )

        expected_ending = max(
            0.0,
            expected_available - demand
        )

        expected_shortage = max(
            0.0,
            demand - expected_available
        )

        if not close(available_after_inbound, expected_after_inbound):
            arithmetic_errors += 1

        if not close(available, expected_available):
            arithmetic_errors += 1

        if not close(ending, expected_ending):
            arithmetic_errors += 1

        if not close(shortage, expected_shortage):
            arithmetic_errors += 1

        if min(
            opening,
            received,
            outstanding,
            demand,
            production,
            consumption,
            ending,
            shortage
        ) < -TOLERANCE:
            arithmetic_errors += 1

        expected_status = (
            "SHORTAGE" if expected_shortage > TOLERANCE
            else "SUFFICIENT"
        )

        if row["projection_status"] != expected_status:
            arithmetic_errors += 1

    if arithmetic_errors:
        errors.append(
            f"Inventory arithmetic/status errors: {arithmetic_errors}"
        )

    print(
        "Inbound balance reconciliation:",
        "PASSED" if arithmetic_errors == 0 else "FAILED"
    )
    print(
        "Production balance reconciliation:",
        "PASSED" if arithmetic_errors == 0 else "FAILED"
    )
    print(
        "Ending inventory reconciliation:",
        "PASSED" if arithmetic_errors == 0 else "FAILED"
    )
    print(
        "Shortage arithmetic reconciliation:",
        "PASSED" if arithmetic_errors == 0 else "FAILED"
    )
    print(
        "Projection status reconciliation:",
        "PASSED" if arithmetic_errors == 0 else "FAILED"
    )

    # --------------------------------------------------
    # 5. Opening inventory and week-to-week continuity
    # --------------------------------------------------

    print("\n4. INVENTORY CONTINUITY")
    print("-" * 70)

    continuity_errors = 0

    projection_by_sku_location = defaultdict(list)

    for row in projection:
        key = (row["sku_id"], row["location_id"])
        projection_by_sku_location[key].append(row)

    for key, rows in projection_by_sku_location.items():

        rows.sort(key=lambda r: r["forecast_week"])

        opening_record = inventory_lookup.get(key)

        if opening_record is None:
            continuity_errors += 1
            continue

        expected_opening = (
            float(opening_record["on_hand_quantity"])
            - float(opening_record["reserved_quantity"])
        )

        if opening_record["inventory_date"] != SNAPSHOT_DATE:
            continuity_errors += 1

        for index, row in enumerate(rows):

            actual_opening = float(
                row["opening_available_quantity"]
            )

            if not close(actual_opening, expected_opening):
                continuity_errors += 1

            expected_opening = float(
                row["ending_available_balance"]
            )

    if continuity_errors:
        errors.append(
            f"Inventory continuity errors: {continuity_errors}"
        )

    print(
        "Opening inventory and weekly balance continuity:",
        "PASSED" if continuity_errors == 0 else "FAILED"
    )

    # --------------------------------------------------
    # 6. Shortage output consistency
    # --------------------------------------------------

    print("\n5. SHORTAGE OUTPUT CONSISTENCY")
    print("-" * 70)

    projection_shortages = {
        row["projection_id"]: row
        for row in projection
        if float(row["projected_shortage_quantity"]) > TOLERANCE
    }

    shortage_by_projection = {}

    for row in shortages:

        projection_id = row["projection_id"]

        if projection_id in shortage_by_projection:
            errors.append(
                f"Duplicate shortage projection reference: {projection_id}"
            )
            continue

        shortage_by_projection[projection_id] = row

    expected_shortage_refs = set(projection_shortages)
    actual_shortage_refs = set(shortage_by_projection)

    shortage_match = (
        expected_shortage_refs == actual_shortage_refs
    )

    if not shortage_match:
        errors.append(
            "Shortage CSV does not match projection shortage rows."
        )

    for projection_id, shortage_row in shortage_by_projection.items():

        source = projection_shortages.get(projection_id)

        if source is None:
            continue

        comparisons = [
            (
                shortage_row["shortage_quantity"],
                source["projected_shortage_quantity"]
            ),
            (
                shortage_row["demand_quantity"],
                source["forecast_demand"]
            ),
            (
                shortage_row["available_quantity"],
                source["available_before_demand"]
            )
        ]

        if any(not close(a, b) for a, b in comparisons):
            errors.append(
                f"Shortage quantity/details mismatch: {projection_id}"
            )

        if shortage_row["forecast_id"] != source["forecast_id"]:
            errors.append(
                f"Shortage forecast reference mismatch: {projection_id}"
            )

        if (
            shortage_row["sku_id"] != source["sku_id"]
            or shortage_row["location_id"] != source["location_id"]
            or shortage_row["shortage_week"] != source["forecast_week"]
        ):
            errors.append(
                f"Shortage SKU/location/week mismatch: {projection_id}"
            )

    print(
        "Shortage CSV matches projection:",
        "PASSED" if shortage_match else "FAILED"
    )

    # --------------------------------------------------
    # 7. Weekly summary
    # --------------------------------------------------

    weekly = defaultdict(lambda: {
        "demand": 0.0,
        "shortage": 0.0,
        "production": 0.0,
        "records": 0
    })

    for row in projection:

        week = row["forecast_week"]

        weekly[week]["demand"] += float(row["forecast_demand"])
        weekly[week]["shortage"] += float(
            row["projected_shortage_quantity"]
        )
        weekly[week]["production"] += float(
            row["production_output_quantity"]
        )
        weekly[week]["records"] += 1

    print("\n6. WEEKLY SUMMARY")
    print("-" * 70)

    for week in sorted(weekly):
        values = weekly[week]

        print(
            f"{week} | "
            f"Records: {values['records']} | "
            f"Demand: {values['demand']:.2f} | "
            f"Production: {values['production']:.2f} | "
            f"Shortage: {values['shortage']:.2f}"
        )

    # --------------------------------------------------
    # 8. Unit-of-measure summary
    # --------------------------------------------------

    unit_summary = defaultdict(lambda: {
        "demand": 0.0,
        "shortage": 0.0,
        "production": 0.0,
        "shortage_records": 0
    })

    for row in projection:

        unit = row["unit_of_measure"]

        unit_summary[unit]["demand"] += float(
            row["forecast_demand"]
        )
        unit_summary[unit]["shortage"] += float(
            row["projected_shortage_quantity"]
        )
        unit_summary[unit]["production"] += float(
            row["production_output_quantity"]
        )

        if float(row["projected_shortage_quantity"]) > TOLERANCE:
            unit_summary[unit]["shortage_records"] += 1

    print("\n7. UNIT-OF-MEASURE SUMMARY")
    print("-" * 70)

    for unit, values in sorted(unit_summary.items()):
        print(
            f"{unit} | "
            f"Demand: {values['demand']:.2f} | "
            f"Production: {values['production']:.2f} | "
            f"Shortage: {values['shortage']:.2f} | "
            f"Shortage records: {values['shortage_records']}"
        )

    # --------------------------------------------------
    # 9. Final verification
    # --------------------------------------------------

    print("\n8. FINAL VERIFICATION")
    print("-" * 70)

    if errors:
        print("VERIFICATION FAILED")
        print("Errors found:", len(errors))

        for error in errors[:30]:
            print("-", error)

        if len(errors) > 30:
            print("Additional errors:", len(errors) - 30)

    else:
        print("ALL INDEPENDENT CHECKS PASSED")

    print("\nDatabase changes: NONE")

    return len(errors) == 0


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Independently verify inventory projections."
    )

    parser.add_argument(
        "--scale",
        choices=["starter", "full"],
        default="starter"
    )

    args = parser.parse_args()

    success = verify_inventory_projection(args.scale)

    if not success:
        raise SystemExit(1)
