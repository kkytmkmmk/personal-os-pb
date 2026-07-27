# Additional correction traceability (2026-07-26)

This document records the implementation and acceptance checks for the latest
Memory Correctness / Personal Inference / Local First instruction. The
immutable `requirements/` directory was not modified.

| Requirement | Implementation | Test / evidence | Status |
|---|---|---|---|
| Same factual value with different notes/metadata is not a timeline conflict | `canonical_factual_payload()` strips extraction/debug metadata before timeline comparison; `_rebuild_fact_timeline()` compares the canonical payload | `test_same_value_with_different_extraction_metadata_is_not_conflict` | Done |
| Same date with different factual values is not made Current | Timeline rebuild marks the date as conflict/evidence review and does not assign Current | `test_same_effective_date_conflict_has_no_current_fact` | Done |
| Historical imports cannot roll back current truth; valid intervals stay ordered | Timeline uses effective/observed dates and closes a superseded interval at the next effective date | `test_fact_timeline_uses_effective_date_and_keeps_old_import_from_rollback`, `test_timeline_intervals_close_at_next_effective_date` | Done |
| Source role/type is explicit | `chunks.speaker_role`, `chunks.source_type`, migration/backfill, and `source_role_for_text()` | schema migration smoke and inference tests | Done |
| Assistant-only text cannot create a Personal Inference | Inference refresh accepts user/mixed/unknown source roles only; assistant-only chunks are excluded | `test_assistant_only_chunk_cannot_create_personal_inference` | Done |
| Inferences expire when current evidence disappears | Refresh expires all active inferences when no candidates remain, and expires candidates no longer supported | inference refresh implementation and projection behavior | Done |
| `provider=auto` is Local First | `selected_provider()` chooses a configured local endpoint before cloud keys; cloud fallback is gated per purpose | `test_auto_provider_prefers_local_before_configured_cloud_keys` | Done |
| Cloud fallback requires explicit permission | `cloud_fallback_allowed()` and `sensitive_cloud_allowed()` default false and are checked by chat/extraction/import paths | provider fallback tests and settings defaults | Done |
| Raw retrieval remains available but carries trust metadata | `retrieval_context()` annotates raw chunks as `confirmed_evidence`, `unverified`, or `conflicted`, including source role/type | retrieval context API inspection; regression suite | Done |
| Retrieval ordering | Current confirmed Facts, Decisions, keyword/FTS, semantic, and raw evidence remain separate projections | retrieval quality tests | Done |
| Test isolation | anomaly and DB-dependent tests use isolated temporary DB/schema fixtures | full unittest suite | Done |
| Adversarial entity handling | deterministic entity gate rejects fictional/media/AI/work/project entities from People even if the LLM says `person` | `benchmarks/memory_relevance_cases.json` and benchmark tests | Done |

## Verification run

```text
python -m py_compile app.py
python -m unittest discover -s tests -q
Ran 67 tests in the current verification run
OK
```

## Remaining partial/deferred items

- Authentication, session isolation, CSRF protection, and database-at-rest
  encryption are still Partial and require deployment/security design.
- Calendar/Gmail/Photos/Drive/financial connectors are Deferred; source type
  columns are ready for them but connectors are not implemented.
- Advanced domain visualizations remain Deferred. Existing projections and
  domain pages are preserved.
- External Context provenance extension is intentionally additive: future
  connector migrations can add `external_source`, `external_item_id`,
  `observed_at`, `imported_at`, and `provenance_json` to `documents`/`chunks`
  without changing Fact lineage. No connector is enabled in this phase.
- Personal system ideas are evidence-backed projections, but a richer UI for
  comparing unused systems and decision outcomes is still a follow-up.

No production DB was reset or deleted as part of this change. Schema additions
are applied by the existing migration path, which performs a backup before
schema changes.

## Provider configuration and parallel extraction

- GUI API-key fields set `OPENAI_API_KEY` / `GEMINI_API_KEY` in process memory
  only; `provider_status` exposes booleans, never key values.
- `extract_parallel_providers` is an explicit comma-separated setting. Empty
  means the legacy single-provider path.
- When two or more configured providers are selected, queue creation creates
  provider/model-specific `analysis_jobs` and the analyzer runs one worker per
  provider. Missing keys or unavailable Local endpoints are filtered before
  workers start.
- Local Ollama recovery now probes `/api/tags`, starts `ollama serve` at most
  once per 30 seconds when enabled, waits for readiness, and never changes to
  a cloud provider implicitly. The setting is `auto_start_local_llm`.

## v3 residual instruction status (2026-07-26)

| v3 item | Status | Evidence |
|---|---|---|
| Mixed-chunk user-span extraction | Done | `user_evidence_text()` parses role spans; mixed contamination and genuine-user tests |
| Local First `auto` | Done | `selected_provider()` returns Local when configured, otherwise `none`; explicit cloud remains supported |
| Canonical domain aliases | Done | `DOMAIN_CANONICAL` / `canonical_domain()` used by projections and recommendations |
| Japanese adversarial entity benchmark | Done | 44/44 benchmark cases, including fictional/media/company and real-person cases |
| Generated system ideas | Partial | Evidence-derived fallback candidates now carry `generation_mode=fallback`, lineage and context signature; reasoning-engine generation remains follow-up |
| Personal Reasoning output contract | Done | Recommendation includes recommendation, options, tradeoffs, context IDs, assumptions, missing information, plan and personalization level |
| Today next-candidate card | Done | `/api/today.next_candidates` and Today UI card, capped at three |
| Raw trust prompt guard | Done | Chat context explicitly distinguishes confirmed current, historical, decision, raw and conflicted evidence |
| LAN authentication/session/CSRF | Partial | Password-gated LAN API, HttpOnly/SameSite session and CSRF header are implemented; HTTPS/reverse-proxy hardening remains |
| v3 traceability | Partial | This document records the residual items; full v3 document-by-document table remains in `docs/requirements_traceability.md` and must retain honest Partial/Deferred states |
| External Context connectors | Deferred | Provenance/source-type columns remain ready; connectors intentionally not implemented |
| Advanced visualization | Deferred | Existing Today/domain summaries retained; Decision/Life/Asset timelines remain next phase |

The `requirements/` directory is treated as the source of truth and was not
edited by this change.
