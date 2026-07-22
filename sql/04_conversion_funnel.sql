-- Business question: where do fans drop between notification and subscription?
-- Metric definition: ordered user-match funnel using first timestamps for each milestone.
-- Expected output: daily/platform/variant step counts and conversion rates.
-- Bytes processed: selected event_name values from app-event date partitions.

CREATE OR REPLACE TABLE `sports_product_analytics.mart_conversion_funnel`
PARTITION BY funnel_date
CLUSTER BY platform, experiment_variant AS
WITH user_match_steps AS (
  SELECT
    user_id,
    match_id,
    platform,
    experiment_variant,
    MIN(event_ts) AS first_event_at,
    MIN(IF(event_name = 'notification_click', event_ts, NULL)) AS notification_at,
    MIN(IF(event_name = 'match_center_view', event_ts, NULL)) AS match_center_at,
    MIN(IF(event_name = 'highlight_view', event_ts, NULL)) AS highlight_at,
    MIN(IF(event_name = 'subscription_start', event_ts, NULL)) AS subscription_at
  FROM `sports_product_analytics.fact_app_events`
  WHERE
    event_name IN (
      'app_open',
      'notification_click',
      'match_center_view',
      'highlight_view',
      'subscription_start'
    )
  GROUP BY user_id, match_id, platform, experiment_variant
),

ordered_steps AS (
  SELECT
    *,
    notification_at IS NOT NULL AS reached_notification,
    match_center_at > notification_at AS reached_match_center,
    match_center_at > notification_at
    AND highlight_at > match_center_at AS reached_highlight,
    match_center_at > notification_at
    AND highlight_at > match_center_at
    AND subscription_at > highlight_at AS reached_subscription
  FROM user_match_steps
)

SELECT
  DATE(first_event_at) AS funnel_date,
  platform,
  experiment_variant,
  COUNT(*) AS user_match_journeys,
  COUNTIF(reached_notification) AS notification_users,
  COUNTIF(reached_match_center) AS match_center_users,
  COUNTIF(reached_highlight) AS highlight_users,
  COUNTIF(reached_subscription) AS subscription_users,
  SAFE_DIVIDE(COUNTIF(reached_match_center), COUNTIF(reached_notification))
    AS notification_to_match,
  SAFE_DIVIDE(COUNTIF(reached_highlight), COUNTIF(reached_match_center)) AS match_to_highlight,
  SAFE_DIVIDE(COUNTIF(reached_subscription), COUNTIF(reached_highlight))
    AS highlight_to_subscription,
  SAFE_DIVIDE(COUNTIF(reached_subscription), COUNT(*)) AS end_to_end_conversion
FROM ordered_steps
GROUP BY funnel_date, platform, experiment_variant;
