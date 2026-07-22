# Looker Studio calculated fields

## Parameter-controlled metric

```text
CASE Metric selector
  WHEN "DAU" THEN DAU
  WHEN "Active Viewers" THEN Active Viewers
  WHEN "Revenue" THEN Revenue USD
  WHEN "ARPU" THEN ARPU USD
END
```

## Product

```text
Stickiness = DAU / MAU
Subscription Conversion = Subscriptions / DAU
Churn D30 = 1 - Retention D30
Highlight → Subscription = Subscription Users / Highlight Users
```

## Sports

```text
Viewer Conversion = Subscriptions / Unique Viewers
Pass Completion = Completed Passes / Passes
Key Moment Lift = App Events ±5m / Baseline App Events 10m
```

## Marketing

```text
CAC = Spend USD / New Users
LTV30 = Revenue 30d / New Users
ROAS30 = Revenue 30d / Spend USD
Spend to Target = Spend USD / Target Spend USD
```

## Experiment

```text
Absolute Lift = Treatment Rate - Control Rate
Relative Lift = Absolute Lift / Control Rate
Decision = CASE WHEN CI 95 Lower > 0 THEN "Significant lift" ELSE "Inconclusive" END
```
