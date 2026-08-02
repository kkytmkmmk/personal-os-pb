# Personal OS 要件ドキュメント

Personal OSは、ユーザー自身が所有する **Personal Context Engine** として、過去・現在・判断・結果・原文を蓄積し、交換可能なAIモデルがそれを使って「今の自分ならどう考えるか」を支援する。

## 文書の役割

- `00_vision.md` — 目的、中核サイクル、長期ビジョン
- `01_user_requirements.md` — ユーザーが実現したいこと
- `02_ui_ux_requirements.md` — 全画面共通のUI/UX原則
- `03_memory_data_requirements.md` — Raw / Fact / Evidence / Current / History / Decision
- `04_ingestion_requirements.md` — メモ・画像・過去会話等の取り込み
- `05_ai_processing_requirements.md` — LLM / OCR / 再解析 / Provider
- `06_retrieval_recommendation_requirements.md` — Retrieval / Recommendation / Planning
- `07_non_functional_requirements.md` — 性能、耐障害、バックアップ、監査
- `08_privacy_security_requirements.md` — Local First、外部送信、認証、削除
- `09_personal_intelligence_requirements.md` — Personal Inference と「自分らしい判断」の要件
- `10_external_context_requirements.md` — Calendar / Gmail / Photos等の将来連携
- `11_visualization_requirements.md` — Timeline / Map / Decision Flow / 3D Personal Space等の可視化
- `12_daily_action_review_inbox_requirements.md` — Today Action Centerと確認Inboxの機能要件正本
- `12_population_benchmark_requirements.md` — 公的統計のLocal DB保持、更新、世間比較・乖離可視化
- `90_requirements_map.md` — 正本の配置・重複防止
- `91_definition_of_done.md` — Done判定と横断Acceptance Criteria
- `99_current_constraints.md` — 現時点の実行環境・優先順位
- `domains/` — 分野別要件

## 正本の優先順位

同一テーマに複数の記述がある場合、次の順で解釈する。

1. テーマ固有の最新正本
2. 横断UI/UX要件
3. User Requirements
4. Vision
5. Historical documentation

Today Action Centerおよび確認Inboxの機能要件は、`12_daily_action_review_inbox_requirements.md`を最新正本とする。この優先順位はVisionやUser Requirementsに反する実装を許可するものではない。

## 中核思想

**記憶 → 理解 → 推論 → 提案 → 計画 → 判断 → 実行 → 結果 → 記憶**

Personal OSは「プロフィールDB」ではない。構造化Factだけでなく、必要時に関連する原文・Evidenceへ戻り、現在状態と過去の実体験を使って推論する。

## Requirement / Design / Acceptance / Traceability

| 文書群 | 役割 |
|---|---|
| `requirements/` | 満たすべき状態、ユーザーが得る状態、守るべき境界 |
| `docs/design/` | 実現方式、Projection、状態遷移、優先順位の詳細 |
| `docs/acceptance/` | テストシナリオ、合格条件、Verification手順 |
| `docs/requirements_traceability.md` | 現在の実装状態 |

要件書には細かいAPI名、Table名、SQL、テスト操作順を固定せず、DesignまたはAcceptanceへ分離する。
