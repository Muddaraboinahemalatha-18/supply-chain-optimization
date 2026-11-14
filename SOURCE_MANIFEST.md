# Source Manifest – Supply Chain Optimization

## 1. Purpose

This document describes the configuration, source data, generation scripts, generated outputs, and storage formats used in the Supply Chain Optimization project.

## 2. Data Sources

The project uses programmatically generated synthetic data based on documented supply chain rules and relationships.

The generated data includes:

- SKU master data
- Location master data
- Supplier master data
- SKU-location relationships
- Supplier-SKU relationships
- Forecast demand
- Inventory snapshots
- Supplier capacity
- Lead times
- Purchase orders and inbound orders
- Production capacity and production plans
- Bill of materials (BOM)
- Approved substitute relationships
- Weekly inventory projections
- Shortage and mitigation recommendation outputs

Scenario data includes valid baseline cases and deliberately constructed exception cases.

## 3. Configuration

Configuration file:

`config/generator_config.py`

The project uses the following fixed random seed:

`20261022`

| Configuration | Starter | Full |
|---|---:|---:|
| SKU count | 30 | 3,000 |
| Location count | 5 | 50 |
| Supplier count | 10 | 500 |
| Demand weeks | 4 | 52 |
| Inbound orders | 100 | 10,000 |

Other generation rules include three locations per SKU, three suppliers per SKU, and a 10% manufactured SKU target.

## 4. Generation Scripts

The primary data-generation scripts are:

| Script | Purpose |
|---|---|
| `generate_master_data.py` | Generates SKU, location, supplier, and relationship data |
| `generate_demand_inventory.py` | Generates demand forecasts and inventory snapshots |
| `generate_supplier_constraints.py` | Generates supplier capacity and lead-time data |
| `generate_purchase_inbound.py` | Generates purchasing policies, purchase orders, and inbound data |
| `generate_production_data.py` | Generates BOM, substitutes, production capacity, and production plans |
| `generate_inventory_projection.py` | Calculates weekly inventory projections and shortages |
| `generate_mitigation_recommendations.py` | Generates mitigation options and recommendation summaries |

## 5. Generated Output Locations

Starter outputs:

- `data/generated/starter/master_data/`
- `data/generated/starter/transactions/`

Full outputs:

- `data/generated/full/master_data/`
- `data/generated/full/transactions/`

Scenario outputs:

- `data/scenarios/`

## 6. Generated Dataset Contents

The generated datasets include eight master-data CSV files and thirteen transaction-data CSV files for each scale.

Master-data files:

- `sku.csv`
- `location.csv`
- `supplier.csv`
- `sku_location.csv`
- `supplier_sku.csv`
- `supplier_sku_policy.csv`
- `sku_substitute.csv`
- `bom.csv`

Transaction-data files:

- `forecast_demand.csv`
- `inventory.csv`
- `supplier_capacity.csv`
- `lead_time.csv`
- `purchase_order.csv`
- `purchase_order_line.csv`
- `inbound_order.csv`
- `production_capacity.csv`
- `production_plan.csv`
- `weekly_inventory_projection.csv`
- `projected_shortages.csv`
- `mitigation_options.csv`
- `mitigation_summary.csv`

## 7. Scenario Data Sources

Scenario files are stored in `data/scenarios/`.

They include:

- `exception_scenarios.csv`
- `exception_ground_truth.csv`
- `valid_scenarios.csv`
- `combined_ground_truth.csv`
- `combined_detection_results.csv`
- `combined_evaluation_results.csv`
- `exception_detection_results.csv`
- `w47_performance_evaluation.csv`
- Related W47 synthetic capacity input files

The exception cases cover inbound double counting, unapproved substitutes, supplier capacity violations, missing lead times, and unit-of-measure mismatches.

## 8. Reproducibility

The generators use the fixed random seed configured in `config/generator_config.py`.

The starter and full scales use separate output directories to keep their generated files distinct.

Generation scripts accept a scale argument where supported.

Example:

```cmd id="1z89op"
python scripts/generate_master_data.py --scale full
```

## 9. Data Validation

The project includes validation and independent verification scripts for:

- Master-data relationships and record counts
- Demand and inventory data
- Supplier capacity and lead times
- Purchase and inbound data
- Production data
- Weekly inventory projections
- Mitigation recommendations
- Exception scenarios
- Valid baseline scenarios
- Combined ground-truth evaluation

Validation results are documented in `VALIDATION_SUMMARY.md`.

## 10. Data Storage and Export

The project uses the following storage and export formats:

- **CSV:** Generated master-data and transaction-data files.
- **SQLite:** `data/supply_chain.db`
- **JSON:** `data/exports/supply_chain_database.json`
- **SQL:** `data/exports/supply_chain_database.sql`

The SQLite database contains 27 tables.

Independent export verification confirmed:

- All 27 table names match across the original database, JSON export, and SQL export.
- Record counts match for every table.
- The SQL dump was successfully tested in a temporary in-memory database.
- The original database was opened in read-only mode and was not modified.

The JSON and SQL exports contain records from the SQLite database. They are separate from the generated full-scale CSV datasets. Verification compared table names and record counts, not every individual field value.

## 11. Limitations

- The generated datasets are synthetic and do not represent live supplier or customer transactions.
- Evaluation results are based on defined test scenarios and should not be interpreted as proof of real-world predictive accuracy.
- JSON and SQL exports represent the SQLite database contents, not the complete generated CSV datasets.
- Database schema changes are maintained through migration scripts.