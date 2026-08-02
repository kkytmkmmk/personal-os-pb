# Today Action Center

Todayは機能一覧ではなく、アプリを開いた直後に最初の一操作を決める画面です。最上部には「今やること」を1件だけ表示し、その理由と主操作をセットで示します。

## 優先順位

ブラウザー内に残る状態を先に確認し、その後はServerの共通Projectionが次の順で1件を選びます。

1. 保存失敗後のDraft再試行
2. 72時間以内・10文字以上のDraft
3. 結果待ちの判断
4. 後日評価待ちの判断
5. 矛盾している重要な確認
6. Current Factを置き換える候補
7. 実行待ちの判断
8. 判断待ち
9. 相談候補
10. 記録開始

Server側の順位は `action_center_projection()` を正本とし、`GET /api/action-center` と `GET /api/today/digest` が同じ結果を利用します。Draftと保存失敗だけはServerから見えないため、Clientが最上位へ差し込みます。

## Draftと保存失敗

記録・相談・判断結果・後日評価・Feedbackの入力途中データは、`version`、`kind`、`body`、種類別`fields`、`updated_at`、`save_failed`、`hidden_until`、`route`、`focus`を持つ共通Draft v2として `sessionStorage` に保持します。対象がある場合は`target_id`と`mode`も保持します。保存失敗は空白以外1文字以上なら最優先、通常Draftは72時間以内かつ10文字以上だけを主Actionにします。72時間超、7日以上、未来の`hidden_until`、更新日時不明のlegacy Draftは主Actionにせず、すべて再開一覧から復元できます。判断Draftは対象の結果・後日評価Sheet、Feedback DraftはFeedback Sheetを直接再開します。「今回は表示しない」は1日だけ隠し、「破棄」は確認後にだけ削除します。成功応答を受け取った場合だけDraftを削除します。

## 表示理由と延期

すべての主Actionには「結果が未記録」「現在情報を更新する可能性がある」などの日本語の理由があります。内部の状態名やIDは表示しません。Factの「1日後」「1週間後」は`pending`を維持して再表示期限だけを保存し、「Inboxに残す」だけが`deferred`になります。延期はFact本文やDecision Lifecycleを変更しません。通常ReviewはTodayの主Actionにせず、確認Inboxだけで扱います。

## Todayから移動した機能

- 現在の真実と更新履歴: 記憶／自分の変化
- 保存前の確認: 確認Inbox
- 判断入力と判断一覧: 判断
- 記憶監査・修復・再解析: 管理の「記憶メンテナンス」

Todayには主Action、記録・相談・確認Inboxの3入口、短い件数、今日の一言、最近の変化だけを通常表示します。

## Actionがない場合

対応待ちやDraftがない場合は「新しく記録する」を案内します。確認候補の全件処理を要求する文言は表示しません。
