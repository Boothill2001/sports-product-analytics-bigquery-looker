"""Download and normalize a small, attributed slice of StatsBomb Open Data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"


class StatsBombClient:
    """Cached client for the public StatsBomb JSON repository."""

    def __init__(self, cache_dir: Path, timeout_seconds: int = 30) -> None:
        self.cache_dir = cache_dir
        self.timeout_seconds = timeout_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504))
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def _get_json(self, relative_path: str) -> Any:
        cache_file = self.cache_dir / relative_path
        if cache_file.exists():
            return json.loads(cache_file.read_text(encoding="utf-8"))

        response = self.session.get(
            f"{BASE_URL}/{relative_path}", timeout=self.timeout_seconds
        )
        response.raise_for_status()
        payload = response.json()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return payload

    def matches(self, competition_id: int, season_id: int) -> list[dict[str, Any]]:
        return self._get_json(f"matches/{competition_id}/{season_id}.json")

    def events(self, match_id: int) -> list[dict[str, Any]]:
        return self._get_json(f"events/{match_id}.json")

    def lineups(self, match_id: int) -> list[dict[str, Any]]:
        return self._get_json(f"lineups/{match_id}.json")


def _nested_id(value: Any) -> int | None:
    return value.get("id") if isinstance(value, dict) else None


def _nested_name(value: Any) -> str | None:
    return value.get("name") if isinstance(value, dict) else None


def _location(value: Any, index: int) -> float | None:
    if isinstance(value, list) and len(value) > index:
        return float(value[index])
    return None


def normalize_matches(raw_matches: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for match in raw_matches:
        rows.append(
            {
                "match_id": int(match["match_id"]),
                "match_date": pd.to_datetime(match["match_date"]).date(),
                "kick_off": str(match.get("kick_off", "00:00:00")),
                "competition_id": int(match["competition"]["competition_id"]),
                "competition_name": match["competition"]["competition_name"],
                "season_id": int(match["season"]["season_id"]),
                "season_name": match["season"]["season_name"],
                "home_team_id": int(match["home_team"]["home_team_id"]),
                "home_team_name": match["home_team"]["home_team_name"],
                "away_team_id": int(match["away_team"]["away_team_id"]),
                "away_team_name": match["away_team"]["away_team_name"],
                "home_score": int(match.get("home_score", 0)),
                "away_score": int(match.get("away_score", 0)),
            }
        )
    return pd.DataFrame(rows).sort_values(["match_date", "match_id"]).reset_index(drop=True)


def normalize_teams(matches: pd.DataFrame) -> pd.DataFrame:
    home = matches[["home_team_id", "home_team_name"]].rename(
        columns={"home_team_id": "team_id", "home_team_name": "team_name"}
    )
    away = matches[["away_team_id", "away_team_name"]].rename(
        columns={"away_team_id": "team_id", "away_team_name": "team_name"}
    )
    return (
        pd.concat([home, away], ignore_index=True)
        .drop_duplicates("team_id")
        .reset_index(drop=True)
    )


def normalize_lineups(raw_lineups: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for team in raw_lineups:
        team_id = int(team["team_id"])
        team_name = team["team_name"]
        for player in team.get("lineup", []):
            rows.append(
                {
                    "player_id": int(player["player_id"]),
                    "player_name": player["player_name"],
                    "team_id": team_id,
                    "team_name": team_name,
                }
            )
    return pd.DataFrame(rows)


def normalize_events(
    raw_events: list[dict[str, Any]], match: pd.Series
) -> pd.DataFrame:
    kickoff = pd.Timestamp(f"{match['match_date']} {match['kick_off']}", tz="UTC")
    rows: list[dict[str, Any]] = []
    for event in raw_events:
        event_type = _nested_name(event.get("type"))
        location = event.get("location")
        pass_data = event.get("pass") or {}
        shot_data = event.get("shot") or {}
        duel_data = event.get("duel") or {}
        end_location = pass_data.get("end_location") or shot_data.get("end_location")
        rows.append(
            {
                "event_id": str(event["id"]),
                "match_id": int(match["match_id"]),
                "event_index": int(event.get("index", 0)),
                "event_ts": kickoff
                + pd.Timedelta(minutes=int(event.get("minute", 0)))
                + pd.Timedelta(seconds=int(event.get("second", 0))),
                "period": int(event.get("period", 1)),
                "minute": int(event.get("minute", 0)),
                "second": int(event.get("second", 0)),
                "event_type": event_type,
                "team_id": _nested_id(event.get("team")),
                "player_id": _nested_id(event.get("player")),
                "possession_team_id": _nested_id(event.get("possession_team")),
                "x": _location(location, 0),
                "y": _location(location, 1),
                "end_x": _location(end_location, 0),
                "end_y": _location(end_location, 1),
                "shot_xg": float(shot_data["statsbomb_xg"])
                if shot_data.get("statsbomb_xg") is not None
                else None,
                "shot_outcome": _nested_name(shot_data.get("outcome")),
                "pass_outcome": _nested_name(pass_data.get("outcome")) or "Complete",
                "duel_type": _nested_name(duel_data.get("type")),
                "under_pressure": bool(event.get("under_pressure", False)),
                "duration_seconds": float(event.get("duration", 0.0) or 0.0),
            }
        )
    return pd.DataFrame(rows).sort_values(["match_id", "event_index"]).reset_index(drop=True)


def load_football_data(
    cache_dir: Path,
    competition_id: int,
    season_id: int,
    max_matches: int,
) -> dict[str, pd.DataFrame]:
    """Return normalized matches, teams, players and events from real open data."""

    client = StatsBombClient(cache_dir)
    matches = normalize_matches(client.matches(competition_id, season_id)).tail(max_matches)
    event_frames: list[pd.DataFrame] = []
    player_frames: list[pd.DataFrame] = []

    for _, match in matches.iterrows():
        match_id = int(match["match_id"])
        event_frames.append(normalize_events(client.events(match_id), match))
        player_frames.append(normalize_lineups(client.lineups(match_id)))

    events = pd.concat(event_frames, ignore_index=True)
    players = (
        pd.concat(player_frames, ignore_index=True)
        .drop_duplicates("player_id")
        .reset_index(drop=True)
    )
    return {
        "dim_matches": matches.reset_index(drop=True),
        "dim_teams": normalize_teams(matches),
        "dim_players": players,
        "fact_match_events": events,
    }
