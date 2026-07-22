# Case study: what turns football attention into product value?

## Business question

Which matches, moments and content journeys drive fan engagement and subscription conversion, and where should a sports product team invest next?

## Approach

I modelled eight World Cup matches from StatsBomb at event grain, then linked them to a reproducible synthetic sports-app journey. The product layer includes 25,000 users, 1.2 million app events, paid acquisition, Match Center content and a user-level A/B assignment.

The analysis separates three kinds of evidence:

- real football facts;
- simulated product behavior;
- derived metrics and recommendations.

That separation matters: the portfolio proves analysis capability without presenting synthetic outcomes as live-company results.

## Findings

### 1. Match Center v2 produced a clear simulated conversion signal

Control converted at 12.19%; treatment converted at 15.76%. That is +3.57 percentage points, +29.25% relative. The 95% interval for absolute lift is +2.71 to +4.43 points, and assignment reconciliation found no crossover.

Interpretation: the simulated effect is large enough to justify a controlled ramp, but production guardrails remain necessary.

### 2. High-intensity moments concentrate attention

The 38′ goal in Argentina vs Croatia coincided with 12,886 app events within ±5 minutes—1.94× the match-window baseline. This supports moment-triggered editorial and notification workflows, but a live holdout is needed to measure incremental rather than coincident engagement.

### 3. Reach and conversion are not the same ranking

France vs Morocco generated the largest simulated audience at 21,516 unique viewers and 502 subscriptions. Match-level drill-down prevents the team from using overall DAU as a proxy for which inventory creates value.

### 4. Paid acquisition needs a longer value horizon

Social was the most efficient paid channel at $10.06 CAC and 0.05× ROAS30, yet no paid channel recovered spend inside 30 days. Scaling from CAC alone would be misleading. The next decision needs a properly observed renewal curve and gross-margin LTV.

## Recommendations

1. Roll Match Center v2 from experiment into a staged release, watching cancellation, latency, crash rate and revenue per user.
2. Test contextual subscription prompts after highlight consumption. The ordered journey shows the remaining commercial drop after product value has been delivered.
3. Build a moment-trigger playbook for goals and other high-intensity events, then run a notification holdout to separate causation from football-driven demand.
4. Hold paid budget flat until observed lifetime value supports CAC; use social as the first optimization channel because it leads the current efficiency ranking.

## Limitations and next data request

- The product layer is synthetic and the experiment effect is intentionally encoded.
- Eight matches cannot establish competition or season generalization.
- Engagement around a goal is observational; the match event may cause both attention and conversion.
- LTV30 excludes renewal, margin, refunds and non-subscription revenue.

For a production follow-up I would request real subscription lifecycle data, notification exposure/control logs, content metadata, match rights/availability and a longer football calendar.
