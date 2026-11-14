
import sys
import csv
import math
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
        records = list(csv.DictReader(file))

    if not records:
        raise ValueError(f"Input CSV is empty: {file_path}")

    return records


def write_csv(file_path, records):
    if not records:
        raise ValueError(f"No records generated for {file_path}")

    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(records[0].keys())
        )
        writer.writeheader()
        writer.writerows(records)


def check_bom_cycles(bom_records):
    graph = {}

    for row in bom_records:
        graph.setdefault(row["parent_sku_id"], []).append(
            row["component_sku_id"]
        )

    visiting = set()
    visited = set()

    def visit(sku_id):
        if sku_id in visiting:
            raise ValueError(
                f"BOM cycle detected involving {sku_id}"
            )

        if sku_id in visited:
            return

        visiting.add(sku_id)

        for component_id in graph.get(sku_id, []):
            visit(component_id)

        visiting.remove(sku_id)
        visited.add(sku_id)

    for sku_id in graph:
        visit(sku_id)


def generate_production_data(scale="starter"):

    config = get_config(scale)
    rng = random.Random(config["random_seed"] + 4)

    # Use scale-specific directories.
    master_dir = (
        BASE_DIR / "data" / "generated" / scale / "master_data"
    )

    transaction_dir = (
        BASE_DIR / "data" / "generated" / scale / "transactions"
    )

    master_dir.mkdir(parents=True, exist_ok=True)
    transaction_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------
    # 1. Read scale-specific input data
    # --------------------------------------------------

    skus = read_csv(master_dir / "sku.csv")
    sku_locations = read_csv(master_dir / "sku_location.csv")
    forecasts = read_csv(transaction_dir / "forecast_demand.csv")

    sku_lookup = {row["sku_id"]: row for row in skus}
    valid_sku_ids = set(sku_lookup)

    if len(sku_lookup) != len(skus):
        raise ValueError("Duplicate SKU IDs found.")

    # --------------------------------------------------
    # 2. Prepare SKU-location and forecast lookups
    # --------------------------------------------------

    locations_by_sku = {}

    for row in sku_locations:
        sku_id = row["sku_id"]
        location_id = row["location_id"]

        if sku_id not in valid_sku_ids:
            raise ValueError(
                f"Unknown SKU in sku_location: {sku_id}"
            )

        locations_by_sku.setdefault(sku_id, set()).add(location_id)

    if set(locations_by_sku) != valid_sku_ids:
        raise ValueError(
            "Some SKUs do not have SKU-location assignments."
        )

    forecast_lookup = {}
    forecasts_by_sku = {}

    for row in forecasts:
        key = (
            row["sku_id"],
            row["location_id"],
            row["forecast_week"]
        )

        if key in forecast_lookup:
            raise ValueError(
                f"Duplicate forecast record: {key}"
            )

        if row["sku_id"] not in valid_sku_ids:
            raise ValueError(
                f"Unknown forecast SKU: {row['sku_id']}"
            )

        if row["location_id"] not in locations_by_sku.get(
            row["sku_id"], set()
        ):
            raise ValueError(
                f"Invalid forecast SKU-location: {key}"
            )

        quantity = float(row["forecast_quantity"])

        if not math.isfinite(quantity) or quantity < 0:
            raise ValueError(
                f"Invalid forecast quantity: {key}"
            )

        forecast_lookup[key] = quantity

        forecasts_by_sku.setdefault(
            row["sku_id"], []
        ).append((key, quantity))

    # --------------------------------------------------
    # 3. Find manufactured SKUs with valid BOM coverage
    # --------------------------------------------------

    manufactured_percentage = config["manufactured_sku_percentage"]

    manufactured_count = max(
        1,
        round(len(skus) * manufactured_percentage / 100)
    )

    component_options = {}

    if scale == "full":

        # Full-scale master data uses shared rotating
        # location patterns. Group by UOM and exact
        # location coverage to avoid an O(SKU x SKU)
        # candidate search.

        sku_groups = {}

        for sku_id in sorted(valid_sku_ids):

            group_key = (
                sku_lookup[sku_id]["unit_of_measure"],
                frozenset(locations_by_sku.get(sku_id, set()))
            )

            sku_groups.setdefault(group_key, []).append(sku_id)

        for group_key, group_skus in sku_groups.items():

            if len(group_skus) >= 3:

                for parent_sku_id in group_skus:

                    candidates = [
                        sku_id
                        for sku_id in group_skus
                        if sku_id != parent_sku_id
                    ]

                    if len(candidates) >= 2:
                        component_options[parent_sku_id] = candidates

    else:

        # Preserve the original starter behavior:
        # components may cover the same or more locations
        # than their parent SKU.

        for parent_sku_id in sorted(valid_sku_ids):

            parent_uom = sku_lookup[parent_sku_id][
                "unit_of_measure"
            ]

            parent_locations = locations_by_sku.get(
                parent_sku_id, set()
            )

            candidates = [
                component_sku_id
                for component_sku_id in sorted(valid_sku_ids)
                if component_sku_id != parent_sku_id
                and sku_lookup[component_sku_id][
                    "unit_of_measure"
                ] == parent_uom
                and parent_locations.issubset(
                    locations_by_sku.get(component_sku_id, set())
                )
            ]

            if len(candidates) >= 2:
                component_options[parent_sku_id] = candidates

    # Prefer parents with more valid component choices.

    ordered_parents = sorted(
        component_options,
        key=lambda sku_id: (
            -len(component_options[sku_id]),
            sku_id
        )
    )

    manufactured_skus = set()
    reserved_component_ids = set()
    selected_components = {}

    for parent_sku_id in ordered_parents:

        if len(manufactured_skus) >= manufactured_count:
            break

        if parent_sku_id in reserved_component_ids:
            continue

        available_components = [
            component_id
            for component_id in component_options[parent_sku_id]
            if component_id not in manufactured_skus
        ]

        if len(available_components) < 2:
            continue

        chosen_components = rng.sample(
            available_components,
            2
        )

        manufactured_skus.add(parent_sku_id)
        selected_components[parent_sku_id] = chosen_components
        reserved_component_ids.update(chosen_components)

    if len(manufactured_skus) != manufactured_count:
        raise ValueError(
            "Could not select enough manufactured SKUs with "
            "two valid components covering all production locations. "
            f"Required: {manufactured_count}, "
            f"Selected: {len(manufactured_skus)}. "
            "Review SKU categories and location assignments."
        )

    # --------------------------------------------------
    # 4. Generate BOM records
    # --------------------------------------------------

    bom_records = []
    bom_counter = 1

    for parent_sku_id in sorted(manufactured_skus):

        for component_sku_id in selected_components[parent_sku_id]:

            bom_records.append({
                "bom_id": f"BOM-2026-{bom_counter:06d}",
                "parent_sku_id": parent_sku_id,
                "component_sku_id": component_sku_id,
                "component_quantity": round(
                    rng.uniform(0.5, 2.0), 2
                )
            })

            bom_counter += 1

    # --------------------------------------------------
    # 5. Generate production capacity and plans
    # --------------------------------------------------

    capacity_records = []
    production_records = []

    capacity_counter = 1
    production_counter = 1

    for sku_id in sorted(manufactured_skus):

        sku_forecasts = forecasts_by_sku.get(sku_id, [])

        if not sku_forecasts:
            raise ValueError(
                f"No forecast found for manufactured SKU {sku_id}"
            )

        for key, demand_quantity in sorted(sku_forecasts):

            forecast_sku, location_id, production_week = key

            planned_quantity = demand_quantity
            maximum_quantity = math.ceil(
                demand_quantity * 1.20
            )

            capacity_records.append({
                "production_capacity_id":
                    f"PCAP-2026-{capacity_counter:06d}",
                "sku_id": forecast_sku,
                "location_id": location_id,
                "production_week": production_week,
                "maximum_quantity": maximum_quantity
            })

            production_records.append({
                "production_id":
                    f"PROD-2026-{production_counter:06d}",
                "sku_id": forecast_sku,
                "location_id": location_id,
                "production_week": production_week,
                "planned_quantity": planned_quantity
            })

            capacity_counter += 1
            production_counter += 1

    # --------------------------------------------------
    # 6. Generate approved substitute relationships
    # --------------------------------------------------

    substitute_records = []
    substitute_counter = 1

    substitute_originals = sorted(valid_sku_ids)
    rng.shuffle(substitute_originals)

    substitute_count = max(
        1,
        round(len(skus) * 0.10)
    )

    used_pairs = set()

    for original_sku_id in substitute_originals:

        if len(substitute_records) >= substitute_count:
            break

        original_uom = sku_lookup[original_sku_id][
            "unit_of_measure"
        ]

        candidates = [
            sku_id
            for sku_id in valid_sku_ids
            if sku_id != original_sku_id
            and sku_lookup[sku_id]["unit_of_measure"] == original_uom
            and tuple(sorted(
                (original_sku_id, sku_id)
            )) not in used_pairs
        ]

        if not candidates:
            continue

        substitute_sku_id = rng.choice(sorted(candidates))

        pair = tuple(sorted(
            (original_sku_id, substitute_sku_id)
        ))

        used_pairs.add(pair)

        substitute_records.append({
            "substitute_id": f"SUB-2026-{substitute_counter:06d}",
            "original_sku_id": original_sku_id,
            "substitute_sku_id": substitute_sku_id,
            "is_approved": 1,
            "conversion_factor": 1.0,
            "effective_from": config["inventory_snapshot_date"],
            "effective_to": ""
        })

        substitute_counter += 1

    if len(substitute_records) != substitute_count:
        raise ValueError(
            "Could not generate the requested number of "
            "substitute records."
        )

    # --------------------------------------------------
    # 7. Validate generated records
    # --------------------------------------------------

    assert len({
        r["bom_id"] for r in bom_records
    }) == len(bom_records)

    assert len({
        r["production_capacity_id"] for r in capacity_records
    }) == len(capacity_records)

    assert len({
        r["production_id"] for r in production_records
    }) == len(production_records)

    assert len({
        r["substitute_id"] for r in substitute_records
    }) == len(substitute_records)

    # BOM foreign keys and component rules.

    assert all(
        r["parent_sku_id"] in valid_sku_ids
        and r["component_sku_id"] in valid_sku_ids
        and r["parent_sku_id"] != r["component_sku_id"]
        and float(r["component_quantity"]) > 0
        for r in bom_records
    )

    assert all(
        sku_lookup[r["parent_sku_id"]]["unit_of_measure"]
        == sku_lookup[r["component_sku_id"]]["unit_of_measure"]
        for r in bom_records
    )

    # Every component must cover every parent location.

    assert all(
        locations_by_sku[r["parent_sku_id"]].issubset(
            locations_by_sku[r["component_sku_id"]]
        )
        for r in bom_records
    )

    # A manufactured SKU cannot be used as a component.

    assert not any(
        r["component_sku_id"] in manufactured_skus
        for r in bom_records
    )

    check_bom_cycles(bom_records)

    # Production capacity and plan reconciliation.

    capacity_lookup = {
        (
            r["sku_id"],
            r["location_id"],
            r["production_week"]
        ): float(r["maximum_quantity"])
        for r in capacity_records
    }

    assert len(capacity_lookup) == len(capacity_records)

    assert all(
        r["sku_id"] in manufactured_skus
        and r["location_id"] in locations_by_sku[r["sku_id"]]
        and float(r["maximum_quantity"]) >= 0
        for r in capacity_records
    )

    assert all(
        (
            r["sku_id"],
            r["location_id"],
            r["production_week"]
        ) in capacity_lookup
        and 0 <= float(r["planned_quantity"])
        <= capacity_lookup[
            (
                r["sku_id"],
                r["location_id"],
                r["production_week"]
            )
        ]
        for r in production_records
    )

    # Substitute foreign keys and policy checks.

    assert all(
        r["original_sku_id"] in valid_sku_ids
        and r["substitute_sku_id"] in valid_sku_ids
        and r["original_sku_id"] != r["substitute_sku_id"]
        and r["is_approved"] in (0, 1)
        and float(r["conversion_factor"]) > 0
        for r in substitute_records
    )

    assert all(
        sku_lookup[r["original_sku_id"]]["unit_of_measure"]
        == sku_lookup[r["substitute_sku_id"]]["unit_of_measure"]
        for r in substitute_records
    )

    # --------------------------------------------------
    # 8. Export CSV files
    # --------------------------------------------------

    write_csv(master_dir / "bom.csv", bom_records)
    write_csv(master_dir / "sku_substitute.csv", substitute_records)

    write_csv(
        transaction_dir / "production_capacity.csv",
        capacity_records
    )

    write_csv(
        transaction_dir / "production_plan.csv",
        production_records
    )

    # --------------------------------------------------
    # 9. Display results
    # --------------------------------------------------

    print("=" * 65)
    print("PRODUCTION DATA GENERATION COMPLETED")
    print("=" * 65)

    print(f"Scale: {scale}")
    print(f"Random seed: {config['random_seed'] + 4}")

    print("\nGENERATED RECORD COUNTS")
    print("-" * 65)
    print(f"Manufactured SKUs: {len(manufactured_skus)}")
    print(f"Bill of Materials: {len(bom_records)}")
    print(f"SKU substitutes: {len(substitute_records)}")
    print(f"Production capacity: {len(capacity_records)}")
    print(f"Production plans: {len(production_records)}")

    print("\nVALIDATION")
    print("-" * 65)
    print("SKU and location references: PASSED")
    print("BOM component references: PASSED")
    print("BOM component location coverage: PASSED")
    print("BOM quantity and unit checks: PASSED")
    print("BOM cycle detection: PASSED")
    print("Production capacity checks: PASSED")
    print("Production plan capacity checks: PASSED")
    print("Substitute relationship checks: PASSED")
    print("Primary key uniqueness: PASSED")

    print("\nOUTPUT DIRECTORIES")
    print(master_dir)
    print(transaction_dir)

    print("\nDatabase changes: NONE")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Generate production and BOM data."
    )

    parser.add_argument(
        "--scale",
        choices=["starter", "full"],
        default="starter"
    )

    args = parser.parse_args()

    generate_production_data(args.scale)
