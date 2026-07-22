"""Deterministic synthetic product events linked to real football matches."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

CHANNELS = np.array(["organic", "paid_search", "social", "referral", "partner"])
PLATFORMS = np.array(["android", "ios", "web"])
COUNTRIES = np.array(["VN", "TH", "ID", "MY", "PH"])
CONTENT_TYPES = ("match_center", "live_blog", "highlight", "player_story")


def generate_date_dimension(start_date: object, end_date: object) -> pd.DataFrame:
    """Build a deterministic calendar dimension covering the full analysis window."""

    dates = pd.date_range(pd.Timestamp(start_date), pd.Timestamp(end_date), freq="D")
    iso_calendar = dates.isocalendar()
    return pd.DataFrame(
        {
            "date": dates.date,
            "year": dates.year,
            "quarter": dates.quarter,
            "month": dates.month,
            "month_name": dates.month_name(),
            "iso_week": iso_calendar.week.to_numpy(dtype="int64"),
            "day_of_week": dates.dayofweek + 1,
            "day_name": dates.day_name(),
            "is_weekend": dates.dayofweek >= 5,
        }
    )


def generate_users(
    n_users: int, min_match_date: pd.Timestamp, seed: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    signup_offsets = rng.integers(1, 91, size=n_users)
    signup_dates = pd.Timestamp(min_match_date).normalize() - pd.to_timedelta(
        signup_offsets, unit="D"
    )
    channels = rng.choice(CHANNELS, size=n_users, p=[0.38, 0.19, 0.23, 0.12, 0.08])
    platforms = rng.choice(PLATFORMS, size=n_users, p=[0.53, 0.36, 0.11])
    countries = rng.choice(COUNTRIES, size=n_users, p=[0.52, 0.12, 0.14, 0.10, 0.12])
    premium = rng.random(n_users) < 0.18
    user_ids = np.array([f"U{i:06d}" for i in range(1, n_users + 1)])

    users = pd.DataFrame(
        {
            "user_id": user_ids,
            "signup_date": signup_dates.date,
            "acquisition_channel": channels,
            "platform": platforms,
            "country": countries,
            "subscription_tier": np.where(premium, "premium", "free"),
        }
    )
    variants = np.where(rng.random(n_users) < 0.5, "control", "treatment")
    assignments = pd.DataFrame(
        {
            "user_id": user_ids,
            "experiment_name": "match_center_v2",
            "variant": variants,
            "assigned_at": pd.to_datetime(signup_dates, utc=True) + pd.Timedelta(hours=12),
        }
    )
    return users, assignments


def generate_content(matches: pd.DataFrame, players: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 1)
    rows: list[dict[str, object]] = []
    player_ids = players["player_id"].to_numpy() if not players.empty else np.array([None])

    for match in matches.itertuples(index=False):
        kickoff = pd.Timestamp(f"{match.match_date} {match.kick_off}", tz="UTC")
        for content_type in CONTENT_TYPES:
            team_id = int(
                rng.choice(np.array([match.home_team_id, match.away_team_id], dtype="int64"))
            )
            player_id = int(rng.choice(player_ids)) if player_ids[0] is not None else None
            offset = {
                "match_center": -30,
                "live_blog": -10,
                "highlight": 120,
                "player_story": 240,
            }[content_type]
            rows.append(
                {
                    "content_id": f"C{int(match.match_id)}_{content_type}",
                    "match_id": int(match.match_id),
                    "content_type": content_type,
                    "published_at": kickoff + pd.Timedelta(minutes=offset),
                    "team_id": team_id,
                    "player_id": player_id,
                }
            )
    return pd.DataFrame(rows)


def generate_campaign_spend(
    users: pd.DataFrame, matches: pd.DataFrame, seed: int
) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 2)
    first_date = pd.Timestamp(users["signup_date"].min())
    last_date = pd.Timestamp(matches["match_date"].max()) + pd.Timedelta(days=7)
    rows: list[dict[str, object]] = []
    paid_channels = ["paid_search", "social", "partner"]

    for spend_date in pd.date_range(first_date, last_date, freq="D"):
        for channel in paid_channels:
            base = {"paid_search": 720.0, "social": 540.0, "partner": 310.0}[channel]
            spend = max(80.0, rng.normal(base, base * 0.14))
            cpc = {"paid_search": 0.72, "social": 0.46, "partner": 1.05}[channel]
            clicks = int(spend / cpc)
            installs = int(clicks * rng.uniform(0.18, 0.32))
            impressions = int(clicks / rng.uniform(0.012, 0.029))
            rows.append(
                {
                    "spend_date": spend_date.date(),
                    "campaign_id": f"{channel}_{spend_date:%Y%m%d}",
                    "channel": channel,
                    "impressions": impressions,
                    "clicks": clicks,
                    "installs": installs,
                    "spend_usd": round(spend, 2),
                    "target_spend_usd": round(base, 2),
                }
            )
    return pd.DataFrame(rows)


def _session_types(
    variants: np.ndarray, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    draws = rng.random(len(variants))
    treatment = variants == "treatment"
    session_type = np.full(len(variants), "browse", dtype="U10")
    session_type[(~treatment) & (draws < 0.18)] = "bounce"
    session_type[(~treatment) & (draws >= 0.38) & (draws < 0.48)] = "alert"
    session_type[(~treatment) & (draws >= 0.48) & (draws < 0.57)] = "match"
    session_type[(~treatment) & (draws >= 0.57) & (draws < 0.992)] = "highlight"
    session_type[(~treatment) & (draws >= 0.992)] = "convert"
    session_type[treatment & (draws < 0.14)] = "bounce"
    session_type[treatment & (draws >= 0.30) & (draws < 0.39)] = "alert"
    session_type[treatment & (draws >= 0.39) & (draws < 0.49)] = "match"
    session_type[treatment & (draws >= 0.49) & (draws < 0.989)] = "highlight"
    session_type[treatment & (draws >= 0.989)] = "convert"
    cancellation = (session_type == "convert") & (rng.random(len(variants)) < 0.035)
    lengths = np.select(
        [
            session_type == "bounce",
            session_type == "alert",
            session_type == "browse",
            session_type == "match",
            session_type == "highlight",
        ],
        [1, 2, 3, 3, 4],
        default=5,
    ).astype("int64")
    lengths += cancellation.astype("int64")
    return session_type, lengths


def generate_app_events(
    n_events: int,
    users: pd.DataFrame,
    assignments: pd.DataFrame,
    matches: pd.DataFrame,
    content: pd.DataFrame,
    seed: int,
    match_events: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if n_events < 1:
        raise ValueError("n_events must be positive")
    rng = np.random.default_rng(seed + 3)
    estimated_sessions = max(1, math.ceil(n_events / 3.25))
    session_user_index = rng.integers(0, len(users), size=estimated_sessions)
    variants_by_user = assignments.set_index("user_id")["variant"]
    session_user_ids = users.iloc[session_user_index]["user_id"].to_numpy()
    session_variants = variants_by_user.loc[session_user_ids].to_numpy()
    session_type, lengths = _session_types(session_variants, rng)

    while int(lengths.sum()) < n_events:
        extra = max(1, math.ceil((n_events - int(lengths.sum())) / 3.25))
        extra_users = rng.integers(0, len(users), size=extra)
        extra_user_ids = users.iloc[extra_users]["user_id"].to_numpy()
        extra_variants = variants_by_user.loc[extra_user_ids].to_numpy()
        extra_types, extra_lengths = _session_types(extra_variants, rng)
        session_user_index = np.concatenate([session_user_index, extra_users])
        session_user_ids = np.concatenate([session_user_ids, extra_user_ids])
        session_variants = np.concatenate([session_variants, extra_variants])
        session_type = np.concatenate([session_type, extra_types])
        lengths = np.concatenate([lengths, extra_lengths])

    session_count = len(lengths)
    match_index = rng.integers(0, len(matches), size=session_count)
    match_ids = matches.iloc[match_index]["match_id"].to_numpy(dtype="int64")
    kickoffs = pd.to_datetime(
        matches["match_date"].astype(str) + " " + matches["kick_off"].astype(str), utc=True
    ).to_numpy()
    base_kickoffs = kickoffs[match_index]
    near_match = rng.random(session_count) < 0.78
    minute_offsets = np.where(
        near_match,
        np.clip(rng.normal(25, 78, size=session_count), -120, 260),
        rng.uniform(-60 * 24 * 7, 60 * 24 * 7, size=session_count),
    )
    session_starts = pd.to_datetime(base_kickoffs, utc=True) + pd.to_timedelta(
        minute_offsets, unit="m"
    )

    # Model fan reactions around real public match events. Goal moments are deliberately
    # more likely to attract a session than ordinary shots or substitutions.
    if match_events is not None and not match_events.empty:
        key_events = match_events[
            match_events["event_type"].isin(["Shot", "Substitution", "Bad Behaviour"])
        ].copy()
        key_events["anchor_weight"] = np.select(
            [
                key_events["shot_outcome"].eq("Goal"),
                key_events["event_type"].eq("Shot"),
            ],
            [6.0, 2.0],
            default=1.0,
        )
        starts = session_starts.to_numpy(dtype="datetime64[ns]")
        for match_id, match_key_events in key_events.groupby("match_id"):
            matching_sessions = np.flatnonzero(match_ids == match_id)
            reaction_sessions = matching_sessions[
                rng.random(len(matching_sessions)) < 0.36
            ]
            if len(reaction_sessions) == 0:
                continue
            probabilities = (
                match_key_events["anchor_weight"]
                / match_key_events["anchor_weight"].sum()
            ).to_numpy()
            anchors = rng.choice(
                pd.to_datetime(match_key_events["event_ts"], utc=True).to_numpy(
                    dtype="datetime64[ns]"
                ),
                size=len(reaction_sessions),
                p=probabilities,
            )
            jitter = rng.integers(-90, 8 * 60, size=len(reaction_sessions)).astype(
                "timedelta64[s]"
            )
            starts[reaction_sessions] = anchors + jitter
        session_starts = pd.to_datetime(starts, utc=True)

    # Seed lifecycle activity so exact-day retention behaves like a product cohort:
    # D1 is intentionally more common than D7, which is more common than D30.
    lifecycle_draws = rng.random(session_count)
    lifecycle_days = np.select(
        [lifecycle_draws < 0.04, lifecycle_draws < 0.065, lifecycle_draws < 0.077],
        [1, 7, 30],
        default=0,
    )
    lifecycle_sessions = lifecycle_days > 0
    signup_dates = pd.to_datetime(
        users.iloc[session_user_index]["signup_date"].to_numpy(), utc=True
    )
    lifecycle_minutes = rng.integers(8 * 60, 22 * 60, size=session_count)
    session_starts = pd.DatetimeIndex(session_starts)
    session_starts = session_starts.where(
        ~lifecycle_sessions,
        signup_dates
        + pd.to_timedelta(lifecycle_days, unit="D")
        + pd.to_timedelta(lifecycle_minutes, unit="m"),
    )

    repeated_session = np.repeat(np.arange(session_count, dtype="int64"), lengths)[:n_events]
    repeated_starts = np.repeat(np.cumsum(np.r_[0, lengths[:-1]]), lengths)[:n_events]
    positions = np.arange(n_events, dtype="int64") - repeated_starts
    repeated_type = session_type[repeated_session]
    event_names = np.full(n_events, "content_view", dtype="U24")
    event_names[positions == 0] = "app_open"
    event_names[(repeated_type == "browse") & (positions == 1)] = "match_center_view"
    event_names[(repeated_type == "alert") & (positions == 1)] = "notification_click"
    event_names[(repeated_type == "match") & (positions == 1)] = "notification_click"
    event_names[(repeated_type == "match") & (positions == 2)] = "match_center_view"
    event_names[(repeated_type == "highlight") & (positions == 1)] = "notification_click"
    event_names[(repeated_type == "highlight") & (positions == 2)] = "match_center_view"
    event_names[(repeated_type == "highlight") & (positions == 3)] = "highlight_view"
    event_names[(repeated_type == "convert") & (positions == 1)] = "notification_click"
    event_names[(repeated_type == "convert") & (positions == 2)] = "match_center_view"
    event_names[(repeated_type == "convert") & (positions == 3)] = "highlight_view"
    event_names[(repeated_type == "convert") & (positions == 4)] = "subscription_start"
    event_names[(repeated_type == "convert") & (positions == 5)] = "subscription_cancel"

    seconds = positions * 60 + rng.integers(0, 20, size=n_events)
    event_ts = session_starts[repeated_session] + pd.to_timedelta(seconds, unit="s")
    repeated_user_index = session_user_index[repeated_session]
    user_rows = users.iloc[repeated_user_index]
    repeated_match_ids = match_ids[repeated_session]
    repeated_variants = session_variants[repeated_session]

    content_lookup = content.set_index(["match_id", "content_type"])["content_id"]
    content_type = np.full(n_events, "live_blog", dtype="U20")
    content_type[event_names == "match_center_view"] = "match_center"
    content_type[event_names == "highlight_view"] = "highlight"
    content_type[(event_names == "content_view") & (positions % 2 == 1)] = "player_story"
    content_ids: list[str | None] = []
    content_events = {"match_center_view", "highlight_view", "content_view"}
    for name, match_id, kind in zip(event_names, repeated_match_ids, content_type, strict=True):
        content_ids.append(
            str(content_lookup.loc[(int(match_id), str(kind))])
            if name in content_events
            else None
        )

    revenue = np.zeros(n_events, dtype="float64")
    revenue[event_names == "subscription_start"] = 9.99
    revenue[event_names == "subscription_cancel"] = -9.99
    event_dates = pd.DatetimeIndex(event_ts).date
    channels = user_rows["acquisition_channel"].to_numpy()
    campaign_ids = np.where(
        np.isin(channels, ["paid_search", "social", "partner"]),
        np.char.add(
            np.char.add(channels.astype(str), "_"),
            pd.DatetimeIndex(event_ts).strftime("%Y%m%d"),
        ),
        None,
    )

    return pd.DataFrame(
        {
            "event_id": [f"E{i:09d}" for i in range(1, n_events + 1)],
            "user_id": session_user_ids[repeated_session],
            "session_id": [f"S{i + 1:08d}" for i in repeated_session],
            "event_ts": pd.to_datetime(event_ts, utc=True),
            "event_date": event_dates,
            "event_name": event_names,
            "match_id": repeated_match_ids,
            "content_id": content_ids,
            "platform": user_rows["platform"].to_numpy(),
            "acquisition_channel": channels,
            "experiment_variant": repeated_variants,
            "campaign_id": campaign_ids,
            "revenue_usd": revenue,
        }
    )
