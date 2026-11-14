
import sys
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection


SCENARIO_ID = "SYN-W47-001"
PLANNING_WEEK = "2026-W47"

CSV_PATH = (
    BASE_DIR
    / "data"
    / "scenarios"
    / "SYN-W47-001_supplier_capacity.csv"
)

# Conditional purchase quantities from the W47 purchase preview.
# These are the proposed order quantities, not shortage quantities.
PROPOSED_PURCHASES = {
    ("SUP001", "SKU001"): 50.0,
    ("SUP002", "SKU003"): 25.0,
    ("SUP003", "SKU005"): 10.0,
}


def load_synthetic_capacity():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Synthetic capacity CSV not found: {CSV_PATH}"
        )

    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        required_columns = {
            "scenario_id",
            "supplier_id",
            "sku_id",
            "capacity_week",
            "maximum_quantity",
            "unit_of_measure",
            "source_type",
        }

        if not required_columns.issubset(set(reader.fieldnames or [])):
            raise ValueError("CSV is missing one or more required columns.")

        records = list(reader)

    if not records:
        raise ValueError("Synthetic capacity CSV contains no records.")

    return records


def main():
    print("=" * 90)
    print("SYNTHETIC W47 SUPPLIER CAPACITY VALIDATION")
    print("=" * 90)

    print("\nSCENARIO INFORMATION")
    print("-" * 90)
    print("Scenario ID:", SCENARIO_ID)
    print("Planning week:", PLANNING_WEEK)
    print("Source: Synthetic CSV input")
    print("Actual supplier commitment: NOT CLAIMED")
    print("Database modifications: NONE")

    records = load_synthetic_capacity()

    connection = get_connection()

    try:
        print("\nVALIDATION RESULTS")
        print("-" * 90)

        seen_pairs = set()
        valid_count = 0
        invalid_count = 0
        capacity_pass_count = 0
        capacity_fail_count = 0

        for record in records:
            supplier_id = record["supplier_id"].strip()
            sku_id = record["sku_id"].strip()
            scenario_id = record["scenario_id"].strip()
            capacity_week = record["capacity_week"].strip()
            unit = record["unit_of_measure"].strip()
            source_type = record["source_type"].strip()

            try:
                capacity = float(record["maximum_quantity"])
            except (TypeError, ValueError):
                capacity = -1

            print("\nSupplier:", supplier_id)
            print("SKU:", sku_id)
            print("Scenario:", scenario_id)

            errors = []

            pair = (supplier_id, sku_id)

            if scenario_id != SCENARIO_ID:
                errors.append("Incorrect scenario ID")

            if capacity_week != PLANNING_WEEK:
                errors.append("Incorrect planning week")

            if source_type != "SYNTHETIC":
                errors.append("Source type must be SYNTHETIC")

            if capacity < 0:
                errors.append("Capacity must be non-negative")

            if pair in seen_pairs:
                errors.append("Duplicate supplier-SKU capacity record")

            seen_pairs.add(pair)

            supplier = connection.execute("""
                SELECT supplier_name, is_active
                FROM supplier
                WHERE supplier_id = ?
            """, (supplier_id,)).fetchone()

            if supplier is None:
                errors.append("Supplier does not exist")
            elif supplier["is_active"] != 1:
                errors.append("Supplier is inactive")

            sku = connection.execute("""
                SELECT sku_name, unit_of_measure
                FROM sku
                WHERE sku_id = ?
            """, (sku_id,)).fetchone()

            if sku is None:
                errors.append("SKU does not exist")
            elif sku["unit_of_measure"].strip().lower() != unit.lower():
                errors.append("Unit of measure does not match SKU")

            relationship = connection.execute("""
                SELECT is_approved
                FROM supplier_sku
                WHERE supplier_id = ?
                  AND sku_id = ?
            """, (supplier_id, sku_id)).fetchone()

            if relationship is None:
                errors.append("Supplier-SKU relationship does not exist")
            elif relationship["is_approved"] != 1:
                errors.append("Supplier-SKU relationship is not approved")

            if errors:
                invalid_count += 1
                print("Record validation: FAIL")
                for error in errors:
                    print(" -", error)
                continue

            valid_count += 1

            print("Supplier name:", supplier["supplier_name"])
            print("Product:", sku["sku_name"])
            print("Capacity:", capacity, unit)
            print("Record validation: PASS")

            proposed_quantity = PROPOSED_PURCHASES.get(pair)

            if proposed_quantity is None:
                print("Purchase comparison: NO PROPOSAL CONFIGURED")
                continue

            print("Proposed purchase quantity:", proposed_quantity, unit)

            if proposed_quantity <= capacity:
                capacity_pass_count += 1
                print("Capacity validation: PASS")
                print("Remaining synthetic capacity:",
                      capacity - proposed_quantity, unit)
            else:
                capacity_fail_count += 1
                print("Capacity validation: FAIL")
                print("Capacity shortfall:",
                      proposed_quantity - capacity, unit)

        print("\n" + "=" * 90)
        print("SYNTHETIC CAPACITY VALIDATION SUMMARY")
        print("=" * 90)

        print("CSV records:", len(records))
        print("Valid synthetic records:", valid_count)
        print("Invalid synthetic records:", invalid_count)
        print("Purchase capacity checks passed:", capacity_pass_count)
        print("Purchase capacity checks failed:", capacity_fail_count)

        print("\nIMPORTANT INTERPRETATION")
        print("-" * 90)
        print("These results apply only to scenario:", SCENARIO_ID)
        print("They do not establish actual supplier commitments.")
        print("Synthetic capacity is not inserted into supplier_capacity.")
        print("Existing W46 capacity records remain unchanged.")
        print("This script is read-only.")

    finally:
        connection.close()


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError) as error:
        print("\nVALIDATION COULD NOT COMPLETE")
        print("Reason:", error)
