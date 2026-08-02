# 判断 / Decision 要件

## 1. 目的

Personal OSではFactだけでなく、**なぜその選択をしたか、その後実際に何をし、結果どうだったか**を長期記憶として扱う。

## 2. Lifecycle

```text
considered
→ candidate
→ decided
→ executed
→ result
→ evaluated
```

を区別する。

会話で検討しただけのものを実行済みとしない。

- `considered`: 検討を開始した
- `candidate`: 選択肢または判断候補がある
- `decided`: 本人が選択を確定した
- `executed`: 本人が実行した、または実行Evidenceが確認された
- `result`: 実行直後または結果が記録された
- `evaluated`: 一定時間後の後日評価が記録された

`lesson`、`next_time`、満足度、良かった点、後悔はLifecycle状態ではなく付随情報とする。ResultまたはEvaluationがない状態を許容し、AIが推測だけで状態を進めない。Decision ReplayもこのLifecycleを参照する。

## 3. Decisionで扱いたい情報

- 何について悩んだか
- 選択肢
- 選んだもの
- 判断理由
- 判断時点の前提
- 関連Fact
- Execution Evidence
- 実際の結果
- 満足・後悔
- Expected vs Actual
- 次回変えたいこと

## 4. 複数分野で利用する

資産、旅行、住居、人間関係、買い物、個人開発、その他を横断して利用する。

## 5. 過去Decisionを次の判断へ利用する

似た状況で、過去に何を選び、なぜ選び、結果どうだったかを関連Contextとして利用する。

## 6. Result Unknownを許容する

ExecutionやResultを確認できるEvidenceがなければ推測して埋めない。

unknownのまま保持できること。

## 7. 結果学習

良かった、普通、悪かった、自由記述等の評価を次回提案へ反映する。

## 8. 将来的な分析

満足しやすい判断、後悔しやすい判断、ExpectedとActualがずれやすい条件、繰り返し重視する判断軸等を分析できることが望ましい。

分析結果を無条件に人格Factへ固定しない。

## 9. AIは最終実行者にならない

選択肢整理、比較、提案、Planまで行えるが、最終Decision / Executionは本人が行う。

AI RecommendationだけではDecisionとして保存しない。

## 10. 買い物はDecisionとして扱う

比較候補、選択、理由、購入価格、使用後評価、後悔をResultとして次回の商品選びへ利用する。
