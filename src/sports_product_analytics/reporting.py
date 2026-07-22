"""Build small, reproducible dashboard extracts from generated Parquet facts."""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _read_frames(data_dir: Path) -> dict[str, pd.DataFrame]:
    names = (
        "dim_users",
        "dim_matches",
        "dim_content",
        "fact_app_events",
        "fact_match_events",
        "fact_campaign_spend",
        "fact_experiment_assignments",
        "data_quality_results",
    )
    return {name: pd.read_parquet(data_dir / f"{name}.parquet") for name in names}


def _executive_daily(events: pd.DataFrame) -> pd.DataFrame:
    events = events.copy()
    events["event_date"] = pd.to_datetime(events["event_date"])
    active_viewers = events[events["event_name"].isin(["match_center_view", "highlight_view"])]
    daily = (
        events.groupby("event_date", as_index=False)
        .agg(
            dau=("user_id", "nunique"),
            sessions=("session_id", "nunique"),
            events=("event_id", "count"),
            subscriptions=("event_name", lambda values: values.eq("subscription_start").sum()),
            cancellations=("event_name", lambda values: values.eq("subscription_cancel").sum()),
            revenue_usd=("revenue_usd", "sum"),
        )
        .sort_values("event_date")
    )
    viewer_daily = active_viewers.groupby("event_date")["user_id"].nunique()
    daily["active_viewers"] = daily["event_date"].map(viewer_daily).fillna(0).astype(int)

    user_days = events[["event_date", "user_id"]].drop_duplicates()
    daily["mau"] = [
        user_days.loc[
            user_days["event_date"].between(date - pd.Timedelta(days=29), date),
            "user_id",
        ].nunique()
        for date in daily["event_date"]
    ]
    daily["stickiness"] = daily["dau"] / daily["mau"]
    daily["arpu_usd"] = daily["revenue_usd"] / daily["dau"]
    daily["subscription_conversion"] = daily["subscriptions"] / daily["dau"]
    daily["event_date"] = daily["event_date"].dt.date
    return daily


def _retention(events: pd.DataFrame, users: pd.DataFrame) -> pd.DataFrame:
    activity = events[["user_id", "event_date"]].drop_duplicates().copy()
    activity["event_date"] = pd.to_datetime(activity["event_date"])
    cohorts = users[["user_id", "signup_date", "acquisition_channel", "platform"]].copy()
    cohorts["signup_date"] = pd.to_datetime(cohorts["signup_date"])
    joined = activity.merge(cohorts, on="user_id", validate="many_to_one")
    joined["day_number"] = (joined["event_date"] - joined["signup_date"]).dt.days
    cohort_sizes = cohorts.groupby(["acquisition_channel", "platform"])["user_id"].nunique()
    rows: list[dict[str, object]] = []
    for (channel, platform), cohort_size in cohort_sizes.items():
        segment = joined[
            joined["acquisition_channel"].eq(channel) & joined["platform"].eq(platform)
        ]
        row: dict[str, object] = {
            "acquisition_channel": channel,
            "platform": platform,
            "cohort_size": int(cohort_size),
        }
        for day in (1, 7, 30):
            retained = segment.loc[segment["day_number"].eq(day), "user_id"].nunique()
            row[f"retained_d{day}"] = int(retained)
            row[f"retention_d{day}"] = retained / cohort_size
        row["churn_d30"] = 1 - float(row["retention_d30"])
        rows.append(row)
    return pd.DataFrame(rows)


