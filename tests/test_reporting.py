from __future__ import annotations

from pathlib import Path

import pandas as pd

from sports_product_analytics.pipeline import write_frames
from sports_product_analytics.quality import assert_valid
from sports_product_analytics.reporting import (
    _ab_test,
    _executive_daily,
    _funnel,
    build_dashboard_extracts,
)


def test_executive_extract_has_core_product_metrics(
    complete_frames: dict[str, pd.DataFrame],
) -> None:
    daily = _executive_daily(complete_frames["fact_app_events"])
    assert {"dau", "mau", "stickiness", "arpu_usd", "active_viewers"} <= set(daily)
    assert daily["mau"].ge(daily["dau"]).all()


def test_funnel_and_ab_extracts_show_treatment_signal(
    complete_frames: dict[str, pd.DataFrame],
) -> None:
    funnel = _funnel(complete_frames["fact_app_events"])
    assert funnel["notification_users"].ge(funnel["subscription_users"]).all()
    ab_test = _ab_test(complete_frames).set_index("variant")
    assert ab_test.loc["treatment", "conversion_rate"] > ab_test.loc[
        "control", "conversion_rate"
    ]
    assert ab_test["ci_95_lower"].notna().all()


def test_dashboard_extracts_build_from_parquet(
    complete_frames: dict[str, pd.DataFrame], tmp_path: Path
) -> None:
    data_dir = tmp_path / "processed"
    output_dir = tmp_path / "dashboard"
    frames = {**complete_frames, "data_quality_results": assert_valid(complete_frames)}
    write_frames(frames, data_dir)

    summary = build_dashboard_extracts(data_dir, output_dir)

    assert summary["generated_from"]["app_events"] == 5_000
    assert summary["kpis"]["peak_dau"] > 0
    assert summary["top_match"]["match_label"]
    retention = summary["charts"]["retention"]
    retained_users = [
        sum(row[f"retained_d{day}"] for row in retention) for day in (1, 7, 30)
    ]
    assert retained_users[0] > retained_users[1] > retained_users[2]
    assert (output_dir / "dashboard-data.js").exists()
    assert (output_dir / "key_moments.csv").exists()
