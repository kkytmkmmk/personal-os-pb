import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DecisionReplayUiTests(unittest.TestCase):
    def test_replay_uses_a_local_read_only_projection_and_sheet(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "daily-ux.js").read_text(encoding="utf-8")
        self.assertIn('id="decision-replay-sheet"', html)
        self.assertIn('/api/decisions/${Number(decisionId)}/replay', script)
        self.assertIn('window.personalOsOpenDecisionReplay', script)
        self.assertIn('replayStageLabels', script)
        self.assertIn('data-decision-replay', script)
        self.assertNotIn('requestSubmit()', script[script.index('function openDecisionReplay'):script.index('function setupUxFeedback')])

    def test_feedback_is_local_and_preserves_a_draft(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "daily-ux.js").read_text(encoding="utf-8")
        self.assertIn('id="ux-feedback-sheet"', html)
        self.assertIn('/api/ux-feedback', script)
        self.assertIn('personal-os-draft-ux-feedback', script)
        self.assertIn('data-action="ux-feedback"', html)

    def test_service_worker_cache_is_refreshed_for_b3(self):
        worker = (ROOT / "static" / "service-worker.js").read_text(encoding="utf-8")
        self.assertIn('personal-os-v3-phase-b-ux1-stabilization-3', worker)


if __name__ == "__main__":
    unittest.main()
