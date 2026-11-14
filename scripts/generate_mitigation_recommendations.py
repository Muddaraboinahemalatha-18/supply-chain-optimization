import argparse
import csv
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


# ============================================================
# PATHS AND CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# These paths are selected from the required --scale argument in main().
MASTER_DIR = None
TRANSACTION_DIR = None

SNAPSHOT_DATE = date(2026, 1, 1)

OPTIONS_FILE = None
SUMMARY_FILE = None


# ============================================================
# CSV HELPERS
# ============================================================

def read_csv(file_path):
    if not file_path.exists():
        raise FileNotFoundError(
            f"Required input file not found: {file_path}"
        )

    with open(file_path, "r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def write_csv(file_path, rows, fieldnames):
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )

        writer.writeheader()
        writer.writerows(rows)


def to_float(value, default=0.0):
    if value is None or str(value).strip() == "":
        return default

    return float(value)


def to_int(value, default=0):
    if value is None or str(value).strip() == "":
        return default

    return int(float(value))


def is_true(value):
    return str(value).strip().upper() in {
        "1", "TRUE", "YES", "Y", "APPROVED"
    }


def parse_date(value):
    if not value:
        return None

    return datetime.strptime(value, "%Y-%m-%d").date()


def is_effective(record, check_date):
    effective_from = parse_date(record.get("effective_from"))
    effective_to = parse_date(record.get("effective_to"))

    if effective_from is None:
        return False

    if check_date < effective_from:
        return False

    if effective_to is not None and check_date > effective_to:
        return False

    return True


def get_week_start(week_value):
    """
    Convert a value such as 2026-W03 into its Monday date.
    """

    year_text, week_text = week_value.split("-W")

    return date.fromisocalendar(
        int(year_text),
        int(week_text),
        1
    )


def get_iso_week(check_date):
    iso = check_date.isocalendar()

    return f"{iso.year}-W{iso.week:02d}"


def round_quantity(value):
    return round(float(value), 6)


# ============================================================
# INPUT FILES
# ============================================================

def load_inputs():

    sku_rows = read_csv(MASTER_DIR / "sku.csv")
    supplier_sku_rows = read_csv(MASTER_DIR / "supplier_sku.csv")
    policy_file = MASTER_DIR / "supplier_sku_policy.csv"
    if not policy_file.exists():
        policy_file = TRANSACTION_DIR / "supplier_sku_policy.csv"

    substitute_file = MASTER_DIR / "sku_substitute.csv"
    if not substitute_file.exists():
        substitute_file = TRANSACTION_DIR / "sku_substitute.csv"

    policy_rows = read_csv(policy_file)
    substitute_rows = read_csv(substitute_file)

    capacity_rows = read_csv(
        TRANSACTION_DIR / "supplier_capacity.csv"
    )

    lead_time_rows = read_csv(
        TRANSACTION_DIR / "lead_time.csv"
    )

    purchase_order_rows = read_csv(
        TRANSACTION_DIR / "purchase_order.csv"
    )

    purchase_order_line_rows = read_csv(
        TRANSACTION_DIR / "purchase_order_line.csv"
    )

    shortage_rows = read_csv(
        TRANSACTION_DIR / "projected_shortages.csv"
    )

    projection_rows = read_csv(
        TRANSACTION_DIR / "weekly_inventory_projection.csv"
    )

    return {
        "skus": sku_rows,
        "supplier_sku": supplier_sku_rows,
        "policies": policy_rows,
        "substitutes": substitute_rows,
        "capacities": capacity_rows,
        "lead_times": lead_time_rows,
        "purchase_orders": purchase_order_rows,
        "purchase_order_lines": purchase_order_line_rows,
        "shortages": shortage_rows,
        "projections": projection_rows,
    }


# ============================================================
# INDEX SOURCE RECORDS
# ============================================================

def build_indexes(data):

    sku_by_id = {
        row["sku_id"]: row
        for row in data["skus"]
    }

    approved_relationships = defaultdict(list)

    for row in data["supplier_sku"]:
        approved_relationships[row["sku_id"]].append(row)

    policies_by_supplier_sku = defaultdict(list)

    for row in data["policies"]:
        key = (row["supplier_id"], row["sku_id"])
        policies_by_supplier_sku[key].append(row)

    lead_times_by_supplier_location = defaultdict(list)

    for row in data["lead_times"]:
        key = (row["supplier_id"], row["location_id"])
        lead_times_by_supplier_location[key].append(row)

    capacities_by_supplier_sku_week = {}

    for row in data["capacities"]:
        key = (
            row["supplier_id"],
            row["sku_id"],
            row["capacity_week"]
        )

        capacities_by_supplier_sku_week[key] = row

    substitutes_by_original_sku = defaultdict(list)

    for row in data["substitutes"]:
        substitutes_by_original_sku[
            row["original_sku_id"]
        ].append(row)

    projections_by_sku_location_week = {}

    for row in data["projections"]:
        key = (
            row["sku_id"],
            row["location_id"],
            row["forecast_week"]
        )

        projections_by_sku_location_week[key] = row

    return {
        "sku_by_id": sku_by_id,
        "approved_relationships": approved_relationships,
        "policies": policies_by_supplier_sku,
        "lead_times": lead_times_by_supplier_location,
        "capacities": capacities_by_supplier_sku_week,
        "substitutes": substitutes_by_original_sku,
        "projections": projections_by_sku_location_week,
    }


