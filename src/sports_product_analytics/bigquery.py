"""Optional BigQuery loader and dry-run validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sports_product_analytics.contracts import BIGQUERY_LAYOUT


def _bigquery() -> Any:
    try:
        from google.cloud import bigquery
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("Install cloud dependencies: pip install -e '.[cloud]'") from exc
    return bigquery


def ensure_dataset(project_id: str, dataset_id: str, location: str = "asia-southeast1") -> None:
    bigquery = _bigquery()
    client = bigquery.Client(project=project_id)
    dataset = bigquery.Dataset(f"{project_id}.{dataset_id}")
    dataset.location = location
    client.create_dataset(dataset, exists_ok=True)


def load_parquet_directory(
    project_id: str,
    dataset_id: str,
    data_dir: Path,
    location: str = "asia-southeast1",
) -> dict[str, int]:
    bigquery = _bigquery()
    ensure_dataset(project_id, dataset_id, location)
    client = bigquery.Client(project=project_id, location=location)
    loaded: dict[str, int] = {}

    for parquet_file in sorted(data_dir.glob("*.parquet")):
        table = parquet_file.stem
        if table == "data_quality_results":
            layout: dict[str, object] = {}
        elif table in BIGQUERY_LAYOUT:
            layout = BIGQUERY_LAYOUT[table]
        else:
            continue
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        partition = layout.get("partition")
        if partition:
            job_config.time_partitioning = bigquery.TimePartitioning(
                type_=getattr(
                    bigquery.TimePartitioningType,
                    str(layout.get("partition_type", "DAY")),
                ),
                field=str(partition),
            )
        clusters = layout.get("clusters")
        if clusters:
            job_config.clustering_fields = list(clusters)
        with parquet_file.open("rb") as handle:
            job = client.load_table_from_file(
                handle,
                f"{project_id}.{dataset_id}.{table}",
                job_config=job_config,
                location=location,
            )
        job.result()
        loaded[table] = int(client.get_table(job.destination).num_rows)
    return loaded


def dry_run_sql_directory(
    project_id: str,
    sql_dir: Path,
    location: str = "asia-southeast1",
) -> dict[str, int]:
    bigquery = _bigquery()
    client = bigquery.Client(project=project_id, location=location)
    results: dict[str, int] = {}
    config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    for sql_file in sorted(sql_dir.glob("[0-9][1-9]_*.sql")):
        query = sql_file.read_text(encoding="utf-8")
        job = client.query(query, job_config=config, location=location)
        results[sql_file.name] = int(job.total_bytes_processed or 0)
    return results


def execute_sql_directory(
    project_id: str,
    sql_dir: Path,
    location: str = "asia-southeast1",
) -> list[str]:
    bigquery = _bigquery()
    client = bigquery.Client(project=project_id, location=location)
    completed: list[str] = []
    for sql_file in sorted(sql_dir.glob("[0-9][1-9]_*.sql")):
        client.query(sql_file.read_text(encoding="utf-8"), location=location).result()
        completed.append(sql_file.name)
    return completed

