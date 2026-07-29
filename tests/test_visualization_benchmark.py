import tempfile
import unittest
import ast
from unittest import mock
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
                       created_at,status,retrieval_eligibility,truth_confidence,personal_relevance,subject_scope)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (document_id, "finance", "asset_balance", "finance.total_assets", '{"amount": 9800000, "currency": "JPY", "details": {"benchmark_contract": {"metric_key": "finance.total_assets", "statistical_unit": "individual", "measurement_kind": "balance", "time_basis": "current"}}}',
                     "current total assets", .98, "test", timestamp, "current", "eligible", .98, "personal", "individual"),
                ).lastrowid
                connection.execute("INSERT INTO fact_reviews(fact_id,state,reviewed_at,created_at) VALUES(?,?,?,?)", (fact_id, "confirmed", timestamp, timestamp))
            app.import_benchmark_reference({
                "source": {"source_name": "Official sample", "publisher": "Statistics office", "source_url": "https://example.test/source"},
                "series": {"metric_key": "finance.total_assets", "metric_name": "Financial assets", "domain": "finance", "unit": "JPY", "statistic_type": "median", "definition": "individual total assets", "population_scope": "sample population", "segment_definition": {"subject_scope": "individual"}},
                "observations": [{"reference_period": "2025", "value": 4100000}],
            })
            series = app.benchmark_projection("finance.total_assets")["series"][0]
            self.assertEqual(series["compatibility"], "exact")
            self.assertEqual(series["personal"]["fact_id"], fact_id)

    def test_registry_contract_is_not_derived_from_subject_scope(self):
        with isolated_personal_os():
            timestamp = app.now()
            with app.db() as connection:
                document_id = connection.execute("INSERT INTO documents(title,source,source_created_at,ingested_at,created_at,updated_at) VALUES(?,?,?,?,?,?)", ("source", "manual", timestamp, timestamp, timestamp, timestamp)).lastrowid
                fact_id = connection.execute(
                    """INSERT INTO facts(document_id,category,fact_type,fact_key,value_json,summary,confidence,extractor,created_at,status,retrieval_eligibility,truth_confidence,personal_relevance,subject_scope)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (document_id, "finance", "asset_balance", "finance.total_assets", '{"amount": 1000, "currency": "JPY"}', "assets", .99, "test", timestamp, "current", "eligible", .99, "personal", "self"),
                ).lastrowid
                connection.execute("INSERT INTO fact_reviews(fact_id,state,reviewed_at,created_at) VALUES(?,?,?,?)", (fact_id, "confirmed", timestamp, timestamp))
            app.import_benchmark_reference({"source":{"source_name":"R","publisher":"P","source_url":"https://example.test/r"},"series":{"metric_key":"finance.total_assets","metric_name":"Assets","domain":"finance","unit":"JPY","statistic_type":"median","definition":"assets","population_scope":"people","segment_definition":{"subject_scope":"individual"}},"observations":[{"reference_period":"2025","value":500}]})
            comparison = app.benchmark_projection("finance.total_assets")["series"][0]["comparison"]
            self.assertEqual(comparison["compatibility"], "exact")
            self.assertEqual(comparison["absolute_difference"], 500.0)

    def test_normalizes_explicit_monetary_units_and_rejects_unknown_units(self):
        self.assertEqual(app.normalize_benchmark_value(19, "万円", "JPY"), (190000.0, "JPY"))
        self.assertEqual(app.normalize_benchmark_value(190000, "円", "JPY"), (190000.0, "JPY"))
        self.assertEqual(app.normalize_benchmark_value(18, "mystery", "JPY"), (None, None))

    def test_bundle_validation_rolls_back_all_datasets_and_decodes_distribution(self):
        with isolated_personal_os():
            bundle = {"datasets": [
                {"source":{"source_name":"A","publisher":"P","source_url":"https://example.test/a"},"series":{"metric_key":"life.sleep_duration","metric_name":"Sleep","domain":"life","unit":"hours","statistic_type":"median","definition":"sleep","population_scope":"people","segment_definition":{}},"observations":[{"reference_period":"2025","value":7,"distribution":{"p10":5,"p25":6,"p50":7,"p75":8,"p90":9}}]},
                {"source":{"source_name":"B","publisher":"P","source_url":"https://example.test/b"},"series":{"metric_key":"housing.monthly_rent","metric_name":"Rent","domain":"housing","unit":"JPY","statistic_type":"median","definition":"rent","population_scope":"people","segment_definition":{}},"observations":[{"reference_period":"2025","value":"not-a-number"}]},
            ]}
            with self.assertRaises(ValueError):
                app.import_benchmark_bundle(bundle)
            self.assertEqual(app.benchmark_projection()["series"], [])
            bundle["datasets"][1]["observations"][0]["value"] = 90000
            app.import_benchmark_bundle(bundle)
            observation = app.benchmark_projection("life.sleep_duration")["series"][0]["observations"][0]
            self.assertEqual(observation["distribution"]["p50"], 7)
            self.assertNotIn("distribution_json", observation)

    def test_percentile_band_never_falls_back_to_a_fake_marker(self):
        self.assertEqual(app.benchmark_percentile_band({"p10": 10, "p25": 20, "p50": 30, "p75": 40, "p90": 50}, 42), "p75_p90")
        self.assertIsNone(app.benchmark_percentile_band({"p50": 30}, 32))

    def test_bundle_writer_failure_rolls_back_prior_dataset(self):
        with isolated_personal_os():
            bundle = {"datasets": [
                {"source":{"source_name":"A","publisher":"P","source_url":"https://example.test/a"},"series":{"metric_key":"life.sleep_duration","metric_name":"Sleep","domain":"life","unit":"hours","statistic_type":"mean","definition":"sleep","population_scope":"people","segment_definition":{}},"observations":[{"reference_period":"2025","value":7}]},
                {"source":{"source_name":"B","publisher":"P","source_url":"https://example.test/b"},"series":{"metric_key":"housing.monthly_rent","metric_name":"Rent","domain":"housing","unit":"JPY","statistic_type":"median","definition":"rent","population_scope":"people","segment_definition":{}},"observations":[{"reference_period":"2025","value":90000}]},
            ]}
            writer = app._import_benchmark_reference_write
            calls = 0
            def fail_second(connection, payload, channel):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise app.sqlite3.OperationalError("test-only writer failure")
                return writer(connection, payload, channel)
            with mock.patch.object(app, "_import_benchmark_reference_write", side_effect=fail_second):
                with self.assertRaises(app.sqlite3.OperationalError):
                    app.import_benchmark_bundle(bundle)
            self.assertEqual(app.benchmark_projection()["series"], [])

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
            self.assertNotIn("private relationship detail", node["label"])
            unmasked = app.personal_space_projection(include_sensitive=True)
            node = next(item for item in unmasked["nodes"] if item["id"] == f"fact-{fact_id}")
            self.assertFalse(node["masked"])

    def test_personal_space_masks_every_sensitive_node_and_inherits_result_domain(self):
        with isolated_personal_os():
            timestamp = app.now()
            with app.db() as connection:
                decision_id = connection.execute("""INSERT INTO decisions(title,context,options_json,decision,rationale,status,created_at,updated_at,domain,decision_state)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""", ("private financial decision", "", "[]", "", "", "decided", timestamp, timestamp, "finance", "decided")).lastrowid
                recommendation_id = connection.execute("""INSERT INTO recommendations(domain,title,created_at,updated_at) VALUES(?,?,?,?)""", ("finance", "private recommendation", timestamp, timestamp)).lastrowid
                plan_id = connection.execute("""INSERT INTO plans(domain,title,source_recommendation_id,decision_id,status,result,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)""", ("finance", "private plan", recommendation_id, decision_id, "completed", "private result", timestamp, timestamp)).lastrowid
                connection.execute("INSERT INTO execution_events(decision_id,plan_id,event_type,summary,created_at) VALUES(?,?,?,?,?)", (decision_id, plan_id, "completed", "private execution", timestamp))
            projection = app.personal_space_projection()
            sensitive = [node for node in projection["nodes"] if node["domain"] == "finance"]
            self.assertTrue(sensitive)
            self.assertTrue(all(node["masked"] for node in sensitive))
            event = next(node for node in sensitive if node["id"].startswith("result-event-"))
            self.assertEqual(event["domain"], "finance")
            self.assertEqual(event["temporal_bucket"], "history")
            self.assertTrue(all(edge["from"] in {node["id"] for node in projection["nodes"]} and edge["to"] in {node["id"] for node in projection["nodes"]} for edge in projection["edges"]))
            detail = app.personal_space_node_detail("decision", decision_id)
            self.assertTrue(detail["masked"])
            self.assertNotIn("private financial decision", detail["title"])

    def test_fenced_bundle_validates_before_import_and_imports_all_datasets(self):
        with isolated_personal_os():
            raw = """```json
            {"bundle_version":"1","datasets":[
              {"source":{"source_name":"A","publisher":"P","source_url":"https://example.test/a"},"series":{"metric_key":"life.sleep_duration","metric_name":"Sleep","domain":"life","unit":"hours","statistic_type":"mean","definition":"duration","population_scope":"individuals","segment_definition":{"subject_scope":"individual"}},"observations":[{"reference_period":"2025","value":7}]},
              {"source":{"source_name":"B","publisher":"P","source_url":"https://example.test/b"},"series":{"metric_key":"housing.monthly_rent","metric_name":"Rent","domain":"housing","unit":"JPY","statistic_type":"median","definition":"monthly rent","population_scope":"individuals","segment_definition":{"subject_scope":"individual"}},"observations":[{"reference_period":"2025","value":90000}]}
            ]}
            ```"""
            preview = app.validate_benchmark_bundle(raw)
            self.assertEqual(preview["datasets"], 2)
            result = app.import_benchmark_bundle(raw, channel="chatgpt_copy")
            self.assertEqual(result["datasets"], 2)
            self.assertEqual(len(app.benchmark_projection()["series"]), 2)

    def test_total_assets_is_not_matched_to_financial_assets(self):
        with isolated_personal_os():
            timestamp = app.now()
            with app.db() as connection:
                document_id = connection.execute("INSERT INTO documents(title,source,source_created_at,ingested_at,created_at,updated_at) VALUES(?,?,?,?,?,?)", ("source", "manual", timestamp, timestamp, timestamp, timestamp)).lastrowid
                fact_id = connection.execute(
                    """INSERT INTO facts(document_id,category,fact_type,fact_key,value_json,summary,confidence,extractor,created_at,status,retrieval_eligibility,truth_confidence,personal_relevance,subject_scope)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (document_id, "finance", "asset_balance", "finance.total_assets", '{"amount": 10000000, "currency": "JPY", "details": {"subject_scope": "individual"}}', "total assets", .99, "test", timestamp, "current", "eligible", .99, "personal", "individual"),
                ).lastrowid
                connection.execute("INSERT INTO fact_reviews(fact_id,state,reviewed_at,created_at) VALUES(?,?,?,?)", (fact_id, "confirmed", timestamp, timestamp))
            app.import_benchmark_reference({"source":{"source_name":"R","publisher":"P","source_url":"https://example.test/r"},"series":{"metric_key":"finance.financial_assets","metric_name":"Financial assets","domain":"finance","unit":"JPY","statistic_type":"median","definition":"financial assets","population_scope":"individuals","segment_definition":{"subject_scope":"individual"}},"observations":[{"reference_period":"2025","value":5000000}]})
            series = app.benchmark_projection("finance.financial_assets")["series"][0]
            self.assertEqual(series["compatibility"], "reference_only")
            self.assertIsNone(series["personal"])

    def test_registry_derives_existing_contract_for_reviewed_safe_alias_only(self):
        with isolated_personal_os():
            timestamp = app.now()
            with app.db() as connection:
                document_id = connection.execute("INSERT INTO documents(title,source,source_created_at,ingested_at,created_at,updated_at) VALUES(?,?,?,?,?,?)", ("source", "manual", timestamp, timestamp, timestamp, timestamp)).lastrowid
                fact_id = connection.execute("""INSERT INTO facts(document_id,category,fact_type,fact_key,value_json,summary,confidence,extractor,created_at,status,retrieval_eligibility,truth_confidence,personal_relevance)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (document_id, "finance", "asset_balance", "finance.asset_balance.total_assets", '{"amount": 2000000, "currency": "JPY"}', "total", .99, "test", timestamp, "current", "eligible", .99, "personal")).lastrowid
                connection.execute("INSERT INTO fact_reviews(fact_id,state,reviewed_at,created_at) VALUES(?,?,?,?)", (fact_id, "confirmed", timestamp, timestamp))
            app.import_benchmark_reference({"source":{"source_name":"R","publisher":"P","source_url":"https://example.test/r"},"series":{"metric_key":"finance.total_assets","metric_name":"Assets","domain":"finance","unit":"JPY","statistic_type":"median","definition":"assets","population_scope":"people","segment_definition":{}},"observations":[{"reference_period":"2025","value":1000000}]})
            series = app.benchmark_projection("finance.total_assets")["series"][0]
            self.assertEqual(series["compatibility"], "exact")
            self.assertEqual(series["personal"]["fact_id"], fact_id)
            self.assertEqual(series["personal"]["contract_source"], "registry")
            audit = app.benchmark_compatibility_audit()
            row = next(item for item in audit["metrics"] if item["metric_key"] == "finance.total_assets")
            self.assertTrue(row["matched_current_fact"])
            self.assertIn({"fact_key": "finance.asset_balance.total_assets", "count": 1}, row["candidate_fact_keys"])

    def test_registry_resolves_all_declared_personal_fact_keys(self):
        expected = {
            "work.annual_income": ("work.annual_income", "JPY", "annual"),
            "housing.monthly_rent": ("housing.monthly_rent", "JPY", "monthly"),
            "life.sleep_duration": ("life.sleep_duration", "hours", "daily"),
        }
        for fact_key, (metric_key, unit, time_basis) in expected.items():
            with self.subTest(fact_key=fact_key):
                contract = app.resolve_personal_metric_contract(fact_key)
                self.assertIsNotNone(contract)
                self.assertEqual(contract["metric_key"], metric_key)
                self.assertEqual(contract["canonical_unit"], unit)
                self.assertEqual(contract["time_basis"], time_basis)
        self.assertTrue(all("personal_fact_keys" in definition for definition in app.BENCHMARK_METRIC_CONTRACTS.values()))
        self.assertTrue(all("fact_keys" not in definition for definition in app.BENCHMARK_METRIC_CONTRACTS.values()))

    def test_registry_remains_authoritative_when_embedded_contract_is_stale(self):
        with isolated_personal_os():
            timestamp = app.now()
            with app.db() as connection:
                document_id = connection.execute("INSERT INTO documents(title,source,source_created_at,ingested_at,created_at,updated_at) VALUES(?,?,?,?,?,?)", ("source", "manual", timestamp, timestamp, timestamp, timestamp)).lastrowid
                fact_id = connection.execute(
                    """INSERT INTO facts(document_id,category,fact_type,fact_key,value_json,summary,confidence,extractor,created_at,status,retrieval_eligibility,truth_confidence,personal_relevance)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (document_id, "finance", "asset_balance", "finance.total_assets", '{"amount": 1000000, "currency": "JPY", "details": {"benchmark_contract": {"metric_key": "finance.total_assets", "statistical_unit": "household", "measurement_kind": "flow", "time_basis": "annual", "canonical_unit": "USD"}}}', "assets", .99, "test", timestamp, "current", "eligible", .99, "personal"),
                ).lastrowid
                connection.execute("INSERT INTO fact_reviews(fact_id,state,reviewed_at,created_at) VALUES(?,?,?,?)", (fact_id, "confirmed", timestamp, timestamp))
            app.import_benchmark_reference({"source":{"source_name":"R","publisher":"P","source_url":"https://example.test/r"},"series":{"metric_key":"finance.total_assets","metric_name":"Assets","domain":"finance","unit":"JPY","statistic_type":"median","definition":"assets","population_scope":"individuals","segment_definition":{}},"observations":[{"reference_period":"2025","value":500000}]})
            series = app.benchmark_projection("finance.total_assets")["series"][0]
            self.assertEqual(series["compatibility"], "exact")
            self.assertEqual(series["comparison"]["absolute_difference"], 500000.0)
            self.assertEqual(series["personal"]["contract_source"], "registry")
            self.assertTrue(series["personal"]["embedded_contract_present"])
            self.assertFalse(series["personal"]["embedded_contract_matches_registry"])
            self.assertIn({"code": "embedded_contract_conflicts_with_registry"}, series["comparison"]["reasons"])

    def test_unknown_personal_fact_cannot_self_authorize_with_embedded_contract(self):
        with isolated_personal_os():
            timestamp = app.now()
            with app.db() as connection:
                document_id = connection.execute("INSERT INTO documents(title,source,source_created_at,ingested_at,created_at,updated_at) VALUES(?,?,?,?,?,?)", ("source", "manual", timestamp, timestamp, timestamp, timestamp)).lastrowid
                fact_id = connection.execute(
                    """INSERT INTO facts(document_id,category,fact_type,fact_key,value_json,summary,confidence,extractor,created_at,status,retrieval_eligibility,truth_confidence,personal_relevance)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (document_id, "other", "status", "unknown.metric", '{"amount": 12, "unit": "JPY", "details": {"benchmark_contract": {"metric_key": "unknown.metric", "statistical_unit": "individual", "measurement_kind": "balance", "time_basis": "current", "canonical_unit": "JPY"}}}', "unknown", .99, "test", timestamp, "current", "eligible", .99, "personal"),
                ).lastrowid
                connection.execute("INSERT INTO fact_reviews(fact_id,state,reviewed_at,created_at) VALUES(?,?,?,?)", (fact_id, "confirmed", timestamp, timestamp))
            app.import_benchmark_reference({"source":{"source_name":"R","publisher":"P","source_url":"https://example.test/r"},"series":{"metric_key":"unknown.metric","metric_name":"Unknown","domain":"other","unit":"JPY","statistic_type":"median","definition":"unknown","population_scope":"individuals","segment_definition":{},"metric_contract":{"metric_key":"unknown.metric","statistical_unit":"individual","measurement_kind":"balance","time_basis":"current","canonical_unit":"JPY"}},"observations":[{"reference_period":"2025","value":10}]})
            series = app.benchmark_projection("unknown.metric")["series"][0]
            self.assertEqual(series["compatibility"], "reference_only")
            self.assertEqual(series["personal"]["contract_source"], "none")
            self.assertNotIn("absolute_difference", series["comparison"])
            self.assertNotIn("ratio", series["comparison"])
            self.assertNotIn("percentile_band", series["comparison"])
            self.assertIn({"code": "personal_contract_missing", "subject_scope": "unknown"}, series["comparison"]["reasons"])

    def test_benchmark_projection_has_one_safe_definition(self):
        tree = ast.parse((Path(app.__file__).read_text(encoding="utf-8")))
        names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        self.assertEqual(names.count("benchmark_projection"), 1)
        self.assertNotIn("_legacy_benchmark_projection_unsafe", names)
        source = Path(app.__file__).read_text(encoding="utf-8")
        self.assertNotIn("Subject scope differs", source)
        self.assertNotIn("Metric key, unit, and subject scope match", source)
        self.assertNotIn("No compatible confirmed current Fact", source)


if __name__ == "__main__":
    unittest.main()
