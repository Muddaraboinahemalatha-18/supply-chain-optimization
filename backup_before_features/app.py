
import csv
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from flask import Flask, jsonify, render_template


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data" / "generated" / "full"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "frontend" / "templates"),
    static_folder=str(BASE_DIR / "frontend" / "static"),
    static_url_path="/static"
)


# ============================================================
# CSV HELPERS
# ============================================================

def csv_path(relative_path):
    path = DATA_DIR / relative_path

    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    return path


def read_csv(relative_path):
    path = csv_path(relative_path)

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        yield from csv.DictReader(file)


def count_csv_records(relative_path):
    count = 0

    for _ in read_csv(relative_path):
        count += 1

    return count


def to_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


# ============================================================
# DASHBOARD DATA
# ============================================================

@lru_cache(maxsize=1)
def load_dashboard_data():

    # --------------------------------------------------------
    # 1. MASTER DATA COUNTS
    # --------------------------------------------------------

    total_skus = count_csv_records("master_data/sku.csv")

    total_locations = count_csv_records(
        "master_data/location.csv"
    )

    total_suppliers = count_csv_records(
        "master_data/supplier.csv"
    )

    # --------------------------------------------------------
    # 2. WEEKLY DEMAND AGGREGATION
    # --------------------------------------------------------

    weekly_demand = defaultdict(float)

    for row in read_csv("transactions/forecast_demand.csv"):
        week = row["forecast_week"]

        quantity = to_float(row["forecast_quantity"])

        weekly_demand[week] += quantity

    demand_labels = sorted(weekly_demand.keys())

    demand_values = [
        round(weekly_demand[week], 2)
        for week in demand_labels
    ]

    # --------------------------------------------------------
    # 3. INVENTORY AGGREGATION
    # --------------------------------------------------------

    total_on_hand = 0.0
    total_reserved = 0.0

    for row in read_csv("transactions/inventory.csv"):

        total_on_hand += to_float(
            row["on_hand_quantity"]
        )

        total_reserved += to_float(
            row["reserved_quantity"]
        )

    available_inventory = max(
        0.0,
        total_on_hand - total_reserved
    )

    inventory_chart = {
        "labels": [
            "Available Inventory",
            "Reserved Inventory"
        ],
        "values": [
            round(available_inventory, 2),
            round(total_reserved, 2)
        ]
    }

    # --------------------------------------------------------
    # 4. PROJECTED SHORTAGES
    # --------------------------------------------------------

    shortage_count = 0
    shortage_preview = []

    for row in read_csv("transactions/projected_shortages.csv"):

        shortage_count += 1

        if len(shortage_preview) < 10:
            shortage_preview.append({
                "sku_id": row["sku_id"],
                "location_id": row["location_id"],
                "week": row["shortage_week"],
                "quantity": to_float(
                    row["shortage_quantity"]
                ),
                "status": row["status"]
            })

    # --------------------------------------------------------
    # 5. PRODUCTION SUMMARY
    # --------------------------------------------------------

    total_planned_production = 0.0

    for row in read_csv("transactions/production_plan.csv"):
        total_planned_production += to_float(
            row["planned_quantity"]
        )

    total_production_capacity = 0.0

    for row in read_csv("transactions/production_capacity.csv"):
        total_production_capacity += to_float(
            row["maximum_quantity"]
        )

    # --------------------------------------------------------
    # 6. RETURN DASHBOARD DATA
    # --------------------------------------------------------

    return {
        "metrics": {
            "total_skus": total_skus,
            "total_locations": total_locations,
            "total_suppliers": total_suppliers,
            "total_shortages": shortage_count,
            "total_on_hand": round(total_on_hand, 2),
            "total_reserved": round(total_reserved, 2),
            "available_inventory": round(
                available_inventory, 2
            ),
            "planned_production": round(
                total_planned_production, 2
            ),
            "production_capacity": round(
                total_production_capacity, 2
            )
        },

        "demand_chart": {
            "labels": demand_labels,
            "values": demand_values
        },

        "inventory_chart": inventory_chart,

        "shortages": shortage_preview
    }


# ============================================================
# WEB ROUTES
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/dashboard")
def dashboard_api():

    try:
        data = load_dashboard_data()

        return jsonify({
            "success": True,
            "data": data
        })

    except Exception as error:

        app.logger.exception("Dashboard data loading failed")

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


@app.route("/health")
def health():
    return jsonify({
        "status": "running",
        "application": "Supply Chain Optimization"
    })


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("SUPPLY CHAIN OPTIMIZATION DASHBOARD")
    print("=" * 60)

    print("Starting Flask server...")
    print("Open: http://127.0.0.1:5000")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
