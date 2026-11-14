
RANDOM_SEED = 20261022

GENERATOR_CONFIG = {
    "starter": {
        "sku_count": 30,
        "location_count": 5,
        "supplier_count": 10,
        "demand_weeks": 4,
        "inbound_order_count": 100,
    },
    "full": {
        "sku_count": 3000,
        "location_count": 50,
        "supplier_count": 500,
        "demand_weeks": 52,
        "inbound_order_count": 10000,
    },
}

GENERATION_RULES = {
    "locations_per_sku": 3,
    "suppliers_per_sku": 3,
    "manufactured_sku_percentage": 10,
    "forecast_version": "1",
    "planning_year": 2026,
    "inventory_snapshot_date": "2026-01-01",
}


def get_config(scale):
    if scale not in GENERATOR_CONFIG:
        raise ValueError(
            "Invalid scale. Choose 'starter' or 'full'."
        )

    return {
        **GENERATOR_CONFIG[scale],
        **GENERATION_RULES,
        "random_seed": RANDOM_SEED,
        "scale": scale,
    }
