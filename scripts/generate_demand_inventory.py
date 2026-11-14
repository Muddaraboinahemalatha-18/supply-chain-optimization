
import sys
import csv
import random
import argparse
from pathlib import Path

# Add project root to Python path
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


def generate_demand_inventory(scale="starter"):

    config = get_config(scale)
    rng = random.Random(config["random_seed"] + 1)

    # Separate folders for starter and full datasets
    scale_dir = BASE_DIR / "data" / "generated" / scale

    master_dir = scale_dir / "master_data"
    output_dir = scale_dir / "transactions"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Read previously generated master data
    skus = read_csv(master_dir / "sku.csv")
    sku_locations = read_csv(master_dir / "sku_location.csv")
    locations = read_csv(master_dir / "location.csv")

    if not skus or not sku_locations or not locations:
        raise ValueError("Master data files must not be empty.")

    sku_lookup = {
        sku["sku_id"]: sku
        for sku in skus
    }

    forecasts = []
    inventories = []

    inventory_counter = 1

    # ------------------------------------------------
    # 1. GENERATE WEEKLY FORECAST DEMAND
    # ------------------------------------------------

    demand_by_sku_location = {}

    for relationship in sku_locations:

        sku_id = relationship["sku_id"]
        location_id = relationship["location_id"]

        if sku_id not in sku_lookup:
            raise ValueError(
                f"Unknown SKU reference: {sku_id}"
            )

        sku = sku_lookup[sku_id]
        category = sku["category"]

        # Category-based synthetic weekly demand
        if category in ["Grains", "Pulses"]:
            base_demand = rng.randint(60, 180)
        elif category in ["Oil", "Dairy"]:
            base_demand = rng.randint(30, 120)
        else:
            base_demand = rng.randint(40, 140)

        location_key = (sku_id, location_id)
        demand_by_sku_location[location_key] = []

        for week_number in range(1, config["demand_weeks"] + 1):

            # Normal weekly variation
            variation = rng.uniform(0.85, 1.15)

            # Controlled synthetic demand spike
            spike_multiplier = 1.5 if rng.random() < 0.10 else 1.0

            demand_quantity = max(
                1,
                round(base_demand * variation * spike_multiplier)
            )

            week_label = (
                f"{config['planning_year']}-W{week_number:02d}"
            )

            week_id = (
                f"{config['planning_year']}W{week_number:02d}"
            )

            forecast_id = (
                f"DEM-{sku_id}-{location_id}-{week_id}"
            )

            forecasts.append({
                "forecast_id": forecast_id,
                "sku_id": sku_id,
                "location_id": location_id,
                "forecast_week": week_label,
                "forecast_quantity": demand_quantity,
                "forecast_version": config["forecast_version"]
            })

            demand_by_sku_location[location_key].append(
                demand_quantity
            )

    # ------------------------------------------------
    # 2. GENERATE OPENING INVENTORY
    # ------------------------------------------------

    for relationship in sku_locations:

        sku_id = relationship["sku_id"]
        location_id = relationship["location_id"]

        sku = sku_lookup[sku_id]
        unit_of_measure = sku["unit_of_measure"]

        location_key = (sku_id, location_id)

        weekly_demands = demand_by_sku_location[location_key]

        average_weekly_demand = (
            sum(weekly_demands) / len(weekly_demands)
        )

        # Opening stock based on generated demand
        on_hand_quantity = max(
            1,
            round(
                average_weekly_demand * rng.uniform(1.5, 3.0)
            )
        )

        reserved_quantity = rng.randint(
            0,
            max(0, round(on_hand_quantity * 0.15))
        )

        inventories.append({
            "inventory_id": f"INV-2026-{inventory_counter:06d}",
            "sku_id": sku_id,
            "location_id": location_id,
            "on_hand_quantity": on_hand_quantity,
            "reserved_quantity": reserved_quantity,
            "unit_of_measure": unit_of_measure,
            "inventory_date": config["inventory_snapshot_date"]
        })

        inventory_counter += 1

    # ------------------------------------------------
    # 3. EXPORT CSV FILES
    # ------------------------------------------------

    datasets = {
        "forecast_demand.csv": forecasts,
        "inventory.csv": inventories
    }

    for filename, records in datasets.items():

        if not records:
            raise ValueError(
                f"No records generated for {filename}"
            )

        file_path = output_dir / filename

        with open(
            file_path,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=list(records[0].keys())
            )

            writer.writeheader()
            writer.writerows(records)

    # ------------------------------------------------
    # 4. VALIDATION
    # ------------------------------------------------

    forecast_ids = [
        row["forecast_id"]
        for row in forecasts
    ]

    inventory_ids = [
        row["inventory_id"]
        for row in inventories
    ]

    assert len(forecast_ids) == len(set(forecast_ids))
    assert len(inventory_ids) == len(set(inventory_ids))

    valid_sku_ids = set(sku_lookup.keys())

    valid_location_ids = {
        row["location_id"] for row in locations
    }

    assert all(
        row["sku_id"] in valid_sku_ids
        and row["location_id"] in valid_location_ids
        for row in forecasts
    )

    assert all(
        row["sku_id"] in valid_sku_ids
        and row["location_id"] in valid_location_ids
        for row in inventories
    )

    assert all(
        int(row["forecast_quantity"]) >= 0
        for row in forecasts
    )

    assert all(
        int(row["on_hand_quantity"]) >=
        int(row["reserved_quantity"]) >= 0
        for row in inventories
    )

    # ------------------------------------------------
    # 5. GENERATION SUMMARY
    # ------------------------------------------------

    print("=" * 60)
    print("FORECAST AND INVENTORY GENERATION COMPLETED")
    print("=" * 60)

    print(f"Scale: {scale}")
    print(f"Random seed: {config['random_seed'] + 1}")

    print("\nGENERATED RECORD COUNTS")
    print("-" * 60)

    for filename, records in datasets.items():
        print(f"{filename}: {len(records)}")

    print("\nVALIDATION")
    print("Forecast ID uniqueness: PASSED")
    print("Inventory ID uniqueness: PASSED")
    print("SKU and location references: PASSED")
    print("Non-negative demand: PASSED")
    print("Inventory reservation checks: PASSED")

    print("\nOUTPUT DIRECTORY")
    print(output_dir)

    print("\nDatabase changes: NONE")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Generate forecast demand and inventory data."
    )

    parser.add_argument(
        "--scale",
        choices=["starter", "full"],
        default="starter"
    )

    args = parser.parse_args()

    generate_demand_inventory(args.scale)
