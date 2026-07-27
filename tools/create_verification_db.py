"""Create a small, disposable Personal OS database for migrations and LLM tests.

The production database is copied with SQLite's online backup API and then
trimmed in the copy.  The source database is never modified.  The resulting
database keeps a few real entries, their raw documents/chunks, related facts,
attachments and jobs, while dropping unrelated history so startup and tests
do not spend time or LLM budget on the complete export.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "personal_os.db"
DEFAULT_OUTPUT = ROOT / "data" / "verification" / "personal_os_verification.db"
PERSONAL_MARKERS = (
    "自分", "私", "今月", "資産", "積立", "投資", "持株", "旅行", "温泉",
    "家賃", "引っ越し", "仕事", "休日", "恋愛", "彼女", "彼氏", "友人",
)


def rows(connection: sqlite3.Connection, sql: str, params: tuple[object, ...] = ()) -> list[sqlite3.Row]:
    return list(connection.execute(sql, params).fetchall())


def ids(values: list[sqlite3.Row], key: str = "id") -> set[int]:
    return {int(row[key]) for row in values if row[key] is not None}


def marks(values: set[int]) -> str:
    return ",".join("?" for _ in values) or "NULL"


def choose_entries(connection: sqlite3.Connection, count: int) -> set[int]:
    all_rows = rows(
        connection,
        "SELECT id,title,body,source,created_at FROM entries "
        "WHERE source IN ('chatgpt-export','ai-ingest','screenshot') "
        "ORDER BY created_at DESC,id DESC",
    )
    fact_entry_ids = {
        int(row["legacy_entry_id"])
        for row in rows(
            connection,
            """SELECT DISTINCT d.legacy_entry_id
               FROM documents d JOIN facts f ON f.document_id=d.id
               WHERE d.legacy_entry_id IS NOT NULL""",
        )
    } if connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='facts'"
    ).fetchone() else set()
    scored = sorted(
        all_rows,
        key=lambda row: (
            int(row["id"]) in fact_entry_ids,
            sum(marker in f"{row['title']}\n{row['body']}" for marker in PERSONAL_MARKERS),
            row["created_at"] or "",
            int(row["id"]),
        ),
        reverse=True,
    )
    selected = scored[: max(1, count)]
    return ids(selected)


def retain_first_chunks(connection: sqlite3.Connection, document_ids: set[int], per_document: int) -> set[int]:
    if not document_ids:
        return set()
    kept: set[int] = set()
    has_facts = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='facts'"
    ).fetchone() is not None
    fact_priority = (
        "EXISTS(SELECT 1 FROM facts f WHERE f.source_chunk_id=chunks.id) DESC,"
        if has_facts else ""
    )
    for document_id in document_ids:
        chunk_rows = rows(
            connection,
            f"""SELECT id FROM chunks
                WHERE document_id=?
                ORDER BY {fact_priority} is_active DESC,ordinal,id
                LIMIT ?""",
            (document_id, max(1, per_document)),
        )
        kept.update(ids(chunk_rows))
    all_chunk_rows = rows(connection, "SELECT id FROM chunks WHERE document_id IN (" + marks(document_ids) + ")", tuple(document_ids))
    drop = ids(all_chunk_rows) - kept
    if drop:
        connection.execute("DELETE FROM chunks WHERE id IN (" + marks(drop) + ")", tuple(drop))
    return kept


def trim_database(connection: sqlite3.Connection, entry_ids: set[int], chunks_per_entry: int, analysis_jobs: int) -> dict[str, int]:
    connection.execute("PRAGMA foreign_keys=OFF")
    entry_clause = marks(entry_ids)
    documents = rows(connection, "SELECT id FROM documents WHERE legacy_entry_id IN (" + entry_clause + ")", tuple(entry_ids))
    document_ids = ids(documents)
    attachment_rows = rows(connection, "SELECT id FROM attachments WHERE entry_id IN (" + entry_clause + ")", tuple(entry_ids)) if entry_ids else []
    attachment_ids = ids(attachment_rows)
    chunk_ids = retain_first_chunks(connection, document_ids, chunks_per_entry)
    if document_ids:
        connection.execute("DELETE FROM chunks WHERE document_id NOT IN (" + marks(document_ids) + ")", tuple(document_ids))
    else:
        connection.execute("DELETE FROM chunks")

    # Delete rows owned by entries/documents/chunks/attachments before the
    # generic cleanup below.  Tables not mentioned here (settings, categories,
    # schema history) are intentionally kept so initialize() can migrate the
    # verification database exactly like production.
    table_columns: dict[str, set[str]] = {}
    for (table,) in rows(connection, "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        table_columns[table] = {row[1] for row in connection.execute(f"PRAGMA table_info([{table}])")}

    fact_ids: set[int] = set()
    for table, columns in table_columns.items():
        if table in {"entries", "documents", "chunks", "attachments"}:
            continue
        if "entry_id" in columns:
            connection.execute(f"DELETE FROM [{table}] WHERE entry_id NOT IN ({entry_clause})", tuple(entry_ids))
        if "source_entry_id" in columns:
            connection.execute(f"DELETE FROM [{table}] WHERE source_entry_id IS NOT NULL AND source_entry_id NOT IN ({entry_clause})", tuple(entry_ids))
        if "legacy_entry_id" in columns:
            connection.execute(f"DELETE FROM [{table}] WHERE legacy_entry_id IS NOT NULL AND legacy_entry_id NOT IN ({entry_clause})", tuple(entry_ids))
        if "document_id" in columns:
            clause = marks(document_ids)
            connection.execute(f"DELETE FROM [{table}] WHERE document_id NOT IN ({clause})", tuple(document_ids))
        if "source_chunk_id" in columns:
            clause = marks(chunk_ids)
            connection.execute(f"DELETE FROM [{table}] WHERE source_chunk_id IS NOT NULL AND source_chunk_id NOT IN ({clause})", tuple(chunk_ids))
        if "source_attachment_id" in columns:
            clause = marks(attachment_ids)
            connection.execute(f"DELETE FROM [{table}] WHERE source_attachment_id IS NOT NULL AND source_attachment_id NOT IN ({clause})", tuple(attachment_ids))

    # Keep the parent rows after dependent rows have been trimmed.
    connection.execute("DELETE FROM attachments WHERE entry_id NOT IN (" + entry_clause + ")", tuple(entry_ids))
    connection.execute("DELETE FROM documents WHERE legacy_entry_id NOT IN (" + entry_clause + ")", tuple(entry_ids))
    connection.execute("DELETE FROM entries WHERE id NOT IN (" + entry_clause + ")", tuple(entry_ids))

    fact_rows = rows(connection, "SELECT id FROM facts") if "facts" in table_columns else []
    fact_ids = ids(fact_rows)
    # Provenance/review tables can otherwise retain thousands of historical
    # rows even after their parent Fact was removed from the verification set.
    for table, columns in table_columns.items():
        if table == "facts" or "fact_id" not in columns:
            continue
        connection.execute(
            f"DELETE FROM [{table}] WHERE fact_id NOT IN (" + marks(fact_ids) + ")",
            tuple(fact_ids),
        )
    if "fact_id" in table_columns.get("fact_reviews", set()):
        connection.execute("DELETE FROM fact_reviews WHERE fact_id NOT IN (" + marks(fact_ids) + ")", tuple(fact_ids))

    # Limit pending analysis work.  Raw chunks remain available for manual
    # tests; only a small deterministic job set is runnable by the worker.
    if "analysis_jobs" in table_columns:
        job_rows = rows(
            connection,
            "SELECT id FROM analysis_jobs WHERE source_chunk_id IN (" + marks(chunk_ids) + ") ORDER BY id LIMIT ?",
            tuple(chunk_ids) + (max(0, analysis_jobs),),
        ) if chunk_ids else []
        keep_jobs = ids(job_rows)
        if keep_jobs:
            connection.execute("UPDATE analysis_jobs SET status='pending',attempts=0,error='',started_at=NULL,finished_at=NULL WHERE id IN (" + marks(keep_jobs) + ")", tuple(keep_jobs))
            connection.execute("DELETE FROM analysis_jobs WHERE id NOT IN (" + marks(keep_jobs) + ")", tuple(keep_jobs))
        else:
            connection.execute("DELETE FROM analysis_jobs")

    # Runtime coordination is local to a process, not user data. A copied
    # production lease/lock must never block the verification server.
    for volatile_table in ("runtime_leases", "analysis_locks"):
        if volatile_table in table_columns:
            connection.execute(f"DELETE FROM [{volatile_table}]")

    # Never spend LLM/GPU budget merely by starting the verification copy.
    # The developer can explicitly resume it from the verification UI/API.
    if "app_settings" in table_columns:
        connection.execute(
            "INSERT INTO app_settings(key,value,updated_at) VALUES('analysis_paused','true',datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value='true',updated_at=excluded.updated_at"
        )

    connection.execute("PRAGMA user_version=0")
    connection.commit()
    connection.execute("VACUUM")
    connection.commit()
    retained_jobs = (
        int(connection.execute("SELECT COUNT(*) FROM analysis_jobs").fetchone()[0])
        if "analysis_jobs" in table_columns
        else 0
    )
    return {
        "entries": len(entry_ids),
        "documents": len(document_ids),
        "chunks": len(chunk_ids),
        "attachments": len(attachment_ids),
        "facts": len(fact_ids),
        "analysis_jobs": retained_jobs,
    }


def create_verification_db(source: Path, output: Path, entry_count: int, chunks_per_entry: int, analysis_jobs: int) -> dict[str, object]:
    source = source.resolve()
    output = output.resolve()
    if source == output:
        raise ValueError("source and output must be different")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    with sqlite3.connect(source, timeout=30) as source_connection:
        source_connection.row_factory = sqlite3.Row
        entry_ids = choose_entries(source_connection, entry_count)
        destination = sqlite3.connect(temporary)
        try:
            source_connection.backup(destination)
        finally:
            destination.close()
    connection = sqlite3.connect(temporary, timeout=30)
    try:
        connection.row_factory = sqlite3.Row
        summary = trim_database(connection, entry_ids, chunks_per_entry, analysis_jobs)
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"verification database integrity check failed: {integrity}")
    finally:
        connection.close()
    temporary.replace(output)
    return {"source": str(source), "output": str(output), "summary": summary}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--entries", type=int, default=8, help="number of raw entries to retain")
    parser.add_argument("--chunks-per-entry", type=int, default=2)
    parser.add_argument("--analysis-jobs", type=int, default=20)
    args = parser.parse_args()
    print(json.dumps(create_verification_db(args.source, args.output, args.entries, args.chunks_per_entry, args.analysis_jobs), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
