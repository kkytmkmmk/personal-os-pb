"""Create a wholly synthetic Personal OS database for UX verification.

This utility never reads, copies, or opens the production database.  It is
used by the browser E2E runner and may also be run manually against an empty
temporary path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_NAMES = {"ux-synthetic.db"}
VERIFICATION_SUFFIX = ".verification.db"


class SeedSafetyError(ValueError):
    """Raised before the synthetic seed tool can touch an unsafe path."""


def _within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def production_database_paths(root: Path = ROOT) -> set[Path]:
    paths = {root.resolve() / "data" / "personal_os.db"}
    configured = os.environ.get("PERSONAL_OS_PRODUCTION_DB_PATH")
    if configured:
        paths.add(Path(configured).resolve())
    return {path.resolve() for path in paths}


def validate_seed_target(
    candidate: Path,
    *,
    environment: str | None = None,
    root: Path = ROOT,
    temporary_directory: Path | None = None,
    protected_paths: set[Path] | None = None,
) -> Path:
    """Return a safe resolved E2E target without creating or deleting it."""
    if environment != "verification":
        raise SeedSafetyError("Refusing to seed outside PERSONAL_OS_ENV=verification.")
    target = candidate.resolve()
    protected = {path.resolve() for path in (protected_paths or production_database_paths(root))}
    if target in protected:
        raise SeedSafetyError("Refusing to modify the production database.")
    if target.name not in ALLOWED_NAMES and not target.name.endswith(VERIFICATION_SUFFIX):
        raise SeedSafetyError("Refusing to modify a database without an approved verification name.")
    verification_root = (root.resolve() / "data" / "verification")
    temp_root = (temporary_directory or Path(tempfile.gettempdir())).resolve()
    if not (_within(target, verification_root) or _within(target, temp_root)):
        raise SeedSafetyError("Refusing to modify a database outside the temporary or data/verification directories.")
    # ``resolve`` above follows an existing symlink, so a link to a protected
    # file reaches the production comparison before any filesystem mutation.
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--replace", action="store_true", help="Replace an existing approved verification database")
    args = parser.parse_args()
    try:
        db_path = validate_seed_target(args.db, environment=os.environ.get("PERSONAL_OS_ENV"))
    except SeedSafetyError as error:
        parser.error(str(error))
    if db_path.exists():
        if not args.replace:
            parser.error("Refusing to replace an existing verification database without --replace.")
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["PERSONAL_OS_DB_PATH"] = str(db_path)
    os.environ["PERSONAL_OS_BACKUP_DIR"] = str(db_path.parent / "backups")
    os.environ["PERSONAL_OS_ATTACHMENT_DIR"] = str(db_path.parent / "attachments")

    sys.path.insert(0, str(ROOT))
    import app  # Imported only after the isolated database environment is set.

    app.initialize()
    stamp = "2026-07-29T10:00:00+09:00"

    def columns(connection, table: str) -> set[str]:
        return {str(row["name"]) for row in connection.execute(f"PRAGMA table_info({table})")}

    def insert(connection, table: str, values: dict[str, object]) -> int:
        accepted = {key: value for key, value in values.items() if key in columns(connection, table)}
        names = ",".join(accepted)
        marks = ",".join("?" for _ in accepted)
        return int(connection.execute(f"INSERT INTO {table} ({names}) VALUES ({marks})", tuple(accepted.values())).lastrowid)

    with app.db() as connection:
        document_id = insert(connection, "documents", {
            "title": "合成UXデモ会話",
            "source": "manual",
            "source_created_at": stamp,
            "ingested_at": stamp,
            "created_at": stamp,
            "updated_at": stamp,
        })
        source_text = "私は合成デモの資産、旅行、住居、人物予定を記録します。この文章は実在の個人情報ではありません。"
        chunk_id = insert(connection, "chunks", {
            "document_id": document_id,
            "ordinal": 0,
            "text": source_text,
            "text_hash": hashlib.sha256(source_text.encode()).hexdigest(),
            "segment_type": "demo",
            "segment_version": "ux-demo-v1",
            "speaker_role": "user",
            "source_type": "manual",
            "is_active": 1,
            "created_at": stamp,
        })

        entities: dict[str, int] = {}
        for entity_type, name in (("place", "サンプル市"), ("person", "サンプル利用者A"), ("person", "サンプル利用者B"), ("asset", "デモ投資信託")):
            entities[name] = insert(connection, "entities", {
                "entity_type": entity_type, "canonical_name": name, "created_at": stamp, "updated_at": stamp,
            })

        facts = [
            ("finance", "asset_balance", "finance.total_assets", "デモ総資産", {"amount": 12345678, "currency": "JPY"}, None),
            ("finance", "investment", "finance.monthly_investment.total", "デモ月間積立", {"amount": 123456, "currency": "JPY"}, None),
            ("finance", "asset_balance", "finance.asset_balance.index_fund", "デモ投資信託の残高", {"asset": "デモ投資信託", "amount": 4567890, "currency": "JPY"}, entities["デモ投資信託"]),
            ("travel", "plan", "travel.next_trip", "サンプル温泉旅行", {"place": "サンプル市", "date": "2026-08-15"}, entities["サンプル市"]),
            ("travel", "preference", "travel.preference.quiet_onsen", "静かな温泉が好き", {"value": "静かな温泉"}, None),
            ("travel", "visit", "travel.visited.sample_city", "サンプル市を訪問", {"place": "サンプル市", "amount": 24000, "currency": "JPY"}, entities["サンプル市"]),
            ("housing", "status", "housing.current.home", "デモ住居", {"area": "サンプル市", "layout": "1LDK", "size_sqm": 35}, None),
            ("housing", "rent", "housing.monthly_rent", "デモ月額家賃", {"amount": 89000, "currency": "JPY"}, None),
            ("housing", "preference", "housing.preference", "明るいキッチンを希望", {"value": "明るいキッチン"}, None),
            ("relationship", "relationship", "relationship.sample_user_a", "サンプル利用者Aさんはボードゲームが好き", {"value": "ボードゲーム"}, entities["サンプル利用者A"]),
            ("relationship", "plan", "relationship.next_plan.sample_user_b", "サンプル利用者Bさんと会う予定", {"date": "2026-08-10"}, entities["サンプル利用者B"]),
        ]
        fact_ids: list[int] = []
        for category, fact_type, fact_key, summary, value, entity_id in facts:
            fact_id = insert(connection, "facts", {
                "document_id": document_id,
                "chunk_id": chunk_id,
                "source_chunk_id": chunk_id,
                "subject_entity_id": entity_id,
                "subject_scope": "person" if category == "relationship" else "self",
                "resolved_entity_type": "person" if category == "relationship" else "unknown",
                "personal_relevance": "personal",
                "extraction_confidence": 0.98,
                "truth_confidence": 0.98,
                "evidence_support_count": 1,
                "retrieval_eligibility": "eligible",
                "category": category,
                "fact_type": fact_type,
                "occurred_on": "2026-07-29",
                "valid_from": "2026-07-29",
                "status": "current",
                "fact_key": fact_key,
                "value_json": json.dumps(value, ensure_ascii=False),
                "summary": summary,
                "confidence": 0.98,
                "extractor": "synthetic-fixture",
                "extractor_model": "none",
                "prompt_version": "ux-demo-v1",
                "extracted_at": stamp,
                "created_at": stamp,
            })
            fact_ids.append(fact_id)
            insert(connection, "fact_reviews", {
                "fact_id": fact_id, "state": "confirmed", "reason": "ユーザー確認済み（合成検証用）",
                "review_note": "No personal data", "reviewed_at": stamp, "created_at": stamp,
            })
            insert(connection, "fact_evidence", {
                "fact_id": fact_id, "evidence_kind": "synthetic", "source_chunk_id": chunk_id,
                "source_group": "ux-demo", "source_identity": "synthetic-only", "quote": source_text,
                "support": "supports", "reliability": 1.0, "created_at": stamp,
            })

        # A semantic before/after pair lets the Timeline E2E exercise the
        # non-mutating "今と比べる" route with wholly synthetic data.
        old_housing_id = insert(connection, "facts", {
            "document_id": document_id, "chunk_id": chunk_id, "source_chunk_id": chunk_id,
            "subject_scope": "self", "resolved_entity_type": "unknown", "personal_relevance": "personal",
            "extraction_confidence": 0.98, "truth_confidence": 0.98, "evidence_support_count": 1,
            "retrieval_eligibility": "eligible", "category": "housing", "fact_type": "status",
            "occurred_on": "2026-04-01", "valid_from": "2026-04-01", "status": "superseded",
            "fact_key": "housing.current.home", "value_json": json.dumps({"layout": "1R", "size_sqm": 25}, ensure_ascii=False),
            "summary": "以前のデモ住居", "confidence": 0.98, "extractor": "synthetic-fixture",
            "extractor_model": "none", "prompt_version": "ux-demo-v1", "extracted_at": stamp, "created_at": stamp,
        })
        insert(connection, "fact_reviews", {"fact_id": old_housing_id, "state": "confirmed", "reason": "Synthetic timeline fixture", "reviewed_at": stamp, "created_at": stamp})
        insert(connection, "fact_evidence", {"fact_id": old_housing_id, "evidence_kind": "synthetic", "source_chunk_id": chunk_id, "source_group": "ux-demo", "source_identity": "synthetic-only", "quote": source_text, "support": "supports", "reliability": 1.0, "created_at": stamp})
        connection.execute("UPDATE facts SET supersedes_fact_id=? WHERE id=?", (old_housing_id, fact_ids[6]))

        insert(connection, "finance_transactions", {
            "fact_id": fact_ids[1], "asset_entity_id": entities["デモ投資信託"], "amount": 123456,
            "normalized_amount": 123456, "currency": "JPY", "transaction_type": "investment", "transaction_kind": "investment",
            "actor": "user", "is_actual": 1, "eligibility_state": "confirmed", "eligibility_reason": "Synthetic fixture",
            "occurred_on": "2026-07-29",
        })
        for domain, title, decision, result in (
            ("travel", "サンプル旅行計画", "移動時間が短い経路を選ぶ", "移動時間を短くできて良かった。"),
            ("finance", "デモ資産配分の見直し", "月間積立を維持する", ""),
            ("housing", "デモ住居比較", "日当たりを優先して探す", ""),
            ("relationship", "デモ会話の計画", "ボードゲームについて聞く", ""),
        ):
            insert(connection, "decisions", {
                "domain": domain, "title": title, "context": "Synthetic UX fixture", "options_json": json.dumps(["Option A", "Option B"]),
                "decision": decision, "selected_option": decision, "rationale": "Synthetic rationale", "status": "decided",
                "decision_state": "result" if result else ("executed" if domain == "finance" else "decided"), "result": result, "decided_on": "2026-07-29",
                "created_at": stamp, "updated_at": stamp,
            })
        # A complete, explicitly user-owned lifecycle is kept separate from
        # the recommendation that preceded it.  It is synthetic-only and
        # drives the Decision Replay acceptance journey.
        recommendation_id = insert(connection, "recommendations", {
            "domain": "travel", "title": "Sample weekend proposal", "rationale": "Keep transfer time short.",
            "options_json": json.dumps(["Sample hot spring", "Sample city walk"], ensure_ascii=False),
            "criteria_json": "[]", "source_fact_ids_json": "[]", "source_decision_ids_json": "[]",
            "source_evidence_ids_json": "[]", "context_json": "{}", "tradeoffs_json": "[]", "missing_context_json": "[]",
            "status": "accepted", "created_at": "2026-07-01T09:00:00+09:00", "updated_at": "2026-07-01T09:00:00+09:00",
        })
        replay_decision_id = insert(connection, "decisions", {
            "domain": "travel", "title": "Sample weekend decision", "context": "A short weekend is available.",
            "question": "How should the weekend be used?", "options_json": json.dumps(["Sample hot spring", "Sample city walk"], ensure_ascii=False),
            "decision": "Choose Sample hot spring", "selected_option": "Sample hot spring", "rationale": "Shorter travel time.",
            "status": "decided", "decision_state": "result", "decided_on": "2026-07-02", "result": "It was relaxing.",
            "later_evaluation": "次回: keep the transfer time short.", "source_recommendation_id": recommendation_id,
            "outcome_recorded_at": "2026-07-04", "evaluation_recorded_at": "2026-07-10", "related_fact_ids_json": "[]",
            "related_entity_ids_json": "[]", "created_at": "2026-07-01T09:00:00+09:00", "updated_at": "2026-07-10T09:00:00+09:00",
        })
        insert(connection, "execution_events", {
            "decision_id": replay_decision_id, "plan_id": None, "event_type": "executed", "summary": "User completed the sample trip.",
            "source_entry_id": None, "source_chunk_id": None, "occurred_at": "2026-07-03", "created_at": "2026-07-03T12:00:00+09:00",
        })
        connection.commit()
    print(f"Synthetic UX demo database created: {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
