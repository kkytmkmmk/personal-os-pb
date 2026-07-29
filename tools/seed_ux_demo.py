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
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, type=Path)
    args = parser.parse_args()
    db_path = args.db.resolve()
    if db_path.exists():
        db_path.unlink()
    os.environ["PERSONAL_OS_ENV"] = "verification"
    os.environ["PERSONAL_OS_DB_PATH"] = str(db_path)
    os.environ["PERSONAL_OS_BACKUP_DIR"] = str(db_path.parent / "backups")
    os.environ["PERSONAL_OS_ATTACHMENT_DIR"] = str(db_path.parent / "attachments")

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
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
                "decision_state": "executed" if result else "decided", "result": result, "decided_on": "2026-07-29",
                "created_at": stamp, "updated_at": stamp,
            })
        connection.commit()
    print(f"Synthetic UX demo database created: {db_path}")


if __name__ == "__main__":
    main()
