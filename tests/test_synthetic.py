from __future__ import annotations

import pandas as pd

from sports_product_analytics.synthetic import (
    generate_app_events,
    generate_content,
    generate_date_dimension,
    generate_users,
)


def test_date_dimension_is_complete_and_unique() -> None:
    dates = generate_date_dimension("2022-12-01", "2022-12-31")
    assert len(dates) == 31
    assert dates["date"].is_unique
    assert set(dates["is_weekend"].unique()) == {False, True}


def test_users_and_assignment_are_deterministic() -> None:
    first_users, first_assignments = generate_users(100, pd.Timestamp("2022-12-01"), 7)
    second_users, second_assignments = generate_users(100, pd.Timestamp("2022-12-01"), 7)
    pd.testing.assert_frame_equal(first_users, second_users)
    pd.testing.assert_frame_equal(first_assignments, second_assignments)


def test_app_events_are_exact_size_and_ordered(
    football_frames: dict[str, pd.DataFrame],
) -> None:
    matches = football_frames["dim_matches"]
    users, assignments = generate_users(100, pd.Timestamp(matches["match_date"].min()), 9)
    content = generate_content(matches, football_frames["dim_players"], 9)
    events = generate_app_events(2_501, users, assignments, matches, content, 9)
    assert len(events) == 2_501
    assert events["event_id"].is_unique
    assert (
        events.groupby("session_id")["event_ts"]
        .apply(lambda values: values.is_monotonic_increasing)
        .all()
    )


def test_app_event_generation_is_deterministic(
    football_frames: dict[str, pd.DataFrame],
) -> None:
    matches = football_frames["dim_matches"]
    users, assignments = generate_users(120, pd.Timestamp(matches["match_date"].min()), 31)
    content = generate_content(matches, football_frames["dim_players"], 31)
    first = generate_app_events(
        3_000,
        users,
        assignments,
        matches,
        content,
        31,
        match_events=football_frames["fact_match_events"],
    )
    second = generate_app_events(
        3_000,
        users,
        assignments,
        matches,
        content,
        31,
        match_events=football_frames["fact_match_events"],
    )
    pd.testing.assert_frame_equal(first, second)


def test_treatment_has_higher_conversion_signal(
    football_frames: dict[str, pd.DataFrame],
) -> None:
    matches = football_frames["dim_matches"]
    users, assignments = generate_users(2_000, pd.Timestamp(matches["match_date"].min()), 42)
    content = generate_content(matches, football_frames["dim_players"], 42)
    events = generate_app_events(80_000, users, assignments, matches, content, 42)
    converted = (
        events.assign(converted=events["event_name"].eq("subscription_start"))
        .groupby("experiment_variant")["converted"]
        .mean()
    )
    assert converted["treatment"] > converted["control"]


def test_revenue_only_exists_on_subscription_events(
    complete_frames: dict[str, pd.DataFrame],
) -> None:
    events = complete_frames["fact_app_events"]
    paid = events[events["revenue_usd"].ne(0)]
    assert set(paid["event_name"]) <= {"subscription_start", "subscription_cancel"}


def test_sessions_are_anchored_to_real_match_moments(
    football_frames: dict[str, pd.DataFrame],
) -> None:
    matches = football_frames["dim_matches"]
    users, assignments = generate_users(800, pd.Timestamp(matches["match_date"].min()), 17)
    content = generate_content(matches, football_frames["dim_players"], 17)
    events = generate_app_events(
        25_000,
        users,
        assignments,
        matches,
        content,
        17,
        match_events=football_frames["fact_match_events"],
    )
    session_starts = events.groupby("session_id", as_index=False)["event_ts"].min()
    anchors = football_frames["fact_match_events"][["match_id", "event_ts"]]
    joined = session_starts.merge(
        events[["session_id", "match_id"]].drop_duplicates(), on="session_id"
    ).merge(anchors, on="match_id", suffixes=("_session", "_anchor"))
    within_ten_minutes = (
        (joined["event_ts_session"] - joined["event_ts_anchor"])
        .abs()
        .le(pd.Timedelta(minutes=10))
    )
    assert within_ten_minutes.any()
