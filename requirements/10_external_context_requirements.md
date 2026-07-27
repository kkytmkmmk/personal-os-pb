# External Context 要件

## 1. 目的

外部連携の目的はデータ量を増やすことではなく、会話だけでは分からない

**「実際に何をしたか」**

を補完することである。

## 2. Sourceごとの意味を区別する

例:

- ChatGPT / User conversation → 考えたこと、理由
- Calendar → 予定したこと
- Gmail → 予約・購入・通知等のEvidence
- Photos → 実際に行った/体験した可能性のEvidence
- Financial data → 実際の金銭移動
- Later conversation → Result / Satisfaction

1ソースだけでDecision→Execution→Resultを過剰推定しない。

## 3. 優先候補

将来の優先順位の目安:

1. Google Calendar
2. Gmail
3. Google Photos Picker等のユーザー選択型画像取得
4. Financial CSV / PDF
5. Google Drive

Browser History、LINE Export、Maps Timeline、Health等は必要性に応じて後段とする。

## 4. Selective Import

GmailやPhotos等を無条件に全件取り込まない。

用途、期間、検索条件、ユーザー選択等で範囲を絞れること。

## 5. Provenanceを保持する

外部Sourceの種類、日時、元識別情報、取得方法を保持し、Evidenceの独立性評価に利用できること。

## 6. Execution Evidenceとして利用する

例:

```text
旅行を相談 → considered
行くと決めた → decided
航空券/ホテル予約 → execution evidence
写真/後日会話 → actual/result evidence
```

と段階を補完する。

## 7. Privacy First

External integrationは `08_privacy_security_requirements.md` のSecurity Gateを満たしてから本格導入する。

## 8. API制約に依存しすぎない

特定APIが将来変更されても、External SourceをRaw/Evidenceとして取り込む抽象構造を維持する。
