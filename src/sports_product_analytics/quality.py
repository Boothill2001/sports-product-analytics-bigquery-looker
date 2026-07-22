"""Data-quality checks and reconciliation outputs for BigQuery and Looker."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from sports_product_analytics.contracts import PRIMARY_KEYS, TABLE_CONTRACTS


@dataclass(frozen=True)
class QualityResult:
    check_name: str
    status: str
    observed: int | float | str
    expected: int | float | str


def validate_frames(frames: dict[str, pd.DataFrame]) -> list[QualityResult]:
    results: list[QualityResult] = []
    for table, columns in TABLE_CONTRACTS.items():
        if table not in frames:
            results.append(QualityResult(f"{table}.present", "FAIL", 0, 1))
            continue
        frame = frames[table]
        missing_columns = sorted(set(columns) - set(frame.columns))
        results.append(
            QualityResult(
                f"{table}.schema",
                "PASS" if not missing_columns else "FAIL",
                ",".join(missing_columns) if missing_columns else "complete",
                "complete",
            )
        )
        keys = list(PRIMARY_KEYS[table])
        duplicate_count = (
            int(frame.duplicated(keys).sum()) if set(keys) <= set(frame.columns) else -1
        )
        results.append(
            QualityResult(
                f"{table}.primary_key_unique",
                "PASS" if duplicate_count == 0 else "FAIL",
                duplicate_count,
                0,
            )
        )
        null_keys = (
            int(frame[keys].isna().any(axis=1).sum())
            if set(keys) <= set(frame.columns)
            else -1
        )
        results.append(
            QualityResult(
                f"{table}.primary_key_not_null",
                "PASS" if null_keys == 0 else "FAIL",
                null_keys,
                0,
            )
        )

    if {"fact_app_events", "dim_users"} <= frames.keys():
        unknown = int(
            (~frames["fact_app_events"]["user_id"].isin(frames["dim_users"]["user_id"])).sum()
        )
        results.append(
            QualityResult("app_events.user_fk", "PASS" if unknown == 0 else "FAIL", unknown, 0)
        )

    if {"fact_app_events", "dim_matches"} <= frames.keys():
        unknown = int(
            (~frames["fact_app_events"]["match_id"].isin(frames["dim_matches"]["match_id"])).sum()
        )

    if {"fact_app_events", "dim_date"} <= frames.keys():
        unknown = int(
            (~frames["fact_app_events"]["event_date"].isin(frames["dim_date"]["date"])).sum()
        )
        results.append(
            QualityResult("app_events.date_fk", "PASS" if unknown == 0 else "FAIL", unknown, 0)
        )

    if {"fact_app_events", "dim_content"} <= frames.keys():
        content_ids = frames["fact_app_events"]["content_id"].dropna()
        unknown = int((~content_ids.isin(frames["dim_content"]["content_id"])).sum())
        results.append(
            QualityResult("app_events.content_fk", "PASS" if unknown == 0 else "FAIL", unknown, 0)
        )

    if {"dim_content", "dim_matches"} <= frames.keys():
        unknown = int(
            (~frames["dim_content"]["match_id"].isin(frames["dim_matches"]["match_id"])).sum()
        )
        results.append(
            QualityResult("content.match_fk", "PASS" if unknown == 0 else "FAIL", unknown, 0)
        )
        results.append(
            QualityResult("app_events.match_fk", "PASS" if unknown == 0 else "FAIL", unknown, 0)
        )

    if {"fact_match_events", "dim_matches"} <= frames.keys():
        unknown = int(
            (~frames["fact_match_events"]["match_id"].isin(frames["dim_matches"]["match_id"])).sum()
        )
        results.append(
            QualityResult("match_events.match_fk", "PASS" if unknown == 0 else "FAIL", unknown, 0)
        )
        xg = frames["fact_match_events"]["shot_xg"].dropna()
        invalid_xg = int((~xg.between(0, 1)).sum())
        results.append(
            QualityResult(
                "match_events.xg_range",
                "PASS" if invalid_xg == 0 else "FAIL",
                invalid_xg,
                0,
            )
        )

    if "fact_app_events" in frames:
        app_events = frames["fact_app_events"]
        backwards = int(
            app_events.groupby("session_id", sort=False)["event_ts"]
            .diff()
            .lt(pd.Timedelta(0))
            .sum()
        )
        results.append(
            QualityResult(
                "app_events.session_order",
                "PASS" if backwards == 0 else "FAIL",
                backwards,
                0,
            )
        )

    if "fact_experiment_assignments" in frames:
        assignments = frames["fact_experiment_assignments"]
        crossover = int(
            assignments.groupby(["user_id", "experiment_name"])["variant"]
            .nunique()
            .gt(1)
            .sum()
        )
        results.append(
            QualityResult(
                "experiment.no_crossover",
                "PASS" if crossover == 0 else "FAIL",
                crossover,
                0,
            )
        )

    return results


def quality_frame(results: list[QualityResult]) -> pd.DataFrame:
    generated_at = pd.Timestamp.now(tz="UTC")
    return pd.DataFrame(
        [
            {
                "check_name": item.check_name,
                "status": item.status,
                "observed": str(item.observed),
                "expected": str(item.expected),
                "checked_at": generated_at,
            }
            for item in results
        ]
    )


def assert_valid(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    results = validate_frames(frames)
    failures = [item for item in results if item.status == "FAIL"]
    if failures:
        detail = "; ".join(f"{item.check_name}={item.observed}" for item in failures)
        raise ValueError(f"Data quality failed: {detail}")
    return quality_frame(results)
