# Looker Studio build guide

## Sources

1. BigQuery dataset: `sports_product_analytics`
2. Google Sheets target source: import [`google-sheets/campaign_targets.csv`](google-sheets/campaign_targets.csv)
3. Join actual marketing metrics to targets on `channel`

Do not add a public URL until it works in incognito and exposes no account identity beyond what the owner intends.

## Report canvas

- Theme: dark green `#071F24`, primary `#0A7C61`, highlight `#C8F04A`, alert `#FF8F3D`, paper `#F4F7F3`.
- Canvas: widescreen 16:9.
- Report controls on every page: date range, platform and competition.
- Parameter: `Metric selector` with DAU, Active Viewers, Revenue and ARPU.
- Drill hierarchy: competition → match → content type; team → player for football tables.

## Page 1 — Executive pulse

Source: `mart_product_daily`, with a secondary match table from `mart_sports_engagement`.

- Scorecards: DAU, trailing MAU, stickiness, subscription conversion, ARPU, active viewers.
- Time series: parameter-controlled primary metric.
- Ranked bar: unique viewers by match.
- Insight card: selected match reach and conversion.

## Page 2 — Product journey

Sources: `mart_conversion_funnel`, `mart_retention_cohort`.

- Ordered funnel from notification through subscription.
- D1/D7/D30 cohort heatmap.
- Churn by platform and acquisition channel.
- Platform control and funnel-step drill table.

## Page 3 — Sports engagement

Sources: `mart_sports_engagement`, `mart_football_team_match`, `mart_key_moment_engagement`.

- Match leaderboard for viewers, subscriptions and xG.
- Shot map: `x`, `y`, shot outcome, shot xG and player.
- Team football table: xG, shots, passes, completion, possession and tackles.
- Key-moment table: app events ±5 minutes and baseline lift.
- Drill: competition → match → team/player/content.

## Page 4 — Marketing economics

Source: `mart_marketing_economics` blended with the target Sheet.

- Scorecards: spend, CAC, LTV30 and ROAS30.
- Actual vs target spend bullet bars.
- Channel economics decision table.
- Conditional formatting: ROAS below 1.0 and CAC above target.

## Page 5 — Experiment & quality

Sources: `mart_ab_test_match_center_v2`, `mart_data_quality`.

- Control/treatment conversion bars.
- Absolute/relative lift and 95% confidence interval.
- Variant sample sizes and ARPU guardrail.
- Quality scorecard: checks passed, duplicates, FK gaps, crossover, reconciliation and freshness.

## Verification checklist

- All controls affect intended charts; no unintended cross-filtering.
- Metric parameter switches label, format and field consistently.
- Funnel never increases between steps.
- Period 5 is excluded from regular-match xG.
- Marketing blend joins exactly one target row per channel.
- Totals reconcile to BigQuery source queries.
- Public link opens in incognito without login.
- PDF export, five screenshots and a short walkthrough are saved in `dashboard/exports/`.
