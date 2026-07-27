# Personal OS Vision

## 1. 目的

Personal OSは、

**「これまでの自分」と「今の自分」を正しく理解したうえで、次にどうするかをAIと一緒に考えるための自分専用OS**

とする。

単なるメモ帳、日記、家計簿、プロフィール管理、ChatGPTクローンにはしない。

## 2. Personal Context Engine

Personal OSが長期的に保持する価値の中心はAIモデルではなく、ユーザー自身のContextである。

主なContext:

- Raw Evidence / 原文
- 現在状態
- 過去状態
- 行動履歴
- Decision
- 判断理由
- Execution
- Result
- 明示された好み・希望
- Evidenceから再評価可能なPersonal Inference

AIモデルは、このContextを利用する交換可能なReasoning Engineとする。

## 3. 中核サイクル

```text
Evidence / Raw Source
        ↓
Fact / Current State
        ↓
Relevant Context Retrieval
        ↓
Personal Inference
        ↓
Recommendation
        ↓
Planning
        ↓
Decision
        ↓
Execution
        ↓
Result
        ↓
Memory / Re-evaluation
```

つまり、

**記憶 → 理解 → 推論 → 提案 → 計画 → 判断 → 実行 → 結果 → 記憶**

を中核サイクルとする。

## 4. 最重要原則

データ量を増やすこと自体を目的にしない。

蓄積したデータにより、

- 次の旅行
- 次の買い物
- 次の住居
- 次の資産判断
- 次に作るシステム
- 休日の使い方
- その他の具体的な意思決定

の質を上げることを目的とする。

## 5. ChatGPT Memoryとの差

Personal OSは「この人はこういう人」という短いプロフィールだけでなく、

**Current State + Life History + Decisions + Results + Raw Context + Evidence**

を保持する。

例えば「温泉が好き」というFactだけでなく、どの旅行で温泉を選び、いくら払い、結果どう評価したかまで必要に応じて参照できることを重視する。

## 6. 長期ビジョン: Digital Twin / Personal Model

将来的には、ユーザーの口調を真似することではなく、

**Evidence・選択・結果から「今の自分ならどう考えるか」を高精度に再構成するPersonal Model**

へ発展できることを目指す。

ただし、AIが一度推測した人格を自己参照して強化する構造は禁止する。

Personal Modelは常にユーザー本人のEvidenceへ遡れ、再評価・失効可能であること。

## 7. 最終的なユーザー体験

ユーザーはPersonal OSを細かく管理しない。

普通に、

- 相談する
- メモする
- スクリーンショットを貼る
- 旅行する
- 買い物する
- 投資する
- 人と会う
- 何かを作る

ことでContextが自然に蓄積される。

そして、

> 今の俺ならどうする？

> 次の3連休どうする？

> 次に何を作ると自分に刺さりそう？

> 以前似た判断をしたとき、結果どうだった？

と聞けば、根拠のある提案・計画を返せることを目指す。

## Consultation Cycleの完走

Personal OSの価値は回答の一回性ではなく、相談から提案・計画・判断・実行・結果・後日評価までを本人の操作で完走し、その結果を次回相談へ戻すことにある。AIの推薦は候補に留め、DecisionとExecutionは本人の明示操作だけで確定する。
