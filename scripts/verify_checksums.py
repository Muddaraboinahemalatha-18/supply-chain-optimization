
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFEST = BASE_DIR / "CHECKSUMS_SHA256.txt"

def calculate_sha256(file_path):
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


passed = 0
failed = 0

with open(MANIFEST, encoding="utf-8") as file:
    records = [line.strip() for line in file if line.strip()]

for record in records:
    expected_hash, relative_path = record.split("  ", 1)
    file_path = BASE_DIR / relative_path

    if not file_path.is_file():
        print("MISSING:", relative_path)
        failed += 1
        continue

    actual_hash = calculate_sha256(file_path)

    if actual_hash == expected_hash:
        passed += 1
    else:
        print("MISMATCH:", relative_path)
        failed += 1

print("\nSHA-256 VERIFICATION")
print("====================")
print("Total:", len(records))
print("Passed:", passed)
print("Failed:", failed)

if failed == 0:
    print("PASS: All file checksums match.")
else:
    print("FAIL: Checksum verification found issues.")
    raise SystemExit(1)
