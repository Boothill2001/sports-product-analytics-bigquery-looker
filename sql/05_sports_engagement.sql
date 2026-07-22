-- Business question: which matches and content formats create the most fan engagement?
-- Metric definition: unique viewers, views, subscriptions and revenue by real football match.
-- Expected output: match/content rows enriched with score, xG and product engagement.
-- Bytes processed: clustered joins on match_id across match and app-event facts.

CREATE OR REPLACE TABLE `sports_product_analytics.mart_sports_engagement`
CLUSTER BY competition_name, match_id, content_type AS
WITH football AS (
  SELECT
    match_id,
    COUNTIF(event_type = 'Shot') AS shots,
    COUNTIF(event_type = 'Shot' AND shot_outcome = 'Goal') AS goals_in_events,
    SUM(COALESCE(shot_xg, 0)) AS total_xg,
    COUNTIF(event_type = 'Pass') AS passes,
    COUNTIF(event_type = 'Duel') AS duels
  FROM `sports_product_analytics.fact_match_events`
  WHERE period <= 4
  GROUP BY match_id
),

engagement AS (
  SELECT
    events.match_id,
    content.content_type,
    COUNT(*) AS views,
    COUNT(DISTINCT events.user_id) AS unique_viewers,
    COUNT(DISTINCT events.session_id) AS sessions,
    COUNTIF(events.event_name = 'subscription_start') AS subscriptions,
    SUM(events.revenue_usd) AS net_revenue_usd
  FROM `sports_product_analytics.fact_app_events` AS events
  LEFT JOIN
    `sports_product_analytics.dim_content` AS content
    ON events.content_id = content.content_id
  GROUP BY events.match_id, content.content_type
)

SELECT
  matches.match_id,
  matches.match_date,
  matches.competition_name,
  matches.season_name,
  matches.home_team_name,
  matches.away_team_name,
  matches.home_score,
  matches.away_score,
  engagement.content_type,
  football.shots,
  football.goals_in_events,
  football.total_xg,
  football.passes,
  football.duels,
  engagement.views,
  engagement.unique_viewers,
  engagement.sessions,
  engagement.subscriptions,
  engagement.net_revenue_usd,
  SAFE_DIVIDE(engagement.subscriptions, engagement.unique_viewers) AS viewer_conversion_rate
FROM engagement
INNER JOIN
  `sports_product_analytics.dim_matches` AS matches
  ON engagement.match_id = matches.match_id
INNER JOIN football
  ON engagement.match_id = football.match_id;
