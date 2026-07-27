# 要件差分監査（実装前ベースライン）

作成日: 2026-07-26  
正本: `requirements/` 配下の全Markdown、ならびに添付された再構築指示書（リポジトリ直下に `CODEX_REBUILD_INSTRUCTION.md` は存在しなかったため、添付指示書を同等の作業指示として扱う）。

この文書は着手時点の差分を残す監査記録です。表内の「未実装」「追加する」はその後の実装で解消済みです。現在の判定、実装箇所、テスト、要件外/TBDは [要件トレーサビリティ](requirements_traceability.md) を正として参照してください。

## 監査対象

- `app.py` のSQLiteスキーマ、HTTP API、LLM Provider、解析Job、バックアップ、ランタイムリース
- `personal_os/ingest.py`、`personal_os/llm_ollama.py`
- `static/index.html`、PWA manifest/service worker
- `tests/`、README/ユーザーガイド/アーキテクチャ文書
- 既存DBのデータを変更しない読み取り監査と、バックアップ作成

## 実装前の現状と差分

| 領域 | 現状 | 要件との差分 | 対応方針 |
|---|---|---|---|
| 正本 | `facts`、`fact_currentness`、`memory_changes` が存在 | legacy参照が一部残る | 新規Projection/retrievalはfacts中心。legacyは移行互換として保持 |
| 時間軸 | `valid_from/to`、current/supersededを実装 | 日付不明時の判定、履歴の監査表示を強化したい | current/history APIとEvidence表示を追加 |
| Fact/Evidence | chunk/attachmentへのsource参照はある | FactとEvidenceが独立した監査単位ではない | `fact_evidence`を追加し、保存時に根拠を記録 |
| 同一性 | `fact_key`とscopeを考慮した正規化を実装 | 正規化ルールの拡張余地 | canonical keyを正本とし、テストを追加 |
| 入力 | raw entryを保存後にLLM抽出 | `/api/ingest`と画像取込が同期処理 | raw保存→analysis job化し、応答をブロックしない |
| ChatGPT取込 | ZIPを原文として保存し、文書/Chunk/Jobを作成 | lazy解析のUI説明を整理 | importは原文保存とJob投入まで。再解析はversion/hash単位 |
| AI | OpenAI/Gemini/Ollama Provider切替、クラウドfallback設定あり | fallbackを入力種別・センシティブで明示的に制御する必要 |安全側デフォルトとJob上のprovider固定を維持 |
| 解析Job | `analysis_jobs`、status/attempts/hash/prompt/modelを実装 | 画像/手入力も同じJobモデルに統一されていない | `job_kind`/`source_attachment_id`を追加し、同一Workerで処理 |
| Retrieval | current fact→decision→FTS→rawの順序を実装 | local embedding Workerを追加 | `/api/search`とchatでsemantic候補をFTS後・raw前に利用 |
| Recommendation/Planning | ドメインProjectionはあるが提案/計画が一級データでない | 記憶→理解→提案→計画→判断→結果→記憶の自動フィードバックが未接続 | recommendations/plansを追加し、推薦生成時のDraft Plan自動作成とDecision変換を実装 |
| Decision | decision/結果/後日評価を保存可能 | 提案・計画との関連が弱い | related IDsと結果フィードバックAPIを追加 |
| 金融 | 正規化と決定論的validator、candidate分離済み | 既存誤集計の再発防止を継続 | eligible queryを唯一の集計入口にする |
| 専用画面 | Today/Money/Travel/Housing/People/Decisionsあり | 住居・旅行の候補/根拠表示を拡張 | Projection APIはfacts/entities/decisionsのみを参照 |
| Privacy | local-first、クラウド許可設定、推測Factの自動除外 | 暗号化/認証/人物単位の送信UIは未完成 | Evidence-based自動確定・推測除外、明示confirm付き削除API、pre-delete backup、削除監査APIを追加 |
| Backup/Restore | 起動・定期バックアップ、全世代保持 | 復元UI/APIが未実装 | backup manifest/検証APIを追加。復元は安全確認付きで別途実装 |
| テスト | ユニット14件 | 実DBスモーク/要件トレーサビリティ不足 | migration/API/workerのテストを追加 |

## データ保全

スキーマ変更前に `data/backups/personal_os-20260726-014844.db` を作成済み。SQLiteのonline backup APIを使用し、既存の原文・画像・Fact・Decisionを初期化しない。各migrationは冪等にし、`schema_migrations`へ記録する。

## 実装順序

1. 追加スキーマ（Evidence、Job種別、Recommendation/Plan）と冪等migration
2. raw-firstの入力・画像取込と解析Job Worker
3. retrieval/根拠表示と提案→計画→Decision接続
4. 専用Projection/UIとバックアップ監査
5. 要件トレーサビリティと実DBテスト
