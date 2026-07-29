# 自分の変化 Timeline

「自分の変化」は、記録をただ作成日時順に並べる画面ではありません。確認済みの本人Fact、計画、判断、実行、結果、後日評価を読み取り専用で重ね、過去から現在までの変化を確認するExplore画面です。

## 表示するもの

- 確認済み・本人関連・検索利用可能なFactの追加または更新
- 好み、旅行、住居、資産Snapshot、人間関係の明示的な記録
- Plan、Decision、Execution、結果、後日評価
- `confirmed` または `confirmed_pattern` と明示されたPersonal Inference

Recommendation、未確認のInference、`scenario` / `simulation` / `what_if` は本人の実際の変化ではないため表示しません。

## 時刻と並び順

`occurred_at`、`occurred_on`、`effective_at`、`valid_from`、`decided_on`、実行・結果・評価の時刻、原文の作成日時、記録日時の順に意味的な日時を選びます。記録日時しかない場合は画面に「記録日時」と明示します。後から古い会話を取り込んでも、Importした時点の最近の変化にはなりません。

同じFact seriesの更新では、`supersedes_fact_id` を使って旧値と新値を詳細に表示します。Timelineは元のFact、Decision、Plan、原文を変更しません。

## 使い方

1. 「その他」→「探索」→「自分の変化」を開きます。
2. 期間（1か月、3か月、1年、すべて）、領域、種類で必要な変化だけに絞ります。
3. Cardをタップすると詳細Sheetを開きます。判断には「同じ判断を見る」が表示されます。
4. 過去Factの更新では「今と比べる」を使えます。相談画面に比較文が入るだけで、自動送信・Fact作成・Recommendation作成は行いません。

資産額、健康本文、人間関係本文などは一覧で既定マスクします。詳細でも、通常の画面では必要最小限に留めます。

## APIと検証

`GET /api/timeline` は `domain`、`kind`、`from`、`to`、`limit`、`cursor` を受け取るカーソル式の共通Event Projectionです。`GET /api/timeline/{event_id}` は1 Eventの読み取り専用詳細です。

Desktop 1280 × 720とMobile 390 × 844で、フィルタ、詳細Sheet、Focus復帰、Empty State、今と比べる下書きをPlaywright Chromiumで検証しています。テストは必ず一時の`ux-synthetic.db`とポート8877を使い、本番DBを開きません。