# ============================================================
# EXISTING PURCHASE ORDER CAPACITY CONSUMPTION
# ============================================================

def calculate_existing_ordered_quantities(data):

    purchase_orders_by_id = {
        row["po_id"]: row
        for row in data["purchase_orders"]
    }

    existing_quantities = defaultdict(float)

    joined_line_count = 0

    for line in data["purchase_order_lines"]:

        po_id = line["po_id"]

        if po_id not in purchase_orders_by_id:
            continue

        purchase_order = purchase_orders_by_id[po_id]

        supplier_id = purchase_order["supplier_id"]
        sku_id = line["sku_id"]

        order_date = parse_date(
            purchase_order["order_date"]
        )

        if order_date is None:
            continue

        order_week = get_iso_week(order_date)

        quantity = to_float(
            line["order_quantity"]
        )

        key = (
            supplier_id,
            sku_id,
            order_week
        )

        # Count all existing order quantities.
        # Do not subtract only unreceived quantities:
        # the PO already consumed capacity in its order week.
        existing_quantities[key] += quantity

        joined_line_count += 1

    return existing_quantities, joined_line_count


# ============================================================
# POLICY AND LEAD-TIME LOOKUPS
# ============================================================

def find_active_policy(
    supplier_id,
    sku_id,
    check_date,
    policies_index
):

    key = (supplier_id, sku_id)

    candidates = [
        row
        for row in policies_index.get(key, [])
        if is_effective(row, check_date)
    ]

    if not candidates:
        return None

    candidates.sort(
        key=lambda row: row["effective_from"],
        reverse=True
    )

    return candidates[0]


def find_active_lead_time(
    supplier_id,
    location_id,
    check_date,
    lead_time_index
):

    key = (supplier_id, location_id)

    candidates = [
        row
        for row in lead_time_index.get(key, [])
        if is_effective(row, check_date)
    ]

    if not candidates:
        return None

    candidates.sort(
        key=lambda row: row["effective_from"],
        reverse=True
    )

    return candidates[0]


# ============================================================
# OPTION OUTPUT STRUCTURE
# ============================================================

OPTION_FIELDS = [
    "option_id",
    "shortage_id",
    "projection_id",
    "forecast_id",
    "sku_id",
    "location_id",
    "shortage_week",
    "option_type",
    "supplier_id",
    "policy_id",
    "capacity_id",
    "lead_time_id",
    "substitute_id",
    "substitute_sku_id",
    "unit_of_measure",
    "shortage_quantity",
    "proposed_quantity",
    "equivalent_original_quantity",
    "uncovered_shortage_quantity",
    "minimum_order_quantity",
    "unit_cost",
    "estimated_cost",
    "capacity_week",
    "existing_ordered_quantity",
    "maximum_capacity",
    "remaining_capacity_before_option",
    "capacity_source",
    "lead_time_days",
    "planned_order_date",
    "expected_arrival_date",
    "required_arrival_date",
    "conversion_factor",
    "substitute_surplus_before_option",
    "is_primary_recommendation",
    "rule_check_status",
    "feasibility_status",
    "decision_reason",
    "assumptions",
]


SUMMARY_FIELDS = [
    "shortage_id",
    "projection_id",
    "forecast_id",
    "sku_id",
    "location_id",
    "shortage_week",
    "shortage_quantity",
    "unit_of_measure",
    "primary_option_id",
    "primary_option_type",
    "proposed_quantity",
    "equivalent_original_quantity",
    "uncovered_shortage_quantity",
    "estimated_cost",
    "feasibility_status",
    "decision_reason",
]


# ============================================================
# SUPPLIER PURCHASE OPTION
# ============================================================

