
import sys
import csv
import random
import argparse
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
        raise ValueError(f"No records to write: {file_path}")

    with open(file_path, "w", newline="", encoding="utf-8") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(records[0].keys())
        )

        writer.writeheader()
        writer.writerows(records)


def generate_supplier_constraints(scale="starter"):

    config = get_config(scale)
    rng = random.Random(config["random_seed"] + 2)

    # Scale-specific directories
    scale_dir = BASE_DIR / "data" / "generated" / scale

    master_dir = scale_dir / "master_data"
    transaction_dir = scale_dir / "transactions"

    transaction_dir.mkdir(parents=True, exist_ok=True)

    # Read required input files
    suppliers = read_csv(master_dir / "supplier.csv")
    locations = read_csv(master_dir / "location.csv")
    supplier_skus = read_csv(master_dir / "supplier_sku.csv")
    forecasts = read_csv(transaction_dir / "forecast_demand.csv")

    if not suppliers or not locations or not supplier_skus or not forecasts:
        raise ValueError("Required input CSV files must not be empty.")

    supplier_ids = {row["supplier_id"] for row in suppliers}
    location_ids = {row["location_id"] for row in locations}

    # ------------------------------------------------
    # 1. CALCULATE TOTAL SKU DEMAND PER WEEK
    # ------------------------------------------------

    demand_by_sku_week = {}

    for row in forecasts:

        key = (row["sku_id"], row["forecast_week"])

        demand_by_sku_week[key] = (
            demand_by_sku_week.get(key, 0)
            + int(row["forecast_quantity"])
        )

    # Count approved suppliers assigned to each SKU
    suppliers_per_sku = {}

    for row in supplier_skus:

        if int(row["is_approved"]) == 1:

            sku_id = row["sku_id"]

            suppliers_per_sku[sku_id] = (
                suppliers_per_sku.get(sku_id, 0) + 1
            )

    # ------------------------------------------------
    # 2. GENERATE WEEKLY SUPPLIER CAPACITY
    # ------------------------------------------------

    capacity_records = []
    capacity_counter = 1

    for relationship in supplier_skus:

        if int(relationship["is_approved"]) != 1:
            continue

        supplier_id = relationship["supplier_id"]
        sku_id = relationship["sku_id"]

        supplier_number = int(supplier_id.split("-")[-1])

        supplier_count = suppliers_per_sku.get(sku_id, 0)

        if supplier_count == 0:
            raise ValueError(
                f"No approved supplier found for SKU: {sku_id}"
            )

        for week_number in range(1, config["demand_weeks"] + 1):

            forecast_week = (
                f"{config['planning_year']}-W{week_number:02d}"
            )

            total_demand = demand_by_sku_week.get(
                (sku_id, forecast_week), 0
            )

            average_supplier_share = (
                total_demand / supplier_count
            )

            # Every fifth supplier is treated as constrained.
            if supplier_number % 5 == 0:
                capacity_factor = rng.uniform(0.45, 0.70)
            else:
                capacity_factor = rng.uniform(0.85, 1.20)

            maximum_quantity = max(
                1,
                round(average_supplier_share * capacity_factor)
            )

            capacity_records.append({
                "capacity_id": f"CAP-2026-{capacity_counter:06d}",
                "supplier_id": supplier_id,
                "sku_id": sku_id,
                "capacity_week": forecast_week,
                "maximum_quantity": maximum_quantity
            })

            capacity_counter += 1

    # ------------------------------------------------
    # 3. GENERATE SUPPLIER-LOCATION LEAD TIMES
    # ------------------------------------------------

    lead_time_records = []
    lead_time_counter = 1

    for supplier in suppliers:

        supplier_id = supplier["supplier_id"]

        for location in locations:

            location_id = location["location_id"]

            lead_time_records.append({
                "lead_time_id": f"LT-{lead_time_counter:06d}",
                "supplier_id": supplier_id,
                "location_id": location_id,
                "lead_time_days": rng.randint(1, 14),
                "effective_from": f"{config['planning_year']}-01-01",
                "effective_to": ""
            })

            lead_time_counter += 1

    # ------------------------------------------------
    # 4. VALIDATE BEFORE EXPORT
    # ------------------------------------------------

    capacity_ids = [
        row["capacity_id"] for row in capacity_records
    ]

    lead_time_ids = [
        row["lead_time_id"] for row in lead_time_records
    ]

    assert len(capacity_ids) == len(set(capacity_ids))
    assert len(lead_time_ids) == len(set(lead_time_ids))

    valid_supplier_sku_pairs = {
        (row["supplier_id"], row["sku_id"])
        for row in supplier_skus
        if int(row["is_approved"]) == 1
    }

    assert all(
        (row["supplier_id"], row["sku_id"])
        in valid_supplier_sku_pairs
        for row in capacity_records
    )

    assert all(
        row["supplier_id"] in supplier_ids
        and row["location_id"] in location_ids
        for row in lead_time_records
    )

    assert all(
        int(row["maximum_quantity"]) >= 0
        for row in capacity_records
    )

    assert all(
        int(row["lead_time_days"]) >= 0
        for row in lead_time_records
    )

    capacity_keys = [
        (
            row["supplier_id"],
            row["sku_id"],
            row["capacity_week"]
        )
        for row in capacity_records
    ]

    lead_time_keys = [
        (row["supplier_id"], row["location_id"])
        for row in lead_time_records
    ]

    assert len(capacity_keys) == len(set(capacity_keys))
    assert len(lead_time_keys) == len(set(lead_time_keys))

    # ------------------------------------------------
    # 5. EXPORT CSV FILES
    # ------------------------------------------------

    write_csv(
        transaction_dir / "supplier_capacity.csv",
        capacity_records
    )

    write_csv(
        transaction_dir / "lead_time.csv",
        lead_time_records
    )

    # ------------------------------------------------
    # 6. DISPLAY RESULTS
    # ------------------------------------------------

    print("=" * 60)
    print("SUPPLIER CONSTRAINT GENERATION COMPLETED")
    print("=" * 60)

    print(f"Scale: {scale}")
    print(f"Random seed: {config['random_seed'] + 2}")

    print("\nGENERATED RECORD COUNTS")
    print("-" * 60)
    print(f"supplier_capacity.csv: {len(capacity_records)}")
    print(f"lead_time.csv: {len(lead_time_records)}")

    print("\nVALIDATION")
    print("Capacity ID uniqueness: PASSED")
    print("Lead-time ID uniqueness: PASSED")
    print("Approved supplier-SKU relationships: PASSED")
    print("Supplier and location references: PASSED")
    print("Capacity and lead-time values: PASSED")
    print("Duplicate capacity and lead-time checks: PASSED")

    print("\nOUTPUT DIRECTORY")
    print(transaction_dir)

    print("\nDatabase changes: NONE")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Generate supplier capacity and lead-time data."
    )

    parser.add_argument(
        "--scale",
        choices=["starter", "full"],
        default="starter"
    )

    args = parser.parse_args()

    generate_supplier_constraints(args.scale)
