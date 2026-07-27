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


class VisualizationBenchmarkTests(unittest.TestCase):
    def test_reference_import_is_local_and_keeps_provenance(self):
        with isolated_personal_os():
            result = app.import_benchmark_reference({
                "source": {"source_name": "Official sample", "publisher": "Statistics office", "source_url": "https://example.test/source", "methodology": "published survey"},
                "series": {"metric_key": "finance.total_assets", "metric_name": "Financial assets", "domain": "finance", "unit": "JPY", "statistic_type": "median", "definition": "household financial assets", "population_scope": "sample population"},
                "observations": [{"reference_period": "2025", "value": 4100000, "sample_size": 1000}],
            })
            self.assertEqual(result["new_observations"], 1)
            projection = app.benchmark_projection("finance.total_assets")
            self.assertEqual(len(projection["series"]), 1)
            series = projection["series"][0]
            self.assertEqual(series["publisher"], "Statistics office")
            self.assertEqual(series["observations"][0]["value"], 4100000.0)
            with app.db() as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM benchmark_refresh_runs WHERE status='completed'").fetchone()[0], 1)

    def test_import_rejects_undocumented_reference_source(self):
        with isolated_personal_os():
            with self.assertRaises(ValueError):
                app.import_benchmark_reference({"source": {}, "series": {}, "observations": []})

    def test_comparison_uses_only_confirmed_current_exact_fact(self):
        with isolated_personal_os():
            timestamp = app.now()
            with app.db() as connection:
                document_id = connection.execute(
                    "INSERT INTO documents(title,source,source_created_at,ingested_at,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                    ("source", "manual", timestamp, timestamp, timestamp, timestamp),
                ).lastrowid
                fact_id = connection.execute(
                    """INSERT INTO facts(document_id,category,fact_type,fact_key,value_json,summary,confidence,extractor,
                       created_at,status,retrieval_eligibility,truth_confidence,personal_relevance)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (document_id, "finance", "asset_balance", "finance.total_assets", '{"amount": 9800000, "currency": "JPY"}',
                     "current total assets", .98, "test", timestamp, "current", "eligible", .98, "personal"),
                ).lastrowid
                connection.execute("INSERT INTO fact_reviews(fact_id,state,reviewed_at,created_at) VALUES(?,?,?,?)", (fact_id, "confirmed", timestamp, timestamp))
            app.import_benchmark_reference({
                "source": {"source_name": "Official sample", "publisher": "Statistics office", "source_url": "https://example.test/source"},
                "series": {"metric_key": "finance.total_assets", "metric_name": "Financial assets", "domain": "finance", "unit": "JPY", "statistic_type": "median", "definition": "household financial assets", "population_scope": "sample population"},
                "observations": [{"reference_period": "2025", "value": 4100000}],
            })
            series = app.benchmark_projection("finance.total_assets")["series"][0]
            self.assertEqual(series["compatibility"], "exact")
            self.assertEqual(series["personal"]["fact_id"], fact_id)

    def test_personal_space_masks_sensitive_domains_by_default(self):
        with isolated_personal_os():
            with app.db() as connection:
                timestamp = app.now()
                document_id = connection.execute(
                    "INSERT INTO documents(title,source,source_created_at,ingested_at,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                    ("source", "manual", timestamp, timestamp, timestamp, timestamp),
                ).lastrowid
                fact_id = connection.execute(
                    """INSERT INTO facts(document_id,category,fact_type,fact_key,value_json,summary,confidence,extractor,
                       created_at,status,retrieval_eligibility,truth_confidence,personal_relevance)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (document_id, "relationship", "status", "relationship.sample", "{}", "private relationship detail", .98,
                     "test", timestamp, "current", "eligible", .98, "personal"),
                ).lastrowid
                connection.execute("INSERT INTO fact_reviews(fact_id,state,reviewed_at,created_at) VALUES(?,?,?,?)", (fact_id, "confirmed", timestamp, timestamp))
            masked = app.personal_space_projection()
            node = next(item for item in masked["nodes"] if item["id"] == f"fact-{fact_id}")
            self.assertTrue(node["masked"])
            self.assertEqual(node["label"], "Sensitive fact")
            unmasked = app.personal_space_projection(include_sensitive=True)
            node = next(item for item in unmasked["nodes"] if item["id"] == f"fact-{fact_id}")
            self.assertFalse(node["masked"])


if __name__ == "__main__":
    unittest.main()