def _funnel(events: pd.DataFrame) -> pd.DataFrame:
    milestones = [
        "notification_click",
        "match_center_view",
        "highlight_view",
        "subscription_start",
    ]
    filtered = events[events["event_name"].isin(milestones)].copy()
    steps = filtered.pivot_table(
        index=["user_id", "match_id", "platform", "experiment_variant"],
        columns="event_name",
        values="event_ts",
        aggfunc="min",
    ).reset_index()
    for milestone in milestones:
        if milestone not in steps:
            steps[milestone] = pd.NaT
    steps["notification"] = steps["notification_click"].notna()
    steps["match_center"] = steps["notification"] & steps["match_center_view"].gt(
        steps["notification_click"]
    )
    steps["highlight"] = steps["match_center"] & steps["highlight_view"].gt(
        steps["match_center_view"]
    )
    steps["subscription"] = steps["highlight"] & steps["subscription_start"].gt(
        steps["highlight_view"]
    )
    grouped = (
        steps.groupby(["platform", "experiment_variant"], as_index=False)
        .agg(
            journeys=("user_id", "size"),
            notification_users=("notification", "sum"),
            match_center_users=("match_center", "sum"),
            highlight_users=("highlight", "sum"),
            subscription_users=("subscription", "sum"),
        )
    )
    grouped["notification_to_match"] = (
        grouped["match_center_users"] / grouped["notification_users"]
    )
    grouped["match_to_highlight"] = grouped["highlight_users"] / grouped["match_center_users"]
    grouped["highlight_to_subscription"] = (
        grouped["subscription_users"] / grouped["highlight_users"]
    )
    grouped["end_to_end_conversion"] = grouped["subscription_users"] / grouped["journeys"]
    return grouped


