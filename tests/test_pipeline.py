from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from sports_product_analytics.pipeline import write_frames


def test_write_frames_creates_reproducible_artifacts(
    complete_frames: dict[str, pd.DataFrame], tmp_path: Path
) -> None:
    quality = pd.DataFrame(
        {
            "check_name": ["fixture"],
            "status": ["PASS"],
            "observed": ["1"],
            "expected": ["1"],
            "checked_at": [pd.Timestamp("2022-01-01", tz="UTC")],
        }
    )
    frames = {**complete_frames, "data_quality_results": quality}
    counts = write_frames(frames, tmp_path)
    assert counts["fact_app_events"] == 5_000
    assert (tmp_path / "fact_app_events.parquet").exists()
    assert (tmp_path / "campaign_targets_for_sheets.csv").exists()
    assert json.loads((tmp_path / "manifest.json").read_text())["dim_users"] == 250

