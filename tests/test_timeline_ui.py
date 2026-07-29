import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TimelineUiTests(unittest.TestCase):
    def test_explore_has_a_japanese_timeline_mode_and_detail_sheet(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-explore-mode="timeline">自分の変化', html)
        self.assertIn('id="explore-timeline"', html)
        self.assertIn('id="timeline-detail-sheet"', html)
        self.assertIn('id="timeline-period"', html)

    def test_timeline_client_uses_paginated_api_and_never_auto_sends_compare(self):
        script = (ROOT / "static" / "visualization.js").read_text(encoding="utf-8")
        self.assertIn('/api/timeline?', script)
        self.assertIn('timelineCursor', script)
        self.assertIn('data-timeline-compare', script)
        self.assertIn("window.personalOsNavigate?.('chat')", script)
        self.assertNotIn("chatForm.requestSubmit", script)

    def test_today_digest_links_to_timeline(self):
        script = (ROOT / "static" / "daily-ux.js").read_text(encoding="utf-8")
        self.assertIn('data-digest-timeline', script)
        self.assertIn('data-explore-mode="timeline"', script)


if __name__ == "__main__":
    unittest.main()
