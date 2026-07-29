# UI/UX フェーズ2〜5 トレーサビリティ

対象は `requirements/` を変更せずに実装した日常利用UXの後半フェーズです。すべての確認はVerification DBとポート8877を前提とし、本番DBは使用しません。

| フェーズ | 要件 | 実装 | テスト/確認 | 状態 |
| --- | --- | --- | --- | --- |
| 2 | 相談の回答優先、根拠の折りたたみ、処理状態、不足情報 | `static/daily-ux.js` の `streamlineConsultation` | `test_consultation_exposes_progress_missing_context_and_collapsed_evidence` | Done |
| 2 | 判断を次のAction中心にし、結果/評価をSheetで入力 | `streamlineDecisions`、`decision-outcome-sheet` | `test_decision_screen_prioritizes_next_action_and_uses_sheet_for_outcomes`、Decision cycle APIテスト | Done |
| 3 | Domainを現在・最近の変化・関連判断・履歴へ統一 | `standardizeDomainViews` | `test_domain_and_explore_surfaces_keep_daily_and_technical_actions_separate` | Done |
| 3 | Exploreに入力Formを常駐させず、Benchmark取込をSheetに隔離 | `streamlineExplore`、`benchmark-import-sheet` | UI静的テスト、Benchmark importテスト | Done |
| 4 | Mobile/Draft/Empty state | `sessionStorage` Draft、`data-space-record`、PWA cache v2 | `test_empty_personal_space_can_return_to_recording`、`test_mobile_sheets_preserve_focus_and_pwa_shell_is_refreshed` | Done |
| 5 | A11y: label、live region、Sheet focus、Escape、reduced motion、Canvas fallback、44px | `static/index.html`、`static/daily-ux.js`、`static/styles.css`、`static/visualization.js` | UI静的テスト | Done |
| 5 | Desktop/Mobile Browser E2Eの自動化 | ブラウザ受入手順は `docs/usability_audit.md` に記載 | Verification環境で画面読取は実施。クリック実行は制御層の `SyntaxError` により再実行不能 | Partial |

## 回帰保護

- `static/index.html` のToday候補更新はカード参照を自前で初期化し、`ReferenceError` を起こさない。
- `static/service-worker.js` は `personal-os-v3-daily-ux-2` とし、今回の画面資産を旧キャッシュから分離する。
- 結果・後日評価の通常導線にBrowserの `prompt()` を使わない。
- 相談の不足情報は最大3件で、Factを自動作成しない。
