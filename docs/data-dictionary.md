# Data dictionary

## Dimensions

### `dim_date`

Calendar date with year, quarter, month, ISO week, weekday and weekend flags. Grain: one date.

### `dim_users`

Synthetic user profile. Key fields: `user_id`, `signup_date`, `acquisition_channel`, `platform`, `country`, `subscription_tier`. Grain: one user.

### `dim_matches`

Real StatsBomb match metadata: competition, season, date, kick-off, teams and score. Grain: one match.

### `dim_teams`, `dim_players`

Real team and lineup entities normalized from selected matches. Grain: one team / one player.

### `dim_content`

Synthetic product content linked to a real match and optional team/player. Content types: match center, live blog, highlight and player story. Grain: one content item.

## Facts

### `fact_app_events`

One synthetic product event. Includes event/session/user identifiers, UTC timestamp, event date, event name, match/content links, platform, acquisition channel, A/B variant, campaign and net revenue.

Event names: `app_open`, `notification_click`, `match_center_view`, `highlight_view`, `content_view`, `subscription_start`, `subscription_cancel`.

### `fact_match_events`

One real StatsBomb event. Includes match/event order, UTC match-relative timestamp, period/minute/second, event/team/player/possession entities, start/end coordinates, xG, shot/pass outcome, duel type, pressure and duration.

Regular-match xG excludes period 5 penalty shootouts.

### `fact_campaign_spend`

One synthetic campaign-day with impressions, clicks, installs, actual spend and target spend.

### `fact_experiment_assignments`

One user-experiment assignment. `match_center_v2` uses deterministic control/treatment assignment and enforces no crossover.

## Metric definitions

| Metric | Definition |
|---|---|
| DAU | distinct users with at least one event on the metric date |
| MAU | distinct users active in the trailing 30 calendar days, inclusive |
| Stickiness | DAU / trailing MAU |
| D1/D7/D30 retention | cohort users active on exactly signup day + 1/7/30 divided by cohort size |
| Churn D30 | `1 - retention_d30` for this demonstration |
| Ordered funnel | first notification < first valid match center < first valid highlight < first subscription at user-match grain |
| ARPU | net revenue / active users in the selected period |
| Match xG | sum of StatsBomb `shot_xg` for periods 1–4; shootout penalties excluded |
| Possession share | possession-team events / all possession-labelled match events |
| Key-moment lift | app events within ±5 minutes / expected events in a 10-minute interval across that match window |
| CAC | spend / acquired users |
| LTV30 | net revenue in first 30 days / acquired users |
| ROAS30 | 30-day net revenue / campaign spend |
| A/B conversion | users with ≥1 subscription start / assigned users |
| Absolute lift | treatment conversion rate − control conversion rate |

## Data-quality rules

- Contract columns present.
- Primary keys unique and non-null.
- User, match, content and date relationships valid.
- Events are ordered within session.
- xG remains in `[0, 1]` when present.
- Experiment assignments do not cross variants.
- Raw revenue reconciles to the product daily mart.
