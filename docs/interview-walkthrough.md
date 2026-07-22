# Five-minute interview walkthrough

## 0:00–0:35 — Business goal

“I wanted to answer one sports-product question: which matches, moments and content journeys create engagement and subscription value? I used real StatsBomb football events and clearly labelled synthetic product data so I could demonstrate the full analytics workflow without implying access to company data.”

## 0:35–1:15 — Data model

Show the architecture and BigQuery schema.

“The event facts are separated from user, match, team, player and content dimensions. App and football facts are partitioned by date and clustered for the user/match filters used by the dashboard. Parquet batch loads keep the project free-tier friendly.”

## 1:15–2:00 — Advanced SQL

Open `01_sessionization.sql` and `04_conversion_funnel.sql`.

“Sessionization uses `LAG`, a 30-minute boundary and a cumulative window. The funnel operates at user-match grain and only counts ordered milestones, so no later step can exceed the earlier step. I also exclude penalty shootouts from regular-match xG.”

## 2:00–3:10 — Dashboard and insight

Navigate Executive → Product Journey → Sports Engagement.

“The treatment variant moved simulated user conversion from 12.19% to 15.76%. The absolute lift is 3.57 points and the 95% interval is 2.71 to 4.43 points. In football context, the 38th-minute Argentina–Croatia goal coincided with 1.94 times baseline engagement.”

## 3:10–4:05 — Recommendation

“I would ramp the Match Center treatment behind cancellation and performance guardrails. I would test a subscription prompt after highlight value is delivered and use a holdout for moment-triggered notifications. For marketing, social has the best CAC, but all ROAS30 values are below one, so I would not scale until observed lifetime value supports it.”

## 4:05–4:40 — Trust and reproducibility

Show Experiment & Quality.

“The build has deterministic generation, schema/key/FK/order/xG checks, experiment crossover validation, raw-to-mart reconciliation, SQLFluff, dry-run support and 94% Python test coverage.”

## 4:40–5:00 — Limitation

“The product behavior and A/B outcome are synthetic, so these are portfolio findings, not claims about Unity Sport. The next step would be real subscription lifecycle, exposure logs and more competitions.”

## Likely follow-ups

**Why BigQuery marts instead of connecting Looker to raw events?**  
To reduce repeated scans, centralize metric logic and keep dashboard response predictable.

**Why can a significant result still be unsafe to ship?**  
Statistical significance does not protect guardrails, implementation quality or external validity.

**Why exclude period 5 from xG?**  
Penalty shootouts are a separate competition-deciding mechanism and inflate ordinary match xG.

**What would you change with production data?**  
Use exposure-based experiment analysis, account for eligibility and novelty, define finance-approved LTV, and monitor data freshness/late arrivals.