def _sports_engagement(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    events = frames["fact_app_events"].merge(
        frames["dim_content"][["content_id", "content_type"]],
        on="content_id",
        how="left",
        validate="many_to_one",
    )
    engagement = (
        events.groupby(["match_id", "content_type"], dropna=False, as_index=False)
        .agg(
            views=("event_id", "count"),
            unique_viewers=("user_id", "nunique"),
            sessions=("session_id", "nunique"),
            subscriptions=("event_name", lambda values: values.eq("subscription_start").sum()),
            revenue_usd=("revenue_usd", "sum"),
        )
    )
    football_events = frames["fact_match_events"]
    football_events = football_events[football_events["period"].le(4)]
    football = (
        football_events.groupby("match_id", as_index=False)
        .agg(
            shots=("event_type", lambda values: values.eq("Shot").sum()),
            goals=("shot_outcome", lambda values: values.eq("Goal").sum()),
            xg=("shot_xg", "sum"),
            passes=("event_type", lambda values: values.eq("Pass").sum()),
            tackles=("duel_type", lambda values: values.eq("Tackle").sum()),
        )
    )
    result = engagement.merge(football, on="match_id", validate="many_to_one").merge(
        frames["dim_matches"], on="match_id", validate="many_to_one"
    )
    result["viewer_conversion_rate"] = result["subscriptions"] / result["unique_viewers"]
    result["match_label"] = result["home_team_name"] + " vs " + result["away_team_name"]
    return result


def _marketing(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    spend = (
        frames["fact_campaign_spend"]
        .groupby("channel", as_index=False)
        .agg(
            impressions=("impressions", "sum"),
            clicks=("clicks", "sum"),
            installs=("installs", "sum"),
            spend_usd=("spend_usd", "sum"),
            target_spend_usd=("target_spend_usd", "sum"),
        )
    )
    users = frames["dim_users"][["user_id", "signup_date", "acquisition_channel"]].copy()
    users["signup_date"] = pd.to_datetime(users["signup_date"])
    revenue = frames["fact_app_events"][["user_id", "event_date", "revenue_usd"]].copy()
    revenue["event_date"] = pd.to_datetime(revenue["event_date"])
    revenue = revenue.merge(users, on="user_id", validate="many_to_one")
    revenue["age_days"] = (revenue["event_date"] - revenue["signup_date"]).dt.days
    revenue = revenue[revenue["age_days"].between(0, 30)]
    revenue_by_channel = revenue.groupby("acquisition_channel")["revenue_usd"].sum()
    user_counts = users.groupby("acquisition_channel")["user_id"].nunique()
    spend["new_users"] = spend["channel"].map(user_counts).fillna(0).astype(int)
    spend["revenue_30d"] = spend["channel"].map(revenue_by_channel).fillna(0)
    spend["cac_usd"] = spend["spend_usd"] / spend["new_users"]
    spend["ltv_30d_usd"] = spend["revenue_30d"] / spend["new_users"]
    spend["roas_30d"] = spend["revenue_30d"] / spend["spend_usd"]
    spend["ctr"] = spend["clicks"] / spend["impressions"]
    spend["install_rate"] = spend["installs"] / spend["clicks"]
    return spend


def _ab_test(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    events = frames["fact_app_events"]
    outcomes = (
        events.groupby("user_id", as_index=False)
        .agg(
            converted=("event_name", lambda values: values.eq("subscription_start").any()),
            match_center_views=("event_name", lambda values: values.eq("match_center_view").sum()),
            revenue_usd=("revenue_usd", "sum"),
        )
    )
    outcomes = frames["fact_experiment_assignments"].merge(
        outcomes, on="user_id", how="left", validate="one_to_one"
    )
    metrics = (
        outcomes.groupby("variant", as_index=False)
        .agg(
            users=("user_id", "nunique"),
            converted_users=("converted", "sum"),
            conversion_rate=("converted", "mean"),
            avg_match_center_views=("match_center_views", "mean"),
            arpu_usd=("revenue_usd", "mean"),
        )
    )
    control = metrics.set_index("variant").loc["control"]
    treatment = metrics.set_index("variant").loc["treatment"]
    absolute_lift = float(treatment["conversion_rate"] - control["conversion_rate"])
    standard_error = math.sqrt(
        float(control["conversion_rate"] * (1 - control["conversion_rate"]) / control["users"])
        + float(
            treatment["conversion_rate"]
            * (1 - treatment["conversion_rate"])
            / treatment["users"]
        )
    )
    metrics["absolute_lift"] = absolute_lift
    metrics["relative_lift"] = absolute_lift / float(control["conversion_rate"])
    metrics["ci_95_lower"] = absolute_lift - 1.96 * standard_error
    metrics["ci_95_upper"] = absolute_lift + 1.96 * standard_error
    metrics["significant_at_95pct"] = not (
        metrics["ci_95_lower"].iloc[0] <= 0 <= metrics["ci_95_upper"].iloc[0]
    )
    return metrics


def _key_moments(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    app_events = frames["fact_app_events"]
    match_events = frames["fact_match_events"]
    moments = match_events[
        match_events["period"].le(4)
        & (
            match_events["event_type"].eq("Shot")
            | match_events["event_type"].isin(["Substitution", "Bad Behaviour"])
        )
    ].copy()
    rows: list[dict[str, object]] = []
    for match_id, match_moments in moments.groupby("match_id"):
        timestamps = np.sort(
            pd.to_datetime(
                app_events.loc[app_events["match_id"].eq(match_id), "event_ts"], utc=True
            ).to_numpy(dtype="datetime64[ns]")
        )
        regular_match_events = match_events[
            match_events["match_id"].eq(match_id) & match_events["period"].le(4)
        ]
        window_start = np.datetime64(
            pd.Timestamp(regular_match_events["event_ts"].min())
            .tz_convert("UTC")
            .tz_localize(None)
        ) - np.timedelta64(30, "m")
        window_end = np.datetime64(
            pd.Timestamp(regular_match_events["event_ts"].max())
            .tz_convert("UTC")
            .tz_localize(None)
        ) + np.timedelta64(15, "m")
        match_window_events = int(
            np.searchsorted(timestamps, window_end) - np.searchsorted(timestamps, window_start)
        )
        window_minutes = float((window_end - window_start) / np.timedelta64(1, "m"))
        baseline_10m = match_window_events / window_minutes * 10
        for moment in match_moments.itertuples(index=False):
            timestamp = np.datetime64(
                pd.Timestamp(moment.event_ts).tz_convert("UTC").tz_localize(None)
            )
            lower = timestamp - np.timedelta64(5, "m")
            upper = timestamp + np.timedelta64(5, "m")
            engagement = int(
                np.searchsorted(timestamps, upper) - np.searchsorted(timestamps, lower)
            )
            rows.append(
                {
                    "match_id": int(match_id),
                    "minute": int(moment.minute),
                    "event_type": moment.event_type,
                    "shot_outcome": moment.shot_outcome,
                    "shot_xg": moment.shot_xg,
                    "team_id": moment.team_id,
                    "player_id": moment.player_id,
                    "app_events_plus_minus_5m": engagement,
                    "baseline_app_events_10m": baseline_10m,
                    "engagement_lift_vs_baseline": engagement / baseline_10m,
                }
            )
    result = pd.DataFrame(rows).merge(
        frames["dim_matches"][
            ["match_id", "competition_name", "home_team_name", "away_team_name"]
        ],
        on="match_id",
        validate="many_to_one",
    )
    result["match_label"] = result["home_team_name"] + " vs " + result["away_team_name"]
    return result.sort_values("app_events_plus_minus_5m", ascending=False)


def build_dashboard_extracts(data_dir: Path, output_dir: Path) -> dict[str, object]:
    """Create compact CSV and JS sources for Looker setup and offline fallback."""

    frames = _read_frames(data_dir)
    extracts = {
        "executive_daily": _executive_daily(frames["fact_app_events"]),
        "retention": _retention(frames["fact_app_events"], frames["dim_users"]),
        "funnel": _funnel(frames["fact_app_events"]),
        "sports_engagement": _sports_engagement(frames),
        "marketing": _marketing(frames),
        "ab_test": _ab_test(frames),
        "key_moments": _key_moments(frames),
        "quality": frames["data_quality_results"],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, extract in extracts.items():
        extract.to_csv(output_dir / f"{name}.csv", index=False)

    executive = extracts["executive_daily"]
    sports = extracts["sports_engagement"]
    match_rollup = (
        sports.groupby("match_label", as_index=False)
        .agg(
            unique_viewers=("unique_viewers", "max"),
            views=("views", "sum"),
            subscriptions=("subscriptions", "sum"),
            xg=("xg", "max"),
        )
        .sort_values("unique_viewers", ascending=False)
    )
    ab_test = extracts["ab_test"]
    marketing = extracts["marketing"].sort_values("roas_30d", ascending=False)
    goal_moments = extracts["key_moments"]
    goal_moments = goal_moments[goal_moments["shot_outcome"].eq("Goal")]
    top_moment = goal_moments.iloc[0]
    treatment = ab_test.set_index("variant").loc["treatment"]
    summary: dict[str, object] = {
        "generated_from": {
            "football_source": "StatsBomb Open Data — FIFA World Cup 2022",
            "product_source": "Deterministic synthetic events (seed=42)",
            "app_events": int(len(frames["fact_app_events"])),
            "match_events": int(len(frames["fact_match_events"])),
            "users": int(len(frames["dim_users"])),
            "matches": int(len(frames["dim_matches"])),
        },
        "kpis": {
            "peak_dau": int(executive["dau"].max()),
            "mau": int(executive["mau"].max()),
            "total_revenue_usd": round(float(executive["revenue_usd"].sum()), 2),
            "active_viewers": int(executive["active_viewers"].sum()),
            "ab_relative_lift": round(float(treatment["relative_lift"]), 4),
            "ab_ci_lower": round(float(treatment["ci_95_lower"]), 4),
            "ab_ci_upper": round(float(treatment["ci_95_upper"]), 4),
        },
        "top_match": match_rollup.iloc[0].to_dict(),
        "best_channel": marketing.iloc[0].to_dict(),
        "top_moment": top_moment.to_dict(),
        "charts": {
            "executive_daily": executive.to_dict(orient="records"),
            "funnel": extracts["funnel"].to_dict(orient="records"),
            "retention": extracts["retention"].to_dict(orient="records"),
            "sports": match_rollup.to_dict(orient="records"),
            "marketing": extracts["marketing"].to_dict(orient="records"),
            "ab_test": ab_test.to_dict(orient="records"),
            "key_moments": extracts["key_moments"].head(12).to_dict(orient="records"),
        },
    }
    normalized = _json_safe(summary)
    (output_dir / "insights.json").write_text(
        json.dumps(normalized, indent=2), encoding="utf-8"
    )
    (output_dir / "dashboard-data.js").write_text(
        "window.SPORTS_ANALYTICS_DATA = " + json.dumps(normalized) + ";\n",
        encoding="utf-8",
    )
    return normalized
