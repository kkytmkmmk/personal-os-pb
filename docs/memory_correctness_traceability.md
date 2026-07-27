# Memory Correctness / Personal Intelligence 実装状況

添付の改修指示書に対する実装状況を記録する。`requirements/` は変更していない。

| Phase | 状態 | 実装・テスト |
|---|---|---|
| P0-1 Current / Historical | Done | `facts.effective_at/observed_at/temporal_source`、`_rebuild_fact_timeline()`、migration 011。挿入順ではなく内容時刻を優先し、同日矛盾はCurrentを作らない。`test_fact_timeline_uses_effective_date_and_keeps_old_import_from_rollback`、`test_same_effective_date_conflict_has_no_current_fact` |
| P0-2 Entity / People | Done | `classify_entity_type()` の文脈ゲート。personは関係Evidenceがある場合だけ、fictional/media/AI/work/project等をPeopleから除外。`benchmarks/memory_relevance_cases.json` にずんだもん、YouTuber、OpenAI、実在友人の敵対例を追加 |
| P0-3 Existing DB Repair | Done | `repair_jobs`、`repair_memory_state()`、UIの「既存記憶を修復」、`/api/memory-quality/repair`。Raw entries/chunksは削除せず、訂正ログと件数を保存。`test_repair_job_preserves_raw_evidence_and_records_audit` |
| P0-4 Retrieval Quality Gate | Done | Current Fact→Decision→FTS/keyword→semantic→rawの順。rejected/excluded/conflict/非person relationship/unknown currentをCurrent文脈から除外。historical/rawは別グループ |
| P0-5 Regression | Done | 全テストは一時DBを使用し、schema初期化から実行。 |
| P0-6 Adversarial | Done | memory relevance benchmarkを拡張し、通常テストで全件合格を確認。 |
| P1-1 Structured + Raw | Done | `retrieval_context()` が `current/decisions/history/profile/raw` を返し、回答・推薦が根拠IDを保持。 |
| P1-2 Personal Inference | Done | `personal_inferences` はFactと別テーブル。再生成・期限切れ・source IDsを実装。`/api/inferences`、`/api/inferences/refresh`。 |
| P1-3 Recommendation | Done | Current/制約/Decision/Result/Raw/Inferenceを材料に下書きRecommendationとPlanを生成。外部実行はしない。 |
| P1-4 System Ideas | Done | `personal_system_ideas()` と `/api/personal-system-ideas`。固定リストではなく、InferenceとRaw chunkから根拠付き候補を生成。 |
| P1-5 Decision→Execution→Result | Done | additiveな`decisions.decision_state`（candidate/considered/decided/executed/result）、`execution_events`、イベントAPI。Result不明は自動補完しない。 |
| P2 Security | Partial | Cloud fallback、secret scanner、backup/export/deleteは実装済み。外部公開向けの認証・セッション・CSRF・DB暗号化は未実装。外部連携前の必須残課題。 |
| P2 External Integrations | Deferred | Google Calendar/Gmail/Photos/Financial/Driveは未接続。セキュリティ実装後に着手する。 |
| P3 Visualization | Deferred | 専用projectionと既存集計はあるが、Life/Asset/Travel/Decisionの本格タイムライン可視化は未実装。 |

## Migration

初期化時に migration 011 (`011_memory_correctness`) を記録する。既存DBでは、変更前バックアップを作成してから `effective_at` 等を追加し、FactのTimeline・Evidence・品質ゲートを再構築できる。修復は `/api/memory-quality/repair` またはUIから明示的に実行する。

## 残るリスク

- 同一日で異なる値が明示された場合は安全側に倒してCurrentを作らず、訂正対象として残す。
- Entityの未知ケースはunknown/archive_onlyとして保持し、Peopleへ自動昇格しない。
- 外部LLMへの送信許可と、公開サーバー認証は別途強化が必要。
