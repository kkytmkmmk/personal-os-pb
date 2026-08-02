# 要件トレーサビリティ

最終確認日: 2026-08-02

この文書は現在の実装状態だけを示す。要件正本は[requirements/README.md](../requirements/README.md)に従う。過去の判定と固定テスト件数は[Historical Archive](archive/requirements_traceability_before_2026-08-02_cleanup.md)を参照する。

## 1. Current Requirements Baseline

- Today Action Centerと確認Inboxの機能要件正本は `requirements/12_daily_action_review_inbox_requirements.md` である。
- 実現方式は `docs/design/`、Acceptance手順は `docs/acceptance/`、現在状態は本書に分離する。
- `Done`は実装と対象Acceptanceの実行を必要とする。Browser項目はVerification環境の一時DBで確認し、本番DBは使用しない。

## 2. Current Implementation Status

| 領域 | 現在状態 | 備考 |
|---|---|---|
| Memory / Fact / Evidence | Done | Fact ReviewとMemory Proposalを同一の安全なInbox Projectionで扱う |
| Decision Lifecycle | Partial | 既存Lifecycleはあるが、本書の`evaluated`までの正本へ実装追随が必要 |
| Today / Action Center | Done | 主Action1件、Draft v2、Normal Review除外、単一Digest renderer |
| Review Inbox | Done | 限定Urgent、Focus休止、Memory Proposal、Cursor、明示表示記録 |
| Privacy / Public safety | Done | Sensitive詳細は本人操作後・no-store、Synthetic E2Eと公開検査を使用 |

## 3. Current Gaps

- Production本人データでの確認は安全上自動化せず、User Guideの少量手動手順として残す。
- Pixel-perfect Visual Regressionは対象外。構造、Overflow、操作、永続化をBrowser E2Eで確認する。

## 4. Requirement ID別Traceability

| ID | 要件 | 状態 | 実装 | Acceptance |
|---|---|---|---|---|
| AC-001 | 主Action最大1件 | Done | `action_center_projection` / `renderTopAction` | Unit・Desktop/Mobile E2E |
| AC-002 | 表示理由 | Done | `reason` / `action-reason` | Unit・Browser E2E |
| AC-003 | 初期Viewportから記録・相談 | Done | Action Center quick actions | Mobile 390 E2E・目視 |
| AC-004 | 保存失敗Draft優先 | Done | Draft v2 `save_failed` priority 0 | Browser E2E |
| AC-005 | 古い・無意味なDraftを抑制 | Done | 10文字・72時間・hidden・legacy判定 | Browser E2E・UI static |
| AC-006 | Todayに確認候補全件を出さない | Done | Urgent最大1件、Normal除外 | Unit・Browser E2E |
| AC-007 | 通常利用をブロックしない | Done | 記録・相談・判断導線を常設 | Mobile E2E |
| AC-008 | Current/変化は主Actionの下 | Done | `renderDigest`をAction Card後へ配置 | Screenshot目視 |
| RI-001 | Inbox対象をMemory確認に限定 | Done | Fact Review / Memory Proposalのみ | Unit・Proposal E2E |
| RI-002 | Bucket分離 | Done | `_review_bucket`の限定条件 | Unit・Snooze E2E |
| RI-003 | 決定的な順番 | Done | Opaque sort-key cursor | Unit pagination |
| RI-004 | ランダム順廃止 | Done | Legacy routeも同じProjectionへ委譲 | Unit・source inspection |
| RI-005 | Focus Mode | Done | 1件表示・3件区切り | Desktop E2E・Screenshot |
| RI-006 | 一時Snoozeはpending維持 | Done | `pending + one_day/one_week` | Unit・Mobile DB assertion |
| RI-007 | 期限なし保留だけdeferred | Done | `deferred + indefinite`だけ許可 | Unit |
| RI-008 | Snooze期限前に再表示しない | Done | `snoozed_until`分類 | Unit・Reload E2E |
| RI-009 | Reload後もSnooze維持 | Done | SQLite queue metadata | Mobile Reload E2E |
| RI-010 | legacy deferred保護 | Done | deferredは期限に関係なく維持 | Unit・migration test |
| RI-011 | 技術情報を初期状態で閉じる | Done | Evidence details | Screenshot目視 |
| RI-012 | 管理操作分離 | Done | 閉じた「記憶メンテナンス」へ移動 | UI static・Screenshot |
| RI-013 | Sensitive詳細を本人操作後に表示 | Done | masked list / no-store detail / close purge | Unit・Desktop E2E・目視 |
| RI-014 | 50件Backlog | Done | SQL上限・初回10件・Cursor追加取得 | 61件Synthetic E2E |
| RI-015 | Inboxをゼロにすることを目標にしない | Done | 件数は補助表示、通常導線を維持 | UI static・目視 |

## 5. Historical文書

過去のDone表、Override、時点ごとのテスト件数は[archive/requirements_traceability_before_2026-08-02_cleanup.md](archive/requirements_traceability_before_2026-08-02_cleanup.md)に位置づける。最新の実行件数はGitHub Actions、最新完了報告、自動生成Verification Reportで確認する。
