"""Bounded synthetic performance check for Review Inbox bucket queries."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

if os.environ.get("PERSONAL_OS_ENV") != "verification":
    raise SystemExit("PERSONAL_OS_ENV=verification is required")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app  # noqa: E402


def run_case(size: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="personal-os-review-performance-") as directory:
        root = Path(directory)
        previous = (app.DB_PATH, app.BACKUP_DIR, app.ATTACHMENT_DIR)
        app.DB_PATH = root / "ux-synthetic.db"
        app.BACKUP_DIR = root / "backups"
        app.ATTACHMENT_DIR = root / "attachments"
        try:
            app.initialize()
            stamp = "2026-01-01T00:00:00+00:00"
            with app.db() as connection:
                document_id = connection.execute(
                    "INSERT INTO documents(title,source,source_created_at,ingested_at,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                    ("Synthetic performance source", "manual", stamp, stamp, stamp, stamp),
                ).lastrowid
                chunk_id = connection.execute(
                    "INSERT INTO chunks(document_id,ordinal,text,text_hash,created_at) VALUES(?,?,?,?,?)",
                    (document_id, 0, "Synthetic performance evidence", f"performance-{size}", stamp),
                ).lastrowid
                rows = [
                    (document_id, chunk_id, chunk_id, "life", "preference", f"life.performance.{index}", "{}",
                     f"Synthetic normal {index}", .6, .6, "synthetic", "none", "performance-v1", stamp,
                     "pending", "pending", "unknown", "personal")
                    for index in range(size)
                ]
                connection.executemany(
                    """INSERT INTO facts(document_id,chunk_id,source_chunk_id,category,fact_type,fact_key,value_json,summary,
                              confidence,truth_confidence,extractor,extractor_model,prompt_version,created_at,
                              retrieval_eligibility,validation_status,status,personal_relevance)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows,
                )
                fact_ids = [row[0] for row in connection.execute("SELECT id FROM facts WHERE fact_key LIKE 'life.performance.%' ORDER BY id")]
                connection.executemany(
                    "INSERT INTO fact_reviews(fact_id,state,reason,created_at) VALUES(?,'pending','Synthetic performance',?)",
                    [(fact_id, stamp) for fact_id in fact_ids],
                )
                urgent_id = connection.execute(
                    """INSERT INTO facts(document_id,chunk_id,source_chunk_id,category,fact_type,fact_key,value_json,summary,
                              confidence,truth_confidence,extractor,extractor_model,prompt_version,created_at,
                              retrieval_eligibility,validation_status,status,personal_relevance)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (document_id,chunk_id,chunk_id,"life","status","life.performance.urgent","{}","Synthetic final conflict",.6,.6,
                     "synthetic","none","performance-v1","2026-12-31T00:00:00+00:00","conflict","conflict","unknown","personal"),
                ).lastrowid
                connection.execute("INSERT INTO fact_reviews(fact_id,state,reason,created_at) VALUES(?,'pending','Synthetic conflict',?)", (urgent_id, stamp))

            measurements: dict[str, object] = {"size": size}
            for name, call in (
                ("action_center", app.action_center_projection),
                ("urgent_10", lambda: app.review_inbox_projection("urgent", limit=10)),
                ("normal_10", lambda: app.review_inbox_projection("normal", limit=10)),
            ):
                started = time.perf_counter(); result = call(); elapsed = time.perf_counter() - started
                measurements[name] = {"seconds": round(elapsed, 4), "bytes": len(json.dumps(result, ensure_ascii=False))}
                if name == "action_center" and result["top_action"].get("id") != urgent_id:
                    raise AssertionError("Action Center lost the final urgent Fact")
                if name.endswith("_10") and len(result["items"]) > 10:
                    raise AssertionError("Review response exceeded its requested limit")
            return measurements
        finally:
            app.DB_PATH, app.BACKUP_DIR, app.ATTACHMENT_DIR = previous


if __name__ == "__main__":
    print(json.dumps([run_case(1100), run_case(5000)], ensure_ascii=False, indent=2))
