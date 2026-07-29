# UX Phase 5 最終是正

## 実行条件

- `PERSONAL_OS_ENV=verification`、一時ディレクトリ内の `ux-synthetic.db` のみを使用。
- 本番DB、添付ファイル、APIキー、本人データは開かない。
- Desktop 1280×720 / 1440×900、Mobile 390×844 / 375×667 を実ブラウザで実行する。

## Screenshot の生成と承認

`tools/run_ux_e2e.py --promote` は画像を生成するだけで、Manifest の `reviewed` は必ず `false` になる。公開前には画像を目視したうえで、次を明示実行する。

```powershell
python tools/approve_public_screenshots.py `
  --reviewer "<reviewer>" `
  --approve-all `
  --confirm "I visually reviewed every screenshot"
python tools/check_public_screenshots.py --root .
```

承認時に各PNGのSHA-256、承認者、承認日時をManifestへ記録する。承認後の画像差し替え、未登録PNG、未承認ManifestはPublic Snapshotを失敗させる。

## 今回確認した結果

- 20枚の公開用Synthetic Screenshotを実際に開いて確認した。
- `codex-visual-review` がUTC `2026-07-29T07:49:07.937978+00:00` に承認し、Manifestの全PNGへSHA-256を記録した。
- Desktop / Mobile E2Eでは、記録の成功・失敗、Draft保持、判断結果と後日評価のPATCH、再読込後の永続化を確認した。
- E2Eの実行Browserはこの環境ではMicrosoft Edge。指定Browser、Windows Edge、Playwright Chromiumの順で選択する実装である。Chromium fallbackの実機実行は別環境での追加確認対象。
- Public Snapshotは `manifest.webmanifest`、`icon.svg`、Service WorkerのAPP_SHELL全Assetの整合性を検査する。

## 画面レビューで修正した事項

Desktopで `#today { display:block }` がルーターの `.hidden` より強く、他画面へTodayが重なっていた。`#today:not(.hidden)` に限定し、再撮影して確認した。

## 公開用の代表画像

- `docs/screenshots/ux-phase5/desktop-1280-today.png`
- `docs/screenshots/ux-phase5/desktop-1280-decisions.png`
- `docs/screenshots/ux-phase5/desktop-1280-money.png`
- `docs/screenshots/ux-phase5/mobile-390-today.png`
- `docs/screenshots/ux-phase5/mobile-390-decision-result-sheet.png`
- `docs/screenshots/ux-phase5/mobile-390-benchmark.png`
