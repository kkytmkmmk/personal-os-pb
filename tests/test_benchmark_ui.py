import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BenchmarkUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "static" / "visualization.js").read_text(encoding="utf-8")

    def test_frontend_groups_backend_comparison_context(self):
        self.assertIn("row.comparison_group_key || `series:${row.id}`", self.source)
        self.assertNotIn("groups[row.metric_key]", self.source)

    def test_internal_benchmark_values_have_japanese_display_maps(self):
        for internal, label in {
            "exact": "同条件で比較可能",
            "mean": "平均",
            "official": "公的統計",
            "no_confirmed_current_fact": "比較できる現在情報がありません",
        }.items():
            with self.subTest(internal=internal):
                self.assertIn(internal, self.source)
                self.assertIn(label, self.source)
        self.assertIn("比較条件を確認できません", self.source)


if __name__ == "__main__":
    unittest.main()
