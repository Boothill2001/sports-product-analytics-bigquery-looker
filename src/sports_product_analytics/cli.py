"""Command-line entrypoints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sports_product_analytics.bigquery import (
    dry_run_sql_directory,
    execute_sql_directory,
    load_parquet_directory,
)
from sports_product_analytics.pipeline import PipelineConfig, run_pipeline
from sports_product_analytics.reporting import build_dashboard_extracts


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sports product analytics portfolio pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser(
        "generate", help="Download football data and generate app data"
    )
    generate.add_argument("--events", type=int, default=1_200_000)
    generate.add_argument("--users", type=int, default=25_000)
    generate.add_argument("--matches", type=int, default=8)
    generate.add_argument("--seed", type=int, default=42)
    generate.add_argument("--output", type=Path, default=Path("data/processed"))
    generate.add_argument("--cache", type=Path, default=Path("data/cache/statsbomb"))

    extracts = subparsers.add_parser(
        "build-extracts", help="Build compact dashboard CSV and JavaScript sources"
    )
    extracts.add_argument("--data", type=Path, default=Path("data/processed"))
    extracts.add_argument("--output", type=Path, default=Path("dashboard/data"))

    for name in ("load-bigquery", "dry-run", "build-marts"):
        command = subparsers.add_parser(name)
        command.add_argument("--project", required=True)
        command.add_argument("--location", default="asia-southeast1")
        command.add_argument("--dataset", default="sports_product_analytics")
        command.add_argument("--data", type=Path, default=Path("data/processed"))
        command.add_argument("--sql", type=Path, default=Path("sql"))
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "generate":
        result = run_pipeline(
            PipelineConfig(
                output_dir=args.output,
                cache_dir=args.cache,
                max_matches=args.matches,
                n_users=args.users,
                n_app_events=args.events,
                seed=args.seed,
            )
        )
    elif args.command == "build-extracts":
        result = build_dashboard_extracts(args.data, args.output)
    elif args.command == "load-bigquery":
        result = load_parquet_directory(args.project, args.dataset, args.data, args.location)
    elif args.command == "dry-run":
        result = dry_run_sql_directory(args.project, args.sql, args.location)
    else:
        result = execute_sql_directory(args.project, args.sql, args.location)
    print(json.dumps(result, indent=2))
