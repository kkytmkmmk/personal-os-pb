# Personal OS Daily Action Center / Review Inbox 要件

この文書はToday Action Centerおよび確認Inboxの最新の機能要件正本である。実現方式は[Design](../docs/design/action_center_review_inbox_design.md)、合格条件は[Acceptance](../docs/acceptance/action_center_review_inbox_acceptance.md)を参照する。

## 1. 目的

Personal OSを開いた本人が、保存済みデータや管理機能の一覧を解読せず、今最初に何をすべきか、その理由、今は行わなくてよいかを短時間で理解できるようにする。確認Inboxをゼロにすることを利用目標にせず、未処理候補が残っていても記録・相談・判断を利用できるようにする。

## 2. Todayの構造

Above the foldでは主Action、記録する、相談するを優先する。Mobile 390×844でもこの3要素を確認できること。主Actionより下にはCurrent Stateの要約、最近の変化、結果待ち・後日評価待ち等の状態件数、その他候補への入口を簡潔に表示してよい。

主Actionは今すぐ進める候補1件であり、その他候補は補助情報である。補助候補を初期ViewportでPrimary Actionとして並べない。Current Fact全件、確認候補全件、Decision入力Form、管理操作を大量表示しない。

## 3. Action Centerの責務

Action Centerは、保存失敗後の再試行、有効なDraftの再開、Decisionの結果待ち・後日評価待ち、実行待ち、判断待ち、確認Inbox内のUrgent項目、相談候補、新しい記録の案内から主Actionを最大1件選ぶ。

### AC-001 主Actionは最大1件

Today最上部の主Actionは最大1件とし、複数候補を同格のPrimary Actionとして並べない。

### AC-002 ユーザー向け表示理由

主ActionにはAction名、対象、ユーザーが理解できる表示理由、Primary Action、後で行う操作を表示する。内部状態、内部ID、Extractor、confidence数値等を直接表示しない。

### AC-003 最初のViewportから開始できる

記録・相談は常に開始しやすい入口として残し、最初のViewportから開始できること。

### AC-004 保存失敗Draftを最優先する

保存APIが失敗し未送信内容が残るDraftは、主Actionの最優先候補として扱う。

### AC-005 古い・無意味なDraftは主Actionを占有しない

最近編集された有効なDraftは高優先候補としてよいが、意味のない短いDraftや古いDraftが重要Actionを恒常的に押し下げないこと。各Draftには続きを入力、今回は表示しない、破棄を提供し、破棄は確認を必要とする。

### AC-006 Todayに確認候補全件を表示しない

Todayから確認を促す候補は最大1件とし、大量の総件数を作業の強制として強調しない。通常候補の全件は確認Inboxで扱う。

### AC-007 未処理候補で通常利用をブロックしない

未処理候補があっても、記録・相談・判断の通常利用をブロックしない。

### AC-008 Current Stateと最近の変化は主Actionより下に表示する

Current Stateの要約、最近の変化、結果待ち・後日評価待ちは主Actionの補助情報としてBelow the foldに置く。

## 4. 確認Inboxの責務

確認InboxはMemoryの採否・訂正・Conflict解消に限定する。対象はFact確認、Memory Proposal、Current更新候補、Conflict解消候補とする。Decision結果入力、Decision後日評価、通常Draft、保存失敗の再試行、外部AI送信前確認、Personal Inference候補、週次レビューは対象外とし、それぞれAction Centerまたは専用画面で扱う。

### RI-001 Inbox対象範囲をMemory確認に限定する

確認Inboxへ対象外の項目を無条件に混在させない。Personal Inference候補を将来追加する場合は、別Bucketまたは別画面を要件化してから追加する。

### RI-002 Urgent・Normal・Deferredを分離する

初期表示はUrgentとする。Urgentは、Conflict、Current Fact置換候補、Currentに利用されるMutable Factの矛盾、現在値へ影響する数値外れ値、未確認Actual Transaction、14日以内に有効化・期限到来するscheduleまたはplan、Active Decisionが明示参照する未確認候補に限定する。Normalはその他の`pending`候補、Deferredは`review_state=deferred`または未来の`snoozed_until`を持つ候補とする。

### RI-003 決定的な並び順

同じデータ状態に対して同じ結果になる並び順とする。priority class、Currentへの影響、conflictの有無、意味上の日時、作成日時、IDの順で評価する。

### RI-004 ランダム順を使用しない

候補の表示順やUrgent判定にランダム値を使用しない。LLMの自由文章評価だけでUrgentにしない。

### RI-005 Focus Mode

Focus Modeでは候補を一件ずつ処理でき、「正しい」「修正する」「違う」「後で」を提供する。3件連続処理後は「今日はここまで」「続けて確認する」を表示する。「今日はここまで」を選んでも候補状態を変更しない。

## 5. SnoozeとReview状態

### RI-006 一時Snoozeはpendingを維持する

「明日まで表示しない」「1週間表示しない」の一時Snoozeは`review_state=pending`を維持し、再表示期限だけを設定する。Factの意味状態を変更しない。

### RI-007 期限なし保留だけをdeferredとする

「期限を決めず保留する」を選んだ場合だけ`review_state=deferred`とする。期限なし保留には再表示期限を設定しない。

### RI-008 Snooze期限前に再表示しない

一時Snoozeした候補を、期限前のReload、再起動、主Action、Urgentへ再表示しない。

### RI-009 Reload後もSnoozeを維持する

Snoozeによる表示制御はReload後も維持する。

### RI-010 legacy deferredを自動pending化しない

既存の`deferred`候補を期限経過だけで自動的に`pending`へ戻さない。ユーザーが「確認を再開」を選んだ場合に限り`pending`へ戻してよい。

`confirmed`と`rejected`は通常Queueから除外する。表示制御の都合でFactやEvidence本文を変更しない。具体的なTable・ColumnはDesignで定義する。

## 6. 表示・安全性・規模

### RI-011 技術情報は初期状態で閉じる

通常Cardには分野、候補内容、確認理由、主要操作を表示する。技術情報、長いEvidence全文、Confidence数値等は初期状態で閉じ、候補内容、確認理由、根拠、技術詳細の順に段階的に開示する。

### RI-012 管理・修復操作をInboxから分離する

Evidenceによる自動判定、記憶品質の再監査、既存記憶の修復、会話の再解析、Personal Inference再生成を確認Inboxに置かない。設定または記憶メンテナンスへ分離し、破壊的・大量変更を伴う操作には確認を必要とする。

### RI-013 Sensitive詳細は本人操作後に表示する

Sensitive分野は一覧でSafe Summaryを使用する。本人が内容または根拠の表示を明示的に選んだProduction詳細では、正誤判断に必要な実内容を表示できること。Public Screenshot、Public Fixture、Public SnapshotにはSynthetic Dataのみを使用する。

### RI-014 大量Backlogでも初期表示量を制限する

確認候補はCursor等で段階取得し、全候補を一度にClientへ読み込まない。50件以上の候補でもTodayは最大1件、Inbox初期表示は限定件数とし、初期DOM量と応答時間が候補総数に比例して無制限に増えないようにする。

### RI-015 Inboxをゼロにすることを利用目標にしない

確認Inboxをゼロにすることを日常利用の目標にせず、通常利用を確認作業でブロックしない。

## 7. 名称とProduction利用

「確認Inbox」と「週次レビュー」を明確に区別する。本番利用時には本人が少量ずつ処理できるようにし、Production DBに対する一括処理を受入手順へ含めない。
