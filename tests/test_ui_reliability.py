import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReliabilityStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        cls.client = (ROOT / "static" / "api-client.js").read_text(encoding="utf-8")
        cls.index = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        cls.backend = (ROOT / "app.py").read_text(encoding="utf-8")

    def test_single_api_boundary_and_native_fetch_not_monkeypatched(self):
        self.assertIn("window.apiClient", self.client)
        self.assertIn('X-Request-ID', self.client)
        self.assertNotIn("window.fetch =", self.app)
        self.assertNotIn("window.fetch =", self.index)
        self.assertIn('/api-client.js', self.index)

    def test_auth_csrf_and_structured_errors(self):
        self.assertIn("personal-os-auth-required", self.client)
        self.assertIn("personal-os-api-error", self.client)
        self.assertIn('error_type', self.backend)
        self.assertIn('X-CSRF-Token', self.backend)

    def test_diagnostics_and_trace_are_content_free(self):
        self.assertIn('/api/diagnostics', self.backend)
        self.assertIn('LLM_TRACE_EVENTS', self.backend)
        self.assertIn('frontendErrors', self.app)
        self.assertIn('personal-os-llm-stage', self.app)

    def test_candidate_is_saved_as_displayed(self):
        self.assertIn('body: JSON.stringify({ candidate })', self.app)
        self.assertIn('supplied_candidate = payload.get("candidate")', self.backend)
        self.assertIn('candidate_id', self.backend)


if __name__ == "__main__":
    unittest.main()
