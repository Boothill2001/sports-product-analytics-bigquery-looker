from __future__ import annotations

import pandas as pd
import pytest

from sports_product_analytics.synthetic import (
    generate_app_events,
    generate_campaign_spend,
    generate_content,
    generate_date_dimension,
    generate_users,
)


@pytest.fixture
def football_frames() -> dict[str, pd.DataFrame]:
    matches = pd.DataFrame(
        [
            {
                "match_id": 1001,
                "match_date": pd.Timestamp("2022-12-10").date(),
                "kick_off": "18:00:00",
                "competition_id": 43,
                "competition_name": "FIFA World Cup",
                "season_id": 106,
                "season_name": "2022",
                "home_team_id": 1,
                "home_team_name": "Alpha",
                "away_team_id": 2,
                "away_team_name": "Beta",
                "home_score": 2,
                "away_score": 1,
            },
            {
                "match_id": 1002,
                "match_date": pd.Timestamp("2022-12-11").date(),
                "kick_off": "20:00:00",
                "competition_id": 43,
                "competition_name": "FIFA World Cup",
                "season_id": 106,
                "season_name": "2022",
                "home_team_id": 3,
                "home_team_name": "Gamma",
                "away_team_id": 4,
                "away_team_name": "Delta",
                "home_score": 0,
                "away_score": 0,
            },
        ]
    )
    teams = pd.DataFrame(
        {
            "team_id": [1, 2, 3, 4],
            "team_name": ["Alpha", "Beta", "Gamma", "Delta"],
        }
    )
    players = pd.DataFrame(
        {
            "player_id": [11, 12, 13, 14],
            "player_name": ["One", "Two", "Three", "Four"],
            "team_id": [1, 2, 3, 4],
            "team_name": ["Alpha", "Beta", "Gamma", "Delta"],
        }
    )
    match_events = pd.DataFrame(
        {
            "event_id": ["M1", "M2"],
            "match_id": [1001, 1002],
            "event_index": [1, 1],
            "event_ts": pd.to_datetime(["2022-12-10T18:01:00Z", "2022-12-11T20:02:00Z"]),
            "period": [1, 1],
            "minute": [1, 2],
            "second": [0, 0],
            "event_type": ["Shot", "Pass"],
            "team_id": [1, 3],
            "player_id": [11, 13],
            "possession_team_id": [1, 3],
            "x": [101.0, 42.0],
            "y": [40.0, 32.0],
            "end_x": [120.0, 60.0],
            "end_y": [40.0, 35.0],
            "shot_xg": [0.33, None],
            "shot_outcome": ["Goal", None],
            "pass_outcome": ["Complete", "Complete"],
            "duel_type": [None, None],
            "under_pressure": [False, True],
            "duration_seconds": [0.4, 1.1],
        }
    )
    return {
        "dim_matches": matches,
        "dim_teams": teams,
        "dim_players": players,
        "fact_match_events": match_events,
    }


@pytest.fixture
def complete_frames(football_frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    matches = football_frames["dim_matches"]
    users, assignments = generate_users(250, pd.Timestamp(matches["match_date"].min()), 42)
    content = generate_content(matches, football_frames["dim_players"], 42)
    app_events = generate_app_events(5_000, users, assignments, matches, content, 42)
    date_dimension = generate_date_dimension(
        users["signup_date"].min(), app_events["event_date"].max()
    )
    return {
        **football_frames,
        "dim_date": date_dimension,
        "dim_users": users,
        "dim_content": content,
        "fact_app_events": app_events,
        "fact_campaign_spend": generate_campaign_spend(users, matches, 42),
        "fact_experiment_assignments": assignments,
    }
