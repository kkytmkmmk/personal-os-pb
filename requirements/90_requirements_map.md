# 要件配置マップ

| テーマ | 正本 |
|---|---|
| Vision / 中核サイクル / Digital Twin方向性 | `00_vision.md` |
| ユーザーがしたいこと | `01_user_requirements.md` |
| UI / 日常導線 | `02_ui_ux_requirements.md` |
| Raw / Fact / Evidence / Current / Decision | `03_memory_data_requirements.md` |
| Input / Import | `04_ingestion_requirements.md` |
| AI / Provider / Local First解析 | `05_ai_processing_requirements.md` |
| Retrieval / Recommendation / Planning | `06_retrieval_recommendation_requirements.md` |
| 性能 / Reliability / Test | `07_non_functional_requirements.md` |
| Privacy / Security / Cloud send | `08_privacy_security_requirements.md` |
| Personal Inference / Personal Model | `09_personal_intelligence_requirements.md` |
| External Context | `10_external_context_requirements.md` |
| Visualization | `11_visualization_requirements.md` |
| Done判定 | `91_definition_of_done.md` |
| 現在の技術制約 | `99_current_constraints.md` |
| Domain固有 | `domains/` |

| UI/UX Adaptive UI・日常導線・外部解析の明示 | `02_ui_ux_requirements.md`（2026-07-26 vNext節） |

## 重複時の優先

詳細テーマの正本を優先し、高レベル文書は意図説明として扱う。

例:

- Personal InferenceのEvidence境界 → `09`
- Cloud送信制御 → `08`、AI選択動作 → `05`
- People判定の意味論 → `domains/people.md` + `03`
- Visualizationの表示方法 → `11` + `02`

## 要件と実装を混同しない

「SQLiteを使う」「Qwenを使う」はCurrent Constraint / Designであり長期要件ではない。
