# 要件トレーサビリティ

最終確認日: 2026-07-26  
正本: `requirements/` 配下（UI/UX vNextの改訂は2026-07-26指示で許可）

判定基準:

- **Done**: 現在確定している要件を実装し、自動テストまたは検証DB/UIで確認済み
- **Partial**: 中核は動くが、要件の一部に未達がある
- **Not implemented**: 未着手
- `TBD`・将来要件は未実装を理由に現在要件をPartialにはしない

## 文書別

| 要件 | 実装 | 主な検証 | 状態 |
|---|---|---|---|
| `00_vision.md` 記憶→理解→提案→計画→判断→結果→記憶 | `facts` / `fact_evidence` / `recommendations` / `plans` / `decisions`、Decision結果・後日評価を次回Recommendation理由へ反映 | `test_decision_result_and_later_evaluation_feed_next_recommendation` | Done |
| `01_user_requirements.md` 軽い入力、現在把握、相談、提案、計画、理由、非実行 | Today、自然文/音声/画像入力、質問依存Retrieval、選択肢・トレードオフ・Draft Plan、外部実行なし | Recommendation/Retrievalテスト、8877 UI smoke | Done |
| `02_ui_ux_requirements.md` Today中心、スマホ、簡潔な進捗、必要時だけ根拠・訂正 | PWA、主/副ナビ分離、日本語ラベル、進捗根拠、Fact訂正、サイクル表示、レスポンシブUI | 8877のToday/People/確認画面を実ブラウザ確認 | Done |
| `03_memory_data_requirements.md` raw、Fact/Evidence、独立性、時系列、信頼、異常、Decision、訂正履歴 | `documents/chunks`、`facts`、`fact_evidence.source_identity`、current/superseded、trust details、数値異常、`memory_corrections` | Evidence独立性、Fact訂正、数値外れ値、Decision結果テスト | Done |
| `04_ingestion_requirements.md` raw-first、重複抑制、画像、ChatGPT履歴、再実行 | HTTP bodyの一時ファイルstream、JSON配列のincremental decode、250会話単位commit、shard checkpoint、`external_id`、画像の即時保存と非同期Job | incremental単一JSON、分割ZIP idempotency、画像削除、multipartテスト | Done |
| `05_ai_processing_requirements.md` 候補扱い、非同期、Lazy解析、Provider交換、再解析、安全fallback | `analysis_jobs`、相談連動priority、OpenAI/Gemini/Ollama adapter、prompt/model/hash、fallback既定OFF、停止/再開 | Provider、queue priority、prompt v3、job集計テスト | Done |
| `06_retrieval_recommendation_requirements.md` 質問に必要な情報、current優先、履歴、提案、計画、理由、結果反映 | `query_plan`、current→Decision→history→FTS/semantic→raw、domain projection、missing context、tradeoff/plan/evidence IDs | 関係ない資産Fact除外、Decision結果取得、Recommendationテスト | Done |
| `07_non_functional_requirements.md` 非同期、再実行、安全性、バックアップ、復元、監査、保守 | 完全`.posbackup`（DB+原文+画像+manifest/hash）、atomic restore、runtime lease、索引、read-only benchmark、`/api/health` | backup/restore E2E、52 tests、検索warm p95 81.565ms（検証DB） | Done（数値SLO・保持期間は要件側TBD） |
| `08_privacy_security_requirements.md` Local First、外部送信制御、推測抑制、削除単位 | wildcard CORS廃止、fallback 4区分、画像はlocal-only、Fact/Entity/Attachment/Entry削除preview、物理画像削除、secret scan | Privacy削除E2E、推測/人物分類、secret scanner | Done（認証・暗号化・完全削除定義は将来/TBD） |
| `domains/money.md` 厳密な現在/履歴/実取引/異常/判断 | Money projection、Transaction Validator、候補分離、円正規化、source Factへ遡及 | 金融validator、集計、外れ値テスト | Done |
| `domains/travel.md` 訪問/希望/好み/費用/提案/計画/結果 | Travel projection、履歴/ホテル/交通/マイル/評価、旅行Recommendation/Plan、Decision feedback | domain projection、Recommendation cycleテスト | Done（外部天気・価格等は未連携であることをUIに明示） |
| `domains/housing.md` 現在/希望/候補比較/過去判断/次の行動 | Housing projection、家賃の月/年差、希望条件、比較Recommendation/Plan | projection・Recommendation回帰 | Done |
| `domains/people.md` 人物タイムライン、推測禁止、確認削減、削除 | `entity_type=person` gate、明示Evidenceのみ、キャラクター等除外、人物単位削除preview UI | 人物/架空分類、People UI smoke、Privacy削除E2E | Done |
| `domains/decisions.md` 選択肢/理由/結果/評価/次回利用、AI非実行 | Decisions横断画面、result/evaluation timestamp、Recommendation source、Plan連携 | Decision feedback test | Done |

