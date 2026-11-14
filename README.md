# Supply Chain Optimization

## 1. Project Overview

The Supply Chain Optimization project is designed to analyze supply and demand, monitor inventory, identify potential shortages, and recommend mitigation options based on supplier capacity, lead times, inventory availability, and production constraints.

The project supports a traceable planning workflow with validation rules, exception detection, shortage projections, and mitigation recommendations.

## 2. Key Features

- Master data generation for SKUs, locations, and suppliers.
- Weekly forecast demand and inventory data generation.
- Supplier capacity and lead-time management.
- Purchase orders and inbound inventory tracking.
- Production planning, BOM, and approved substitute data.
- Weekly inventory projection and shortage identification.
- Mitigation recommendations with feasibility and policy checks.
- Exception scenario detection and ground-truth evaluation.
- CSV, JSON, SQL, and SQLite data storage and exports.
- Independent validation and verification scripts.

## 3. Technology Stack

- Python
- SQLite
- SQL
- CSV and JSON
- Pandas
- Python virtual environment

Additional dependencies are listed in `requirements.txt`.

## 4. Project Structure

```text
supply-chain-optimization/
│
├── config/
│   └── generator_config.py
│
├── data/
│   ├── generated/
│   │   ├── starter/
│   │   └── full/
│   ├── scenarios/
│   ├── exports/
│   └── supply_chain.db
│
├── database/
│   ├── schema.sql
│   ├── connection.py
│   └── migration_*.sql
│
├── docs/
│   ├── data_dictionary.md
│   ├── exception_scenarios_design.md
│   └── other design documents
│
├── scripts/
│   ├── generate_master_data.py
│   ├── generate_demand_inventory.py
│   ├── generate_supplier_constraints.py
│   ├── generate_purchase_inbound.py
│   ├── generate_production_data.py
│   ├── generate_inventory_projection.py
│   ├── generate_mitigation_recommendations.py
│   ├── export_database.py
│   ├── verify_database_exports.py
│   └── validation and evaluation scripts
│
├── README.md
├── SOURCE_MANIFEST.md
├── VALIDATION_SUMMARY.md
└── requirements.txt
```

## 5. Dataset Configuration

The project supports two dataset scales.

| Parameter | Starter | Full |
|---|---:|---:|
| SKUs | 30 | 3,000 |
| Locations | 5 | 50 |
| Suppliers | 10 | 500 |
| Demand weeks | 4 | 52 |
| Inbound orders | 100 | 10,000 |

Random seed: `20261022`

Configuration is maintained in `config/generator_config.py`.

## 6. Installation and Setup

Create and activate a Python virtual environment:

```cmd
python -m venv venv
venv\Scripts\activate
```

Install the project dependencies:

```cmd
pip install -r requirements.txt
```

Run commands from the project root directory.

## 7. Data Generation Workflow

The following commands generate the datasets for the selected scale.

For starter data, use:

```cmd
python scripts/generate_master_data.py --scale starter
python scripts/generate_demand_inventory.py --scale starter
python scripts/generate_supplier_constraints.py --scale starter
python scripts/generate_purchase_inbound.py --scale starter
python scripts/generate_production_data.py --scale starter
```

For full data, use:

```cmd
python scripts/generate_master_data.py --scale full
python scripts/generate_demand_inventory.py --scale full
python scripts/generate_supplier_constraints.py --scale full
python scripts/generate_purchase_inbound.py --scale full
python scripts/generate_production_data.py --scale full
```

Generate weekly inventory projections:

```cmd
python scripts/generate_inventory_projection.py --scale full
```

Generate mitigation recommendations:

```cmd
python scripts/generate_mitigation_recommendations.py --scale full
```

The generated CSV files are stored under:

- `data/generated/starter/`
- `data/generated/full/`

## 8. Validation and Evaluation

The project includes independent validation scripts for inventory projections and mitigation recommendations.

Examples:

```cmd
python scripts/verify_inventory_projection.py --scale full
python scripts/verify_mitigation_recommendations.py --scale full
```

Scenario validation and evaluation:

```cmd
python scripts/validate_exception_scenarios.py
python scripts/validate_valid_scenarios.py
python scripts/validate_combined_ground_truth.py
python scripts/evaluate_combined_scenarios.py
```

The combined scenario evaluation tested five exception scenarios and five valid baseline scenarios. All ten defined test cases passed.

The reported 100% evaluation metrics apply to these ten synthetic test scenarios, not to a broad real-world dataset.

## 9. Database

The project uses SQLite for structured data storage.

Database file:

`data/supply_chain.db`

The live database contains 27 tables, including master data, demand, inventory, supplier constraints, purchase orders, production planning, shortages, mitigation options, and event history.

The original `database/schema.sql` defines the initial schema. Additional tables and columns are introduced through the database migration scripts.

## 10. Database Exports

The project provides the following database exports:

- SQLite: `data/supply_chain.db`
- JSON: `data/exports/supply_chain_database.json`
- SQL: `data/exports/supply_chain_database.sql`

Generate the exports with:

```cmd
python scripts/export_database.py
```

Verify the exports with:

```cmd
python scripts/verify_database_exports.py
```

Independent verification confirmed:

- All 27 table names match.
- Record counts match for all 27 tables.
- The SQL dump was tested in a temporary in-memory database.
- The original database was opened in read-only mode and was not modified.

The JSON and SQL files contain SQLite database records. They are separate from the generated full-scale CSV datasets. Verification compared table names and record counts, not every individual field value.

## 11. Documentation

Additional project documentation is available in the `docs/` directory.

- `docs/data_dictionary.md` describes entities, fields, relationships, and validation rules.
- `SOURCE_MANIFEST.md` describes data sources and generated outputs.
- `VALIDATION_SUMMARY.md` records verification and evaluation results.

## 12. Output Locations

Generated datasets:

- `data/generated/starter/master_data/`
- `data/generated/starter/transactions/`
- `data/generated/full/master_data/`
- `data/generated/full/transactions/`

Scenario data:

- `data/scenarios/`

Database exports:

- `data/exports/`

## 13. Project Objective

The objective is to provide an explainable and traceable supply chain planning workflow that identifies inventory shortages, evaluates available supply and production constraints, and recommends feasible mitigation options while respecting business policies.