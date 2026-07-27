"""Read-only benchmark for analysis queue discovery.

Compares the former full active-chunk scan with the current query that only
returns chunks missing a Job for the selected provider/model/prompt.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import PROMPT_VERSION


def timed_fetch(connection: sqlite3.Connection, sql: str, params: tuple[str, ...], iterations: int) -> dict[str, float | int]:
    elapsed: list[float] = []
    rows = 0
    for _ in range(iterations):
        started = time.perf_counter()
        result = connection.execute(sql, params).fetchall()
        elapsed.append(time.perf_counter() - started)
        rows = len(result)
    return {
        "rows": rows,
        "average_ms": round(sum(elapsed) / len(elapsed) * 1000, 3),
        "minimum_ms": round(min(elapsed) * 1000, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/personal_os.db"))
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--provider")
    parser.add_argument("--model")
    args = parser.parse_args()

    database = args.db.resolve()
    connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
    try:
        settings = dict(connection.execute("SELECT key,value FROM app_settings"))
        provider = args.provider or settings.get("extract_provider", "local")
        if provider == "auto":
            provider = "local" if settings.get("local_llm_base_url") else "none"
        model_key = {
            "local": "local_llm_model",
            "gemini": "gemini_model",
            "openai": "openai_model",
        }.get(provider, "local_llm_model")
        model = args.model or settings.get(model_key, "")
        try:
            batch_size = max(1, min(200, int(settings.get("analysis_batch_size", "100"))))
        except ValueError:
            batch_size = 100
        common = """
            SELECT c.id,c.text
            FROM entries e
            JOIN documents d ON d.legacy_entry_id=e.id
            JOIN chunks c ON c.document_id=d.id AND c.is_active=1
            WHERE e.source IN ('chatgpt-export','ai-ingest')
        """
        legacy = timed_fetch(connection, common, (), max(1, args.iterations))
        indexes = {row[1] for row in connection.execute("PRAGMA index_list(analysis_jobs)")}
        index_ready = "idx_analysis_jobs_chunk_scope" in indexes
        optimized = (
            timed_fetch(
                connection,
                common + """
                  AND NOT EXISTS (
                    SELECT 1 FROM analysis_jobs current_job
                    WHERE current_job.job_kind='chunk'
                      AND current_job.source_chunk_id=c.id
                      AND current_job.provider=? AND current_job.model=?
                      AND current_job.prompt_version=?
                  )
                """,
                (provider, model, PROMPT_VERSION),
                max(1, args.iterations),
            )
            if index_ready
            else {"rows": 0, "average_ms": 0.0, "minimum_ms": 0.0}
        )
        speedup = (
            round(float(legacy["average_ms"]) / float(optimized["average_ms"]), 2)
            if index_ready and float(optimized["average_ms"]) > 0
            else None
        )
        print(json.dumps({
            "database": str(database),
            "read_only": True,
            "provider": provider,
            "model": model,
            "prompt_version": PROMPT_VERSION,
            "scope_index_ready": index_ready,
            "legacy_full_scan": legacy,
            "optimized_missing_job_scan": optimized,
            "query_speedup": speedup,
            "background_batch_size": batch_size,
            "full_queue_scans_per_batch": {"before": batch_size, "after": 1},
        }, ensure_ascii=False, indent=2))
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
