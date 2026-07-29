# Decision Replay traceability

| Requirement | Implementation | Test / evidence | Current status |
| --- | --- | --- | --- |
| Read-only replay lifecycle | `app.py`: `decision_replay()` and `GET /api/decisions/{id}/replay` | `tests/test_decision_replay.py` | Implemented |
| No recommendation-to-decision promotion | Recommendations are an independent replay stage with its own source ID | `test_replay_keeps_recommendation_separate_from_user_decision` | Implemented |
| Missing stages are explicit | Ten ordered stages use `recorded`, `missing`, or `not_applicable`; no values are synthesized | `test_replay_missing_result_has_explicit_action_without_writes` | Implemented |
| Safe evidence access | Fact/evidence counts are projected; sensitive domains are masked unless explicitly requested | `test_sensitive_replay_is_masked_by_default` | Implemented |
| Replay routes and UI | Decision card, Timeline action and `#decisions/replay/{id}` use one shared sheet | `tests/test_decision_replay_ui.py`; Browser E2E | Verification in progress |
| Results and evaluation remain explicit user writes | Existing outcome actions are used from Replay; viewing does not mutate data | Decision-cycle tests and Browser E2E | Verification in progress |
| Local owner feedback | `ux_feedback`, local sheet, Markdown copy, no network provider | `test_ux_feedback_is_local_only` | Implemented |
| First real use | Migration backup plus `docs/first_real_use.md` | Documentation review | Implemented |
