-- Business question: did Match Center v2 improve subscription conversion without crossover?
-- Metric definition: user-level conversion; two-proportion z score and 95% confidence interval.
-- Expected output: control/treatment rates, absolute lift, relative lift, z score and CI.
-- Bytes processed: one user-level aggregation over app events plus experiment assignments.

CREATE OR REPLACE TABLE `sports_product_analytics.mart_ab_test_match_center_v2` AS
WITH user_outcomes AS (
  SELECT
    assignments.user_id,
    assignments.variant,
    COUNTIF(events.event_name = 'match_center_view') AS match_center_views,
    COUNTIF(events.event_name = 'highlight_view') AS highlight_views,
    LOGICAL_OR(events.event_name = 'subscription_start') AS converted,
    SUM(COALESCE(events.revenue_usd, 0)) AS net_revenue_usd
  FROM `sports_product_analytics.fact_experiment_assignments` AS assignments
  LEFT JOIN
    `sports_product_analytics.fact_app_events` AS events
    ON assignments.user_id = events.user_id
  WHERE assignments.experiment_name = 'match_center_v2'
  GROUP BY assignments.user_id, assignments.variant
),

variant_metrics AS (
  SELECT
    variant,
    COUNT(*) AS users,
    COUNTIF(converted) AS converted_users,
    AVG(CAST(converted AS INT64)) AS conversion_rate,
    AVG(match_center_views) AS avg_match_center_views,
    AVG(highlight_views) AS avg_highlight_views,
    AVG(net_revenue_usd) AS arpu_usd
  FROM user_outcomes
  GROUP BY variant
),

pivoted AS (
  SELECT
    MAX(IF(variant = 'control', users, NULL)) AS control_users,
    MAX(IF(variant = 'treatment', users, NULL)) AS treatment_users,
    MAX(IF(variant = 'control', converted_users, NULL)) AS control_converted,
    MAX(IF(variant = 'treatment', converted_users, NULL)) AS treatment_converted,
    MAX(IF(variant = 'control', conversion_rate, NULL)) AS control_rate,
    MAX(IF(variant = 'treatment', conversion_rate, NULL)) AS treatment_rate,
    MAX(IF(variant = 'control', avg_match_center_views, NULL)) AS control_match_views,
    MAX(IF(variant = 'treatment', avg_match_center_views, NULL)) AS treatment_match_views,
    MAX(IF(variant = 'control', arpu_usd, NULL)) AS control_arpu,
    MAX(IF(variant = 'treatment', arpu_usd, NULL)) AS treatment_arpu
  FROM variant_metrics
),

stats AS (
  SELECT
    *,
    SAFE_DIVIDE(
      control_converted + treatment_converted,
      control_users + treatment_users
    ) AS pooled_rate,
    treatment_rate - control_rate AS absolute_lift
  FROM pivoted
),

standard_error AS (
  SELECT
    *,
    SQRT(
      pooled_rate
      * (1 - pooled_rate)
      * (SAFE_DIVIDE(1, control_users) + SAFE_DIVIDE(1, treatment_users))
    ) AS pooled_standard_error,
    SQRT(
      SAFE_DIVIDE(control_rate * (1 - control_rate), control_users)
      + SAFE_DIVIDE(treatment_rate * (1 - treatment_rate), treatment_users)
    ) AS lift_standard_error
  FROM stats
)

SELECT
  *,
  SAFE_DIVIDE(absolute_lift, control_rate) AS relative_lift,
  SAFE_DIVIDE(absolute_lift, pooled_standard_error) AS z_score,
  absolute_lift - 1.96 * lift_standard_error AS ci_95_lower,
  absolute_lift + 1.96 * lift_standard_error AS ci_95_upper,
  ABS(SAFE_DIVIDE(absolute_lift, pooled_standard_error)) >= 1.96 AS significant_at_95pct
FROM standard_error;