## 主要実装とテストの対応

| 機能 | 実装箇所 | テスト |
|---|---|---|
| 完全バックアップ/復元 | `app.py`: `_create_backup_bundle`, `verify_backup`, `restore_database` | `test_backup_restores_database_and_attachment_bytes` |
| Fact信頼・Evidence独立性 | `fact_trust_evaluation`, `record_fact_evidence`, `apply_memory_quality_to_fact` | `test_duplicate_screenshot_is_one_independent_evidence_group`ほか |
| Personal relevance | `classify_personal_relevance`, `benchmarks/memory_relevance_cases.json` | 31/31、minimum accuracy 100% |
| 質問依存Retrieval | `query_plan`, `retrieval_context`, `semantic_search` | 関係ないFact除外、Decision結果参照 |
| 中核サイクル | `build_local_recommendation`、Recommendation/Plan/Decision API | 2つのcycleテスト |
| Fact訂正/削除 | `correct_fact`, `privacy_delete_preview`, `delete_private_data` | 訂正履歴、画像/派生データ削除 |
| OCR routing | `personal_os/ocr.py`, `local_ocr_derivative` | OCR cacheテスト |
| 大量取込 | `stream_request_file`, `iter_json_array`, `_import_chatgpt_archive`, `import_jobs` | incremental単一JSON、shard checkpoint/idempotency |
| 運用境界 | `/api/health`, CORS allowlist、runtime lease、benchmark tools | health/secret/全体回帰 |

## 残るlegacy依存

- `entries`: 原文キャプチャと旧API互換。新規構造化情報の正本ではない。
- `structured_memories`: 起動時の一方向Migration入力だけ。新機能は参照しない。
- `analysis_status`, `task_plans`: 旧画面/API互換の補助テーブル。
- `app.py`と`static/index.html`は依然大きい。機能境界は作ったが、モジュール分割は継続可能。

## 現要件外・方式未確定

現在確定している要件に未完了はありません。次は要件側で方式確定または追加要件化された場合の対象です。

1. DB/画像の保存時暗号化、認証、バックアップからの選択的完全消去
2. 天気・交通・宿泊価格・カレンダー等の外部連携
3. 公開Webサービス化

## v3 residual audit override (2026-07-26)

The table above is retained as the historical implementation baseline. The
following v3 status is authoritative for the current residual instruction;
`Done` requires implementation plus acceptance tests.

