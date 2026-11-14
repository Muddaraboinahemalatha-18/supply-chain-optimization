
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

MASTER_DIR = BASE_DIR / "data" / "generated" / "master_data"
DATA_DIR = BASE_DIR / "data" / "generated" / "transactions"


def inspect_file(folder, filename, sample_count=3):
    path = folder / filename

    print("\n" + "=" * 70)
    print(filename)
    print("=" * 70)

    with open(path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        print("COLUMNS:")
        print(reader.fieldnames)

        print("\nSAMPLE RECORDS:")

        for index, row in enumerate(reader):
            if index >= sample_count:
                break

            print(row)


files = [
    (MASTER_DIR, "supplier_sku_policy.csv"),
    (DATA_DIR, "supplier_capacity.csv"),
    (DATA_DIR, "lead_time.csv"),
    (MASTER_DIR, "sku_substitute.csv"),
    (DATA_DIR, "production_plan.csv"),
    (DATA_DIR, "production_capacity.csv"),
    (DATA_DIR, "projected_shortages.csv"),
]

for folder, filename in files:
    inspect_file(folder, filename)

print("\n" + "=" * 70)
print("INSPECTION COMPLETED")
print("Database changes: NONE")
