-- Business question: can stakeholders trust the dashboard totals and experiment assignment?
-- Metric definition: zero duplicate keys/FK gaps/crossover and exact fact-to-mart reconciliation.
-- Expected output: one row per check with PASS/FAIL, observed value and expected value.
-- Bytes processed: targeted key columns only; use this mart as the dashboard quality page source.

CREATE OR REPLACE TABLE `sports_product_analytics.mart_data_quality` AS
WITH checks AS (
  SELECT
    'fact_app_events.duplicate_event_id' AS check_name,
    COUNT(*) - COUNT(DISTINCT event_id) AS observed,
    0 AS expected
  FROM `sports_product_analytics.fact_app_events`

  UNION ALL

  SELECT
    'fact_match_events.invalid_xg' AS check_name,
    COUNTIF(shot_xg < 0 OR shot_xg > 1) AS observed,
    0 AS expected
  FROM `sports_product_analytics.fact_match_events`

  UNION ALL

  SELECT
    'app_events.unknown_user' AS check_name,
    COUNTIF(users.user_id IS NULL) AS observed,
    0 AS expected
  FROM `sports_product_analytics.fact_app_events` AS events
  LEFT JOIN `sports_product_analytics.dim_users` AS users
    ON events.user_id = users.user_id

  UNION ALL

  SELECT
    'experiment.variant_crossover' AS check_name,
    COUNTIF(variant_count > 1) AS observed,
    0 AS expected
  FROM (
    SELECT
      user_id,
      experiment_name,
      COUNT(DISTINCT variant) AS variant_count
    FROM `sports_product_analytics.fact_experiment_assignments`
    GROUP BY user_id, experiment_name
  )

  UNION ALL

  SELECT
    'product_daily.revenue_reconciliation' AS check_name,
    CAST(
      ROUND(
        ABS(
          (SELECT SUM(revenue_usd) FROM `sports_product_analytics.fact_app_events`)
          - (SELECT SUM(revenue_usd) FROM `sports_product_analytics.mart_product_daily`)
        )
        * 100
      ) AS INT64
    ) AS observed,
    0 AS expected
)

SELECT
  check_name,
  IF(observed = expected, 'PASS', 'FAIL') AS status,
  observed,
  expected,
  CURRENT_TIMESTAMP() AS checked_at
FROM checks;
