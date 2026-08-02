# 確認Inbox

確認Inboxは、自動確定できなかったFact候補を一件ずつ確認する日常画面です。週次レビューや記憶メンテナンスとは別の機能です。

## Bucket

- 今確認したい: 矛盾、Current Factの置換候補、現在状態へ影響する重要情報
- 通常: Evidenceはあるが自動確定基準に届かなかった候補、非Current候補、文脈確認が必要な候補
- 保留中: 本人が後でを選んだ候補、既存の `deferred`、未来の `snoozed_until` を持つ候補
- すべて: 上記を決定的な順序でまとめた一覧

Bucketと優先順位は取得時のFact状態から算出します。DBへ古いPriorityを固定保存しません。同一優先度では古い候補、Fact IDの順に並ぶため、再読込しても順序はランダムに変わりません。

## Focus Mode

初期Tabは「今確認したい」です。先頭の1件だけをFocus Cardへ表示し、「正しい」「修正」「違う」「後で」のいずれかを選ぶと次へ進みます。一覧は明示的に開いた場合だけ表示します。

## 保留

「後で」では1日、1週間、期限なしを選べます。期限付き保留は `fact_review_queue_state.snoozed_until`、表示履歴は `last_presented_at` と `presentation_count` に保存します。既存の期限なし `deferred` は保留中へ残し、自動的に `pending` へ戻しません。「確認を再開」を本人が選んだ場合だけ再開します。

## Sensitive情報

資産、人間関係、健康などの本文とEvidence Previewは通常Responseでマスクします。通常Cardには要約、確認理由、4つの操作だけを表示し、原文は「根拠を見る」、Confidence・Extractor・Model・内部状態・IDは「技術詳細」に折りたたみます。

## API

- `GET /api/review-inbox?bucket=urgent|normal|deferred|all&domain=&limit=&cursor=`
- `PATCH /api/facts/{id}/review`

PATCHの延期値は `one_day`、`one_week`、`indefinite` だけを許可し、Clientが任意日時を直接保存することはできません。Cursor PaginationとDomain Filterを利用でき、confirmed/rejected後の候補はInboxから外れます。

## 管理機能との分離

Evidence自動判定、品質監査、既存記憶の修復、会話の再解析、Personal Inference更新は、管理画面の閉じた「記憶メンテナンス」へ移しました。修復と再解析には確認Dialogが必要です。
