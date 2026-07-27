# Personal OS 要件ドキュメント v3

Personal OSは、ユーザー自身が所有する **Personal Context Engine** として、過去・現在・判断・結果・原文を蓄積し、交換可能なAIモデルがそれを使って「今の自分ならどう考えるか」を支援する。

## 文書構成

- `00_vision.md` — 目的、中核サイクル、長期ビジョン
- `01_user_requirements.md` — ユーザーが実現したいこと
- `02_ui_ux_requirements.md` — 日常利用と可視化のUI/UX原則
- `03_memory_data_requirements.md` — Raw / Fact / Evidence / Current / History / Decision
- `04_ingestion_requirements.md` — メモ・画像・過去会話等の取り込み
- `05_ai_processing_requirements.md` — LLM / OCR / 再解析 / Provider
- `06_retrieval_recommendation_requirements.md` — Retrieval / Recommendation / Planning
- `07_non_functional_requirements.md` — 性能、耐障害、バックアップ、監査
- `08_privacy_security_requirements.md` — Local First、外部送信、認証、削除
- `09_personal_intelligence_requirements.md` — Personal Inference と「自分らしい判断」の要件
- `10_external_context_requirements.md` — Calendar / Gmail / Photos等の将来連携
- `11_visualization_requirements.md` — Timeline / Map / Decision Flow / 3D Personal Space等の可視化
- `12_population_benchmark_requirements.md` — 公的統計のLocal DB保持、更新、世間比較・乖離可視化
- `90_requirements_map.md` — 正本の配置・重複防止
- `91_definition_of_done.md` — Done判定と横断Acceptance Criteria
- `99_current_constraints.md` — 現時点の実行環境・優先順位
- `domains/` — 分野別要件

## 中核思想

**記憶 → 理解 → 推論 → 提案 → 計画 → 判断 → 実行 → 結果 → 記憶**

Personal OSは「プロフィールDB」ではない。構造化Factだけでなく、必要時に関連する原文・Evidenceへ戻り、現在状態と過去の実体験を使って推論する。

## 要件と設計の境界

この配下は「何を満たすべきか」を定義する。DBカラム、API、SQL、モデル名等は設計文書に分離する。
