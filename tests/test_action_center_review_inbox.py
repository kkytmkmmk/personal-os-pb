import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import app


class ActionCenterReviewInboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = (app.DB_PATH, app.BACKUP_DIR, app.ATTACHMENT_DIR, app.ANALYSIS_PREFILTER_SCOPE)
        root = Path(self.temp.name)
        app.DB_PATH = root / "ux-synthetic.db"
        app.BACKUP_DIR = root / "backups"
        app.ATTACHMENT_DIR = root / "attachments"
        app.ANALYSIS_PREFILTER_SCOPE = None
        app.initialize()
        self.stamp = "2026-01-01T00:00:00+00:00"
        with app.db() as connection:
            self.document_id = connection.execute(
                "INSERT INTO documents(title,source,source_created_at,ingested_at,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                ("合成原文", "manual", self.stamp, self.stamp, self.stamp, self.stamp),
            ).lastrowid
            self.chunk_id = connection.execute(
                "INSERT INTO chunks(document_id,ordinal,text,text_hash,created_at) VALUES(?,?,?,?,?)",
                (self.document_id, 0, "合成された本人の明示Evidence", "synthetic", self.stamp),
            ).lastrowid

    def tearDown(self):
        app.DB_PATH, app.BACKUP_DIR, app.ATTACHMENT_DIR, app.ANALYSIS_PREFILTER_SCOPE = self.previous
        self.temp.cleanup()

    def fact(self, *, category="life", fact_type="preference", summary="静かな場所が好き", state="pending",
             eligibility="pending", validation="pending", fact_key=None, created=None, value=None, status="unknown"):
        created = created or self.stamp
        with app.db() as connection:
            fact_id = connection.execute(
                """INSERT INTO facts(document_id,chunk_id,source_chunk_id,category,fact_type,fact_key,value_json,summary,
                          confidence,truth_confidence,extractor,extractor_model,prompt_version,created_at,
                          retrieval_eligibility,validation_status,status,personal_relevance)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (self.document_id, self.chunk_id, self.chunk_id, category, fact_type,
                 fact_key or f"{category}.{fact_type}.{summary}", json.dumps(value or {}, ensure_ascii=False), summary,
                 .6, .6, "synthetic", "none", "ux1-test", created, eligibility, validation, status, "personal"),
            ).lastrowid
            connection.execute(
                "INSERT INTO fact_reviews(fact_id,state,reason,created_at) VALUES(?,?,?,?)",
                (fact_id, state, "要確認", created),
            )
        return int(fact_id)

    def decision(self, state, title, *, result="", evaluation="", created=None):
        created = created or self.stamp
        with app.db() as connection:
            return int(connection.execute(
                """INSERT INTO decisions(title,context,options_json,decision,rationale,status,created_at,updated_at,
                          domain,decision_state,result,later_evaluation)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (title, "", "[]", "", "", "decided", created, created, "travel", state, result, evaluation),
            ).lastrowid)

    def test_empty_action_center_starts_recording(self):
        self.assertEqual(app.action_center_projection()["top_action"]["kind"], "record")

    def test_result_waiting_precedes_evaluation(self):
        self.decision("result", "評価待ち", result="完了")
        self.decision("executed", "結果待ち")
        self.assertEqual(app.action_center_projection()["top_action"]["title"], "結果待ち")

    def test_evaluation_precedes_urgent_review(self):
        self.decision("result", "評価待ち", result="完了")
        self.fact(eligibility="conflict")
        self.assertEqual(app.action_center_projection()["top_action"]["kind"], "decision_evaluation")

    def test_urgent_review_precedes_normal_review(self):
        self.fact(summary="通常")
        urgent = self.fact(summary="矛盾", validation="conflict")
        self.assertEqual(app.action_center_projection()["top_action"]["id"], urgent)

    def test_normal_review_does_not_occupy_today(self):
        self.fact(summary="通常確認")
        self.assertNotEqual(app.action_center_projection()["top_action"]["kind"], "fact_review")

    def test_action_center_returns_exactly_one_top_action(self):
        self.fact(); self.fact(summary="二件目")
        result = app.action_center_projection()
        self.assertIsInstance(result["top_action"], dict)
        self.assertNotIn("actions", result)

    def test_top_action_has_reason(self):
        self.assertTrue(app.action_center_projection()["top_action"]["reason"])

    def test_sensitive_top_action_is_masked(self):
        self.fact(category="relationship", summary="秘密の人物名", validation="conflict")
        self.assertNotIn("秘密", app.action_center_projection()["top_action"]["title"])

    def test_review_order_is_deterministic(self):
        self.fact(summary="A"); self.fact(summary="B")
        first = [row["id"] for row in app.review_inbox_projection("normal")["items"]]
        second = [row["id"] for row in app.review_inbox_projection("normal")["items"]]
        self.assertEqual(first, second)

    def test_conflict_is_first_urgent_kind(self):
        important = self.fact(fact_type="schedule", summary="予定", value={"date": (datetime.now(timezone.utc) + timedelta(days=7)).date().isoformat()})
        conflict = self.fact(summary="矛盾", eligibility="conflict")
        ids = [row["id"] for row in app.review_inbox_projection("urgent")["items"]]
        self.assertEqual(ids[:2], [conflict, important])

    def test_current_replacement_precedes_important(self):
        key = "housing.rent.current"
        self.fact(category="housing", fact_type="status", summary="現在", state="confirmed", fact_key=key, status="current")
        replacement = self.fact(category="housing", fact_type="status", summary="新候補", fact_key=key)
        important = self.fact(category="housing", fact_type="schedule", summary="更新予定", value={"date": (datetime.now(timezone.utc) + timedelta(days=7)).date().isoformat()})
        ids = [row["id"] for row in app.review_inbox_projection("urgent")["items"]]
        self.assertEqual(ids[:2], [replacement, important])

    def test_same_priority_oldest_first(self):
        newer = self.fact(summary="新", created="2026-02-01T00:00:00+00:00")
        older = self.fact(summary="古", created="2025-12-01T00:00:00+00:00")
        ids = [row["id"] for row in app.review_inbox_projection("normal")["items"]]
        self.assertEqual(ids[:2], [older, newer])

    def test_pending_and_deferred_are_separate(self):
        self.fact(state="pending"); self.fact(summary="あとで", state="deferred")
        result = app.review_inbox_projection("all")
        self.assertEqual(result["counts"], {"urgent": 0, "normal": 1, "deferred": 1})

    def test_legacy_deferred_stays_deferred(self):
        fact_id = self.fact(state="deferred")
        self.assertEqual(app.review_inbox_projection("deferred")["items"][0]["id"], fact_id)

    def test_future_snoozed_is_hidden_from_today(self):
        fact_id = self.fact(validation="conflict")
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        with app.db() as connection:
            connection.execute("UPDATE fact_reviews SET state='deferred' WHERE fact_id=?", (fact_id,))
            connection.execute("INSERT INTO fact_review_queue_state(fact_id,snoozed_until,updated_at) VALUES(?,?,?)", (fact_id, future, app.now()))
        self.assertNotEqual(app.action_center_projection()["top_action"].get("id"), fact_id)

    def test_legacy_deferred_with_expired_snooze_stays_deferred(self):
        fact_id = self.fact(validation="conflict", state="deferred")
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        with app.db() as connection:
            connection.execute("INSERT INTO fact_review_queue_state(fact_id,snoozed_until,updated_at) VALUES(?,?,?)", (fact_id, past, app.now()))
        self.assertEqual(app.review_inbox_projection("deferred")["items"][0]["id"], fact_id)

    def test_confirmed_disappears(self):
        self.fact(state="confirmed")
        self.assertEqual(app.review_inbox_projection("all")["items"], [])

    def test_rejected_disappears(self):
        self.fact(state="rejected")
        self.assertEqual(app.review_inbox_projection("all")["items"], [])

    def test_cursor_paginates_without_overlap(self):
        for index in range(4): self.fact(summary=f"通常{index}")
        first = app.review_inbox_projection("normal", limit=2)
        second = app.review_inbox_projection("normal", limit=2, cursor=first["next_cursor"])
        self.assertTrue({row["id"] for row in first["items"]}.isdisjoint(row["id"] for row in second["items"]))

    def test_domain_filter(self):
        self.fact(category="travel", summary="旅行")
        self.fact(category="life", summary="生活")
        rows = app.review_inbox_projection("normal", domain="travel")["items"]
        self.assertEqual([row["category"] for row in rows], ["travel"])

    def test_counts_include_all_buckets(self):
        self.fact(summary="通常")
        self.fact(summary="緊急", validation="conflict")
        self.fact(summary="あとで", state="deferred")
        self.assertEqual(app.review_inbox_projection("urgent")["counts"], {"urgent": 1, "normal": 1, "deferred": 1})

    def test_sensitive_review_masks_summary_value_and_evidence(self):
        self.fact(category="finance", summary="秘密の金額", value={"amount": 999}, validation="conflict")
        item = app.review_inbox_projection("urgent")["items"][0]
        self.assertEqual(item["summary"], "機微情報の確認が必要です")
        self.assertNotIn("value_json", item)
        self.assertNotIn("evidence", item)

    def test_list_projection_excludes_raw_and_technical_detail(self):
        self.fact(summary="通常候補")
        item = app.review_inbox_projection("normal")["items"][0]
        for key in ("evidence", "document_title", "extractor", "extractor_model", "prompt_version", "technical_detail"):
            self.assertNotIn(key, item)

    def test_normal_detail_contains_evidence_and_technical_detail(self):
        fact_id = self.fact(summary="通常候補")
        detail = app.review_inbox_detail(fact_id)
        self.assertIn("本人の明示Evidence", detail["evidence"])
        self.assertEqual(detail["technical_detail"]["extractor"], "synthetic")
        self.assertEqual(detail["technical_detail"]["internal_id"], fact_id)

    def test_sensitive_detail_requires_explicit_include(self):
        fact_id = self.fact(category="finance", summary="秘密の金額", value={"amount": 999})
        self.assertEqual(app.review_inbox_detail(fact_id)["summary"], "機微情報の確認が必要です")
        detail = app.review_inbox_detail(fact_id, include_sensitive=True)
        self.assertEqual(detail["summary"], "秘密の金額")
        self.assertIn("本人の明示Evidence", detail["evidence"])

    def test_masked_summary_cannot_correct_sensitive_fact(self):
        fact_id = self.fact(category="finance", summary="秘密の金額", value={"amount": 999})
        with self.assertRaises(ValueError):
            app.correct_fact(fact_id, {"summary": "機微情報の確認が必要です", "value": {}})

    def test_one_day_snooze_keeps_pending(self):
        fact_id = self.fact(validation="conflict")
        result = app.update_fact_review_state(fact_id, "pending", "one_day")
        self.assertEqual(result["state"], "pending")
        with app.db() as connection:
            self.assertEqual(connection.execute("SELECT state FROM fact_reviews WHERE fact_id=?", (fact_id,)).fetchone()[0], "pending")
            self.assertIsNotNone(connection.execute("SELECT snoozed_until FROM fact_review_queue_state WHERE fact_id=?", (fact_id,)).fetchone()[0])

    def test_one_week_snooze_keeps_pending(self):
        fact_id = self.fact(validation="conflict")
        app.update_fact_review_state(fact_id, "pending", "one_week")
        with app.db() as connection:
            self.assertEqual(connection.execute("SELECT state FROM fact_reviews WHERE fact_id=?", (fact_id,)).fetchone()[0], "pending")

    def test_finite_snooze_is_metadata_only(self):
        fact_id = self.fact(validation="conflict")
        with app.db() as connection:
            connection.execute("UPDATE fact_reviews SET review_note='元の注記',reviewed_at='2025-01-01' WHERE fact_id=?", (fact_id,))
            before = tuple(connection.execute("SELECT state,reason,review_note,reviewed_at FROM fact_reviews WHERE fact_id=?", (fact_id,)).fetchone())
        app.update_fact_review_state(fact_id, "pending", "one_week")
        with app.db() as connection:
            after = tuple(connection.execute("SELECT state,reason,review_note,reviewed_at FROM fact_reviews WHERE fact_id=?", (fact_id,)).fetchone())
        self.assertEqual(after, before)

    def test_defer_and_resume_preserve_reason(self):
        fact_id = self.fact()
        app.update_fact_review_state(fact_id, "deferred", "indefinite")
        app.update_fact_review_state(fact_id, "pending")
        with app.db() as connection:
            self.assertEqual(connection.execute("SELECT reason FROM fact_reviews WHERE fact_id=?", (fact_id,)).fetchone()[0], "要確認")

    def test_terminal_review_cannot_be_reopened_or_changed(self):
        confirmed = self.fact(state="confirmed")
        rejected = self.fact(state="rejected", summary="却下済み")
        self.assertEqual(app.update_fact_review_state(confirmed, "confirmed")["state"], "confirmed")
        self.assertEqual(app.update_fact_review_state(rejected, "rejected")["state"], "rejected")
        for fact_id, state in ((confirmed, "pending"), (confirmed, "deferred"), (confirmed, "rejected"),
                               (rejected, "pending"), (rejected, "confirmed")):
            with self.assertRaises(ValueError):
                app.update_fact_review_state(fact_id, state, "indefinite" if state == "deferred" else "")

    def test_deferred_requires_resume_before_finite_snooze(self):
        fact_id = self.fact(state="deferred")
        with self.assertRaises(ValueError):
            app.update_fact_review_state(fact_id, "pending", "one_day")

    def test_expired_pending_snooze_returns_to_original_bucket(self):
        fact_id = self.fact(validation="conflict")
        app.update_fact_review_state(fact_id, "pending", "one_day")
        with app.db() as connection:
            connection.execute("UPDATE fact_review_queue_state SET snoozed_until=? WHERE fact_id=?", ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(), fact_id))
        self.assertEqual(app.review_inbox_projection("urgent")["items"][0]["id"], fact_id)

    def test_indefinite_defer_is_the_only_deferred_transition(self):
        fact_id = self.fact()
        result = app.update_fact_review_state(fact_id, "deferred", "indefinite")
        self.assertEqual(result["state"], "deferred")
        with app.db() as connection:
            self.assertIsNone(connection.execute("SELECT snoozed_until FROM fact_review_queue_state WHERE fact_id=?", (fact_id,)).fetchone()[0])

    def test_invalid_review_state_period_pair_is_rejected(self):
        fact_id = self.fact()
        with self.assertRaises(ValueError):
            app.update_fact_review_state(fact_id, "confirmed", "one_day")
        with self.assertRaises(ValueError):
            app.update_fact_review_state(fact_id, "deferred", "one_day")

    def test_amount_alone_does_not_make_review_urgent(self):
        fact_id = self.fact(category="finance", summary="試算", value={"amount": 999})
        self.assertEqual(app.review_inbox_projection("normal")["items"][0]["id"], fact_id)

    def test_inactive_decision_reference_does_not_make_review_urgent(self):
        fact_id = self.fact()
        decision_id = self.decision("result", "完了", result="完了", evaluation="良かった")
        with app.db() as connection:
            connection.execute("UPDATE decisions SET related_fact_ids_json=? WHERE id=?", (json.dumps([fact_id]), decision_id))
        self.assertEqual(app.review_inbox_projection("normal")["items"][0]["id"], fact_id)

    def test_memory_proposal_is_in_normal_inbox(self):
        with app.db() as connection:
            entry_id = connection.execute(
                "INSERT INTO entries(kind,title,body,source,tags,status,created_at,updated_at) VALUES('memo','候補','本人の候補','manual','[]','inbox',?,?)",
                (self.stamp, self.stamp),
            ).lastrowid
            proposal_id = connection.execute(
                "INSERT INTO memory_proposals(entry_id,facts_json,policy,status,created_at) VALUES(?,?,?,'pending',?)",
                (entry_id, json.dumps([{"category": "travel", "summary": "温泉が好き"}], ensure_ascii=False), "confirm", self.stamp),
            ).lastrowid
        item = app.review_inbox_projection("normal")["items"][0]
        self.assertEqual((item["item_kind"], item["id"]), ("memory_proposal", proposal_id))

    def test_projection_does_not_mark_items_presented(self):
        fact_id = self.fact()
        app.review_inbox_projection("normal")
        with app.db() as connection:
            self.assertIsNone(connection.execute("SELECT presentation_count FROM fact_review_queue_state WHERE fact_id=?", (fact_id,)).fetchone())

    def test_presented_updates_only_the_requested_item(self):
        first = self.fact(); second = self.fact(summary="二件目")
        self.assertEqual(app.mark_review_item_presented("fact", first), 1)
        with app.db() as connection:
            self.assertIsNone(connection.execute("SELECT presentation_count FROM fact_review_queue_state WHERE fact_id=?", (second,)).fetchone())

    def test_confirmed_removes_snooze_metadata(self):
        fact_id = self.fact()
        app.update_fact_review_state(fact_id, "pending", "one_day")
        app.update_fact_review_state(fact_id, "confirmed")
        with app.db() as connection:
            self.assertIsNone(connection.execute("SELECT 1 FROM fact_review_queue_state WHERE fact_id=?", (fact_id,)).fetchone())

    def test_active_decision_reference_is_urgent(self):
        fact_id = self.fact()
        decision_id = self.decision("decided", "進行中")
        with app.db() as connection:
            connection.execute("UPDATE decisions SET related_fact_ids_json=? WHERE id=?", (json.dumps([fact_id]), decision_id))
        self.assertEqual(app.review_inbox_projection("urgent")["items"][0]["id"], fact_id)

    def test_schedule_beyond_fourteen_days_is_normal(self):
        fact_id = self.fact(fact_type="schedule", value={"date": (datetime.now(timezone.utc) + timedelta(days=20)).date().isoformat()})
        self.assertEqual(app.review_inbox_projection("normal")["items"][0]["id"], fact_id)

    def test_large_backlog_first_page_is_bounded(self):
        for index in range(55): self.fact(summary=f"候補{index}")
        result = app.review_inbox_projection("normal")
        self.assertEqual(len(result["items"]), 10)
        self.assertIsNotNone(result["next_cursor"])

    def test_urgent_after_eleven_hundred_normal_reviews_is_not_lost(self):
        with app.db() as connection:
            for index in range(1100):
                fact_id = connection.execute(
                    """INSERT INTO facts(document_id,chunk_id,source_chunk_id,category,fact_type,fact_key,value_json,summary,
                              confidence,truth_confidence,extractor,extractor_model,prompt_version,created_at,
                              retrieval_eligibility,validation_status,status,personal_relevance)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (self.document_id,self.chunk_id,self.chunk_id,"life","preference",f"life.bulk.{index}","{}",f"候補{index}",.6,.6,"synthetic","none","ux1-test",f"2026-01-01T00:{index//60:02d}:{index%60:02d}+00:00","pending","pending","unknown","personal"),
                ).lastrowid
                connection.execute("INSERT INTO fact_reviews(fact_id,state,reason,created_at) VALUES(?,'pending','要確認',?)", (fact_id,self.stamp))
        urgent = self.fact(summary="最後の矛盾", validation="conflict", created="2026-12-31T00:00:00+00:00")
        self.assertEqual(app.review_inbox_projection("urgent", limit=1)["items"][0]["id"], urgent)
        self.assertEqual(app.action_center_projection()["top_action"]["id"], urgent)

        seen = set(); cursor = None
        while True:
            page = app.review_inbox_projection("normal", limit=100, cursor=cursor)
            ids = {item["id"] for item in page["items"] if item["item_kind"] == "fact"}
            self.assertTrue(seen.isdisjoint(ids)); seen.update(ids)
            cursor = page["next_cursor"]
            if not cursor: break
        self.assertEqual(len(seen), 1100)

    def test_fast_start_applies_015_without_rewriting_reviews(self):
        pending = self.fact(summary="移行前pending")
        deferred = self.fact(summary="移行前deferred", state="deferred")
        with app.db() as connection:
            before_summary = connection.execute("SELECT summary FROM facts WHERE id=?", (pending,)).fetchone()[0]
            connection.execute("DROP TABLE memory_proposal_queue_state")
            connection.execute("DELETE FROM schema_migrations WHERE version='015_action_center_review_inbox_stabilization'")
        old_value = os.environ.get("PERSONAL_OS_RUN_STARTUP_MAINTENANCE")
        os.environ["PERSONAL_OS_RUN_STARTUP_MAINTENANCE"] = "false"
        try:
            app.initialize(); app.initialize()
        finally:
            if old_value is None: os.environ.pop("PERSONAL_OS_RUN_STARTUP_MAINTENANCE", None)
            else: os.environ["PERSONAL_OS_RUN_STARTUP_MAINTENANCE"] = old_value
        with app.db() as connection:
            self.assertIsNotNone(connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='memory_proposal_queue_state'").fetchone())
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM schema_migrations WHERE version='015_action_center_review_inbox_stabilization'").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT summary FROM facts WHERE id=?", (pending,)).fetchone()[0], before_summary)
            self.assertEqual(connection.execute("SELECT state FROM fact_reviews WHERE fact_id=?", (pending,)).fetchone()[0], "pending")
            self.assertEqual(connection.execute("SELECT state FROM fact_reviews WHERE fact_id=?", (deferred,)).fetchone()[0], "deferred")
        self.assertIsInstance(app.review_inbox_projection("all"), dict)

    def test_migration_is_idempotent(self):
        app.migrate_action_center_review_inbox(); app.migrate_action_center_review_inbox()
        with app.db() as connection:
            count = connection.execute("SELECT COUNT(*) FROM schema_migrations WHERE version='014_action_center_review_inbox'").fetchone()[0]
        self.assertEqual(count, 1)

    def test_migration_preserves_review_rows(self):
        fact_id = self.fact(state="pending")
        app.migrate_action_center_review_inbox()
        with app.db() as connection:
            state = connection.execute("SELECT state FROM fact_reviews WHERE fact_id=?", (fact_id,)).fetchone()[0]
        self.assertEqual(state, "pending")

    def test_migration_preserves_legacy_deferred(self):
        fact_id = self.fact(state="deferred")
        app.migrate_action_center_review_inbox()
        with app.db() as connection:
            self.assertIsNone(connection.execute("SELECT snoozed_until FROM fact_review_queue_state WHERE fact_id=?", (fact_id,)).fetchone())

    def test_decision_snooze_does_not_change_decision_state(self):
        decision_id = self.decision("executed", "結果待ち")
        with app.db() as connection:
            connection.execute("INSERT INTO action_center_snoozes(action_key,keep_in_inbox,updated_at) VALUES(?,?,?)", (f"decision:{decision_id}:decision_result", 1, app.now()))
        self.assertNotEqual(app.action_center_projection()["top_action"].get("id"), decision_id)
        with app.db() as connection:
            state = connection.execute("SELECT decision_state FROM decisions WHERE id=?", (decision_id,)).fetchone()[0]
        self.assertEqual(state, "executed")


if __name__ == "__main__":
    unittest.main()
