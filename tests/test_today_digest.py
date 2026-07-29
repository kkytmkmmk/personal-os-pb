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
        app.DB_PATH = root / "personal_os.db"
        app.BACKUP_DIR = root / "backups"
        app.ATTACHMENT_DIR = root / "attachments"
        app.ANALYSIS_PREFILTER_SCOPE = None
        try:
            app.initialize()
            yield
        finally:
            app.DB_PATH, app.BACKUP_DIR, app.ATTACHMENT_DIR, app.ANALYSIS_PREFILTER_SCOPE = previous


class TodayDigestTests(unittest.TestCase):
    def test_empty_digest_has_no_inferred_personal_state(self):
        with isolated_personal_os():
            digest = app.today_digest()
            self.assertEqual(digest["headline"]["text"], "最近の大きな変化はまだありません")
            self.assertEqual(digest["headline"]["basis"], [])
            self.assertEqual(digest["next_actions"], [])
            self.assertEqual(digest["recent_changes"], [])
            self.assertEqual(digest["remember"], [])
            self.assertEqual(digest["consultation_prompts"], [])

    def test_digest_is_bounded_evidence_backed_and_prioritizes_actionable_decisions(self):
        with isolated_personal_os():
            timestamp = app.now()
            with app.db() as connection:
                document_id = connection.execute(
                    "INSERT INTO documents(title,source,source_created_at,ingested_at,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                    ("source", "manual", timestamp, timestamp, timestamp, timestamp),
                ).lastrowid
                fact_id = connection.execute(
                    """INSERT INTO facts(document_id,source_chunk_id,category,fact_type,fact_key,value_json,summary,confidence,extractor,
                       created_at,status,retrieval_eligibility,truth_confidence,personal_relevance)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (document_id, 1, "travel", "preference", "travel.preference.transit", "{}", "旅行では移動時間を短くしたい", .98, "test", timestamp, "current", "eligible", .98, "personal"),
                ).lastrowid
                connection.execute("INSERT INTO fact_reviews(fact_id,state,reviewed_at,created_at) VALUES(?,?,?,?)", (fact_id, "confirmed", timestamp, timestamp))
                connection.execute("INSERT INTO memory_changes(fact_id,change_type,summary,detail_json,created_at) VALUES(?,?,?,?,?)", (fact_id, "updated", "旅行の好みを更新", "{}", timestamp))
                for state, title in (("executed", "旅行計画を実行した"), ("decided", "宿を予約する"), ("candidate", "旅行先を決める"), ("result", "振り返る旅行")):
                    connection.execute(
                        """INSERT INTO decisions(title,context,options_json,decision,rationale,status,created_at,updated_at,domain,decision_state)
                           VALUES(?,?,?,?,?,?,?,?,?,?)""",
                        (title, "", "[]", "", "", "decided", timestamp, timestamp, "travel", state),
                    )
            digest = app.today_digest()
            self.assertEqual(len(digest["next_actions"]), 3)
            self.assertEqual([item["state_label"] for item in digest["next_actions"]], ["結果待ち", "実行待ち", "判断待ち"])
            self.assertEqual(digest["next_actions"][0]["action"], "結果を記録する")
            self.assertLessEqual(len(digest["recent_changes"]), 3)
            self.assertLessEqual(len(digest["remember"]), 2)
            self.assertTrue(digest["remember"][0]["basis"])
            self.assertEqual(digest["consultation_prompts"][0]["text"], "次の旅行候補を整理する")
            self.assertIn("結果待ち", digest["headline"]["text"])

    def test_sensitive_digest_text_is_masked_but_keeps_evidence_link(self):
        with isolated_personal_os():
            timestamp = app.now()
            with app.db() as connection:
                document_id = connection.execute("INSERT INTO documents(title,source,source_created_at,ingested_at,created_at,updated_at) VALUES(?,?,?,?,?,?)", ("source", "manual", timestamp, timestamp, timestamp, timestamp)).lastrowid
                fact_id = connection.execute(
                    """INSERT INTO facts(document_id,source_chunk_id,category,fact_type,fact_key,value_json,summary,confidence,extractor,
                       created_at,status,retrieval_eligibility,truth_confidence,personal_relevance)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (document_id, 1, "relationship", "status", "relationship.private", "{}", "private details must not appear", .98, "test", timestamp, "current", "eligible", .98, "personal"),
                ).lastrowid
                connection.execute("INSERT INTO fact_reviews(fact_id,state,reviewed_at,created_at) VALUES(?,?,?,?)", (fact_id, "confirmed", timestamp, timestamp))
            digest = app.today_digest()
            self.assertEqual(digest["remember"][0]["text"], "人間関係に関する確認済みの記録があります")
            self.assertTrue(digest["remember"][0]["basis"])
            self.assertNotIn("private details", digest["remember"][0]["text"])


if __name__ == "__main__":
    unittest.main()
