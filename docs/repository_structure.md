
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
│   ├── repository_structure.md
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
