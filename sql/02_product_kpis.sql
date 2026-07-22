-- Business question: is the sports product growing with healthy recurring engagement?
-- Metric definition: DAU is distinct active users that day; MAU is the trailing 30-day users.
-- Expected output: daily DAU/MAU, stickiness, sessions, subscriptions, revenue and ARPU.
-- Bytes processed: the rolling join scans at most 30 event_date partitions per metric date.

CREATE OR REPLACE TABLE `sports_product_analytics.mart_product_daily`
PARTITION BY metric_date AS
WITH user_days AS (
  SELECT
    event_date,
    user_id,
    COUNT(*) AS event_count,
    COUNT(DISTINCT session_id) AS sessions,
    COUNTIF(event_name = 'subscription_start') AS subscriptions,
    SUM(revenue_usd) AS net_revenue_usd
  FROM `sports_product_analytics.fact_app_events`
  GROUP BY event_date, user_id
),

metric_dates AS (
  SELECT DISTINCT event_date AS metric_date
  FROM user_days
),

rolling AS (
  SELECT
    dates.metric_date,
    COUNT(DISTINCT IF(activity.event_date = dates.metric_date, activity.user_id, NULL)) AS dau,
    COUNT(DISTINCT activity.user_id) AS mau,
    SUM(IF(activity.event_date = dates.metric_date, activity.sessions, 0)) AS sessions,
    SUM(IF(activity.event_date = dates.metric_date, activity.event_count, 0)) AS events,
    SUM(IF(activity.event_date = dates.metric_date, activity.subscriptions, 0)) AS subscriptions,
    SUM(IF(activity.event_date = dates.metric_date, activity.net_revenue_usd, 0)) AS revenue_usd
  FROM metric_dates AS dates
  INNER JOIN user_days AS activity
    ON
      activity.event_date BETWEEN DATE_SUB(dates.metric_date, INTERVAL 29 DAY)
      AND dates.metric_date
  GROUP BY dates.metric_date
)

SELECT
  *,
  SAFE_DIVIDE(dau, mau) AS dau_mau_stickiness,
  SAFE_DIVIDE(events, dau) AS events_per_active_user,
  SAFE_DIVIDE(subscriptions, dau) AS daily_subscription_conversion,
  SAFE_DIVIDE(revenue_usd, dau) AS arpu_usd
FROM rolling;
