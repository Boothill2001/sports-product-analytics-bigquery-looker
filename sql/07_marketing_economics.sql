-- Business question: which acquisition channel creates profitable sports subscribers?
-- Metric definition: CAC = spend/new users; LTV30 = net revenue in first 30 days/new users.
-- Expected output: daily channel spend, installs, users, CAC, LTV30 and ROAS30.
-- Bytes processed: campaign partitions joined to user cohorts and bounded 30-day revenue.

CREATE OR REPLACE TABLE `sports_product_analytics.mart_marketing_economics`
PARTITION BY metric_date
CLUSTER BY channel AS
WITH acquired_users AS (
  SELECT
    signup_date,
    acquisition_channel AS channel,
    user_id
  FROM `sports_product_analytics.dim_users`
  WHERE acquisition_channel IN ('paid_search', 'social', 'partner')
),

user_revenue_30d AS (
  SELECT
    users.signup_date,
    users.channel,
    users.user_id,
    SUM(COALESCE(events.revenue_usd, 0)) AS revenue_30d
  FROM acquired_users AS users
  LEFT JOIN `sports_product_analytics.fact_app_events` AS events
    ON
      users.user_id = events.user_id
      AND events.event_date BETWEEN users.signup_date AND DATE_ADD(
        users.signup_date, INTERVAL 30 DAY
      )
  GROUP BY users.signup_date, users.channel, users.user_id
),

user_rollup AS (
  SELECT
    signup_date,
    channel,
    COUNT(DISTINCT user_id) AS new_users,
    SUM(revenue_30d) AS revenue_30d
  FROM user_revenue_30d
  GROUP BY signup_date, channel
)

SELECT
  spend.spend_date AS metric_date,
  spend.channel,
  spend.impressions,
  spend.clicks,
  spend.installs,
  spend.spend_usd,
  spend.target_spend_usd,
  COALESCE(users.new_users, 0) AS new_users,
  COALESCE(users.revenue_30d, 0) AS revenue_30d,
  SAFE_DIVIDE(spend.spend_usd, users.new_users) AS cac_usd,
  SAFE_DIVIDE(users.revenue_30d, users.new_users) AS ltv_30d_usd,
  SAFE_DIVIDE(users.revenue_30d, spend.spend_usd) AS roas_30d,
  SAFE_DIVIDE(spend.clicks, spend.impressions) AS click_through_rate,
  SAFE_DIVIDE(spend.installs, spend.clicks) AS click_to_install_rate
FROM `sports_product_analytics.fact_campaign_spend` AS spend
LEFT JOIN user_rollup AS users
  ON
    spend.spend_date = users.signup_date
    AND spend.channel = users.channel;
