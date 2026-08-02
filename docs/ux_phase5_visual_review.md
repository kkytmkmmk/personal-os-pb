# UX Phase 5 Visual Review

## 実施条件

- Verification環境（port 8877）と毎回生成する一時SQLite DB
- 固定の合成データのみ。実在人物、実資産、会話本文、添付、APIキーは使用しない
- Desktop 1280 × 720 / 1440 × 900、Mobile 390 × 844 / 375 × 667

## 代表画面の目視確認

![Desktop 今日](screenshots/ux-phase5/desktop-1280-today.png)

![Mobile 今日](screenshots/ux-phase5/mobile-390-today.png)

![Desktop 今日のダイジェスト](screenshots/ux-phase5/desktop-1280-today-digest.png)

![Mobile 今日のダイジェスト](screenshots/ux-phase5/mobile-390-today-digest.png)

## Phase B-UX1: Today Action Centerと確認Inbox

![Desktop Action Center](screenshots/ux-phase5/desktop-1280-action-center.png)

![Desktop 確認Inbox](screenshots/ux-phase5/desktop-1280-review-inbox.png)

![Desktop Focus確認](screenshots/ux-phase5/desktop-1280-review-focus.png)

![Mobile Action Center](screenshots/ux-phase5/mobile-390-action-center.png)

![Mobile 確認Inbox](screenshots/ux-phase5/mobile-390-review-inbox.png)

![Mobile 保留メニュー](screenshots/ux-phase5/mobile-390-review-snooze.png)

50件以上の固定Synthetic Backlogで確認した。Todayは主Actionが1件、主Buttonが1件で、記録・相談・確認Inboxの3入口が最初のMobile Viewportに収まる。Inboxは10件の重要候補、35件の通常候補、15件の保留候補を本文一覧として積み上げず、先頭1件のFocus Cardを表示する。根拠と技術情報は閉じた状態で、機微候補は本文と原文Previewをマスクする。

目視確認では、非同期で追加されるカテゴリ監査がInboxへ入り込む問題と、Mobileの保留メニューが下部Navigationに隠れる問題を発見した。カテゴリ監査は管理の記憶メンテナンスへ移動し、保留メニューは下部Navigationより上へ表示するよう修正した。人口ベンチマークの補助文・金額・時間単位も通常画面では日本語表示へ統一した。

![Desktop Personal Space](screenshots/ux-phase5/desktop-1280-explore-space.png)

![Mobile 人口ベンチマーク](screenshots/ux-phase5/mobile-390-benchmark.png)

![Desktop 自分の変化](screenshots/ux-phase5/desktop-1280-timeline.png)

![Mobile 自分の変化の詳細](screenshots/ux-phase5/mobile-390-timeline-detail.png)

確認した点は、Primary Actionの初期表示、Bottom Navigationとの非重複、44px以上の操作対象、SheetのEsc／Focus復帰／背景スクロール固定、横Overflowなし、根拠の折りたたみ、機微ラベルの既定マスクである。

## Desktop

今日では「相談する」と「記録する」を最初の表示領域に置き、管理画面の導線は前面に出さない。相談では回答を先に表示し、参照した根拠は明示操作まで折りたたむ。資産・旅行・住居・人間関係は「現在の要約 → 最近の変化 → 関連する判断 → 履歴 → 根拠」の同じ順序で確認した。Personal Spaceは既定で機微ラベルを伏せ、人口ベンチマークは合成の参照データをロードした後の比較表示を確認した。

今日のダイジェストでは、相談・記録の直後に、事実ベースの一言と優先順付きの次の行動を置いた。表示した判断・資産・住居は固定Synthetic Fixtureのみで、実データや原文、絶対パス、APIキーは含まない。「根拠を見る」は折りたたみのままなので、最初の画面を圧迫しない。

## Mobile

390 × 844 と 375 × 667 の両方で、Bottom Navigationが本文と重ならず、＋Sheet、その他Sheet、判断結果SheetがViewport内に収まることを確認した。記憶入力、画像追加、相談、根拠、探索、Personal Space Node Detail、ベンチマーク取込Sheet、Draft復元を実操作し、横方向Overflowがないことを自動検査した。

ダイジェストの相談候補は、タップ後に相談画面へ遷移して文面だけを入力する。回答送信は行われず、入力は本人が編集できることをBrowser E2Eで確認した。

Timelineでは、意味的な日付、領域、日本語の種類ラベルを左から追えるようにし、線やマーカーを本文より強くしない。Mobileの詳細は共通Sheetに収め、閉じた後は元CardにFocusが戻る。資産・人間関係・健康は既定で本文を伏せ、試算・提案・未確認推論は表示しない。

## 修正した点

- 記録は送信時に「保存しています…」と表示し、実APIの2xx応答後だけ成功表示とDraft削除を行うようにした。
- 失敗・Timeout時は「保存できませんでした。入力内容は保持しています」と表示し、再送できるようにした。
- SheetのEsc、Backdrop、Focus Trap、Focus復帰、背景スクロール固定を共通化した。
- Domain画面のCurrent/Recent/Decisions/History/Evidence構造とEmpty Stateを共通Rendererへ統一した。

公開レビュー用の27画面は `screenshots/ux-phase5/manifest.json` に登録する。E2E生成直後はすべて `reviewed=false` とし、Synthetic Dataであることと `contains_sensitive_data=false` を確認した目視承認後だけ、ハッシュ・承認者・承認日時付きで公開前検査を通過する。

## 残課題

初回は構造・操作性のE2Eを優先した。pixel-perfectなVisual Regressionは、画面が安定してから追加する。
