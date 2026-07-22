-- Business question: which acquisition sources create users who return after signup?
-- Metric definition: retention is active cohort users on exact D1, D7 or D30 / cohort size.
-- Expected output: one row per signup date, channel and platform with cohort retention rates.
-- Bytes processed: dim_users plus distinct user-day activity from partitioned app events.

CREATE OR REPLACE TABLE `sports_product_analytics.mart_retention_cohort`
PARTITION BY cohort_date
CLUSTER BY acquisition_channel, platform AS
WITH cohorts AS (
  SELECT
    user_id,
    signup_date AS cohort_date,
    acquisition_channel,
    platform
  FROM `sports_product_analytics.dim_users`
),

activity AS (
  SELECT DISTINCT
    user_id,
    event_date
  FROM `sports_product_analytics.fact_app_events`
),

cohort_activity AS (
  SELECT
    cohorts.*,
    DATE_DIFF(activity.event_date, cohorts.cohort_date, DAY) AS day_number
  FROM cohorts
  LEFT JOIN activity
    ON
      cohorts.user_id = activity.user_id
      AND cohorts.cohort_date <= activity.event_date
),

aggregated AS (
  SELECT
    cohort_date,
    acquisition_channel,
    platform,
    COUNT(DISTINCT user_id) AS cohort_size,
    COUNT(DISTINCT IF(day_number = 1, user_id, NULL)) AS retained_d1,
    COUNT(DISTINCT IF(day_number = 7, user_id, NULL)) AS retained_d7,
    COUNT(DISTINCT IF(day_number = 30, user_id, NULL)) AS retained_d30
  FROM cohort_activity
  GROUP BY cohort_date, acquisition_channel, platform
)

SELECT
  *,
  SAFE_DIVIDE(retained_d1, cohort_size) AS retention_d1,
  SAFE_DIVIDE(retained_d7, cohort_size) AS retention_d7,
  SAFE_DIVIDE(retained_d30, cohort_size) AS retention_d30,
  1 - SAFE_DIVIDE(retained_d30, cohort_size) AS churn_d30
FROM aggregated;