def build_supplier_option(
    shortage,
    relationship,
    indexes,
    existing_quantities,
    remaining_capacity,
    option_number
):

    supplier_id = relationship["supplier_id"]
    sku_id = shortage["sku_id"]
    location_id = shortage["location_id"]

    shortage_quantity = to_float(
        shortage["shortage_quantity"]
    )

    shortage_week = shortage["shortage_week"]

    required_arrival_date = get_week_start(
        shortage_week
    )

    # A purchase must arrive by the beginning of the shortage week.
    # This is a conservative weekly-planning assumption.

    option = {
        "option_id": f"MIT-{shortage['shortage_id']}-{option_number:02d}",
        "shortage_id": shortage["shortage_id"],
        "projection_id": shortage["projection_id"],
        "forecast_id": shortage["forecast_id"],
        "sku_id": sku_id,
        "location_id": location_id,
        "shortage_week": shortage_week,
        "option_type": "SUPPLIER_PURCHASE",
        "supplier_id": supplier_id,
        "policy_id": "",
        "capacity_id": "",
        "lead_time_id": "",
        "substitute_id": "",
        "substitute_sku_id": "",
        "unit_of_measure": shortage["unit_of_measure"],
        "shortage_quantity": round_quantity(shortage_quantity),
        "proposed_quantity": 0,
        "equivalent_original_quantity": 0,
        "uncovered_shortage_quantity": round_quantity(
            shortage_quantity
        ),
        "minimum_order_quantity": "",
        "unit_cost": "",
        "estimated_cost": 0,
        "capacity_week": "",
        "existing_ordered_quantity": 0,
        "maximum_capacity": 0,
        "remaining_capacity_before_option": 0,
        "capacity_source": "SYNTHETIC",
        "lead_time_days": "",
        "planned_order_date": "",
        "expected_arrival_date": "",
        "required_arrival_date": required_arrival_date.isoformat(),
        "conversion_factor": "",
        "substitute_surplus_before_option": "",
        "is_primary_recommendation": 0,
        "rule_check_status": "FAIL",
        "feasibility_status": "BLOCKED",
        "decision_reason": "",
        "assumptions": (
            "Synthetic supplier capacity is not a confirmed commitment. "
            "Alternatives are mutually exclusive."
        ),
    }

    reasons = []

    # --------------------------------------------------------
    # 1. Supplier-SKU approval
    # --------------------------------------------------------

    if not is_true(relationship.get("is_approved")):
        reasons.append("Supplier-SKU relationship is not approved")

    # --------------------------------------------------------
    # 2. Lead time and planned order date
    # --------------------------------------------------------

    lead_time_reference_date = required_arrival_date

    lead_time_row = find_active_lead_time(
        supplier_id,
        location_id,
        lead_time_reference_date,
        indexes["lead_times"]
    )

    if lead_time_row is None:
        # For a required order date before the planning snapshot,
        # try the snapshot date for explanatory lead-time metadata.
        lead_time_row = find_active_lead_time(
            supplier_id,
            location_id,
            SNAPSHOT_DATE,
            indexes["lead_times"]
        )

    planned_order_date = None
    lead_time_days = None

    if lead_time_row is None:
        reasons.append(
            "No effective supplier-location lead-time record"
        )

    else:
        lead_time_days = to_int(
            lead_time_row["lead_time_days"]
        )

        option["lead_time_id"] = lead_time_row["lead_time_id"]
        option["lead_time_days"] = lead_time_days

        planned_order_date = (
            required_arrival_date
            - timedelta(days=lead_time_days)
        )

        option["planned_order_date"] = (
            planned_order_date.isoformat()
        )

        option["expected_arrival_date"] = (
            planned_order_date
            + timedelta(days=lead_time_days)
        ).isoformat()

        if planned_order_date < SNAPSHOT_DATE:
            reasons.append(
                "Required order date is before the planning snapshot"
            )

    # --------------------------------------------------------
    # 3. Policy effective date, MOQ and unit cost
    # --------------------------------------------------------

    policy_check_date = SNAPSHOT_DATE

    if planned_order_date is not None:
        policy_check_date = max(
            planned_order_date,
            SNAPSHOT_DATE
        )

    policy = find_active_policy(
        supplier_id,
        sku_id,
        policy_check_date,
        indexes["policies"]
    )

    if policy is None:
        reasons.append(
            "No effective supplier-SKU purchasing policy"
        )

    else:
        option["policy_id"] = policy["policy_id"]

        moq = to_float(
            policy["minimum_order_quantity"]
        )

        unit_cost = to_float(
            policy["unit_cost"]
        )

        option["minimum_order_quantity"] = moq
        option["unit_cost"] = round_quantity(unit_cost)

        if moq <= 0:
            reasons.append("Invalid minimum order quantity")

        if unit_cost < 0:
            reasons.append("Invalid supplier unit cost")

    # --------------------------------------------------------
    # 4. Capacity in planned purchase order week
    # --------------------------------------------------------

    if planned_order_date is not None:

        capacity_week = get_iso_week(
            planned_order_date
        )

        option["capacity_week"] = capacity_week

        capacity_key = (
            supplier_id,
            sku_id,
            capacity_week
        )

        capacity_row = indexes["capacities"].get(
            capacity_key
        )

        if capacity_row is None:
            reasons.append(
                "No supplier capacity record for planned order week"
            )

        else:
            capacity_id = capacity_row["capacity_id"]

            maximum_capacity = to_float(
                capacity_row["maximum_quantity"]
            )

            existing_key = capacity_key

            existing_quantity = existing_quantities.get(
                existing_key,
                0.0
            )

            if capacity_key not in remaining_capacity:
                remaining_capacity[capacity_key] = max(
                    0.0,
                    maximum_capacity - existing_quantity
                )

            available_capacity = remaining_capacity[
                capacity_key
            ]

            option["capacity_id"] = capacity_id
            option["maximum_capacity"] = round_quantity(
                maximum_capacity
            )
            option["existing_ordered_quantity"] = (
                round_quantity(existing_quantity)
            )
            option["remaining_capacity_before_option"] = (
                round_quantity(available_capacity)
            )

            if maximum_capacity < 0:
                reasons.append("Invalid supplier capacity")

    # --------------------------------------------------------
    # 5. Calculate MOQ-compliant quantity
    # --------------------------------------------------------

    if not reasons:

        required_quantity = (
            math.ceil(shortage_quantity / moq) * moq
        )

        maximum_orderable_quantity = (
            math.floor(
                (available_capacity + 0.0000001) / moq
            ) * moq
        )

        proposed_quantity = min(
            required_quantity,
            maximum_orderable_quantity
        )

        proposed_quantity = round_quantity(
            proposed_quantity
        )

        if proposed_quantity <= 0:
            reasons.append(
                "Remaining supplier capacity is below the MOQ"
            )

        else:
            uncovered_quantity = max(
                0.0,
                shortage_quantity - proposed_quantity
            )

            estimated_cost = (
                proposed_quantity * unit_cost
            )

            option["proposed_quantity"] = proposed_quantity
            option["equivalent_original_quantity"] = (
                proposed_quantity
            )
            option["uncovered_shortage_quantity"] = (
                round_quantity(uncovered_quantity)
            )
            option["estimated_cost"] = round_quantity(
                estimated_cost
            )

    # --------------------------------------------------------
    # 6. Final rule status
    # --------------------------------------------------------

    if reasons:
        option["rule_check_status"] = "FAIL"
        option["feasibility_status"] = "BLOCKED"
        option["decision_reason"] = "; ".join(reasons)

    else:
        option["rule_check_status"] = "PASS"
        option["feasibility_status"] = "CONDITIONAL"

        if option["uncovered_shortage_quantity"] > 0:
            option["decision_reason"] = (
                "Partial MOQ-compliant quantity available. "
                "Remaining shortage is not covered. "
                "Capacity is synthetic and requires supplier confirmation."
            )
        else:
            option["decision_reason"] = (
                "Approval, policy, lead time, MOQ and capacity checks passed. "
                "Capacity is synthetic and requires supplier confirmation."
            )

    return option


