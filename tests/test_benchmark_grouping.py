import unittest

import app


def series(**changes):
    value = {
        "metric_key": "finance.financial_assets",
        "source_url": "https://example.test/statistics",
        "publisher": "Example Statistics Office",
        "population_scope": "individuals aged 30-39",
        "geography": "Japan",
        "segment_definition": {"age": "30-39", "household": "individual"},
        "version": "2026-01",
        "metric_contract": {
            "statistical_unit": "individual",
            "measurement_kind": "balance",
            "time_basis": "point_in_time",
            "canonical_unit": "JPY",
        },
        "observations": [{"reference_period": "2025"}],
    }
    value.update(changes)
    return value


class BenchmarkGroupingTests(unittest.TestCase):
    def test_mean_and_median_share_only_the_same_comparison_context(self):
        self.assertEqual(
            app.benchmark_comparison_group_key(series(statistic_type="mean")),
            app.benchmark_comparison_group_key(series(statistic_type="median")),
        )

    def test_every_compatibility_dimension_separates_groups(self):
        baseline = app.benchmark_comparison_group_key(series())
        variants = (
            series(metric_key="finance.total_assets"),
            series(source_url="https://other.example.test/statistics"),
            series(publisher="Another publisher"),
            series(population_scope="households"),
            series(geography="Tokyo"),
            series(segment_definition={"age": "40-49", "household": "individual"}),
            series(observations=[{"reference_period": "2024"}]),
            series(version="2025-12"),
            series(metric_contract={"statistical_unit": "household", "measurement_kind": "balance", "time_basis": "point_in_time", "canonical_unit": "JPY"}),
            series(metric_contract={"statistical_unit": "individual", "measurement_kind": "flow", "time_basis": "annual", "canonical_unit": "JPY"}),
            series(metric_contract={"statistical_unit": "individual", "measurement_kind": "balance", "time_basis": "point_in_time", "canonical_unit": "USD"}),
        )
        for candidate in variants:
            with self.subTest(candidate=candidate):
                self.assertNotEqual(baseline, app.benchmark_comparison_group_key(candidate))


if __name__ == "__main__":
    unittest.main()
