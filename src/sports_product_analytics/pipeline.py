"""End-to-end orchestration for football and product analytics data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from sports_product_analytics.quality import assert_valid
from sports_product_analytics.statsbomb import load_football_data
from sports_product_analytics.synthetic import (
    generate_app_events,
    generate_campaign_spend,
    generate_content,
    generate_date_dimension,
    generate_users,
)


@dataclass(frozen=True)
class PipelineConfig:
    output_dir: Path = Path("data/processed")
    cache_dir: Path = Path("data/cache/statsbomb")
    competition_id: int = 43
    season_id: int = 106
    max_matches: int = 8
    n_users: int = 25_000
    n_app_events: int = 1_200_000
    seed: int = 42


def build_frames(config: PipelineConfig) -> dict[str, pd.DataFrame]:
    frames = load_football_data(
        cache_dir=config.cache_dir,
        competition_id=config.competition_id,
        season_id=config.season_id,
        max_matches=config.max_matches,
    )
    min_match_date = pd.Timestamp(frames["dim_matches"]["match_date"].min())
    users, assignments = generate_users(config.n_users, min_match_date, config.seed)
    content = generate_content(frames["dim_matches"], frames["dim_players"], config.seed)
    campaign_spend = generate_campaign_spend(users, frames["dim_matches"], config.seed)
    app_events = generate_app_events(
        config.n_app_events,
        users,
        assignments,
        frames["dim_matches"],
        content,
        config.seed,
        match_events=frames["fact_match_events"],
    )
    date_dimension = generate_date_dimension(
        users["signup_date"].min(),
        max(app_events["event_date"].max(), campaign_spend["spend_date"].max()),
    )
    frames.update(
        {
            "dim_date": date_dimension,
            "dim_users": users,
            "dim_content": content,
            "fact_app_events": app_events,
            "fact_campaign_spend": campaign_spend,
            "fact_experiment_assignments": assignments,
        }
    )
    frames["data_quality_results"] = assert_valid(frames)
    return frames


def write_frames(frames: dict[str, pd.DataFrame], output_dir: Path) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    row_counts: dict[str, int] = {}
    for table, frame in frames.items():
        frame.to_parquet(output_dir / f"{table}.parquet", index=False)
        row_counts[table] = len(frame)

    targets = frames["fact_campaign_spend"][
        ["spend_date", "channel", "target_spend_usd"]
    ].copy()
    targets.to_csv(output_dir / "campaign_targets_for_sheets.csv", index=False)
    frames["fact_app_events"].head(5_000).to_csv(
        output_dir / "app_events_sample.csv", index=False
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(row_counts, indent=2), encoding="utf-8"
    )
    return row_counts


def run_pipeline(config: PipelineConfig) -> dict[str, int]:
    return write_frames(build_frames(config), config.output_dir)