| v3 document | Current status | Implementation / test |
|---|---|---|
| `00_vision.md` | Done directional | cycle projection and decision/result feedback |
| `01_user_requirements.md` | Partial | core Today/Ask/Record flow works; broader external context is deferred |
| `02_ui_ux_requirements.md` | Partial | Today/domain UI exists; next-candidate card added; advanced visualization deferred |
| `03_memory_data_requirements.md` | Done | canonical Fact timeline, Evidence lineage, source roles, repair and expiry tests |
| `04_ingestion_requirements.md` | Done | raw-first import, image/ChatGPT ingestion and job checkpoints |
| `05_ai_processing_requirements.md` | Partial | Local First/fallback policy is enforced; reasoning-engine system-idea generation remains fallback-only |
| `06_retrieval_recommendation_requirements.md` | Done | current→decision→history→keyword/semantic→raw, trust-labelled prompt, structured recommendation |
| `07_non_functional_requirements.md` | Done | backup/restore, leases, asynchronous jobs, isolated tests |
| `08_privacy_security_requirements.md` | Partial | LAN password/session/CSRF added; HTTPS, auth hardening and at-rest encryption remain |
| `09_personal_intelligence_requirements.md` | Partial | user-span Evidence, inference expiry/domain aliases implemented; repeat/avoid and time-aware inference remain |
| `10_external_context_requirements.md` | Deferred | provenance/source-type abstraction ready; connectors intentionally not connected |
| `11_visualization_requirements.md` | Partial/Deferred | Today/domain summaries and candidate card exist; Decision/Life/Asset/Travel views remain |
| `91_definition_of_done.md` | Process | this status is tied to tests and explicit Partial/Deferred labels |
| `99_current_constraints.md` | Done as constraints | no automatic execution, no automatic cloud fallback, no Digital Twin persona persistence |
| `domains/*` | Partial by domain | Money/Travel/Housing/People/Decisions projections exist; advanced timelines/maps remain |

Current verification: **78 unit tests pass**, **44/44 memory benchmark cases
pass (accuracy 1.0)**. Older numbers such as 52/52 and 31/31 in the historical
sections above are not current results.

Security is not marked Done until HTTPS/reverse-proxy deployment hardening,
session rotation/invalidations, and database/attachment encryption are
specified and tested.

## UI/UX vNext traceability (2026-07-26)

| 要件 | 実装箇所 | 検証 | 状態 |
|---|---|---|---|
| PC/iPhone Adaptive UI、Primary/Legacy分離 | `static/index.html` (`#os-nav`, `#legacy-nav`, `#mobile-bottom-nav`), `static/styles.css` | 静的HTML/CSS配信 smoke、74 unit tests | Partial（実ブラウザ4 viewportのスクリーンショット自動化は未実装） |
| TodayをCurrent/Next/Recent/Pending中心へ | `static/styles.css` Today selector、既存 `/api/today`/`next_candidates` | `/api/today`既存テスト、verification 8877起動 | Partial（詳細管理カードはDOMに残るが日常表示から非表示） |
| 「＋」Quick Capture（メモ/画像/判断/相談） | `static/index.html` `quick-sheet`、`static/app.js` | 8877で配信確認 | Done（手動UI受入は継続） |
| 相談の回答優先・根拠折りたたみ | `static/app.js` `improveConsultation`、`static/styles.css` | DOM変化後の根拠トグル実装確認 | Partial（Context APIの分類表示は既存互換） |
| Draft保持、44px、aria/focus/Escape/safe-area | `static/app.js` `wireDrafts`/sheet、`static/styles.css` | 静的検査 | Partial（完全focus trapは未実装） |
| ChatGPT深い解析のPreview→確認→監査 | 要件のみ | 専用Preview/execute/audit APIなし | Not implemented |
| CSS/JS外部化 | `static/styles.css`, `static/app.js`, `app.py` static mapping | `/styles.css`, `/app.js` HTTP 200 | Partial（既存index inline処理は互換のため残存） |

UI/UXはAcceptance完了まで `Partial` を維持し、外部ChatGPT解析UIは未実装として扱う。

## Consultation Cycle completion traceability (2026-07-26)

