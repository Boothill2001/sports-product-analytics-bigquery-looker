from __future__ import annotations

import pandas as pd
import pytest

from sports_product_analytics.quality import assert_valid, validate_frames


def test_complete_frames_pass(complete_frames: dict[str, pd.DataFrame]) -> None:
    result = assert_valid(complete_frames)
    assert set(result["status"]) == {"PASS"}
    assert "experiment.no_crossover" in set(result["check_name"])


def test_duplicate_primary_key_is_reported(
    complete_frames: dict[str, pd.DataFrame],
) -> None:
    broken = {key: value.copy() for key, value in complete_frames.items()}
    broken["dim_users"] = pd.concat(
        [broken["dim_users"], broken["dim_users"].iloc[[0]]], ignore_index=True
    )
    results = validate_frames(broken)
    check = next(item for item in results if item.check_name == "dim_users.primary_key_unique")
    assert check.status == "FAIL"
    assert check.observed == 1


def test_invalid_xg_fails_quality(complete_frames: dict[str, pd.DataFrame]) -> None:
    broken = {key: value.copy() for key, value in complete_frames.items()}
    broken["fact_match_events"].loc[0, "shot_xg"] = 1.4
    with pytest.raises(ValueError, match="xg_range"):
        assert_valid(broken)


def test_unknown_user_fails_foreign_key(complete_frames: dict[str, pd.DataFrame]) -> None:
    broken = {key: value.copy() for key, value in complete_frames.items()}
    broken["fact_app_events"].loc[0, "user_id"] = "UNKNOWN"
    with pytest.raises(ValueError, match="user_fk"):
        assert_valid(broken)


def test_experiment_crossover_is_detected(complete_frames: dict[str, pd.DataFrame]) -> None:
    broken = {key: value.copy() for key, value in complete_frames.items()}
    extra = broken["fact_experiment_assignments"].iloc[[0]].copy()
    extra["variant"] = "treatment" if extra.iloc[0]["variant"] == "control" else "control"
    broken["fact_experiment_assignments"] = pd.concat(
        [broken["fact_experiment_assignments"], extra], ignore_index=True
    )
    with pytest.raises(ValueError, match="experiment"):
        assert_valid(broken)