# ============================================================
# APPROVED SUBSTITUTE OPTION
# ============================================================

def build_substitute_option(
    shortage,
    substitute,
    indexes,
    remaining_substitute_surplus,
    option_number
):

    original_sku_id = shortage["sku_id"]
    substitute_sku_id = substitute["substitute_sku_id"]
    location_id = shortage["location_id"]
    shortage_week = shortage["shortage_week"]

    shortage_quantity = to_float(
        shortage["shortage_quantity"]
    )

    required_arrival_date = get_week_start(
        shortage_week
    )

    option = {
        "option_id": f"MIT-{shortage['shortage_id']}-{option_number:02d}",
        "shortage_id": shortage["shortage_id"],
        "projection_id": shortage["projection_id"],
        "forecast_id": shortage["forecast_id"],
        "sku_id": original_sku_id,
        "location_id": location_id,
        "shortage_week": shortage_week,
        "option_type": "APPROVED_SUBSTITUTE",
        "supplier_id": "",
        "policy_id": "",
        "capacity_id": "",
        "lead_time_id": "",
        "substitute_id": substitute["substitute_id"],
        "substitute_sku_id": substitute_sku_id,
        "unit_of_measure": shortage["unit_of_measure"],
        "shortage_quantity": round_quantity(shortage_quantity),
        "proposed_quantity": 0,
        "equivalent_original_quantity": 0,
        "uncovered_shortage_quantity": round_quantity(
            shortage_quantity
        ),
        "minimum_order_quantity": "",
        "unit_cost": "",
        "estimated_cost": 0,
        "capacity_week": "",
        "existing_ordered_quantity": "",
        "maximum_capacity": "",
        "remaining_capacity_before_option": "",
        "capacity_source": "EXISTING_PROJECTED_STOCK",
        "lead_time_days": 0,
        "planned_order_date": "",
        "expected_arrival_date": required_arrival_date.isoformat(),
        "required_arrival_date": required_arrival_date.isoformat(),
        "conversion_factor": substitute.get(
            "conversion_factor", ""
        ),
        "substitute_surplus_before_option": 0,
        "is_primary_recommendation": 0,
        "rule_check_status": "FAIL",
        "feasibility_status": "BLOCKED",
        "decision_reason": "",
        "assumptions": (
            "Conversion factor means substitute units required "
            "per one original SKU unit. Existing projected surplus "
            "is used only once by a selected primary recommendation."
        ),
    }

    reasons = []

    # --------------------------------------------------------
    # 1. Substitute approval and effective dates
    # --------------------------------------------------------

    if not is_true(substitute.get("is_approved")):
        reasons.append("Substitute relationship is not approved")

    if not is_effective(
        substitute,
        required_arrival_date
    ):
        reasons.append(
            "Substitute relationship is not effective for shortage week"
        )

    # --------------------------------------------------------
    # 2. Substitute SKU and UOM checks
    # --------------------------------------------------------

    original_sku = indexes["sku_by_id"].get(
        original_sku_id
    )

    substitute_sku = indexes["sku_by_id"].get(
        substitute_sku_id
    )

    if original_sku is None:
        reasons.append("Original SKU record not found")

    if substitute_sku is None:
        reasons.append("Substitute SKU record not found")

    if original_sku and substitute_sku:

        original_uom = original_sku["unit_of_measure"]
        substitute_uom = substitute_sku["unit_of_measure"]

        if original_uom != substitute_uom:
            reasons.append(
                "Original and substitute SKU units of measure do not match"
            )

        if original_uom != shortage["unit_of_measure"]:
            reasons.append(
                "Shortage unit of measure does not match original SKU"
            )

        substitute_unit_cost = to_float(
            substitute_sku.get("unit_cost")
        )

        option["unit_cost"] = round_quantity(
            substitute_unit_cost
        )

    # --------------------------------------------------------
    # 3. Conversion factor
    # --------------------------------------------------------

    conversion_factor = to_float(
        substitute.get("conversion_factor")
    )

    if conversion_factor <= 0:
        reasons.append("Invalid substitute conversion factor")

    # --------------------------------------------------------
    # 4. Substitute projected surplus
    # --------------------------------------------------------

    projection_key = (
        substitute_sku_id,
        location_id,
        shortage_week
    )

    substitute_projection = indexes[
        "projections"
    ].get(projection_key)

    if substitute_projection is None:
        reasons.append(
            "No substitute SKU projection for the same location and week"
        )

    else:
        projected_surplus = max(
            0.0,
            to_float(
                substitute_projection.get(
                    "ending_available_balance"
                )
            )
        )

        if projection_key not in remaining_substitute_surplus:
            remaining_substitute_surplus[
                projection_key
            ] = projected_surplus

        available_surplus = remaining_substitute_surplus[
            projection_key
        ]

        option["substitute_surplus_before_option"] = (
            round_quantity(available_surplus)
        )

    # --------------------------------------------------------
    # 5. Calculate substitute quantity
    # --------------------------------------------------------

    if not reasons:

        required_substitute_quantity = (
            shortage_quantity * conversion_factor
        )

        proposed_substitute_quantity = min(
            required_substitute_quantity,
            available_surplus
        )

        proposed_substitute_quantity = round_quantity(
            proposed_substitute_quantity
        )

        if proposed_substitute_quantity <= 0:
            reasons.append(
                "No available substitute surplus after its own forecast demand"
            )

        else:
            equivalent_original_quantity = (
                proposed_substitute_quantity
                / conversion_factor
            )

            uncovered_quantity = max(
                0.0,
                shortage_quantity - equivalent_original_quantity
            )

            estimated_cost = (
                proposed_substitute_quantity
                * substitute_unit_cost
            )

            option["proposed_quantity"] = (
                proposed_substitute_quantity
            )

            option["equivalent_original_quantity"] = (
                round_quantity(equivalent_original_quantity)
            )

            option["uncovered_shortage_quantity"] = (
                round_quantity(uncovered_quantity)
            )

            option["estimated_cost"] = round_quantity(
                estimated_cost
            )

    # --------------------------------------------------------
    # 6. Final rule status
    # --------------------------------------------------------

    if reasons:
        option["rule_check_status"] = "FAIL"
        option["feasibility_status"] = "BLOCKED"
        option["decision_reason"] = "; ".join(reasons)

    else:
        option["rule_check_status"] = "PASS"

        if option["uncovered_shortage_quantity"] > 0:
            option["feasibility_status"] = "CONDITIONAL"
            option["decision_reason"] = (
                "Approved substitute has only partial projected surplus. "
                "Remaining shortage is not covered."
            )
        else:
            option["feasibility_status"] = "FEASIBLE"
            option["decision_reason"] = (
                "Approved substitute, effective dates, UOM, "
                "conversion factor and projected surplus checks passed."
            )

    return option


