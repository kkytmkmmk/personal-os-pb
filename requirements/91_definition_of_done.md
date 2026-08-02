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

## 11. 3D Visualization Acceptance

3D Personal SpaceをDoneとするには、少なくとも以下を満たす。

- Fact / Decision / Result等のObject Typeを視覚的に区別できる
- Domain Colorが一貫し、色以外のEncodingも併用する
- Node選択から元のFact / Decision / Evidence等へ遡れる
- SearchまたはFilterで表示対象を絞れる
- Reloadごとに配置が完全Randomにならない
- Current / Historical等の状態差を理解できる
- Sensitiveな本文・具体値をDefault Canvasへ無条件表示しない
- 低性能・3D非対応環境でもCore Personal OSを利用できる

Canvasや3Dライブラリを表示しただけではDoneにしない。

## 12. Population Benchmark Acceptance

Population BenchmarkをDoneとするには、少なくとも以下を満たす。

- Official / high-quality Sourceから取得または正式Importする
- Reference DataをPersonal Factとは別にLocal DBへ保持する
- Source / Definition / Statistic Type / Population Segment / Reference Periodを追跡できる
- Personal MetricとのDefinition Compatibilityを確認する
- mean / median / percentile / distributionを混同しない
- 外部SourceへPersonal Contextを送信しない
- Refresh失敗時にLast valid referenceを保持する
- 新しいReference Periodで過去値を削除しない
- 少なくとも2つ以上の異なるMetricで比較UIが動作する
- Difference / Ratio / Distribution Marker等で乖離を理解できる

固定された平均値を画面に置くだけではDoneにしない。

## 13. Daily Action Center Acceptance

詳細な操作手順は `docs/acceptance/action_center_review_inbox_acceptance.md` を参照する。Daily Action CenterをDoneとするには、少なくとも以下を満たす。

- AC-001: Today最上部の主Actionが最大1件である
- AC-002: Action理由が表示される
- AC-003: Mobile初期Viewportから記録・相談を開始できる
- AC-004: 保存失敗Draftが最優先候補になる
- AC-005: 古い・無意味なDraftが主Actionを占有しない
- AC-006: Todayの主要表示に確認候補全件がない
- AC-007: 未処理候補が通常利用をブロックしない
- AC-008: Current Stateと最近の変化が主Actionより下にある

## 14. Review Inbox Acceptance

詳細な操作手順は `docs/acceptance/action_center_review_inbox_acceptance.md` を参照する。Review InboxをDoneとするには、少なくとも以下を満たす。

- RI-001: Inbox対象がMemory確認に限定される
- RI-002: Urgent・Normal・Deferredが区別され、初期表示がUrgentである
- RI-003 / RI-004: 同じ状態なら同じ順番で、ランダム順を使用しない
- RI-005: Focus Modeで1件ずつ処理できる
- RI-006 / RI-007: 一時Snoozeは`pending`を維持し、期限なし保留だけを`deferred`とする
- RI-008 / RI-009: Snooze期限前に再表示せず、Reload後も維持する
- RI-010: legacy `deferred`を自動的に`pending`化しない
- RI-011 / RI-012: 技術情報を初期状態で閉じ、管理・修復操作をInboxに置かない
- RI-013: Sensitive本文をPublic Screenshotへ出さず、本人操作後はProduction詳細で確認可能とする
- RI-014: 50件以上のSynthetic BacklogでDesktop/Mobile Acceptanceが成功する
- RI-015: Inboxをゼロにすることを利用目標にしない
