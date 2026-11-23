# SimCompanies Production Analytics

An end-to-end data engineering and business intelligence portfolio project focused on analysing the in-game market and evaluating production profitability in **SimCompanies**.

The project collects market snapshots, prepares and models the data with Python and local PySpark, and uses Power BI to explore historical prices, production costs and profitability across products, quality levels and production buildings.

> **Project status:** The first two Power BI report views are implemented: **Production Profitability** and **Profitability Table**. Data coverage and the wider project documentation are still being refined.

## Project objectives

The goal is to turn separate market and production data into a model that can help answer questions such as:

- Which products and quality levels offer the most attractive production returns?
- How do market prices change between snapshots?
- How does the selected production building affect production capacity and labour cost?
- Which recipe ingredients contribute most to the total production cost?
- Is the current market price high enough to cover the estimated cost of production?

## Data pipeline

The project follows an end-to-end workflow:

1. **Market data collection** – market information is collected through a browser-based workflow that captures responses from the game's market interface/API.
2. **Reference data preparation** – product, building, recipe and production-capacity information is used to describe the available products and production processes.
3. **Transformation** – Python and local PySpark are used to prepare, standardise and transform the collected and reference data.
4. **Data modelling** – market snapshots and production-related entities are organised for analytical use.
5. **Business intelligence** – Power BI combines the model with DAX measures to calculate and visualise production costs and profitability.


## Data and analytical model

The model combines two main areas of information.

### Market data

Market observations are stored as snapshots for products and quality levels. The available market metrics include:

- Minimum and maximum listed price
- Average and median price
- Total listed quantity
- Number of offers
- Snapshot date/time

This makes it possible to analyse both individual market states and changes over time.

### Production data

Reference data describes products, production buildings, recipes and production capacity. These inputs are used to estimate the cost and output rate of manufacturing a product.

The production-cost calculation includes:

- **Ingredient cost** – required recipe quantities multiplied by eligible market prices.
- **Labour cost** – building wage allocated across the production capacity for the selected product and building.
- **Total production cost per unit** – ingredient cost plus labour cost.

The model also considers ingredient availability. A product is not treated as currently producible when required market inputs cannot be priced from the available market data or when the required production option is unavailable in the selected context.

## Power BI report

The current report contains two implemented views.

### 1. Production Profitability

A product-level view showing the economics of producing one selected product at a selected quality and production building.

It includes:

- Product and production-building images
- Production availability status
- Profit per unit and profit per hour
- Margin and production rate (units per hour)
- Current market price and production cost
- Cost breakdown by ingredient and labour
- Historical market-price analysis, with selectable price metrics

### 2. Profitability Table

A comparative view for exploring product and quality combinations.

It supports filtering by category, quality and production building, and comparing profitability metrics such as production cost, market price, profit per unit, margin and profit per hour.

### Dashboard screenshots

Dashoboard will be extended to company and midifiers management
![alt text](<docs/Zrzut ekranu 2026-11-23 115346.jpg>)
![alt text](<docs/Zrzut ekranu 2026-11-23 114540.jpg>)
![alt text](<docs/Zrzut ekranu 2026-11-23 114410.jpg>)
## Key calculations

The main profitability measures are based on the following logic:

| Metric | Meaning |
|---|---|
| Production Cost / Unit | Ingredient cost plus labour cost per produced unit |
| Profit / Unit | Selected market sale price minus production cost per unit |
| Profit / Hour | Profit per unit multiplied by production units per hour |
| Margin | Profit per unit relative to the selected market sale price |
| Production Availability | Whether the selected product has a valid production option and its required ingredients can be priced |

Current profitability calculations use the latest available eligible market prices. Historical market snapshots are used separately for price-trend analysis.

## Technology stack

| Area | Technologies |
|---|---|
| Data collection | Python, browser automation with Playwright and Firefox, market interface/API response capture |
| Data transformation | Python, PySpark (local execution) |
| Reference data | Excel workbooks |
| Analytics and reporting | Microsoft Power BI, Power Query (M), DAX |
| Version control | Git / GitHub |

## Repository structure

The repository is organised around the data pipeline, analytical model and Power BI report. The `data/` directory contains local source data, intermediate datasets, analytical outputs and downloaded images; its contents are not included in the public repository.

```text
SimCompanies/
├── data/                               # Local data; excluded from Git
│   ├── bronze/
│   │   └── market/
│   │       └── offers/
│   ├── gold/
│   │   ├── bridge_product_recipe/
│   │   ├── dim_building/
│   │   ├── dim_date/
│   │   ├── dim_product/
│   │   ├── fact_market_snapshot/
│   │   └── fact_production_capacity/
│   ├── images/
│   │   ├── buildings/
│   │   ├── buildings _oryginal_size/
│   │   └── products/
│   ├── market/
│   ├── processed/
│   ├── silver/
│   │   └── market/
│   │       └── snapshot_id=20261104T130919Z/
│   └── source/
├── docs/
│   ├── architecture.md
│   ├── data_dictionary.md
│   └── todo.md
├── power_bi/
│   └── Dashboard.pbix
├── src/
│   ├── app/
│   │   └── app.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── download_images.py
│   │   ├── download_images_products.py
│   │   └── market_collector.py
│   ├── simcompanies/
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── gold.py
│   │   └── __init__.py
│   └── transformation/
│       ├── bronze_to_silver.ipynb
│       ├── map_images.ipynb
│       ├── map_images.py
│       ├── product_mapping.ipynb
│       └── silver_to_gold.ipynb
├── .gitignore
├── README.md
└── requirements.txt
```

The tree lists directories only under `data/` to document the local data layout without publishing individual datasets or image assets. It lists tracked project files outside `data/` to show the implementation.

## Data availability and reproducibility

Raw market snapshots, local reference workbooks and downloaded image assets are intentionally **not included** in this repository. The `.gitignore` is configured to keep the local `data/` directory out of version control.

As a result, the repository documents the project code and approach, but a complete refresh of the report requires the corresponding local source data and configuration. Detailed setup and execution instructions will be added after the ingestion and transformation entry points, dependencies and configuration are finalised.

## Current scope and limitations

- The project is designed for local PySpark execution; it does not currently require a managed Spark platform.
- Market-derived calculations depend on the snapshots available locally and their collection timestamps.
- Production profitability depends on recipe completeness, available ingredient prices and production-capacity reference data.
- Some products or recipes may be missing or incomplete in the current reference data. These cases should be interpreted as coverage gaps rather than proof that production is impossible in the game.
- The dashboard is an analytical tool for the SimCompanies game economy; it is not a real-world financial or investment model.

## License and third-party content

The repository contains project code and documentation. Game data, names, logos and image assets may be subject to the rights and terms of their respective owners. No ownership of SimCompanies or its underlying game assets is claimed. Any public release of third-party assets should be reviewed against the applicable terms before inclusion.

---

*This README describes the current project scope. Dashboard screenshots, exact run instructions and dependency versions can be added as the repository is prepared for public release.*
