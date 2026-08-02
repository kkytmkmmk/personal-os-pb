# Action Center / Review Inbox Acceptance

この文書は合格条件とVerification手順を定義する。機能要件は[要件正本](../../requirements/12_daily_action_review_inbox_requirements.md)、実現方式は[Design](../design/action_center_review_inbox_design.md)を参照する。

## A. Today

- AC-001: 主Actionは1件以下である。
- AC-002: 主Actionにユーザー向け表示理由がある。
- AC-003: Mobile初期Viewportから記録・相談を開始できる。
- AC-006: Todayは確認候補全件を表示しない。
- AC-008: Current Stateは主Actionより下に表示される。

## B. Draft

- AC-004: 保存失敗Draftは主Action候補になる。
- AC-005: 72時間以内の有効Draftは高優先候補、7日以上前のDraftは主Actionにならない。
- 破棄は確認後にだけ削除される。

## C. Review Inbox

- RI-001/RI-002: Urgent、Normal、Deferredの対象範囲が分離される。
- RI-003/RI-004: 同じ状態なら順番が同じで、ランダム順を使用しない。
- RI-005: Focus Modeで一件ずつ処理でき、3件連続処理後に「今日はここまで」「続けて確認する」を表示する。「今日はここまで」は候補状態を変更しない。

## D. Snooze

- RI-006/RI-008/RI-009: 1日Snoozeは`review_state=pending`を維持し、`snoozed_until`を設定し、Reload後も期限前は表示しない。
- RI-007: 期限なし保留は`review_state=deferred`かつ`snoozed_until=null`となる。
- 確認再開は`review_state=pending`へ戻す。

## E. Legacy / Large Backlog

- RI-010: 既存`deferred`は自動的に`pending`化されない。
- RI-014: 50件以上のSynthetic候補でもToday表示は最大1件、Inbox初期取得は限定件数で、初期DOM量が全件数に比例して増えない。

## F. Sensitive / Production

- RI-013: Public ScreenshotはSyntheticのみ、Production一覧はSafe Summary、Production詳細は本人操作後に実内容を確認できる。
- Sensitive本文はURL、Console、Public Fixtureへ出さない。
- Production DBを自動E2Eで開かない。本人による手動確認は、Todayを開く、主Actionを確認、Inboxを開く、1件確認、1件を1日Snooze、Reload後の維持確認に限る。
