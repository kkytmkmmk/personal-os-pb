import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

import app


@contextmanager
def isolated_personal_os():
    previous = (app.DB_PATH, app.BACKUP_DIR, app.ATTACHMENT_DIR, app.ANALYSIS_PREFILTER_SCOPE)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        app.DB_PATH, app.BACKUP_DIR, app.ATTACHMENT_DIR = root / "personal_os.db", root / "backups", root / "attachments"
        app.ANALYSIS_PREFILTER_SCOPE = None
        try:
            app.initialize()
            yield
        finally:
            app.DB_PATH, app.BACKUP_DIR, app.ATTACHMENT_DIR, app.ANALYSIS_PREFILTER_SCOPE = previous


class ChangeTimelineTests(unittest.TestCase):
    def add_document(self, connection, created_at="2026-07-01T10:00:00+09:00"):
        return connection.execute(
            "INSERT INTO documents(title,source,source_created_at,ingested_at,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            ("synthetic", "test", created_at, created_at, created_at, created_at),
        ).lastrowid

    def add_fact(self, connection, document_id, *, category="travel", fact_type="preference", summary="移動時間を短くしたい",
                 effective_at="2026-07-01", supersedes=None, status="current"):
        fact_id = connection.execute(
            """INSERT INTO facts(document_id,category,fact_type,fact_key,value_json,summary,confidence,extractor,created_at,
               effective_at,status,retrieval_eligibility,truth_confidence,personal_relevance,supersedes_fact_id)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (document_id, category, fact_type, f"{category}.{fact_type}.sample", "{}", summary, .99, "test",
             "2026-07-29T10:00:00+09:00", effective_at, status, "eligible", .99, "personal", supersedes),
        ).lastrowid
        connection.execute("INSERT INTO fact_reviews(fact_id,state,reviewed_at,created_at) VALUES(?,?,?,?)", (fact_id, "confirmed", "2026-07-29", "2026-07-29"))
        return fact_id

    def test_fact_change_uses_semantic_time_and_has_old_new_values(self):
        with isolated_personal_os():
            with app.db() as connection:
                document_id = self.add_document(connection, "2024-04-01T10:00:00+09:00")
                old_id = self.add_fact(connection, document_id, summary="1Rを希望", effective_at="2024-04-01", status="superseded")
                new_id = self.add_fact(connection, document_id, summary="1LDKを希望", effective_at="2024-05-01", supersedes=old_id)
            events = app.timeline_projection(limit=30)["events"]
            event = next(item for item in events if item["id"] == f"fact-{new_id}")
            self.assertEqual(event["event_kind"], "fact_changed")
            self.assertEqual(event["occurred_at"], "2024-05-01")
            self.assertEqual(event["detail"]["previous_value"], "1Rを希望")
            self.assertEqual(event["detail"]["new_value"], "1LDKを希望")

    def test_lifecycle_filters_cursor_and_sensitive_mask(self):
        with isolated_personal_os():
            with app.db() as connection:
                document_id = self.add_document(connection)
                self.add_fact(connection, document_id, category="finance", fact_type="asset_balance", summary="総資産12,345,678円", effective_at="2026-06-01")
                decision_id = connection.execute(
                    """INSERT INTO decisions(title,context,options_json,decision,rationale,status,created_at,updated_at,domain,decision_state,
                       decided_on,result,later_evaluation,outcome_recorded_at,evaluation_recorded_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    ("温泉旅行を決める", "", "[]", "行く", "移動時間", "decided", "2026-07-01", "2026-07-28", "travel", "result",
                     "2026-07-03", "移動が楽だった", "良かった", "2026-07-20", "2026-07-25"),
                ).lastrowid
                connection.execute(
                    "INSERT INTO execution_events(decision_id,event_type,summary,occurred_at,created_at) VALUES(?,?,?,?,?)",
                    (decision_id, "executed", "旅行を実行", "2026-07-18", "2026-07-18"),
                )
                connection.execute(
                    "INSERT INTO personal_inferences(statement,inference_type,domain,confidence,source_fact_ids_json,created_at,last_evaluated_at,status) VALUES(?,?,?,?,?,?,?,?)",
                    ("未確認の推測", "pattern", "travel", .9, "[]", "2026-07-20", "2026-07-20", "active"),
                )
                connection.execute(
                    "INSERT INTO personal_inferences(statement,inference_type,domain,confidence,source_fact_ids_json,created_at,last_evaluated_at,status) VALUES(?,?,?,?,?,?,?,?)",
                    ("確認済みの旅行傾向", "confirmed_pattern", "travel", .9, "[]", "2026-07-21", "2026-07-21", "active"),
                )
            events = app.timeline_projection(limit=30)["events"]
            self.assertTrue(any(item["event_kind"] == "executed" for item in events))
            self.assertTrue(any(item["event_kind"] == "result_recorded" for item in events))
            self.assertTrue(any(item["event_kind"] == "evaluation_recorded" for item in events))
            self.assertTrue(any(item["event_kind"] == "inference_confirmed" for item in events))
            self.assertFalse(any("未確認の推測" in item["summary"] for item in events))
            finance = next(item for item in events if item["event_kind"] == "finance_snapshot")
            self.assertNotIn("12,345,678", finance["summary"])
            decisions = app.timeline_projection(kind="decision", limit=30)["events"]
            self.assertTrue(decisions and all(item["event_kind"] in {"decision_created", "decision_made"} for item in decisions))
            travel = app.timeline_projection(domain="travel", limit=1)
            self.assertEqual(len(travel["events"]), 1)
            self.assertTrue(travel["next_cursor"])
            second = app.timeline_projection(domain="travel", limit=30, cursor=travel["next_cursor"])["events"]
            self.assertTrue(all(item["id"] != travel["events"][0]["id"] for item in second))

    def test_simulation_and_empty_state_are_excluded(self):
        with isolated_personal_os():
            self.assertEqual(app.timeline_projection()["events"], [])
            with app.db() as connection:
                document_id = self.add_document(connection)
                self.add_fact(connection, document_id, category="simulation", fact_type="what_if", summary="これは試算", effective_at="2026-07-01")
            self.assertEqual(app.timeline_projection()["events"], [])


if __name__ == "__main__":
    unittest.main()
