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
| Current Fact comparison safety | Only confirmed, retrieval-eligible, current Facts with an exact/allow-listed `fact_key` can be compared; a unit mismatch is `incompatible` | Code path and unit suite | Done |
| Historical reference preservation | Observation uniqueness includes series, period, revision, and segment definition; imports update only the same revision key | `test_reference_import_is_local_and_keeps_provenance` | Done |
| Personal Space deterministic layout | `/api/personal-space` returns bounded nodes; `static/visualization.js` derives coordinates from stable IDs and domain anchors | API smoke | Done |
| Current/history distinction and filtering | Node status/opacity, local current/history filters, category legend, drag/zoom controls | API/UI smoke | Done |
| Sensitive-label default masking | Finance, health, and relationship labels are masked unless the local reveal toggle is selected | `test_personal_space_masks_sensitive_domains_by_default` | Done |
| iPhone/reduced-motion fallback | Canvas renderer caps mobile node count; no animation loop; Canvas is the non-WebGL fallback | source inspection | Done |
| Automated remote source refresh | No remote refresh adapter is implemented yet; manual import is intentional for the first release | N/A | Partial |
| Distribution percentile visualization | Distribution metadata is retained but a percentile chart is not yet rendered | N/A | Partial |

## Operational notes

- Migration `012_visualization_benchmark` creates a full backup before the
  first schema change on an existing database.
- Public-reference imports are local and additive. They do not copy or mutate
  Facts, Decisions, raw conversations, or attachments.
- The comparison screen is a secondary management surface. It is not shown in
  the primary Today navigation.
