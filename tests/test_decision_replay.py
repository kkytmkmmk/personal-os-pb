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


class DecisionReplayTests(unittest.TestCase):
    def create_decision(self, *, domain="travel", state="result", result="The trip was comfortable", evaluation="次回: keep transfers short"):
        with app.db() as connection:
            recommendation_id = connection.execute(
                """INSERT INTO recommendations(domain,title,rationale,options_json,criteria_json,source_fact_ids_json,
                   source_decision_ids_json,source_evidence_ids_json,context_json,tradeoffs_json,missing_context_json,status,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (domain, "Synthetic recommendation", "A suggestion from consultation", '["A","B"]', "[]", "[]", "[]", "[]", "{}", "[]", "[]", "accepted", "2026-07-01", "2026-07-01"),
            ).lastrowid
            decision_id = connection.execute(
                """INSERT INTO decisions(domain,title,context,question,options_json,decision,selected_option,rationale,status,
                   decision_state,decided_on,result,later_evaluation,outcome_recorded_at,evaluation_recorded_at,
                   source_recommendation_id,related_fact_ids_json,related_entity_ids_json,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (domain, "Synthetic decision", "Known constraint", "Which option should I choose?", '["A","B"]', "A", "A", "Because evidence supports it", "decided",
                 state, "2026-07-02", result, evaluation, "2026-07-04", "2026-07-10", recommendation_id, "[]", "[]", "2026-07-01", "2026-07-10"),
            ).lastrowid
            connection.execute(
                "INSERT INTO execution_events(decision_id,event_type,summary,occurred_at,created_at) VALUES(?,?,?,?,?)",
                (decision_id, "executed", "Executed by the user", "2026-07-03", "2026-07-03"),
            )
        return decision_id

    def test_replay_orders_lifecycle_and_keeps_recommendation_distinct(self):
        with isolated_personal_os():
            decision_id = self.create_decision()
            replay = app.decision_replay(decision_id)
            self.assertEqual([item["stage"] for item in replay["stages"]], [
                "trigger", "context", "options", "recommendation", "decision", "rationale", "execution", "result", "later_evaluation", "lesson",
            ])
            self.assertEqual(next(item for item in replay["stages"] if item["stage"] == "recommendation")["status"], "recorded")
            self.assertEqual(next(item for item in replay["stages"] if item["stage"] == "decision")["summary"], "A")
            self.assertEqual(next(item for item in replay["stages"] if item["stage"] == "lesson")["summary"], "keep transfers short")
            self.assertIsNone(replay["next_action"])

    def test_missing_result_has_an_explicit_user_action_without_writing_data(self):
        with isolated_personal_os():
            decision_id = self.create_decision(state="executed", result="", evaluation="")
            replay = app.decision_replay(decision_id)
            self.assertIn("result", replay["missing_stages"])
            self.assertEqual(replay["next_action"], {"type": "record_result", "label": "結果を記録する"})
            with app.db() as connection:
                self.assertEqual(connection.execute("SELECT result FROM decisions WHERE id=?", (decision_id,)).fetchone()[0], "")

    def test_sensitive_replay_masks_content_by_default(self):
        with isolated_personal_os():
            decision_id = self.create_decision(domain="finance", result="Private balance changed", evaluation="Next time: private note")
            masked = app.decision_replay(decision_id)
            revealed = app.decision_replay(decision_id, include_sensitive=True)
            self.assertTrue(masked["has_sensitive_content"])
            self.assertNotIn("Private balance", " ".join(str(item["summary"]) for item in masked["stages"]))
            self.assertIn("Private balance", " ".join(str(item["summary"]) for item in revealed["stages"]))

    def test_feedback_table_is_local_schema(self):
        with isolated_personal_os():
            with app.db() as connection:
                connection.execute(
                    "INSERT INTO ux_feedback(screen,feedback_type,body,expected_behavior,severity,status,created_at) VALUES(?,?,?,?,?,?,?)",
                    ("today", "improvement", "Synthetic local feedback", "A clearer action", "medium", "open", app.now()),
                )
                row = connection.execute("SELECT body FROM ux_feedback").fetchone()
            self.assertEqual(row[0], "Synthetic local feedback")


if __name__ == "__main__":
    unittest.main()
