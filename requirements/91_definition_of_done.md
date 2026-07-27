# Definition of Done / Acceptance Requirements

## 1. Done判定

要件をDoneとするには原則として、

- 実装が存在する
- 正常系Acceptance Testがある
- 重要な異常系/Regression Testがある
- テストが成功する
- Existing DB / Migrationへの影響を確認する
- 要件の主要ユースケースを満たす

こと。

Prototype、固定テンプレート、画面だけ存在する場合はPartialとする。

## 2. 必須Memory Acceptance

- 新しいFactを先に保存し、古いFactを後ImportしてもCurrentが巻き戻らない
- 同日同値のFactはmetadata差だけでConflictにならない
- 同日異値は適切にConflict扱いできる
- `valid_to < valid_from` を作らない
- Rejected / Excluded / unresolved conflictをCurrentとして通常Retrievalしない

## 3. Entity Acceptance

- 「ずんだもんの動画を見た」「ドラえもんが好き」「OpenAIを調べた」をRelationship Personにしない
- 「友人の田中さんと会った」等はPerson候補にできる
- LLMがpersonと誤分類してもDeterministic/Context Gateで修正可能

## 4. Personal Inference Acceptance

- Assistant発言しか存在しない場合、それを根拠にユーザー興味Inferenceを生成しない
- 支持Evidenceが失われたInferenceはactiveのまま残らない
- InferenceからUser Evidenceへ遡れる

## 5. Local First Acceptance

Localが利用可能、OpenAI/Gemini Keyも存在、provider=autoの場合にLocalを選ぶ。

Cloud通信は明示Provider選択または明示Fallback許可なしに行わない。

## 6. Finance Acceptance

会社業績、株価、物件価格、Simulation等をActual Personal Transactionへ混入させない。

## 7. Decision Acceptance

検討しただけ、決めた、実行した、結果が出たを区別する。

## 8. Retrieval Acceptance

相談時にStructured Currentだけでなく、必要に応じて関連Raw Sourceを取得する。

Raw Sourceが未確認/Conflictの場合は確定Factと区別できるContextを渡す。

## 9. UI Acceptance

通常トップナビに管理系機能を大量配置しない。

Today / Consultation中心の主要導線を維持する。

## 10. Test Quality

Unit Testは実DBに依存しない。

Memoryを壊しやすいAdversarial Caseを継続的なRegressionとして保持する。
