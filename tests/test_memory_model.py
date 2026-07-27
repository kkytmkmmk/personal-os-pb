import unittest
import json
import os
import sqlite3
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import app
from personal_os.ingest import multipart_form_file
from personal_os.llm_ollama import OllamaClient


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
            yield root
        finally:
            app.DB_PATH, app.BACKUP_DIR, app.ATTACHMENT_DIR, app.ANALYSIS_PREFILTER_SCOPE = previous


class MemoryModelTests(unittest.TestCase):
    def test_pending_migration_creates_backup_before_schema_change(self) -> None:
        previous_path = app.DB_PATH
        previous_backup_dir = app.BACKUP_DIR
        previous_attachment_dir = app.ATTACHMENT_DIR
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app.DB_PATH = root / "source.db"
            app.BACKUP_DIR = root / "backups"
            app.ATTACHMENT_DIR = root / "attachments"
            try:
                connection = sqlite3.connect(app.DB_PATH)
                try:
                    connection.executescript(
                        """
                        CREATE TABLE schema_migrations(version TEXT PRIMARY KEY,applied_at TEXT);
                        CREATE TABLE durable_data(value TEXT);
                        INSERT INTO durable_data VALUES('preserved');
                        """
                    )
                    connection.commit()
                finally:
                    connection.close()
                backup = app.backup_before_migration("009_analysis_queue_performance")
                self.assertIsNotNone(backup)
                self.assertTrue(backup.exists())
                self.assertEqual(backup.suffix, app.BACKUP_SUFFIX)
                verification = app.verify_backup(str(backup))
                self.assertTrue(verification["valid"])
                with zipfile.ZipFile(backup) as archive:
                    extracted = root / "extracted.db"
                    extracted.write_bytes(archive.read("database.sqlite3"))
                connection = sqlite3.connect(extracted)
                try:
                    self.assertEqual(connection.execute("SELECT value FROM durable_data").fetchone()[0], "preserved")
                finally:
                    connection.close()
            finally:
                app.DB_PATH = previous_path
                app.BACKUP_DIR = previous_backup_dir
                app.ATTACHMENT_DIR = previous_attachment_dir

    def test_analysis_batch_size_is_configurable_and_clamped(self) -> None:
        previous_path = app.DB_PATH
        with tempfile.TemporaryDirectory() as directory:
            app.DB_PATH = Path(directory) / "batch-size.db"
            try:
                with app.db() as connection:
                    connection.execute(
                        "CREATE TABLE app_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at TEXT NOT NULL)"
                    )
                    connection.execute(
                        "INSERT INTO app_settings VALUES('analysis_batch_size','75','2026-01-01')"
                    )
                self.assertEqual(app.analysis_batch_size(), 75)
                app.save_setting("analysis_batch_size", "500")
                self.assertEqual(app.analysis_batch_size(), 200)
                app.save_setting("analysis_batch_size", "invalid")
                self.assertEqual(app.analysis_batch_size(), 100)
            finally:
                app.DB_PATH = previous_path

    def test_memory_relevance_benchmark(self) -> None:
        benchmark_path = Path(__file__).resolve().parents[1] / "benchmarks" / "memory_relevance_cases.json"
        benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        failures = []
        for case in benchmark["cases"]:
            entity_type = app.classify_entity_type(case["fact"], case["source_text"])
            relevance = app.classify_personal_relevance(case["fact"], case["source_text"], entity_type)
            if (entity_type, relevance) != (case["expected_entity_type"], case["expected_relevance"]):
                failures.append(
                    f"{case['id']}: expected {(case['expected_entity_type'], case['expected_relevance'])}, "
                    f"got {(entity_type, relevance)}"
                )
        self.assertFalse(failures, "\n".join(failures))

    def test_numeric_outlier_requires_history_and_blocks_order_of_magnitude_error(self) -> None:
        self.assertFalse(app.is_numeric_outlier(98_000_000_000, [12_345_678]))
        self.assertTrue(app.is_numeric_outlier(98_000_000_000, [12_345_678, 12_555_555, 12_222_222]))
        self.assertFalse(app.is_numeric_outlier(14_000_000, [12_345_678, 12_555_555, 12_222_222]))

    def test_short_named_semantic_query_rejects_unrelated_hash_collision(self) -> None:
        self.assertFalse(app.semantic_candidate_allowed("ExampleCorp", "Sample City A往復マイル交換", "Sample City BとSample City Cの旅行", 0.22))
        self.assertTrue(app.semantic_candidate_allowed("ExampleCorp", "勤務先", "ExampleCorpで働いている", 0.08))
        self.assertTrue(app.semantic_candidate_allowed("次の旅行で温泉に行きたい", "過去の旅行", "海鮮と旅館を楽しんだ", 0.25))

    def test_memory_correction_log_is_idempotent(self) -> None:
        previous_path = app.DB_PATH
        with tempfile.TemporaryDirectory() as directory:
            app.DB_PATH = Path(directory) / "corrections.db"
            try:
                with app.db() as connection:
                    connection.execute(
                        """CREATE TABLE memory_corrections(
                           id INTEGER PRIMARY KEY,fact_id INTEGER,entity_id INTEGER,
                           correction_type TEXT,before_json TEXT,after_json TEXT,
                           reason TEXT,source TEXT,quality_version TEXT,created_at TEXT)"""
                    )
                    for _ in range(2):
                        app._record_memory_correction(
                            connection,
                            fact_id=1,
                            entity_id=None,
                            correction_type="fact_quality",
                            before={"state": "pending"},
                            after={"state": "eligible"},
                            reason="benchmark",
                        )
                    count = connection.execute("SELECT COUNT(*) FROM memory_corrections").fetchone()[0]
                self.assertEqual(count, 1)
            finally:
                app.DB_PATH = previous_path

    def test_analysis_summary_counts_only_current_active_jobs(self) -> None:
        previous_path = app.DB_PATH
        with tempfile.TemporaryDirectory() as directory:
            app.DB_PATH = Path(directory) / "summary.db"
            try:
                connection = sqlite3.connect(app.DB_PATH)
                try:
                    connection.executescript(
                        """
                        CREATE TABLE app_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at TEXT NOT NULL);
                        CREATE TABLE entries(id INTEGER PRIMARY KEY,source TEXT NOT NULL);
                        CREATE TABLE documents(id INTEGER PRIMARY KEY,legacy_entry_id INTEGER);
                        CREATE TABLE chunks(id INTEGER PRIMARY KEY,document_id INTEGER,is_active INTEGER);
                        CREATE TABLE attachments(id INTEGER PRIMARY KEY);
                        CREATE TABLE analysis_locks(lock_name TEXT PRIMARY KEY,acquired_at TEXT);
                        CREATE TABLE analysis_jobs(
                          id INTEGER PRIMARY KEY,document_id INTEGER,provider TEXT,model TEXT,
                          prompt_version TEXT,status TEXT,error TEXT,job_kind TEXT,
                          source_chunk_id INTEGER,source_attachment_id INTEGER,attempts INTEGER,
                          priority INTEGER NOT NULL DEFAULT 100,updated_at TEXT
                        );
                        INSERT INTO app_settings VALUES('extract_provider','local','2026-01-01');
                        INSERT INTO app_settings VALUES('local_llm_model','qwen3.5:9b','2026-01-01');
                        INSERT INTO app_settings VALUES('local_llm_base_url','http://127.0.0.1:11434/v1','2026-01-01');
                        INSERT INTO app_settings VALUES('analysis_paused','false','2026-01-01');
                        INSERT INTO entries VALUES(1,'chatgpt-export');
                        INSERT INTO documents VALUES(1,1);
                        INSERT INTO chunks VALUES(1,1,1);
                        INSERT INTO chunks VALUES(2,1,1);
                        INSERT INTO chunks VALUES(3,1,1);
                        INSERT INTO chunks VALUES(4,1,0);
                        """
                    )
                    jobs = [
                        (1, "local", "qwen3.5:9b", app.PROMPT_VERSION, "pending", "", 1),
                        (2, "local", "qwen3.5:9b", app.PROMPT_VERSION, "completed", "", 2),
                        (3, "local", "qwen3.5:9b", app.PROMPT_VERSION, "completed", "excluded by personal relevance prefilter", 3),
                        (4, "local", "old-model", app.PROMPT_VERSION, "pending", "", 1),
                        (5, "local", "qwen3.5:9b", app.PROMPT_VERSION, "pending", "", 4),
                    ]
                    connection.executemany(
                        """INSERT INTO analysis_jobs(
                           id,document_id,provider,model,prompt_version,status,error,job_kind,
                           source_chunk_id,source_attachment_id,attempts,updated_at)
                           VALUES(?,1,?,?,?,?,?,'chunk',?,NULL,0,'2026-01-01')""",
                        jobs,
                    )
                    connection.commit()
                finally:
                    connection.close()
                summary = app.analysis_job_summary()
                self.assertEqual(summary["pending"], 1)
                self.assertEqual(summary["completed"], 1)
                self.assertEqual(summary["skipped"], 1)
                self.assertEqual(summary["total"], 2)
                self.assertEqual(summary["progress"], 50.0)
                self.assertEqual(summary["scope"]["historical_jobs"], 2)
                self.assertEqual(app.pending_import_count(), 1)
                self.assertEqual(app.runnable_analysis_count(), 1)
            finally:
                app.DB_PATH = previous_path

    def test_monthly_investment_is_a_single_concept_key(self) -> None:
        key = app.canonical_fact_key(
            "finance", "plan", "total", {}, "毎月5.678万円を積立する"
        )
        self.assertEqual(key, "finance.monthly_investment.total")

    def test_different_finance_scopes_do_not_collide(self) -> None:
        fund = app.canonical_fact_key(
            "finance", "plan", "投資信託", {}, "毎月5.678万円を積立する"
        )
        stock_plan = app.canonical_fact_key(
            "finance", "plan", "ExampleCorp持株会", {}, "毎月1.2万円を積立する"
        )
        self.assertNotEqual(fund, stock_plan)

    def test_relationships_require_evidence_not_category_confirmation(self) -> None:
        self.assertEqual(
            app.fact_policy({"category": "relationship", "type": "note"}),
            "evidence_required",
        )

    def test_provider_boundary_resolves_local_ollama(self) -> None:
        provider = app.resolve_llm_provider("local")
        self.assertIsNotNone(provider)
        self.assertEqual(provider.name, "local")
        self.assertIsNone(app.resolve_llm_provider("unknown"))

    def test_auto_provider_prefers_local_before_configured_cloud_keys(self) -> None:
        with patch.dict(os.environ, {
            "LOCAL_LLM_BASE_URL": "http://127.0.0.1:11434/v1",
            "OPENAI_API_KEY": "test-openai",
            "GEMINI_API_KEY": "test-gemini",
        }, clear=False), patch.object(app, "setting", side_effect=lambda key, default="": default):
            self.assertEqual(app.selected_provider("chat"), "local")
            self.assertEqual(app.selected_provider("extract"), "local")

    def test_auto_provider_is_none_when_local_unavailable_even_with_cloud_keys(self) -> None:
        with patch.dict(os.environ, {
            "LOCAL_LLM_BASE_URL": "",
            "OPENAI_API_KEY": "test-openai",
            "GEMINI_API_KEY": "test-gemini",
        }, clear=False), patch.object(app, "setting", side_effect=lambda key, default="": default):
            self.assertEqual(app.selected_provider("chat"), "none")
            self.assertEqual(app.selected_provider("extract"), "none")

    def test_explicit_cloud_provider_remains_available(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-openai"}, clear=False), \
             patch.object(app, "setting", side_effect=lambda key, default="": "openai" if key == "chat_provider" else default):
            self.assertEqual(app.selected_provider("chat"), "openai")

    def test_lan_auth_policy_distinguishes_loopback(self) -> None:
        self.assertFalse(app.access_auth_required("127.0.0.1"))
        self.assertTrue(app.access_auth_required("192.168.1.20"))

    def test_extraction_parallel_is_opt_in_and_filters_unconfigured_providers(self) -> None:
        values = {
            "extract_parallel_providers": "local,gemini",
            "local_llm_base_url": "http://127.0.0.1:11434/v1",
        }
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini"}, clear=False), \
             patch.object(app, "setting", side_effect=lambda key, default="": values.get(key, default)):
            self.assertEqual(app.extraction_providers(), ["local", "gemini"])
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini"}, clear=False), \
             patch.object(app, "setting", side_effect=lambda key, default="": "" if key == "extract_parallel_providers" else default), \
             patch.object(app, "selected_provider", return_value="none"):
            self.assertEqual(app.extraction_providers(), [])

    def test_local_autostart_only_targets_native_ollama_and_can_be_disabled(self) -> None:
        with patch.object(app, "setting", side_effect=lambda key, default="": {
            "local_llm_base_url": "https://remote.example/v1",
            "auto_start_local_llm": "true",
        }.get(key, default)):
            self.assertFalse(app.ensure_local_llm_available())
        with patch.object(app, "setting", side_effect=lambda key, default="": {
            "local_llm_base_url": "http://127.0.0.1:11434/v1",
            "auto_start_local_llm": "false",
        }.get(key, default)), patch.object(app, "_ollama_reachable", return_value=False):
            self.assertFalse(app.ensure_local_llm_available())

    def test_custom_category_slug_is_normalized(self) -> None:
        self.assertEqual(app.normalize_category_slug("Vehicle Notes"), "vehicle-notes")

    def test_reference_is_not_auto_saved_as_personal_memory(self) -> None:
        self.assertEqual(
            app.fact_policy({"category": "reference", "type": "note"}),
            "exclude",
        )

    def test_health_policy_requires_evidence(self) -> None:
        self.assertEqual(app.fact_policy({"category": "health", "type": "note"}), "evidence_required")

    def test_explicit_sensitive_fact_is_auto_confirmed_from_evidence(self) -> None:
        fact = {
            "category": "health", "type": "note", "summary": "頭痛がある",
            "details": {}, "evidence_quote": "頭痛がある",
        }
        state, _ = app.fact_review_decision(fact, 0.9, evidence_text="今日は頭痛がある")
        self.assertEqual(state, "confirmed")

    def test_inferred_relationship_fact_is_rejected_without_human_review(self) -> None:
        fact = {
            "category": "relationship", "type": "note", "summary": "相手は自分に好感度が高いと思われる",
            "details": {},
        }
        state, _ = app.fact_review_decision(fact, 0.99, evidence_text="会話をした")
        self.assertEqual(state, "rejected")

    def test_explicit_sensitive_statement_is_not_rejected_by_topic_word(self) -> None:
        fact = {
            "category": "relationship", "type": "note", "summary": "\u81ea\u5206\u306f\u614e\u91cd\u306a\u6027\u683c\u3060",
            "details": {}, "evidence_quote": "\u81ea\u5206\u306f\u614e\u91cd\u306a\u6027\u683c\u3060",
        }
        state, _ = app.fact_review_decision(
            fact, 0.9, evidence_text="\u672c\u4eba\u304c\u300c\u81ea\u5206\u306f\u614e\u91cd\u306a\u6027\u683c\u3060\u300d\u3068\u660e\u793a\u3057\u305f",
        )
        self.assertEqual(state, "confirmed")

    def test_non_person_project_is_resolved_as_fictional_character(self) -> None:
        fact = {
            "category": "relationship", "type": "note",
            "summary": "\u6771\u5317\u5730\u65b9\u3092PR\u3059\u308b\u30ad\u30e3\u30e9\u30af\u30bf\u30fc\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u306e\u4ef2\u9593\u95a2\u4fc2",
            "asset": "['\u305A\u3093\u3060\u3082\u3093', '\u304D\u308A\u305F\u3093']",
        }
        self.assertEqual(app.classify_entity_type(fact), "fictional_character")

    def test_person_relationship_requires_person_markers(self) -> None:
        self.assertEqual(
            app.classify_entity_type({"category": "relationship", "type": "note", "summary": "\u53cb\u4eba\u306eA\u3055\u3093\u3068\u4f1a\u3063\u305f"}),
            "person",
        )
        self.assertEqual(
            app.classify_entity_type({"category": "relationship", "type": "note", "summary": "\u30ad\u30e3\u30e9\u30af\u30bf\u30fc\u540c\u58eb\u306e\u4ef2\u9593\u95a2\u4fc2"}),
            "fictional_character",
        )

    def test_quality_gate_excludes_non_person_relationship(self) -> None:
        fact = {
            "category": "relationship", "type": "note",
            "summary": "\u30a2\u30cb\u30e1\u306e\u30ad\u30e3\u30e9\u30af\u30bf\u30fc\u306e\u4ef2\u9593\u95a2\u4fc2",
        }
        entity_type = app.classify_entity_type(fact)
        self.assertNotEqual(entity_type, "person")
        self.assertEqual(app._quality_reclassification("relationship", entity_type, fact["summary"]), "reference")

    def test_conversation_chunks_do_not_join_unrelated_turns_when_over_limit(self) -> None:
        text = "user: " + ("資産の相談。" * 220) + "\n\nassistant: 旅行の相談です。"
        chunks = app.conversation_turn_chunks(text, size=500)
        self.assertGreaterEqual(len(chunks), 3)
        self.assertTrue(all("旅行の相談です" not in chunk for chunk in chunks[:-1]))
        self.assertIn("旅行の相談です", chunks[-1])

    def test_conversation_chunks_keep_exchange_boundaries(self) -> None:
        chunks = app.conversation_turn_chunks(
            "user: 資産の相談\n\nassistant: 積立を確認します\n\nuser: 旅行の相談\n\nassistant: 温泉候補を探します",
            size=1800,
        )
        self.assertEqual(len(chunks), 2)
        self.assertNotIn("旅行の相談", chunks[0])
        self.assertNotIn("資産の相談", chunks[1])

    def test_non_personal_reference_is_archive_only(self) -> None:
        fact = {
            "category": "learning", "type": "note",
            "summary": "一般的なプロジェクトの説明",
            "details": {},
        }
        self.assertEqual(app.classify_personal_relevance(fact, "公式設定のプロジェクトです", "project"), "archive_only")

    def test_linked_context_is_not_current_personal_memory(self) -> None:
        fact = {"category": "travel", "type": "note", "summary": "旅行候補の外部情報", "details": {"personal_relevance": "linked_context"}}
        self.assertEqual(app.classify_personal_relevance(fact, "旅行候補", "place"), "linked_context")

    def test_personal_relevance_requires_user_evidence(self) -> None:
        self.assertEqual(
            app.classify_personal_relevance(
                {"category": "travel", "type": "note", "summary": "旅行についての一般情報", "details": {}},
                "観光地の一般的な紹介",
                "place",
            ),
            "archive_only",
        )
        self.assertEqual(
            app.classify_personal_relevance(
                {"category": "travel", "type": "note", "summary": "次の旅行で温泉に行きたい", "details": {}},
                "次の旅行で温泉に行きたい",
                "unknown",
            ),
            "personal",
        )

    def test_extraction_prompt_rejects_assistant_general_knowledge_as_personal_fact(self) -> None:
        prompt = app.extraction_prompt("user: CCLの決算を教えて\n\nassistant: 売上を説明します")
        self.assertIn("assistant: の説明", prompt)
        self.assertIn('{"facts":[]}', prompt)
        self.assertEqual(app.PROMPT_VERSION, "memory-facts-jp-v3")

    def test_chatgpt_chunk_prefilter_rejects_generic_reference(self) -> None:
        self.assertFalse(app.chunk_may_contain_personal_memory("user: Kubernetesの一般的な概要を説明して"))
        self.assertTrue(app.chunk_may_contain_personal_memory("user: 今月は持株会に12,345円入れた"))

    def test_explicit_finance_transaction_can_auto_confirm(self) -> None:
        fact = {
            "category": "finance", "type": "transaction", "summary": "自分が投資信託を12345円購入した",
            "asset": "投資信託", "amount": 12345, "details": {},
        }
        validation = {"state": "auto_confirmed", "is_actual": True, "reason": "eligible"}
        state, _ = app.fact_review_decision(fact, 0.8, evidence_text="自分が投資信託を12345円購入した", transaction_validation=validation)
        self.assertEqual(state, "confirmed")

    def test_screenshot_mime_detection_rejects_non_images(self) -> None:
        self.assertEqual(app.detect_image_mime(b"\x89PNG\r\n\x1a\nrest"), "image/png")
        self.assertEqual(app.detect_image_mime(b"not an image"), None)

    def test_multipart_screenshot_parser_keeps_context_and_file(self) -> None:
        boundary = b"test-boundary"
        body = b"--" + boundary + b"\r\nContent-Disposition: form-data; name=\"context\"\r\n\r\nfinance\r\n"
        body += b"--" + boundary + b"\r\nContent-Disposition: form-data; name=\"file\"; filename=\"shot.png\"\r\nContent-Type: image/png\r\n\r\nPNGDATA\r\n"
        body += b"--" + boundary + b"--\r\n"
        content, name, mime, fields = multipart_form_file(body, "multipart/form-data; boundary=test-boundary")
        self.assertEqual((content, name, mime, fields), (b"PNGDATA", "shot.png", "image/png", {"context": "finance"}))

    def test_ollama_client_detects_native_endpoint(self) -> None:
        client = OllamaClient("http://127.0.0.1:11434/v1", "qwen3.5:9b")
        self.assertTrue(client.is_native)
        self.assertEqual(client.native_base, "http://127.0.0.1:11434")

    def test_money_projection_summarizes_confirmed_current_facts(self) -> None:
        facts = [
            {"status": "current", "review_state": "confirmed", "fact_type": "asset_balance",
             "summary": "現金残高", "value_json": '{"amount": 1000000, "asset": "現金"}'},
            {"status": "current", "review_state": "confirmed", "fact_type": "plan",
             "summary": "毎月積立", "value_json": '{"amount": 56780, "asset": "投資信託"}'},
        ]
        summary = app._money_summary(facts, [])
        self.assertEqual(summary["total_assets"], 1000000)
        self.assertEqual(summary["breakdown"]["現金"], 1000000)
        self.assertEqual(summary["monthly_investment"], 56780)

    def test_transaction_validator_accepts_explicit_user_investment(self) -> None:
        result = app.validate_transaction_candidate({
            "category": "finance", "fact_type": "transaction", "summary": "今月はExampleCorpの持株会に12,345円入れた",
            "value_json": '{"amount": 12345, "currency": "JPY", "details": {}}', "confidence": 1.0,
        })
        self.assertEqual(result["state"], "auto_confirmed")
        self.assertEqual(result["actor"], "self")
        self.assertEqual(result["kind"], "investment")
        self.assertEqual(result["normalized_amount"], 12345)

    def test_transaction_validator_excludes_simulation_and_company_data(self) -> None:
        simulation = app.validate_transaction_candidate({
            "category": "finance", "fact_type": "transaction", "summary": "3,000万円借りた場合の返済シミュレーション",
            "value_json": '{"amount": 3000, "currency": "万円", "details": {}}', "confidence": 1.0,
        })
        company = app.validate_transaction_candidate({
            "category": "finance", "fact_type": "transaction", "summary": "企業Aは980億円の赤字",
            "value_json": '{"amount": 980, "currency": "億円", "details": {}}', "confidence": 1.0,
        })
        self.assertEqual(simulation["state"], "excluded")
        self.assertEqual(simulation["reason"], "simulation")
        self.assertEqual(company["state"], "excluded")
        self.assertEqual(company["reason"], "company_financials")

    def test_transaction_amount_normalizes_japanese_units_and_keeps_raw(self) -> None:
        result = app.normalize_transaction_amount(1847, "万円", "購入価格1847万円")
        self.assertEqual(result["normalized_amount"], 18470000)
        self.assertEqual(result["raw_amount_text"], "1847万円")


    def test_recommendation_is_explainable_and_does_not_execute_actions(self) -> None:
        previous_path = app.DB_PATH
        previous_backup_dir = app.BACKUP_DIR
        previous_attachment_dir = app.ATTACHMENT_DIR
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app.DB_PATH = root / "recommendation.db"
            app.BACKUP_DIR = root / "backups"
            app.ATTACHMENT_DIR = root / "attachments"
            try:
                app.initialize()
                draft = app.build_local_recommendation("travel", "next trip")
                self.assertEqual(draft["domain"], "travel")
                self.assertTrue(draft["options"])
                self.assertEqual(draft["criteria"]["source"], "query_relevant_memory")
            finally:
                app.DB_PATH = previous_path
                app.BACKUP_DIR = previous_backup_dir
                app.ATTACHMENT_DIR = previous_attachment_dir

    def test_anomaly_detection_returns_pairwise_audit_shape(self) -> None:
        with isolated_personal_os():
            anomalies = app.detect_fact_anomalies(2)
            for anomaly in anomalies:
                self.assertIn(anomaly["kind"], {"contradiction", "numeric_outlier"})
                self.assertEqual(len(anomaly["facts"]), 2)

    def test_local_embedding_is_deterministic_and_normalized(self) -> None:
        first = app.local_embedding("旅行 温泉", 32)
        second = app.local_embedding("旅行 温泉", 32)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 32)
        self.assertAlmostEqual(sum(value * value for value in first) ** 0.5, 1.0, places=4)


if __name__ == "__main__":
    unittest.main()
