# 要件トレーサビリティ

最終確認日: 2026-08-02

この文書は現在の実装状態だけを示す。要件正本は[requirements/README.md](../requirements/README.md)に従う。過去の判定と固定テスト件数は[Historical Archive](archive/requirements_traceability_before_2026-08-02_cleanup.md)を参照する。

## 1. Current Requirements Baseline

- Today Action Centerと確認Inboxの機能要件正本は `requirements/12_daily_action_review_inbox_requirements.md` である。
- 実現方式は `docs/design/`、Acceptance手順は `docs/acceptance/`、現在状態は本書に分離する。
- `Done`は実装と対象Acceptanceの確認を必要とする。今回の文書更新は状態をDoneへ変更しない。

## 2. Current Implementation Status

| 領域 | 現在状態 | 備考 |
|---|---|---|
| Memory / Fact / Evidence | Partial | 既存機能はあるが、Action Center / Review Inboxの新要件は未実装 |
| Decision Lifecycle | Partial | 既存Lifecycleはあるが、本書の`evaluated`までの正本へ実装追随が必要 |
| Today / Action Center | Not implemented | 新しい主Action構造は未実装 |
| Review Inbox | Not implemented | Bucket、Snooze、Focus Modeの新要件は未実装 |
| Privacy / Public safety | Partial | Public安全策はあるが、Sensitive ProjectionのAcceptanceは未実施 |

## 3. Current Gaps

- 主Actionの最大1件表示、Draft分類、表示理由
- Memory確認に限定したInbox、決定的なUrgent/Sort、Focus Mode
- 一時Snoozeと期限なし`deferred`の状態分離
- 大量Backlog、Sensitive Production詳細、Public安全のAcceptance

## 4. Requirement ID別Traceability

| ID | 要件 | 状態 | 実装 | Acceptance |
|---|---|---|---|---|
| AC-001 | 主Action最大1件 | Not implemented | 未実装 | 未実施 |
| AC-002 | 表示理由 | Not implemented | 未実装 | 未実施 |
| AC-003 | 初期Viewportから記録・相談 | Not implemented | 未実装 | 未実施 |
| AC-004 | 保存失敗Draft優先 | Not implemented | 未実装 | 未実施 |
| AC-005 | 古い・無意味なDraftを抑制 | Not implemented | 未実装 | 未実施 |
| AC-006 | Todayに確認候補全件を出さない | Not implemented | 未実装 | 未実施 |
| AC-007 | 通常利用をブロックしない | Not implemented | 未実装 | 未実施 |
| AC-008 | Current/変化は主Actionの下 | Not implemented | 未実装 | 未実施 |
| RI-001 | Inbox対象をMemory確認に限定 | Not implemented | 未実装 | 未実施 |
| RI-002 | Bucket分離 | Not implemented | 未実装 | 未実施 |
| RI-003 | 決定的な順番 | Not implemented | 現在はランダム要素あり | 未実施 |
| RI-004 | ランダム順廃止 | Not implemented | 現在はランダム要素あり | 未実施 |
| RI-005 | Focus Mode | Not implemented | 未実装 | 未実施 |
| RI-006 | 一時Snoozeはpending維持 | Not implemented | 未実装 | 未実施 |
| RI-007 | 期限なし保留だけdeferred | Not implemented | 未実装 | 未実施 |
| RI-008 | Snooze期限前に再表示しない | Not implemented | 未実装 | 未実施 |
| RI-009 | Reload後もSnooze維持 | Not implemented | 未実装 | 未実施 |
| RI-010 | legacy deferred保護 | Partial | 既存deferredのみ | 未実施 |
| RI-011 | 技術情報を初期状態で閉じる | Not implemented | 未実装 | 未実施 |
| RI-012 | 管理操作分離 | Partial | 確認画面に混在 | 未実施 |
| RI-013 | Sensitive詳細を本人操作後に表示 | Not implemented | 未実装 | 未実施 |
| RI-014 | 50件Backlog | Not implemented | 未実装 | 未実施 |
| RI-015 | Inboxをゼロにすることを目標にしない | Not implemented | 未実装 | 未実施 |

## 5. Historical文書

過去のDone表、Override、時点ごとのテスト件数は[archive/requirements_traceability_before_2026-08-02_cleanup.md](archive/requirements_traceability_before_2026-08-02_cleanup.md)に位置づける。最新の実行件数はGitHub Actions、最新完了報告、自動生成Verification Reportで確認する。
