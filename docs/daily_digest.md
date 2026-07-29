# 今日のパーソナルダイジェスト

`GET /api/today/digest` は、日常画面のための小さく安全なProjectionです。元のFactやDecisionを更新せず、外部LLMも呼びません。

## 表示順

1. 今日の一言
2. 次にやること（最大3件）
3. 最近変わったこと（最大3件）
4. 思い出しておくこと（最大2件）
5. 相談候補（最大3件）

今日の一言と各項目は、Fact IDまたはDecision IDのbasisを内部に保持します。通常画面ではIDを見せず、「根拠を見る」から関連する記録または判断へ移動します。

## 信頼境界

- confirmedかつretrieval eligibleなFact、明示されたDecision、Result、更新履歴だけを使う。
- AIの推論、Recommendation、Plan、心理状態を本人Factとして扱わない。
- Finance、Relationship、Healthは本文を一覧に出さず、分野を示す短い文にマスクする。
- 相談候補は入力欄を埋めるだけで送信しない。候補表示もFact・Recommendation・Planを作らない。

## 優先順位

行動は、結果待ち → 実行待ち → 判断待ち → 後日評価待ちの順で表示する。同じ優先度内では、更新日時が古いものを先にして、放置されている項目を見つけやすくする。

## 検証

`tests/test_today_digest.py` は空状態、上限、Evidence basis、機微情報のマスク、行動優先順を確認する。
`tools/run_ux_e2e.py` はSynthetic SQLite DBだけで、Desktopの判断導線、Mobileの相談文prefill（自動送信なし）、空状態から記録画面へ進む導線を確認する。
