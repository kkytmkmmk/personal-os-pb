# Visualization and Population Benchmark traceability

This document tracks the additive implementation for
`requirements/11_visualization_requirements.md` and
`requirements/12_population_benchmark_requirements.md`.  Personal memory and
public-reference data remain separate.

| Requirement | Implementation | Verification | Status |
| --- | --- | --- | --- |
| Local reference data and provenance | `benchmark_sources`, `benchmark_series`, `benchmark_observations`, `benchmark_refresh_runs`; migration `012_visualization_benchmark` | `test_reference_import_is_local_and_keeps_provenance` | Done |
| Source/definition/scope required | `import_benchmark_reference()` validates source URL, publisher, definition, scope, statistic type, and observation period | `test_import_rejects_undocumented_reference_source` | Done |
| No personal-data outbound transfer | Import accepts a local payload only; no remote adapter is installed; `/api/benchmarks` reads SQLite only | Unit/API smoke | Done |
| Current Fact comparison safety | `BENCHMARK_METRIC_CONTRACTS` separates metric identity, statistical unit, measurement kind, time basis, and canonical unit. `subject_scope` is not treated as a population unit. | `test_comparison_requires_statistical_contract_not_subject_scope`, `test_total_assets_is_not_matched_to_financial_assets` | Done |
| Explicit unit normalization | JPY/円/万円/億円 and hours/minutes normalize only when an explicit unit is present; unknown units remain reference-only. | `test_normalizes_explicit_monetary_units_and_rejects_unknown_units` | Done |
| Bundle atomicity and preview parity | Every dataset is validated before one SQLite transaction writes the bundle; invalid later datasets leave no earlier write. | `test_bundle_validation_rolls_back_all_datasets_and_decodes_distribution` | Done |
| Distribution API and percentile safety | SQLite JSON is decoded to `distribution`/`segment_values`; only a verified percentile band is shown, never a fabricated point marker. | `test_bundle_validation_rolls_back_all_datasets_and_decodes_distribution`, `test_percentile_band_never_falls_back_to_a_fake_marker` | Done |
| Historical reference preservation | Observation uniqueness includes series, period, revision, and segment definition; imports update only the same revision key | `test_reference_import_is_local_and_keeps_provenance` | Done |
| Personal Space deterministic layout | `/api/personal-space` returns bounded nodes; `static/visualization.js` derives coordinates from stable IDs and domain anchors | API smoke | Done |
| Current/history distinction and filtering | Backend emits `temporal_bucket`; UI filters on it rather than node status. | `test_personal_space_uses_temporal_buckets_and_accessible_fallback` | Done |
| Sensitive-label default masking | Finance, health, and relationship labels are masked for Fact, Decision, Recommendation, Plan, Result, and execution-event nodes unless locally revealed. | `test_personal_space_masks_every_sensitive_node_and_inherits_result_domain` | Done |
| Result domain and edge integrity | Execution-event Results inherit a linked Plan/Decision domain; dangling lifecycle edges are removed. | `test_personal_space_masks_every_sensitive_node_and_inherits_result_domain` | Done |
| Interaction/accessibility | Stable Canvas supports rotate, zoom, pan and reset; a focusable node-list fallback is rendered. | Static UI test and verification-server startup | Partial |
| iPhone/reduced-motion fallback | Canvas renderer caps mobile node count; no animation loop; Canvas is the non-WebGL fallback | source inspection | Done |
| Automated remote source refresh | No remote refresh adapter is implemented yet; manual import is intentional for the first release | N/A | Partial |
| Distribution percentile visualization | Five-point distributions are displayed with a verified band only. Full density rendering is deferred. | `test_percentile_band_never_falls_back_to_a_fake_marker` | Partial |

## Operational notes

- Migration `012_visualization_benchmark` creates a full backup before the
  first schema change on an existing database.
- Public-reference imports are local and additive. They do not copy or mutate
  Facts, Decisions, raw conversations, or attachments.
- The comparison screen is a secondary management surface. It is not shown in
  the primary Today navigation.
