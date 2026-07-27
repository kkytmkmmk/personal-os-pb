# 検索 / 提案 / 計画 要件

## 1. 目的

現在の自分に関連するContextを選び、過去を次の提案・計画・判断へ利用する。

## 2. RetrievalはStructured + Rawの2段構成を基本とする

```text
Question
↓
Structured Retrieval
  - Current Facts
  - Constraints
  - Decisions
  - Results
  - Relevant History
  - Personal Inference
↓
Source Retrieval
  - related user raw text
  - Evidence
  - screenshot/OCR text
  - other relevant source
↓
Reasoning
```

全Rawを毎回投入しない。

## 3. Currentを優先する

Rejected、Excluded、unresolved conflict、supersededをCurrent Factとして利用しない。

## 4. Raw Sourceの信頼状態をAIへ伝える

Raw原文は重要だが「原文に書いてある = 確定Fact」ではない。

Contextでは可能な範囲で、

- Confirmed source evidence
- Historical source
- Related but unverified raw
- Conflicted source

等を区別できること。

## 5. 過去情報は履歴として使う

以前の状態・判断・結果・当時の原文を比較に利用する。

## 6. 明示PreferenceとPersonal Inferenceを区別する

本人が明示した好みと推定傾向を混同しない。

## 7. 複数選択肢とTrade-offを提示する

必要な場合は費用、時間、過去の満足/後悔、Current Constraint等を比較する。

## 8. RecommendationはPersonal Contextから生成する

固定Domainテンプレートだけで結論を決めない。

Current State、Decision、Result、Raw、Personal InferenceをReasoningに利用する。

テンプレートはFallbackとして許容する。

## 9. 「次に作りたそうなシステム」を提案できる

以下を関連Contextとして利用する。

- 技術経験
- 使用ツール
- 繰り返し発生する困りごと
- 過去の開発相談
- 作成済みシステム
- 未完了アイデア
- Decision / Result
- Personal Inference
- User Raw Context

固定アイデアの条件分岐だけではなく、新しい候補を生成できること。

## 10. 計画へ落とし込む

必要に応じて、Recommendationから具体的なAction Planへ進める。

## 11. 不足情報は必要最小限だけ確認する

既知情報を再質問しない。仮定可能なら仮定を明示して進める。

## 12. 根拠を説明できる

Recommendationについて、Current、Decision/Result、Inference、Raw Evidenceのどれを使ったか確認できること。

## 13. 根拠不足なら無理にPersonalizeしない

Personal Evidenceが弱い場合は一般提案とPersonalized部分を区別する。

## 14. RecommendationをFact / Decisionにしない

AIの提案だけではDecisionにならない。本人の明示選択を必要とする。

## 15. Resultを次回へ反映する

実費、満足、不満、予想との差、次回改善点等を次の類似判断へ利用する。

## 16. Consultation Cycle

相談の回答は `response_type`（`answer_only` / `recommendation` / `planning` / `decision_review`）を持ち、推薦が必要な場合だけRecommendation Candidateを返す。Candidateが出ただけではCanonical Decisionにしない。

ユーザー操作は、`recommended → planned → decided → executed → result → evaluated` の順に進む。RecommendationからPlan、PlanからDecision候補、本人確認後のDecision確定、実行記録、Result、Later Evaluationをそれぞれ明示操作で行う。Backendは`cycle_stage`と`available_actions`を返し、不正な状態遷移を拒否する。

ResultとLater Evaluationは次回の同Domain RetrievalでRelevant Resultとして参照し、回答の根拠に過去結果が利用されたことを確認できるようにする。
