# UI/UX フェーズ2〜5 トレーサビリティ

> 2026-08-02のPhase B-UX1 Stabilizationで、Desktop/Mobileの独立DB E2E、Microsoft Edge/Playwright Chromiumの両Browser、機微情報の`no-store`詳細、保存・再読込、Snooze、42枚の承認済みSynthetic Screenshotを再検証した。Service Worker cacheは`personal-os-v3-phase-b-ux1-stabilization-3`である。

対象は `requirements/` を変更せずに実装した日常利用UXの後半フェーズです。すべての確認はVerification DBとポート8877を前提とし、本番DBは使用しません。

| フェーズ | 要件 | 実装 | テスト/確認 | 状態 |
| --- | --- | --- | --- | --- |
| 2 | 相談の回答優先、根拠の折りたたみ、処理状態、不足情報 | `static/daily-ux.js` の `streamlineConsultation` | `test_consultation_exposes_progress_missing_context_and_collapsed_evidence` | Done |
| 2 | 判断を次のAction中心にし、結果/評価をSheetで入力 | `streamlineDecisions`、`decision-outcome-sheet` | `test_decision_screen_prioritizes_next_action_and_uses_sheet_for_outcomes`、Decision cycle APIテスト | Done |
| 3 | Domainを現在・最近の変化・関連判断・履歴へ統一 | `standardizeDomainViews` | `test_domain_and_explore_surfaces_keep_daily_and_technical_actions_separate` | Done |
| 3 | Exploreに入力Formを常駐させず、Benchmark取込をSheetに隔離 | `streamlineExplore`、`benchmark-import-sheet` | UI静的テスト、Benchmark importテスト | Done |
| 4 | Mobile/Draft/Empty state | `sessionStorage` Draft、`data-space-record`、PWA cache v2 | `test_empty_personal_space_can_return_to_recording`、`test_mobile_sheets_preserve_focus_and_pwa_shell_is_refreshed` | Done |
| 5 | A11y: label、live region、Sheet focus、Escape、reduced motion、Canvas fallback、44px | `static/index.html`、`static/daily-ux.js`、`static/styles.css`、`static/visualization.js` | UI静的テスト | Done |
| 5 | Desktop/Mobile Browser E2Eの自動化 | `tools/run_ux_e2e.py` と `requirements-dev.txt`。Verification環境・一時SQLite・固定Synthetic DataでPlaywrightがServerを起動し、実クリック、実入力、実API応答、Console Error、横Overflow、Screenshotを検査 | Desktop 1280 × 720とMobile 390 × 844の受入Journeyを実行。レビュー済みScreenshotはManifestとSafety Scanを通過して公開Snapshotへ限定連携 | Done |

## 回帰保護

- `static/index.html` のToday候補更新はカード参照を自前で初期化し、`ReferenceError` を起こさない。
- `static/service-worker.js` は `personal-os-v3-daily-ux-phase5` とし、今回の画面資産を旧キャッシュから分離する。
- 結果・後日評価の通常導線にBrowserの `prompt()` を使わない。

## Phase B-1: 今日のパーソナルダイジェスト

| 要件 | 実装 | 検証 | 状態 |
|---|---|---|---|
| 事実ベースの今日の一言 | `today_digest()` / `GET /api/today/digest` | `test_today_digest.py` | Done |
| 次にやることを最大3件・優先順で表示 | `executed → decided → candidate/considered → result` のProjection | Backend unit test / Desktop Browser E2E | Done |
| 最近の変化・思い出しておくこと | `memory_changes` とEvidence付きconfirmed Factを最大3/2件に制限 | Backend unit test | Done |
| 相談候補は自動送信しない | `data-digest-prompt` が相談入力欄だけをprefill | Mobile Browser E2E | Done |
| Empty State | `today_digest()` の空Projectionと記録導線 | Backend unit test / Browser E2E | Done |

## Phase B-2: 自分の変化 Timeline

| 要件 | 実装 | 検証 | 状態 |
|---|---|---|---|
| 読み取り専用の共通Timeline Event | `timeline_projection()` / `GET /api/timeline` | `test_change_timeline.py` | Done |
| 意味的時刻・Fact更新・Decision lifecycle | Factの有効日時、Plan、Decision、Execution、結果、評価をProjection | Timeline unit test | Done |
| Privacyと推論境界 | finance / relationship / healthを既定マスク、未確認Inference・Recommendation・Simulationを除外 | Timeline unit test | Done |
| Explore UI・Filter・Cursor・Detail | `static/visualization.js` / `explore-timeline` / shared Sheet | `test_timeline_ui.py` / Browser E2E | Done |
| 今日からの導線と今と比べる | `daily-ux.js`、比較Promptの下書きのみ | Browser E2E | Done |

## Phase B-UX1: Today Action Center＋確認Inbox

| 要件 | 実装 | 検証 | 状態 |
|---|---|---|---|
| Todayの主Actionを1件へ統合 | `action_center_projection()` / `GET /api/action-center` / `static/action-center.js` | Backend unit / Desktop・Mobile Browser E2E | Done |
| Draft・保存失敗を最優先 | Draft v2の日時・失敗・非表示metadataとClient override | UI static / Browser E2E | Done |
| 確認候補を決定的に分類 | 限定Urgent / sort-key Cursor / 初回10件 | Backend tests / 61件backlog E2E | Done |
| Snoozeとlegacy deferred保護 | `pending + one_day/one_week` / `deferred + indefinite` | Unit / ReloadとDB assertionを含むMobile E2E | Done |
| Focus Mode・機微情報Mask | 明示`no-store`詳細、閉鎖時破棄、3件区切り | Desktop Screenshot / Browser assertion | Done |
| Memory Proposal統合 | Apply・修正Apply・Discard、独立表示metadata | Unit / Desktop E2E | Done |
| 管理操作の分離 | 管理画面の閉じた「記憶メンテナンス」 | UI static / Screenshot | Done |
| 公開画面証跡 | 9枚のAction Center/Inbox Synthetic ScreenshotとManifest | 実画像目視、Hash付き承認、Screenshot Safety | Done |
- 相談の不足情報は最大3件で、Factを自動作成しない。