# ============================================================
# SELECT ONE PRIMARY OPTION PER SHORTAGE
# ============================================================

def choose_primary_option(candidate_options):

    feasible_options = [
        option
        for option in candidate_options
        if (
            option["rule_check_status"] == "PASS"
            and to_float(option["proposed_quantity"]) > 0
        )
    ]

    if not feasible_options:
        return None

    def option_score(option):

        uncovered = to_float(
            option["uncovered_shortage_quantity"]
        )

        cost = to_float(
            option["estimated_cost"]
        )

        arrival = option.get("expected_arrival_date") or "9999-12-31"

        option_type = option["option_type"]

        supplier_id = option.get("supplier_id") or ""

        substitute_id = option.get("substitute_sku_id") or ""

        return (
            uncovered,
            cost,
            arrival,
            option_type,
            supplier_id,
            substitute_id
        )

    feasible_options.sort(key=option_score)

    return feasible_options[0]


# ============================================================
# MAIN GENERATION
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Generate scale-specific supply-chain mitigation recommendations."
    )
    parser.add_argument(
        "--scale",
        choices=("starter", "full"),
        required=True,
        help="Dataset scale to process (starter or full).",
    )
    args = parser.parse_args()

    global MASTER_DIR, TRANSACTION_DIR, OPTIONS_FILE, SUMMARY_FILE

    scale_dir = BASE_DIR / "data" / "generated" / args.scale
    MASTER_DIR = scale_dir / "master_data"
    TRANSACTION_DIR = scale_dir / "transactions"
    OPTIONS_FILE = TRANSACTION_DIR / "mitigation_options.csv"
    SUMMARY_FILE = TRANSACTION_DIR / "mitigation_summary.csv"

    print("=" * 76)
    print("MITIGATION RECOMMENDATION GENERATION")
    print("Scale:", args.scale)
    print("Input directory:", scale_dir)
    print("=" * 76)

    print("\n1. LOADING INPUT FILES")

    data = load_inputs()

    print("SKU records:", len(data["skus"]))
    print("Supplier-SKU relationships:", len(data["supplier_sku"]))
    print("Supplier policies:", len(data["policies"]))
    print("Supplier capacity records:", len(data["capacities"]))
    print("Lead-time records:", len(data["lead_times"]))
    print("Purchase orders:", len(data["purchase_orders"]))
    print("Purchase order lines:", len(data["purchase_order_lines"]))
    print("Approved substitute source records:", len(data["substitutes"]))
    print("Projected shortage records:", len(data["shortages"]))
    print("Weekly projection records:", len(data["projections"]))

    print("\n2. BUILDING SOURCE INDEXES")

    indexes = build_indexes(data)

    existing_quantities, joined_line_count = (
        calculate_existing_ordered_quantities(data)
    )

    print(
        "Purchase order lines successfully joined:",
        joined_line_count
    )

    # Remaining capacity is initialized lazily for each
    # supplier + SKU + planned order week.
    remaining_capacity = {}

    # Substitute stock is initialized lazily for each
    # substitute SKU + location + week.
    remaining_substitute_surplus = {}

    shortages = sorted(
        data["shortages"],
        key=lambda row: (
            row["shortage_week"],
            row["sku_id"],
            row["location_id"]
        )
    )

    all_options = []
    summary_rows = []

    primary_count = 0
    no_option_count = 0

    total_primary_cost = 0.0
    total_primary_equivalent_quantity = 0.0
    total_uncovered_quantity = 0.0

    print("\n3. GENERATING OPTIONS")

    for shortage in shortages:

        candidate_options = []
        option_number = 1

        sku_id = shortage["sku_id"]

        # ----------------------------------------------------
        # Supplier purchase candidates
        # ----------------------------------------------------

        relationships = indexes[
            "approved_relationships"
        ].get(sku_id, [])

        for relationship in sorted(
            relationships,
            key=lambda row: row["supplier_id"]
        ):

            option = build_supplier_option(
                shortage,
                relationship,
                indexes,
                existing_quantities,
                remaining_capacity,
                option_number
            )

            candidate_options.append(option)
            option_number += 1

        # ----------------------------------------------------
        # Approved substitute candidates
        # ----------------------------------------------------

        substitutes = indexes[
            "substitutes"
        ].get(sku_id, [])

        for substitute in sorted(
            substitutes,
            key=lambda row: row["substitute_id"]
        ):

            option = build_substitute_option(
                shortage,
                substitute,
                indexes,
                remaining_substitute_surplus,
                option_number
            )

            candidate_options.append(option)
            option_number += 1

        # ----------------------------------------------------
        # Choose one primary option
        # ----------------------------------------------------

        primary = choose_primary_option(
            candidate_options
        )

        if primary is not None:

            primary["is_primary_recommendation"] = 1

            primary_count += 1

            primary_quantity = to_float(
                primary["proposed_quantity"]
            )

            primary_equivalent_quantity = to_float(
                primary["equivalent_original_quantity"]
            )

            primary_cost = to_float(
                primary["estimated_cost"]
            )

            # Reserve only the selected primary option.
            # Other alternatives remain unreserved.

            if primary["option_type"] == "SUPPLIER_PURCHASE":

                capacity_key = (
                    primary["supplier_id"],
                    primary["sku_id"],
                    primary["capacity_week"]
                )

                remaining_capacity[capacity_key] = max(
                    0.0,
                    remaining_capacity[capacity_key]
                    - primary_quantity
                )

            elif primary["option_type"] == "APPROVED_SUBSTITUTE":

                substitute_key = (
                    primary["substitute_sku_id"],
                    primary["location_id"],
                    primary["shortage_week"]
                )

                remaining_substitute_surplus[
                    substitute_key
                ] = max(
                    0.0,
                    remaining_substitute_surplus[
                        substitute_key
                    ] - primary_quantity
                )

            total_primary_cost += primary_cost

            total_primary_equivalent_quantity += (
                primary_equivalent_quantity
            )

            # Mark all other passing options as alternatives.
            for option in candidate_options:

                if option is primary:
                    continue

                if (
                    option["rule_check_status"] == "PASS"
                    and to_float(option["proposed_quantity"]) > 0
                ):
                    option["feasibility_status"] = (
                        "ALTERNATIVE_NOT_RESERVED"
                    )

                    option["decision_reason"] += (
                        " This is an alternative, not an allocation. "
                        "It is mutually exclusive with the primary option "
                        "and must be rechecked before selection."
                    )

            summary_status = primary["feasibility_status"]

            summary_reason = primary["decision_reason"]

            primary_option_id = primary["option_id"]

            primary_option_type = primary["option_type"]

            proposed_quantity = primary_quantity

            equivalent_quantity = primary_equivalent_quantity

            uncovered_quantity = to_float(
                primary["uncovered_shortage_quantity"]
            )

            estimated_cost = primary_cost

        else:

            no_option_count += 1

            summary_status = "NO_FEASIBLE_OPTION"

            summary_reason = (
                "No supplier purchase or approved substitute option "
                "passed the required feasibility checks."
            )

            primary_option_id = ""
            primary_option_type = ""
            proposed_quantity = 0
            equivalent_quantity = 0

            uncovered_quantity = to_float(
                shortage["shortage_quantity"]
            )

            estimated_cost = 0

        total_uncovered_quantity += uncovered_quantity

        # Store every candidate, including blocked candidates.
        all_options.extend(candidate_options)

        summary_rows.append({
            "shortage_id": shortage["shortage_id"],
            "projection_id": shortage["projection_id"],
            "forecast_id": shortage["forecast_id"],
            "sku_id": shortage["sku_id"],
            "location_id": shortage["location_id"],
            "shortage_week": shortage["shortage_week"],
            "shortage_quantity": shortage["shortage_quantity"],
            "unit_of_measure": shortage["unit_of_measure"],
            "primary_option_id": primary_option_id,
            "primary_option_type": primary_option_type,
            "proposed_quantity": round_quantity(
                proposed_quantity
            ),
            "equivalent_original_quantity": round_quantity(
                equivalent_quantity
            ),
            "uncovered_shortage_quantity": round_quantity(
                uncovered_quantity
            ),
            "estimated_cost": round_quantity(
                estimated_cost
            ),
            "feasibility_status": summary_status,
            "decision_reason": summary_reason,
        })

    # ========================================================
    # WRITE OUTPUT FILES
    # ========================================================

    print("\n4. WRITING OUTPUT FILES")

    write_csv(
        OPTIONS_FILE,
        all_options,
        OPTION_FIELDS
    )

    write_csv(
        SUMMARY_FILE,
        summary_rows,
        SUMMARY_FIELDS
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    print("\n5. VALIDATION")

    option_ids = [
        row["option_id"]
        for row in all_options
    ]

    summary_shortage_ids = [
        row["shortage_id"]
        for row in summary_rows
    ]

    primary_rows = [
        row for row in all_options
        if to_int(row["is_primary_recommendation"]) == 1
    ]

    primary_count_by_shortage = defaultdict(int)

    for row in primary_rows:
        primary_count_by_shortage[
            row["shortage_id"]
        ] += 1

    one_primary_max = all(
        count <= 1
        for count in primary_count_by_shortage.values()
    )

    all_shortages_in_summary = (
        len(summary_rows) == len(shortages)
        and len(set(summary_shortage_ids)) == len(shortages)
    )

    unique_option_ids = (
        len(option_ids) == len(set(option_ids))
    )

    # Verify selected supplier primary quantities do not exceed
    # capacity remaining after existing POs.

    supplier_primary_allocations = defaultdict(float)

    for row in primary_rows:

        if row["option_type"] != "SUPPLIER_PURCHASE":
            continue

        key = (
            row["supplier_id"],
            row["sku_id"],
            row["capacity_week"]
        )

        supplier_primary_allocations[key] += to_float(
            row["proposed_quantity"]
        )

    supplier_capacity_check = True

    for key, allocated_quantity in supplier_primary_allocations.items():

        capacity_row = indexes["capacities"].get(key)

        if capacity_row is None:
            supplier_capacity_check = False
            continue

        maximum_capacity = to_float(
            capacity_row["maximum_quantity"]
        )

        existing_quantity = existing_quantities.get(
            key,
            0.0
        )

        available_capacity = max(
            0.0,
            maximum_capacity - existing_quantity
        )

        if allocated_quantity > available_capacity + 0.000001:
            supplier_capacity_check = False

    # Verify selected substitute primary quantities do not exceed
    # the original projected surplus.

    substitute_primary_allocations = defaultdict(float)

    for row in primary_rows:

        if row["option_type"] != "APPROVED_SUBSTITUTE":
            continue

        key = (
            row["substitute_sku_id"],
            row["location_id"],
            row["shortage_week"]
        )

        substitute_primary_allocations[key] += to_float(
            row["proposed_quantity"]
        )

    substitute_stock_check = True

    for key, allocated_quantity in substitute_primary_allocations.items():

        projection = indexes["projections"].get(key)

        if projection is None:
            substitute_stock_check = False
            continue

        projected_surplus = max(
            0.0,
            to_float(
                projection.get("ending_available_balance")
            )
        )

        if allocated_quantity > projected_surplus + 0.000001:
            substitute_stock_check = False

    # Every selected supplier option must satisfy MOQ.
    moq_check = True

    for row in primary_rows:

        if row["option_type"] != "SUPPLIER_PURCHASE":
            continue

        moq = to_float(
            row["minimum_order_quantity"]
        )

        quantity = to_float(
            row["proposed_quantity"]
        )

        if moq <= 0 or quantity + 0.000001 < moq:
            moq_check = False

    # Supplier purchase recommendations must have a planned order
    # date on or after the planning snapshot.
    lead_time_check = True

    for row in primary_rows:

        if row["option_type"] != "SUPPLIER_PURCHASE":
            continue

        planned_date = parse_date(
            row["planned_order_date"]
        )

        expected_date = parse_date(
            row["expected_arrival_date"]
        )

        required_date = parse_date(
            row["required_arrival_date"]
        )

        if (
            planned_date is None
            or expected_date is None
            or required_date is None
            or planned_date < SNAPSHOT_DATE
            or expected_date > required_date
        ):
            lead_time_check = False

    print(
        "Option ID uniqueness:",
        "PASSED" if unique_option_ids else "FAILED"
    )

    print(
        "One primary recommendation maximum per shortage:",
        "PASSED" if one_primary_max else "FAILED"
    )

    print(
        "All shortages represented in summary:",
        "PASSED" if all_shortages_in_summary else "FAILED"
    )

    print(
        "Primary supplier capacity allocation:",
        "PASSED" if supplier_capacity_check else "FAILED"
    )

    print(
        "Primary substitute stock allocation:",
        "PASSED" if substitute_stock_check else "FAILED"
    )

    print(
        "Primary supplier MOQ compliance:",
        "PASSED" if moq_check else "FAILED"
    )

    print(
        "Primary supplier lead-time checks:",
        "PASSED" if lead_time_check else "FAILED"
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    supplier_option_count = sum(
        1 for row in all_options
        if row["option_type"] == "SUPPLIER_PURCHASE"
    )

    substitute_option_count = sum(
        1 for row in all_options
        if row["option_type"] == "APPROVED_SUBSTITUTE"
    )

    blocked_option_count = sum(
        1 for row in all_options
        if row["feasibility_status"] == "BLOCKED"
    )

    alternative_option_count = sum(
        1 for row in all_options
        if row["feasibility_status"] == "ALTERNATIVE_NOT_RESERVED"
    )

    print("\n6. GENERATION SUMMARY")

    print("Shortages processed:", len(shortages))
    print("Total options generated:", len(all_options))
    print("Supplier purchase options:", supplier_option_count)
    print("Approved substitute options:", substitute_option_count)
    print("Primary recommendations:", primary_count)
    print("Alternative options not reserved:", alternative_option_count)
    print("Blocked options:", blocked_option_count)
    print("Shortages without a feasible option:", no_option_count)

    print(
        "Total primary recommended cost:",
        round(total_primary_cost, 2)
    )

    print(
        "Total primary equivalent quantity:",
        round(total_primary_equivalent_quantity, 2)
    )

    print(
        "Total uncovered shortage quantity:",
        round(total_uncovered_quantity, 2)
    )

    print("\nOUTPUT FILES")
    print(OPTIONS_FILE)
    print(SUMMARY_FILE)

    print("\nDATABASE CHANGES: NONE")
    print("SOURCE CSV FILES MODIFIED: NONE")

    all_checks_passed = all([
        unique_option_ids,
        one_primary_max,
        all_shortages_in_summary,
        supplier_capacity_check,
        substitute_stock_check,
        moq_check,
        lead_time_check,
    ])

    print("\n" + "=" * 76)

    if all_checks_passed:
        print("MITIGATION RECOMMENDATION GENERATION COMPLETED")
        print("ALL VALIDATION CHECKS PASSED")
    else:
        print("MITIGATION GENERATION COMPLETED WITH VALIDATION FAILURES")
        print("Review the failed checks before proceeding.")

    print("=" * 76)


if __name__ == "__main__":
    main()