| 要件 | 実装箇所 | 検証 | 状態 |
|---|---|---|---|
| Consultation Responseの`response_type`/Candidate | `app.py`: `consultation_response_type`, `/api/chat` response | `test_consultation_response_types_and_cycle_stage_transitions` | Done（候補は保存前） |
| Recommendation → Plan | `POST /api/recommendations/{id}/plan`、`cycle_snapshot` | verification API E2E | Done |
| Plan → Decision候補 → 本人確定 | `POST /api/plans/{id}/decision`、`PATCH /api/decisions/{id}` | verification API E2E、invalid transition guard | Done |
| Decision → Execution → Result → Later Evaluation | `/api/decisions/{id}/execute|result|evaluate`、Modal/Bottom Sheet | verification API E2E | Done |
| `cycle_stage` / `available_actions` | `cycle_snapshot`, `/api/cycles/{id}`, Today Cycle board | unit + verification API E2E | Done |
| Resultを次回Recommendationへ反映 | `build_local_recommendation`のDecision/Result retrieval | `test_decision_result_and_later_evaluation_feed_next_recommendation` | Done |
| Today / Mobile / PCから完走 | `static/app.js` Cycle board、`static/styles.css` responsive card/sheet | 8877 API/asset smoke | Partial（4 viewportの自動操作は未実装） |
| ChatGPT深い解析のPreview→確認→監査 | 未実装 | なし | Not implemented |

最新検証: **74 unit tests pass**, **44/44 memory benchmark**, verification API Travel Cycle E2E（evaluatedまで完走）。
## UI/UX Phase 2 traceability (2026-07-26)

| Requirement | Implementation | Verification | Status |
|---|---|---|---|
| One navigation/router and hash state | `static/app.js`: `navigateTo`, `setActiveTab`, `hashchange`/`popstate`; legacy inline tab handlers removed | Node syntax check; static asset smoke | Done |
| Exactly one visible page tab | Router canonicalizes `memory`/`admin` aliases and toggles `.tab.hidden` centrally | 74 unit tests remain green | Done |
| Today is a read-only summary | `cleanupLegacyToday`, Today CSS allow-list, `refreshTodayCycleSummary` with “続きを見る” | API smoke and DOM source inspection | Done |
| Consultation owns detailed Cycle operations | Cycle board is mounted under `#chat`; Today only receives summary | Cycle API E2E; Node syntax check | Done |
| Unified Memory Record input | `setupRecordUI` creates `#record-card/#record-text`; legacy capture/extraction cards are under Advanced details | Static asset smoke | Done |
| Draft preservation and non-prompt correction UI | sessionStorage drafts; modal sheets for Decision result/evaluation and Fact correction | Node syntax check; API-compatible handlers | Partial (remaining legacy admin prompts) |
| Responsive PC/iPhone shell | Fixed mobile nav, quick/more sheets, focus/scroll handling, no horizontal body overflow | CSS/static smoke | Partial (automated viewport screenshots not included) |

Phase 2 implementation intentionally leaves `requirements/` unchanged because it is the immutable source of truth. Current verification: **78 unit tests**, **44/44 memory benchmark cases**, and a clean secret scan.

## UI Action / LLM reliability (2026-07-26)

| Requirement | Implementation | Verification | Status |
|---|---|---|---|
| Single API boundary, request IDs, safe retry | `static/api-client.js`, `X-Request-ID`, CORS headers | `tests/test_ui_reliability.py`, asset smoke | Done |
| Auth resume and CSRF error distinction | `api-client.js` auth event/pending action, server `error_type` | static tests; verification API health/diagnostics | Done |
| Action state and duplicate-submit guard | `wireActionReliability`, `data-action-state`, disabled primary buttons | static tests; verification UI acceptance | Done |
| Content-free frontend error ring buffer | `frontendErrors` max 20, diagnostics copy view | static tests | Done |
| LLM stage/provider/model trace | `LLM_TRACE_EVENTS`, `/api/llm-traces`, `/api/diagnostics` | verification API smoke | Done |
| Candidate continuity | `/api/chat` IDs and exact candidate save path | `test_candidate_is_saved_as_displayed` | Done |
| Versioned service-worker shell | `personal-os-v3-reliability-1`, `/api-client.js` in shell | `test_service_worker_refreshes_phase2_assets` | Done |
| Full mobile/PC/auth/unavailable-LLM E2E matrix | Browser automation and slow-network fixtures | Browser control layer currently fails click execution with `SyntaxError`; static/API coverage remains | Partial |
