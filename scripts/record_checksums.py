
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "generated"
OUTPUT_FILE = BASE_DIR / "CHECKSUMS_SHA256.txt"

def calculate_sha256(file_path):
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


records = []

for scale in ("starter", "full"):
    scale_dir = DATA_DIR / scale

    if not scale_dir.exists():
        raise FileNotFoundError(scale_dir)

    for file_path in sorted(scale_dir.rglob("*")):
        if file_path.is_file():
            digest = calculate_sha256(file_path)
            relative_path = file_path.relative_to(BASE_DIR)

            records.append(f"{digest}  {relative_path}")

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    file.write("\n".join(records) + "\n")

print("SHA-256 CHECKSUM RECORDING")
print("==========================")
print("Files recorded:", len(records))
print("Manifest:", OUTPUT_FILE.name)
print("PASS: Existing generated files were hashed.")
print("Original generated files were not modified.")
