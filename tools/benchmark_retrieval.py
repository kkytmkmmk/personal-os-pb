"""Read-only retrieval benchmark for a production or verification database.

This script does not initialize or migrate the database.  It temporarily
points the application retrieval layer at the selected existing SQLite file
and reports latency for representative Japanese queries.  The budget is a
regression guard for local development, not a public response-time SLO.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


DEFAULT_QUERIES = [
    "今の資産と毎月の積立を確認したい",
    "次の旅行先を過去の好みから考えたい",
    "住居候補と現在の家賃を比較したい",
    "最近の判断結果から次に気を付けることは？",
]


def run(database: Path, queries: list[str], iterations: int, budget_ms: float) -> dict[str, object]:
    if not database.exists():
        raise FileNotFoundError(database)
    previous_path = app.DB_PATH
    app.DB_PATH = database
    timings: list[dict[str, object]] = []
    try:
        # OneDrive/Windows can spend seconds hydrating the SQLite file on the
        # first access.  Warm the read-only connection/cache once so this
        # benchmark measures retrieval regressions, not storage cold-start.
        if queries:
            app.retrieval_context(queries[0])
        for query in queries:
            samples: list[float] = []
            counts: dict[str, int] = {}
            for _ in range(max(1, iterations)):
                started = time.perf_counter()
                context = app.retrieval_context(query)
                samples.append((time.perf_counter() - started) * 1000)
                counts = {
                    key: len(context.get(key, []))
                    for key in ("current", "decisions", "history", "profile", "raw")
                }
            ordered = sorted(samples)
            p95_index = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95)))
            timings.append({
                "query": query,
                "average_ms": round(statistics.mean(samples), 3),
                "p95_ms": round(ordered[p95_index], 3),
                "result_counts": counts,
            })
    finally:
        app.DB_PATH = previous_path
    worst_p95 = max((float(item["p95_ms"]) for item in timings), default=0.0)
    return {
        "database": str(database),
        "read_only": True,
        "warmup_runs": 1 if queries else 0,
        "iterations": max(1, iterations),
        "regression_budget_ms": budget_ms,
        "worst_p95_ms": round(worst_p95, 3),
        "within_budget": worst_p95 <= budget_ms,
        "queries": timings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/verification/personal_os_verification.db"))
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--budget-ms", type=float, default=2000.0)
    parser.add_argument("--query", action="append", dest="queries")
    args = parser.parse_args()
    result = run(args.db.resolve(), args.queries or DEFAULT_QUERIES, args.iterations, args.budget_ms)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["within_budget"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
