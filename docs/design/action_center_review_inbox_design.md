# Action Center / Review Inbox Design

この文書は現在の実現方式を示す。満たすべき状態は[要件正本](../../requirements/12_daily_action_review_inbox_requirements.md)、合格条件は[Acceptance](../acceptance/action_center_review_inbox_acceptance.md)を参照する。

## 1. Domain Boundary

```text
Action Center
  保存失敗・有効Draft・Decision Lifecycle・実行/判断待ち・Urgent Memory確認・相談/記録導線

Review Inbox
  Fact確認・Memory Proposal・Current更新候補・Conflict解消候補

専用導線
  Decision結果/後日評価、通常Draft、外部送信前確認、Personal Inference、週次レビュー
```

Action Centerは異種の次行動から主Actionを最大1件選ぶ。Review InboxはMemoryの採否・訂正・Conflict解消に限定する。

## 2. Action Contract案

```json
{
  "action_id": "review-fact-123",
  "action_kind": "memory_review",
  "priority_class": "urgent",
  "title": "住居情報を確認する",
  "reason": "現在の住居予定を更新する可能性があります",
  "primary_action": {},
  "defer_options": [],
  "basis": []
}
```

API名、保存形式、Table名は実装時に決定する。

## 3. 主Action選択案

保存失敗Draftを最優先とする。最近編集された有効Draftは高優先候補とするが、古いDraftや内容がほぼないDraftは主Actionにしない。暫定基準は、有効Draftを空白以外10文字以上かつ72時間以内、古いDraftを7日以上とする。72時間超7日未満は再開導線へ置く。各Draftには「続きを入力」「今回は表示しない」「破棄」を提供し、破棄には確認を要求する。

## 4. Inbox Bucketと優先順位案

Urgentは次の決定的条件に限定する。

1. `validation_status`または`retrieval_eligibility`が`conflict`
2. Current Factを置き換える候補
3. Currentに利用されるMutable Factの矛盾候補
4. 現在値へ影響する数値外れ値
5. 未確認のActual Transaction候補
6. 14日以内に有効化・期限到来するscheduleまたはplan候補
7. Active Decisionから明示的に参照されている未確認候補

Normalは上記以外の`pending`確認候補、Deferredは`review_state=deferred`または未来の`snoozed_until`を持つ候補とする。同一Bucketはpriority class、Currentへの影響、conflict、意味上の日時、作成日時、IDの順で並べ、ランダム値を使用しない。LLMの自由文章評価だけでUrgentにしない。

## 5. Review状態遷移案

```text
pending + one_day_or_week_snooze -> pending / snoozed_until設定
pending + indefinite_defer          -> deferred / snoozed_until=null
deferred + resume                   -> pending
pending + confirm                   -> confirmed
pending + reject                    -> rejected
```

`confirmed`と`rejected`は通常Queueから除外する。表示都合でFactまたはEvidence本文を変更しない。PaginationはCursor等で段階的に取得する。

## 6. Sensitive Projection案

Public Snapshot・Fixture・ScreenshotはSynthetic Dataのみとする。Production一覧はSafe Summaryを表示し、本人が「内容を確認する」または「根拠を見る」を選んだProduction詳細では、正誤判断に必要な実内容を表示できる。Sensitive本文をURL、Browser History、Console、HTML dataset属性へ入れない。

## 7. 将来拡張

Personal Inferenceを確認対象へ追加する場合は、Fact確認Inboxへ無条件に混在させず、別Bucketまたは別画面を要件化する。

## 8. Startup MigrationとMaintenance

`initialize()`は既存DBで最初に`schema_migrations`を保証し、軽量で冪等なMigrationを実行してから、必須Tableと`015_action_center_review_inbox_stabilization`を検証する。`PERSONAL_OS_RUN_STARTUP_MAINTENANCE=false`が省略するのは全件Backfill・再監査・再解析・Embedding再生成等だけであり、Table・Column・Index・Migration markerの作成は省略しない。Migration 015はQueue metadataとIndexだけを追加し、Fact本文とReview状態を更新しない。

## 9. Review State Transition

| 現在 | 操作 | 保存状態 | Queue metadata |
|---|---|---|---|
| pending | 1日・1週間 | pending | `snoozed_until`だけ更新 |
| pending | 期限なし | deferred | `snoozed_until=NULL` |
| pending/deferred | 正しい・違う | confirmed/rejected | 削除 |
| deferred | 確認再開 | pending | 削除 |
| pending snoozed | Snooze解除 | pending | 削除 |

`confirmed`と`rejected`は終端状態とし、同じ終端状態の再送だけを冪等成功として許可する。異なる終端状態への変更、終端状態の再開、deferredから直接の有限Snoozeは400とする。一時Snooze、期限なし保留、再開では元の`reason`、`review_note`、`reviewed_at`を保持する。

## 10. Evidence Detail

一覧ProjectionはEvidence本文、値、Document title、Extractor、Promptを含めない。通常Factは「根拠を見る」の初回`toggle`、Sensitive Factは「内容を確認する」の明示操作で詳細APIを取得する。詳細は`private, no-store`で返し、技術詳細を入れ子の閉じた`details`へ分離する。同一Cardの取得Promiseを共有し、Review完了、Tab変更、Reload、Sensitive詳細を閉じた時にClient Mapから破棄する。

## 11. Draft v2

`draft-store.js`が記録、相談、判断結果、後日評価、Feedback、画像Context、Benchmark Importを同じContractで扱う。保存失敗かつ非空を文字数に関係なく最優先とし、通常Draftは10文字以上・72時間以内だけを主Action候補にする。それ以外は削除せず再開一覧へ置く。Legacy plaintextと旧複数Field JSONは読込時にLosslessなv2 Projectionへ変換し、日時不明のDraftを主Actionへ昇格させない。

## 12. Bucket QueryとCursor

Fact候補はSQL CTEでUrgent priorityを算出し、指定Bucket条件を適用した後に`LIMIT`する。Memory ProposalもNormal/Deferred専用Queryで取得する。Action Centerは`bucket=urgent&limit=1`相当だけを利用する。Cursorは`bucket_rank, priority, sort_time, item_kind, id`をBase64 JSONで保持し、各Source Queryへ同じrow-value条件を適用する。件数は各BucketのCOUNT Queryで算出し、`counts_exact=true`を返す。Pythonへ全候補を読み込んでから分類しない。
