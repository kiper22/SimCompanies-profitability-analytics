"""Explicit PySpark schemas for the SimCompanies Gold layer."""

from pyspark.sql.types import (
    DateType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


dim_product_schema = StructType([
    StructField("product_id", IntegerType(), nullable=False),
    StructField("name", StringType(), nullable=False),
    StructField("category", StringType(), nullable=True),
    StructField("transport_unit", DoubleType(), nullable=True),
    StructField("product_api_id", IntegerType(), nullable=True),
    StructField("mapping_status", StringType(), nullable=False),
])

dim_building_schema = StructType([
    StructField("building_id", IntegerType(), nullable=False),
    StructField("name", StringType(), nullable=False),
    StructField("base_wage", DoubleType(), nullable=True),
])

dim_date_schema = StructType([
    StructField("date_key", IntegerType(), nullable=False),
    StructField("date", DateType(), nullable=False),
    StructField("year", IntegerType(), nullable=False),
    StructField("month", IntegerType(), nullable=False),
    StructField("day", IntegerType(), nullable=False),
    StructField("weekday", IntegerType(), nullable=False),
])

bridge_product_recipe_schema = StructType([
    StructField("output_product_id", IntegerType(), nullable=False),
    StructField("input_product_id", IntegerType(), nullable=False),
    StructField("input_quantity", DoubleType(), nullable=False),
])

fact_production_capacity_schema = StructType([
    StructField("product_id", IntegerType(), nullable=False),
    StructField("building_id", IntegerType(), nullable=False),
    StructField("base_units_per_hour", DoubleType(), nullable=False),
])

fact_market_snapshot_schema = StructType([
    StructField("snapshot_id", StringType(), nullable=False),
    StructField("snapshot_timestamp", TimestampType(), nullable=False),
    StructField("product_id", IntegerType(), nullable=False),
    StructField("quality", IntegerType(), nullable=False),
    StructField("kind", IntegerType(), nullable=False),
    StructField("avg_price", DoubleType(), nullable=True),
    StructField("median_price", DoubleType(), nullable=True),
    StructField("min_price", DoubleType(), nullable=True),
    StructField("max_price", DoubleType(), nullable=True),
    StructField("total_quantity", LongType(), nullable=False),
    StructField("offer_count", LongType(), nullable=False),
])
