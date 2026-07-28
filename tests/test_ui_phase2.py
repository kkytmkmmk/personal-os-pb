import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class UiPhase2StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        cls.index = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        cls.css = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")
        cls.sw = (ROOT / "static" / "service-worker.js").read_text(encoding="utf-8")

    def test_router_owns_hash_navigation(self):
        self.assertIn("function navigateTo", self.app_js)
        self.assertIn("hashchange", self.app_js)
        self.assertIn("popstate", self.app_js)
        self.assertNotIn("document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener", self.index)

    def test_today_has_no_daily_input_or_cycle_board(self):
        self.assertIn("cleanupLegacyToday", self.app_js)
        self.assertIn("today-cycle-summary", self.app_js)
        self.assertIn("const consultation = $('#chat')", self.app_js)
        self.assertIn("#today-ask-form, #recommendation-panel", self.css)

    def test_memory_record_is_single_primary_input(self):
        self.assertIn("id = 'record-card'", self.app_js)
        self.assertIn('id="record-text"', self.app_js)
        self.assertIn("record-advanced", self.app_js)

    def test_correction_actions_do_not_require_browser_prompt(self):
        self.assertIn("function overrideLegacyPrompts", self.app_js)
        self.assertIn("factCorrectionSheet", self.app_js)
        self.assertIn("legacyDecisionSheet", self.app_js)

    def test_service_worker_refreshes_phase2_assets(self):
        self.assertIn("personal-os-v3-reliability-2", self.sw)
        self.assertIn('"/styles.css"', self.sw)
        self.assertIn('"/api-client.js"', self.sw)
        self.assertIn('"/app.js"', self.sw)
        self.assertIn('"/visualization.js"', self.sw)

    def test_personal_space_uses_temporal_buckets_and_accessible_fallback(self):
        visualization = (ROOT / "static" / "visualization.js").read_text(encoding="utf-8")
        self.assertIn("node.temporal_bucket === 'current'", visualization)
        self.assertIn("personal-space-fallback", visualization)
        self.assertIn("wireGestures", visualization)
        self.assertNotIn("percentile_hint || 50", visualization)
        self.assertIn("reasonText", visualization)


if __name__ == "__main__":
    unittest.main()
