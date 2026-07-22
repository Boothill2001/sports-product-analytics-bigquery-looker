-- Business question: can product teams segment engagement using credible football performance?
-- Metric definition: team-match xG, shots, passes, tackles and event-share possession proxy.
-- Expected output: one row per team per match for Looker drill-down and heatmap controls.
-- Bytes processed: one scan of match events, clustered by match_id/event_type.

CREATE OR REPLACE TABLE `sports_product_analytics.mart_football_team_match`
CLUSTER BY match_id, team_id AS
WITH match_teams AS (
  SELECT
    matches.match_id,
    matches.match_date,
    matches.competition_name,
    team.team_id,
    team.team_name
  FROM `sports_product_analytics.dim_matches` AS matches,
    UNNEST(
      [
        STRUCT(matches.home_team_id AS team_id, matches.home_team_name AS team_name),
        STRUCT(matches.away_team_id AS team_id, matches.away_team_name AS team_name)
      ]
    ) AS team
),

event_totals AS (
  SELECT
    match_id,
    COUNT(*) AS match_event_count
  FROM `sports_product_analytics.fact_match_events`
  WHERE period <= 4
  GROUP BY match_id
),

team_events AS (
  SELECT
    match_id,
    team_id,
    COUNTIF(event_type = 'Shot') AS shots,
    COUNTIF(event_type = 'Shot' AND shot_outcome = 'Goal') AS goals,
    SUM(COALESCE(shot_xg, 0)) AS xg,
    COUNTIF(event_type = 'Pass') AS passes,
    COUNTIF(event_type = 'Pass' AND pass_outcome = 'Complete') AS completed_passes,
    COUNTIF(event_type = 'Duel' AND duel_type = 'Tackle') AS tackles,
    COUNTIF(event_type = 'Duel') AS duels,
    COUNTIF(under_pressure) AS events_under_pressure,
    COUNT(*) AS team_event_count
  FROM `sports_product_analytics.fact_match_events`
  WHERE period <= 4
  GROUP BY match_id, team_id
),

possession_events AS (
  SELECT
    match_id,
    possession_team_id AS team_id,
    COUNT(*) AS possession_event_count
  FROM `sports_product_analytics.fact_match_events`
  WHERE possession_team_id IS NOT NULL AND period <= 4
  GROUP BY match_id, team_id
)

SELECT
  match_teams.*,
  COALESCE(team_events.shots, 0) AS shots,
  COALESCE(team_events.goals, 0) AS goals,
  COALESCE(team_events.xg, 0) AS xg,
  COALESCE(team_events.passes, 0) AS passes,
  COALESCE(team_events.completed_passes, 0) AS completed_passes,
  SAFE_DIVIDE(team_events.completed_passes, team_events.passes) AS pass_completion_rate,
  COALESCE(team_events.tackles, 0) AS tackles,
  COALESCE(team_events.duels, 0) AS duels,
  COALESCE(team_events.events_under_pressure, 0) AS events_under_pressure,
  SAFE_DIVIDE(possession_events.possession_event_count, event_totals.match_event_count)
    AS possession_share
FROM match_teams
LEFT JOIN
  team_events
  ON match_teams.match_id = team_events.match_id AND match_teams.team_id = team_events.team_id
LEFT JOIN possession_events
  ON
    match_teams.match_id = possession_events.match_id
    AND match_teams.team_id = possession_events.team_id
LEFT JOIN event_totals
  ON match_teams.match_id = event_totals.match_id;

CREATE OR REPLACE TABLE `sports_product_analytics.mart_key_moment_engagement`
CLUSTER BY match_id, event_type AS
WITH key_moments AS (
  SELECT
    event_id,
    match_id,
    event_ts,
    minute,
    event_type,
    team_id,
    player_id,
    shot_outcome,
    shot_xg
  FROM `sports_product_analytics.fact_match_events`
  WHERE
    period <= 4
    AND (
      event_type IN ('Substitution', 'Bad Behaviour')
      OR (event_type = 'Shot' AND shot_outcome = 'Goal')
    )
),

match_windows AS (
  SELECT
    match_id,
    TIMESTAMP_SUB(MIN(event_ts), INTERVAL 30 MINUTE) AS window_start,
    TIMESTAMP_ADD(MAX(event_ts), INTERVAL 15 MINUTE) AS window_end
  FROM `sports_product_analytics.fact_match_events`
  WHERE period <= 4
  GROUP BY match_id
),

baseline AS (
  SELECT
    windows.match_id,
    SAFE_DIVIDE(
      COUNT(events.event_id),
      TIMESTAMP_DIFF(windows.window_end, windows.window_start, MINUTE) / 10
    ) AS baseline_app_events_10m
  FROM match_windows AS windows
  LEFT JOIN `sports_product_analytics.fact_app_events` AS events
    ON
      windows.match_id = events.match_id
      AND events.event_ts BETWEEN windows.window_start AND windows.window_end
  GROUP BY windows.match_id, windows.window_start, windows.window_end
),

moment_engagement AS (
  SELECT
    moments.*,
    COUNT(events.event_id) AS app_events_plus_minus_5m,
    COUNT(DISTINCT events.user_id) AS users_plus_minus_5m,
    COUNTIF(events.event_name = 'subscription_start') AS subscriptions_plus_minus_5m
  FROM key_moments AS moments
  LEFT JOIN `sports_product_analytics.fact_app_events` AS events
    ON
      moments.match_id = events.match_id
      AND events.event_ts BETWEEN TIMESTAMP_SUB(moments.event_ts, INTERVAL 5 MINUTE)
      AND TIMESTAMP_ADD(moments.event_ts, INTERVAL 5 MINUTE)
  GROUP BY
    moments.event_id,
    moments.match_id,
    moments.event_ts,
    moments.minute,
    moments.event_type,
    moments.team_id,
    moments.player_id,
    moments.shot_outcome,
    moments.shot_xg
)

SELECT
  moment_engagement.*,
  baseline.baseline_app_events_10m,
  SAFE_DIVIDE(
    moment_engagement.app_events_plus_minus_5m,
    baseline.baseline_app_events_10m
  ) AS engagement_lift_vs_baseline
FROM moment_engagement
INNER JOIN baseline
  ON moment_engagement.match_id = baseline.match_id;
