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
        cls.daily_ux = (ROOT / "static" / "daily-ux.js").read_text(encoding="utf-8")
        cls.action_center = (ROOT / "static" / "action-center.js").read_text(encoding="utf-8")

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
        self.assertIn("personal-os-v3-phase-b-ux1-stabilization-4", self.sw)
        self.assertIn('"/styles.css"', self.sw)
        self.assertIn('"/api-client.js"', self.sw)
        self.assertIn('"/app.js"', self.sw)
        self.assertIn('"/visualization.js"', self.sw)
        self.assertIn('"/daily-ux.js"', self.sw)

    def test_personal_space_uses_temporal_buckets_and_accessible_fallback(self):
        visualization = (ROOT / "static" / "visualization.js").read_text(encoding="utf-8")
        self.assertIn("node.temporal_bucket === 'current'", visualization)
        self.assertIn("personal-space-fallback", visualization)
        self.assertIn("wireGestures", visualization)
        self.assertIn('id="space-reset"', self.index)
        self.assertNotIn("percentile_hint || 50", visualization)
        self.assertIn("nodeKindLabels", visualization)
        self.assertIn("temporalLabels", visualization)
        self.assertIn("benchmarkReasonLabels", visualization)
        self.assertNotIn("reasonText", visualization)
        self.assertNotIn("現在Fact", visualization)
        self.assertNotIn("個人Fact", visualization)

    def test_daily_navigation_and_capture_are_static_and_single_purpose(self):
        self.assertIn('src="/daily-ux.js"', self.index)
        self.assertIn('data-action="domains"', self.index)
        self.assertIn('id="domains-sheet"', self.index)
        self.assertIn('id="benchmark-import-sheet"', self.index)
        self.assertIn('data-tab="explore">探索', self.index)
        self.assertIn("unifyCapture", self.daily_ux)
        self.assertIn("closest('.card')?.remove()", self.daily_ux)
        self.assertIn("streamlineConsultation", self.daily_ux)
        self.assertIn("streamlineDecisions", self.daily_ux)
        self.assertIn("sessionStorage", self.daily_ux)

    def test_consultation_exposes_progress_missing_context_and_collapsed_evidence(self):
        self.assertIn('id="consultation-status"', self.daily_ux)
        self.assertIn("記憶と過去の判断を確認しています", self.daily_ux)
        self.assertIn("関連する情報を選んでいます", self.daily_ux)
        self.assertIn("consultation-missing", self.daily_ux)
        self.assertIn("missing_context", self.daily_ux)
        self.assertIn("参照した根拠を見る", self.daily_ux)

    def test_decision_screen_prioritizes_next_action_and_uses_sheet_for_outcomes(self):
        self.assertIn("controls.id = 'decision-filters'", self.daily_ux)
        self.assertIn("decision-state-filter", self.daily_ux)
        self.assertIn("data-decision-action=\"execute\"", self.daily_ux)
        self.assertIn("data-decision-outcome", self.daily_ux)
        self.assertIn("personalOsOpenDecisionOutcome", self.index)
        self.assertNotIn("window.recordDecisionResult=async id=>{const result=prompt", self.index)
        self.assertNotIn("window.evaluateDecision=async id=>{const text=prompt", self.index)

    def test_domain_and_explore_surfaces_keep_daily_and_technical_actions_separate(self):
        self.assertIn("standardizeDomainViews", self.daily_ux)
        self.assertIn("domain-recent-changes", self.daily_ux)
        self.assertIn("根拠あり", self.daily_ux)
        self.assertIn("technical-detail", self.daily_ux)
        self.assertIn("benchmark-import-sheet", self.index)
        self.assertIn("benchmark-import-open", self.daily_ux)

    def test_empty_personal_space_can_return_to_recording(self):
        visualization = (ROOT / "static" / "visualization.js").read_text(encoding="utf-8")
        self.assertIn("data-space-record", visualization)
        self.assertIn("personalOsNavigate?.('home')", visualization)

    def test_mobile_sheets_preserve_focus_and_pwa_shell_is_refreshed(self):
        self.assertIn("const sheetOpeners = new Map()", self.daily_ux)
        self.assertIn("sheetOpeners.get(sheet.id)", self.daily_ux)
        self.assertIn("window.personalOsSheets", self.daily_ux)
        self.assertIn("focusableIn", self.daily_ux)
        self.assertIn("classList.add('sheet-open')", self.daily_ux)
        self.assertIn("personal-os-v3-phase-b-ux1-stabilization-4", self.sw)

    def test_capture_only_confirms_after_response_and_domain_renderer_is_shared(self):
        self.assertIn("保存しています…", self.daily_ux)
        self.assertIn("保存できませんでした。入力内容は保持しています", self.daily_ux)
        self.assertIn("personal-os-api-response", self.daily_ux)
        self.assertIn("domain-current", self.daily_ux)
        self.assertIn("domain-recent", self.daily_ux)
        self.assertIn("domain-decisions", self.daily_ux)
        self.assertIn("domain-history", self.daily_ux)
        self.assertIn("domain-evidence", self.daily_ux)
        self.assertIn("personalOsRenderDomain", self.daily_ux)

    def test_today_candidate_refresh_owns_its_card_reference(self):
        self.assertIn("let card = document.querySelector('#today-next-candidates');", self.index)

    def test_daily_digest_uses_a_dedicated_api_and_never_auto_sends(self):
        self.assertIn("/api/today/digest", self.action_center)
        self.assertIn("digest.id = 'today-digest'", self.action_center)
        self.assertIn("今日の一言", self.action_center)
        self.assertIn("最近変わったこと", self.action_center)
        self.assertIn("相談候補", self.action_center)
        self.assertIn("data-digest-prompt", self.action_center)
        self.assertIn("field.value = button.dataset.digestPrompt", self.action_center)
        self.assertNotIn("chat-form').requestSubmit", self.action_center)
        self.assertIn("function refreshDailyDigest() { return window.refreshActionCenter?.(); }", self.daily_ux)
        self.assertIn("today-digest", self.app_js)


if __name__ == "__main__":
    unittest.main()
