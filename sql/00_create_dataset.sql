-- Purpose: create the analytics namespace once before loading Parquet tables.
-- Location is selected by the CLI/API because dataset location cannot be parameterized here.
CREATE SCHEMA IF NOT EXISTS `sports_product_analytics`;
