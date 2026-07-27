# 取り込み要件

## 1. 原則

**まず失わず保存し、必要に応じて後から理解を深める。**

## 2. 主な入力経路

- 自然文メモ
- AIとの相談・会話
- コピー&ペースト
- スクリーンショット
- ChatGPT等の過去会話Export

## 3. Raw First

```text
Input
↓
Raw / Image Save
↓
保存完了
↓
Background Analysis
```

解析失敗で入力を失わない。

## 4. Provenanceを保持する

入力元、取得日時、元データ、Source Role、同一ソース識別情報を追跡できること。

## 5. 重複取り込みを抑制する

同一会話・画像・ファイルの再Importを独立Evidenceとして過大評価しない。

## 6. スクリーンショットを主要入力として扱う

文字中心はOCRを優先し、視覚的意味が必要な場合のみVisionを利用する。

画像自体をRaw Evidenceとして保持する。

## 7. ChatGPT履歴を初期Memoryとして利用する

Raw保持、検索、Fact候補、Decision候補、Evidence利用を可能にする。

全履歴の完全構造化をImport時の必須条件にしない。

## 8. Assistant発言とUser発言を区別する

Chat履歴では話者Roleを失わない。

Assistant発言をユーザーのPersonal Fact / Personal Inferenceの直接Evidenceとして扱わない。

## 9. 大量Importで日常利用を妨げない

大量解析中も通常利用を継続できること。

## 10. 再実行可能にする

元データを保持し、失敗処理を重複なく再試行できること。

## 11. 将来の外部Context取り込みに対応可能にする

Calendar、Gmail、Photos、金融CSV等を追加してもRaw/Evidence/Provenanceの原則を共通利用できること。
