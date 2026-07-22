from __future__ import annotations

import pandas as pd

from sports_product_analytics.statsbomb import (
    normalize_events,
    normalize_lineups,
    normalize_matches,
    normalize_teams,
)


def test_statsbomb_normalizers_preserve_football_metrics() -> None:
    raw_matches = [
        {
            "match_id": 1,
            "match_date": "2022-12-18",
            "kick_off": "18:00:00",
            "competition": {"competition_id": 43, "competition_name": "FIFA World Cup"},
            "season": {"season_id": 106, "season_name": "2022"},
            "home_team": {"home_team_id": 10, "home_team_name": "Home"},
            "away_team": {"away_team_id": 20, "away_team_name": "Away"},
            "home_score": 3,
            "away_score": 3,
        }
    ]
    matches = normalize_matches(raw_matches)
    teams = normalize_teams(matches)
    raw_events = [
        {
            "id": "shot-1",
            "index": 2,
            "minute": 10,
            "second": 3,
            "period": 1,
            "type": {"id": 16, "name": "Shot"},
            "team": {"id": 10, "name": "Home"},
            "player": {"id": 99, "name": "Striker"},
            "possession_team": {"id": 10, "name": "Home"},
            "location": [102.0, 39.0],
            "shot": {
                "statsbomb_xg": 0.42,
                "outcome": {"id": 97, "name": "Goal"},
                "end_location": [120.0, 40.0, 1.0],
            },
        }
    ]
    events = normalize_events(raw_events, matches.iloc[0])
    assert teams["team_id"].tolist() == [10, 20]
    assert events.loc[0, "shot_xg"] == 0.42
    assert events.loc[0, "shot_outcome"] == "Goal"
    assert events.loc[0, "event_ts"] == pd.Timestamp("2022-12-18T18:10:03Z")


def test_lineups_are_flattened() -> None:
    players = normalize_lineups(
        [
            {
                "team_id": 10,
                "team_name": "Home",
                "lineup": [{"player_id": 99, "player_name": "Striker"}],
            }
        ]
    )
    assert players.to_dict("records") == [
        {"player_id": 99, "player_name": "Striker", "team_id": 10, "team_name": "Home"}
    ]

