# Phase A 安定化記録

## E2E の独立性

`tools/run_ux_e2e.py --suite all` は Desktop と Mobile を別プロセス・別の一時
`ux-synthetic.db` で実行する。各プロセスは次の順で完結する。

1. OS の一時ディレクトリに専用ディレクトリを作成する。
2. `PERSONAL_OS_ENV=verification` と port `8877` で合成データを seed する。
3. 実サーバー、実HTML/CSS/JavaScript、実SQLite を使って Journey を実行する。
4. サーバーを停止し、一時ディレクトリを削除する。

これにより、Desktop で保存した判断結果や後日評価が Mobile の受入条件を消費することはない。Production DB、添付、バックアップは一切参照しない。

## 相談・記録の失敗状態

- 相談の処理中スクリーンショットは POST の完了前に取得し、回答イベント未到着・送信ボタン disabled・結果未表示を確認する。処理中と結果の PNG hash が同じなら E2E は失敗する。
- 記録の timeout Journey は verification 専用の `AbortError` を使い、成功表示を出さず、入力と sessionStorage の Draft を保持し、SQLite に書き込まれないことを確認する。
- 記録成功、判断結果、後日評価は reload 後にも API と画面の両方から確認する。

## Browser 実行

既定の順序は、明示指定した実行ファイル、Windows Edge、Playwright Chromium である。Chromium を明示検証するには次を使う。

```powershell
python -m playwright install chromium
$env:PERSONAL_OS_E2E_FORCE_PLAYWRIGHT_CHROMIUM = '1'
python tools/run_ux_e2e.py --suite desktop
python tools/run_ux_e2e.py --suite mobile --viewport-set primary
```

`--suite all` は日常のフルセット用であり、Desktop と Mobile の状態を共有しない。Playwright Chromium は headless process の終了待ちが Edge より長くなるため、CI 等の非対話環境では十分なジョブ timeout を設定する。

## Benchmark 比較の安全性

Backend は `comparison_group_key` を生成し、`metric_key` だけではなく、出典、発行者、母集団、地域、セグメント、対象期間、版、統計単位、測定方法、時間基準、正規化単位が一致する Series だけを一枚のカードにまとめる。平均と中央値は同じ比較条件なら同じカードに表示する。

通常UIでは compatibility、統計種別、出典種別、比較不能理由を日本語化する。比較不能なら数値差や分布上の位置を作らず、比較条件を説明する。

## Service Worker

Cache name は `personal-os-v3-phase5-final-1`。Activate 時に旧 cache を削除し、`app.js`、`daily-ux.js`、`visualization.js`、`styles.css`、`manifest.webmanifest`、`icon.svg` を新しい shell として取得する。
