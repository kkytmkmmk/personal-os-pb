import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ActionCenterUiStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        cls.app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        cls.js = (ROOT / "static" / "action-center.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")
        cls.worker = (ROOT / "static" / "service-worker.js").read_text(encoding="utf-8")

    def test_action_center_bundle_is_loaded(self):
        self.assertIn('<script src="/action-center.js" defer></script>', self.index)

    def test_today_renders_one_top_action(self):
        self.assertIn('data-action-primary', self.js)
        self.assertNotIn('data-action-primary-${', self.js)

    def test_today_renders_action_reason(self):
        self.assertIn('action.reason', self.js)
        self.assertIn('action-reason', self.css)

    def test_today_has_only_three_quick_routes(self):
        markup = self.js.split('class="quick-actions"', 1)[1].split('</div>', 1)[0]
        self.assertEqual(markup.count('data-quick-route='), 3)

    def test_client_draft_has_priority_hook(self):
        self.assertIn('clientDraftAction() || data.top_action', self.js)
        self.assertIn('personal-os-draft-memo', self.js)
        self.assertIn('personal-os-draft-chat', self.js)

    def test_review_inbox_uses_deterministic_api(self):
        self.assertIn('/api/review-inbox?', self.js)
        self.assertNotIn('Math.random', self.js)

    def test_review_inbox_has_required_tabs(self):
        for label in ('今確認したい', '通常', 'あとで', 'すべて'):
            self.assertIn(label, self.js)

    def test_review_card_has_four_primary_choices(self):
        for label in ('正しい', '修正', '違う', '後で'):
            self.assertIn(label, self.js)

    def test_sensitive_default_is_masked(self):
        self.assertIn('機微情報のため、一覧では原文を表示しません', self.js)

    def test_maintenance_moves_to_closed_details(self):
        self.assertIn("details.id = 'memory-maintenance'", self.js)
        self.assertIn('記憶メンテナンス', self.js)
        self.assertNotIn('details.open = true', self.js)

    def test_user_labels_are_review_inbox_and_weekly_review(self):
        self.assertIn("verify: '確認Inbox'", self.app_js)
        self.assertIn("review: '週次レビュー'", self.app_js)

    def test_service_worker_uses_required_cache_version(self):
        self.assertIn('personal-os-v3-phase-b-ux1-action-center-1', self.worker)
        self.assertIn('/action-center.js', self.worker)


if __name__ == "__main__":
    unittest.main()
