-- Business question: how many intentional product sessions do users create around matches?
-- Metric definition: a new session starts after 30 minutes of inactivity per user.
-- Expected output: one row per derived user session with duration, depth and conversion flags.
-- Bytes processed: inspect with the CLI dry-run; source is partitioned by event_date.

CREATE OR REPLACE TABLE `sports_product_analytics.mart_sessions`
PARTITION BY event_date
CLUSTER BY user_id, match_id AS
WITH ordered_events AS (
  SELECT
    event_id,
    user_id,
    match_id,
    event_name,
    event_ts,
    event_date,
    revenue_usd,
    LAG(event_ts) OVER (
      PARTITION BY user_id
      ORDER BY event_ts, event_id
    ) AS previous_event_ts
  FROM `sports_product_analytics.fact_app_events`
),

session_boundaries AS (
  SELECT
    *,
    IF(
      previous_event_ts IS NULL
      OR TIMESTAMP_DIFF(event_ts, previous_event_ts, MINUTE) > 30,
      1,
      0
    ) AS is_new_session
  FROM ordered_events
),

session_numbers AS (
  SELECT
    *,
    SUM(is_new_session) OVER (
      PARTITION BY user_id
      ORDER BY event_ts, event_id
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS derived_session_number
  FROM session_boundaries
)

SELECT
  CONCAT(user_id, '-', CAST(derived_session_number AS STRING)) AS derived_session_id,
  user_id,
  ANY_VALUE(match_id HAVING MIN event_ts) AS match_id,
  DATE(MIN(event_ts)) AS event_date,
  MIN(event_ts) AS session_started_at,
  MAX(event_ts) AS session_ended_at,
  TIMESTAMP_DIFF(MAX(event_ts), MIN(event_ts), SECOND) AS duration_seconds,
  COUNT(*) AS event_count,
  COUNT(DISTINCT event_name) AS unique_event_types,
  LOGICAL_OR(event_name = 'match_center_view') AS viewed_match_center,
  LOGICAL_OR(event_name = 'highlight_view') AS viewed_highlight,
  LOGICAL_OR(event_name = 'subscription_start') AS converted,
  SUM(revenue_usd) AS net_revenue_usd
FROM session_numbers
GROUP BY user_id, derived_session_number;
