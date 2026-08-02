# Memory / Data 要件

## 1. 原文 / Raw Evidenceを保持する

AIが抽出した情報だけでなく、その根拠となった、

- 会話
- メモ
- 画像
- 取引記録
- インポートデータ

を保持する。

構造化された情報から元Evidenceへたどれること。
AI抽出が間違っていても、原文から再評価できる状態を維持する。

## 2. Rawと構造化データを両方持つ

構造化Factだけに情報を縮約しない。

- Structured Data = Current、検索、集計、絞り込み
- Raw Source = ニュアンス、理由、文脈、再解析

として併用する。

## 3. FactとEvidenceを分離する

Factと、そのFactを裏付けるEvidenceを別概念として扱う。

1つのFactに複数Evidenceを関連付けられること。

Evidenceには少なくとも概念上、

- 出典
- 日時
- 種類
- 同一ソースグループ
- Factを支持するか
- Factと矛盾するか

を持たせられること。

## 4. Evidenceの独立性を考慮する

同じconversationを複数chunkへ分割しただけの場合は、独立した複数Evidenceとして数えない。

同じ画像の再登録や、同じ原文から生成された複数派生データも独立Evidenceとして重複評価しない。

派生Factそのものを新しい独立Evidenceとして数えず、可能な限り元Rawまで遡って独立性を判断する。

単純な多数決ではなく、**独立した複数の根拠**を評価する。

## 5. Source Roleを区別する

Raw Sourceについて少なくとも概念上、

- user
- assistant
- system
- external
- unknown

を区別できること。

Assistantの発言を、ユーザー本人の興味・性格・嗜好を裏付けるPersonal Evidenceとして扱わない。

## 6. 現在と過去を区別する

時間によって変化する情報について、

- 現在正しい情報
- 過去には正しかった情報

を区別する。

例:

- 総資産
- 年収
- 家賃
- 積立額
- 保有株
- 住居
- 旅行予定
- 好み

古い情報は削除せず履歴として保持する。

Currentは「最後にDBへ入った」「最後に解析した」ではなく、その情報がいつ有効だったかを基準に解決する。

過去会話を後からImportしてもCurrentが巻き戻らないこと。

## 7. 同一Factの意味的同値を評価する

同日・同じ意味のFactが、noteや抽出metadataの違いだけでConflictにならないこと。

Factのsemantic valueと付加metadataを区別する。

同日時点で意味的に異なる値が存在する場合は、無理に一方をCurrentへ確定せずEvidence評価へ回す。

## 8. Factの信頼状態を管理する

単純な確認済み/未確認の二択にしない。

概念上、

- high trust / verified
- provisional
- conflicted
- excluded / rejected
- historical / superseded

等を扱えること。

## 9. 人間の全件確認に依存しない

Fact信頼性は少なくとも次を利用して自動評価する。

- 本人が明示した情報か
- 独立した複数Evidenceが一致するか
- 別種類のソースと一致するか
- 情報の新しさ
- 時系列整合性
- 他Factとの矛盾
- 数値の外れ具合
- 仮定・シミュレーション・ニュースではないか
- AIによる推測ではないか

十分なEvidenceがあり矛盾がなければ、人間確認なしで高信頼として利用できることが望ましい。

## 10. 数値・時系列の異常を検知する

例:

- 総資産1,234万円前後の履歴に98億円が混ざる
- 家賃82,400円の履歴に8,240,000円が混ざる
- 月間積立額に企業売上148億円が混ざる

このような値を自動的にCurrentや集計へ採用しない。

判断には、履歴、変化率、中央値・分布、桁、時系列、Raw文脈、他Evidenceを利用できることが望ましい。

## 11. AIの推測を恒久Fact化しない

以下をAI推測だけで恒久Factとして保存しない。

- 性格
- 人物評価
- 心理状態
- 好感度
- 恋愛可能性
- 医学的診断
- 抽象的なユーザー像

保存の中心は本人明示、実際の出来事、数値、日付、行動、選択、結果とする。

## 12. EntityとRelationship Personを区別する

Entityとして名前が抽出されたことと、ユーザーの人間関係に属する実在人間であることを分離する。

概念上、person / organization / place / product / service / brand / fictional/media/AI character / unknown等を区別できること。

架空キャラクター、作品、ブランド、組織、著名人への単なるMention等をPeopleへ投影しない。

## 13. Decision / Execution / Resultを保持し区別する

少なくとも、

```text
considered
candidate
decided
executed
result
```

の意味を区別する。

Decisionでは、悩み、選択肢、選択、理由、判断時点の前提、実際の結果、満足・後悔、次回変えたい点を扱えること。

## 14. 提案・Personal InferenceとFactを混同しない

AIが生成したおすすめ、予測、仮説、Plan、傾向推定は、それだけで本人のFactにはしない。

Personal Inferenceは `09_personal_intelligence_requirements.md` に従う。

## 15. データ修正時も履歴を失わない

ユーザーがAI抽出の誤りを修正できること。

修正時も元Raw、元抽出、修正内容、現在採用情報の関係を追跡できることが望ましい。

## 16. Correction / Repairを既存データにも適用できる

Entity、Fact validation、Timeline、Domain projection、Retrieval eligibility等のロジック改善時、新規データだけでなく既存DBを再評価できること。

Rawを削除せずCorrection履歴を追跡できること。

## 17. 実装詳細は設計文書へ分離する

具体的カラム名、テーブル構造、Current判定アルゴリズム等は設計文書で定義する。

## 18. 確認状態と提示状態を分離する（2026-08-02）

`confirmed`、`rejected`、`pending`、`deferred`はFact確認の意味状態とする。明日または1週間の一時Snoozeは`pending`を維持し、再表示期限を設定する。期限なし保留だけを`deferred`とし、再表示期限は持たない。ユーザーが確認を再開した場合に限り`deferred`を`pending`へ戻してよい。

最終表示日時、再表示期限、表示履歴はUI提示状態とする。SnoozeだけでFactの信頼状態を変更せず、既存`deferred`を期限経過だけで自動的に`pending`へ戻さない。Queue表示履歴はFactやEvidenceの内容を上書きせず、表示優先度は現在のFact状態から再計算可能とする。具体的なTable名・Column名はDesign文書で決定する。
