# Personal Intelligence / Personal Inference 要件

## 1. 目的

Personal OSはFactを保存するだけでなく、関連するEvidenceから、その場の判断に役立つ

- 興味
- 判断軸
- 行動傾向
- 変化
- 反復パターン

を推論できること。

## 2. Personal InferenceはFactではない

Personal Inferenceは再生成可能な仮説であり、恒久人格ラベルではない。

## 3. Evidence Source Boundary

Inferenceの主要根拠として利用できるもの:

- Confirmed Personal Fact
- User発言
- Decision
- Execution
- Result
- Userの実行Evidence
- 外部ソースから確認されたユーザー行動

Assistant発言のみを根拠にユーザーの興味・性格・嗜好を作らない。

## 4. Self-reinforcementを禁止する

```text
AI推測
→ AI文章
→ Personal Evidence
→ 次のInference
```

という自己強化ループを作らない。

過去Inferenceを利用する場合も、最終的に元User Evidenceへ遡れること。

## 5. Inference Lifecycle

Inferenceは少なくとも、

- active
- expired
- superseded
- rejected

等の状態を持てることが望ましい。

支持Evidenceがなくなった場合はactiveのまま永久保持しない。

## 6. 時間変化を扱う

「以前はこうだった」と「今もそうである」を区別する。

古いInferenceは再評価されること。

## 7. 根拠を追跡できる

Inferenceからsource Fact、Decision、Result、Rawへ遡れること。

## 8. 同一人格の再現は判断モデルを中心にする

長期的なDigital Twinでは、口調の模倣よりも、

- 何を重視するか
- どこで妥協するか
- どのリスクを嫌うか
- どの支出に満足しやすいか
- 何を作りたくなるか
- 過去の後悔をどう次へ反映するか

をEvidenceから再構成することを重視する。

## 9. 根拠が弱いInferenceを断定しない

十分なEvidenceがない場合はunknown / weak hypothesisとして扱い、Personalized Recommendationを過剰に断定しない。

## 10. Personal Inferenceの例

許容例:

> 過去数回、旅行では価格より温泉・チェックアウト時間を優先しているため、今回も同条件を重視する可能性がある。

不適切例:

> あなたは贅沢好きな性格です。
