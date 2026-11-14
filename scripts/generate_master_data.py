
import sys
import csv
import random
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from config.generator_config import get_config


def generate_master_data(scale="starter"):

    config = get_config(scale)
    rng = random.Random(config["random_seed"])

    output_dir = (
        BASE_DIR / "data" / "generated" / scale / "master_data"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    sku_count = config["sku_count"]
    location_count = config["location_count"]
    supplier_count = config["supplier_count"]

    locations_per_sku = config["locations_per_sku"]
    suppliers_per_sku = config["suppliers_per_sku"]

    if locations_per_sku > location_count:
        raise ValueError("Not enough locations for SKU assignments.")

    if suppliers_per_sku > supplier_count:
        raise ValueError("Not enough suppliers for SKU assignments.")

    categories = [
        ("Grains", "Kg", 30, 80),
        ("Pulses", "Kg", 60, 150),
        ("Oil", "Liter", 90, 160),
        ("Dairy", "Liter", 35, 90),
        ("Beverages", "Liter", 40, 120),
    ]

    # --------------------------------------------------
    # 1. Generate SKU master data
    # --------------------------------------------------

    skus = []

    for i in range(1, sku_count + 1):

        category, uom, min_cost, max_cost = rng.choice(categories)

        skus.append({
            "sku_id": f"SKU-{i:06d}",
            "sku_name": f"{category} Product {i:06d}",
            "category": category,
            "unit_of_measure": uom,
            "unit_cost": round(rng.uniform(min_cost, max_cost), 2),
            "is_active": 1
        })

    # --------------------------------------------------
    # 2. Generate locations
    # --------------------------------------------------

    cities = [
        ("Hyderabad", "Telangana"),
        ("Vijayawada", "Andhra Pradesh"),
        ("Visakhapatnam", "Andhra Pradesh"),
        ("Bengaluru", "Karnataka"),
        ("Chennai", "Tamil Nadu"),
    ]

    locations = []

    for i in range(1, location_count + 1):

        city, state = cities[(i - 1) % len(cities)]

        locations.append({
            "location_id": f"LOC-{i:06d}",
            "location_name": f"Distribution Center {i:03d}",
            "location_type": "WAREHOUSE",
            "city": city,
            "state": state
        })

    # --------------------------------------------------
    # 3. Generate supplier master data
    # --------------------------------------------------

    suppliers = []

    for i in range(1, supplier_count + 1):

        suppliers.append({
            "supplier_id": f"SUP-{i:06d}",
            "supplier_name": f"Supplier {i:03d}",
            "supplier_type": (
                "MANUFACTURER" if i % 2 == 0 else "DISTRIBUTOR"
            ),
            "reliability_score": round(rng.uniform(0.75, 0.99), 2),
            "is_active": 1
        })

    # --------------------------------------------------
    # 4. Generate SKU-location assignments
    # --------------------------------------------------

    sku_locations = []

    location_ids = [
        location["location_id"] for location in locations
    ]

    for index, sku in enumerate(skus):

        if scale == "full":

            # Full-scale SKUs use rotating location patterns.
            # SKUs assigned to the same pattern share the
            # same location coverage.

            pattern_index = index % location_count

            assigned_locations = [
                location_ids[
                    (pattern_index + offset) % location_count
                ]
                for offset in range(locations_per_sku)
            ]

        else:

            # Preserve the original random assignment for starter.

            assigned_locations = rng.sample(
                location_ids,
                locations_per_sku
            )

        for location_id in assigned_locations:

            sku_locations.append({
                "sku_id": sku["sku_id"],
                "location_id": location_id
            })

    # --------------------------------------------------
    # 5. Generate supplier-SKU relationships
    # --------------------------------------------------

    supplier_skus = []

    supplier_ids = [
        supplier["supplier_id"] for supplier in suppliers
    ]

    for sku in skus:

        assigned_suppliers = rng.sample(
            supplier_ids,
            suppliers_per_sku
        )

        for supplier_id in assigned_suppliers:

            supplier_skus.append({
                "supplier_id": supplier_id,
                "sku_id": sku["sku_id"],
                "is_approved": 1,
                "unit_cost": sku["unit_cost"]
            })

    # --------------------------------------------------
    # 6. Prepare output datasets
    # --------------------------------------------------

    datasets = {
        "sku.csv": skus,
        "location.csv": locations,
        "supplier.csv": suppliers,
        "sku_location.csv": sku_locations,
        "supplier_sku.csv": supplier_skus
    }

    # --------------------------------------------------
    # 7. Export CSV files
    # --------------------------------------------------

    for filename, records in datasets.items():

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

    # --------------------------------------------------
    # 8. Validate generated records
    # --------------------------------------------------

    assert len({row["sku_id"] for row in skus}) == len(skus)
    assert len({row["location_id"] for row in locations}) == len(locations)
    assert len({row["supplier_id"] for row in suppliers}) == len(suppliers)

    valid_sku_ids = {row["sku_id"] for row in skus}
    valid_location_ids = {row["location_id"] for row in locations}
    valid_supplier_ids = {row["supplier_id"] for row in suppliers}

    assert all(
        row["sku_id"] in valid_sku_ids
        and row["location_id"] in valid_location_ids
        for row in sku_locations
    )

    assert all(
        row["sku_id"] in valid_sku_ids
        and row["supplier_id"] in valid_supplier_ids
        for row in supplier_skus
    )

    # Every SKU must have the configured number of locations.

    locations_by_sku = {}

    for row in sku_locations:
        locations_by_sku.setdefault(
            row["sku_id"], set()
        ).add(row["location_id"])

    assert len(locations_by_sku) == sku_count

    assert all(
        len(assigned_locations) == locations_per_sku
        for assigned_locations in locations_by_sku.values()
    )

    # Every configured location must have SKU coverage.

    covered_locations = {
        row["location_id"] for row in sku_locations
    }

    assert covered_locations == valid_location_ids

    # Check duplicate SKU-location and supplier-SKU pairs.

    assert len({
        (row["sku_id"], row["location_id"])
        for row in sku_locations
    }) == len(sku_locations)

    assert len({
        (row["supplier_id"], row["sku_id"])
        for row in supplier_skus
    }) == len(supplier_skus)

    # --------------------------------------------------
    # 9. Display results
    # --------------------------------------------------

    print("=" * 65)
    print("MASTER DATA GENERATION COMPLETED")
    print("=" * 65)

    print(f"Scale: {scale}")
    print(f"Random seed: {config['random_seed']}")

    print("\nGENERATED RECORD COUNTS")
    print("-" * 65)

    for filename, records in datasets.items():
        print(f"{filename}: {len(records)}")

    print("\nSKU-LOCATION ASSIGNMENT")
    print("-" * 65)
    print(f"Locations per SKU: {locations_per_sku}")
    print(f"Locations covered: {len(covered_locations)}")

    if scale == "full":
        print("Assignment strategy: Rotating shared location patterns")
    else:
        print("Assignment strategy: Random location assignment")

    print("\nOUTPUT DIRECTORY")
    print(output_dir)

    print("\nVALIDATION")
    print("-" * 65)
    print("Primary key uniqueness: PASSED")
    print("SKU-location foreign keys: PASSED")
    print("Supplier-SKU foreign keys: PASSED")
    print("SKU location assignment counts: PASSED")
    print("Location coverage: PASSED")
    print("Duplicate relationship checks: PASSED")

    print("\nDatabase changes: NONE")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Generate supply chain master data."
    )

    parser.add_argument(
        "--scale",
        choices=["starter", "full"],
        default="starter"
    )

    args = parser.parse_args()

    generate_master_data(args.scale)
