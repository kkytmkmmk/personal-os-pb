# 確認Inbox

確認Inboxは、自動確定できなかったFactとMemory Proposalを一件ずつ確認する日常画面です。週次レビューや記憶メンテナンスとは別の機能です。

## Bucket

- 今確認したい: 矛盾、Current置換、検出済み外れ値、未確認Actual Transaction、14日以内のschedule/plan、Active Decisionが明示参照する候補
- 通常: Evidenceはあるが自動確定基準に届かなかった候補、非Current候補、文脈確認が必要な候補
- 保留中: 本人が後でを選んだ候補、既存の `deferred`、未来の `snoozed_until` を持つ候補
- すべて: 上記を決定的な順序でまとめた一覧

Bucketと優先順位は取得時のFact状態から算出します。DBへ古いPriorityを固定保存しません。同一優先度では古い候補、Fact IDの順に並ぶため、再読込しても順序はランダムに変わりません。

## Focus Mode

初期Tabは「今確認したい」です。先頭の1件だけをFocus Cardへ表示し、「正しい」「修正」「違う」「後で」のいずれかを選ぶと次へ進みます。3件処理すると「今日はここまで」「続けて確認する」を表示します。一覧は明示的に開いた場合だけ表示し、初回10件、以降はOpaque Cursorで追加取得します。

## 保留

「後で」では1日、1週間、期限なしを選べます。1日・1週間は`review_state=pending`のまま `fact_review_queue_state.snoozed_until`だけを設定し、期限なしだけを`deferred`にします。既存の期限なし `deferred` は自動的に `pending` へ戻しません。「確認を再開」を本人が選んだ場合だけ再開します。表示回数はGETでは増えず、Focus Cardまたは一覧へ実際に描画したItemだけを専用POSTで記録します。

## Sensitive情報

資産、人間関係、健康などの本文、値、Evidence、原文Titleは一覧Responseでマスクします。マスク状態では「内容を確認する」「後で」だけを表示します。本人が明示的に内容を開いた場合だけ`no-store`の詳細APIから実値を取得し、正しい・修正・違うを表示します。閉じると実内容をDOMと一時Mapから削除し、StorageやURLへ保存しません。Memory Proposalも同じInboxから適用、修正して保存、破棄できます。

## API

- `GET /api/review-inbox?bucket=urgent|normal|deferred|all&domain=&limit=&cursor=`
- `GET /api/review-inbox/{id}/detail?include_sensitive=true`
- `POST /api/review-inbox/{kind}/{id}/presented`
- `PATCH /api/facts/{id}/review`

PATCHは`pending + one_day/one_week`、`deferred + indefinite`、期限指定なしの`confirmed/rejected`だけを許可し、Clientが任意日時を直接保存することはできません。Cursor PaginationとDomain Filterを利用でき、confirmed/rejected後の候補はInboxから外れます。

## 管理機能との分離

Evidence自動判定、品質監査、既存記憶の修復、会話の再解析、Personal Inference更新は、管理画面の閉じた「記憶メンテナンス」へ移しました。修復と再解析には確認Dialogが必要です。
