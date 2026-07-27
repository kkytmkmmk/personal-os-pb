# AI / 解析 要件

## 1. AI出力は候補

LLM出力を信頼境界にしない。

```text
Raw
↓
AI Candidate
↓
Evidence / Rule / Temporal / Anomaly Evaluation
↓
Adopt / Provisional / Conflict / Exclude
```

## 2. AI解析を入力完了の前提にしない

AI停止時でもRaw保存と既存Context利用を可能な範囲で継続する。

## 3. 処理を段階化する

保存、dedupe、OCR、軽量AI、本格LLMを必要に応じて使い分ける。

## 4. Lazy解析を利用する

大量Rawを最初から完全解析せず、関連性・重要度に応じて深掘りする。

## 5. Providerを交換可能にする

OpenAI、Gemini、Local LLM等を交換してもMemoryを作り直さない。

## 6. Local First

`auto` 等の自動選択では、利用可能なLocal処理を優先する。

API Keyが存在するだけでCloudへ送信しない。

## 7. 外部AIへの自動フォールバックを行わない

Local失敗時のCloud送信は、ユーザーがその用途について明示的に許可した場合のみ。

## 8. 最小必要Contextだけ送る

Cloud利用時もPersonal OS全履歴を無条件送信しない。

質問に必要なContextだけを送る。

## 9. 再解析可能にする

モデル・Prompt・ルール改善時にRawから再解析可能にする。旧解析との関係も追跡可能にする。

## 10. Fact ExtractionとPersonal Inferenceを分離する

事実抽出と「傾向・興味・判断軸」の推論を同じ確定処理にしない。

Personal Inferenceのルールは `09_personal_intelligence_requirements.md` を正本とする。

## 11. AI自己汚染を防止する

AIが生成した人物像・提案・要約を、ユーザー自身のEvidenceとして再利用して自己強化しない。

Assistant文章をPersonal Inferenceの主要Evidenceにしない。

## 12. 外部解析の明示UI

通常のLocal First相談と、ユーザーが明示的に選ぶ「ChatGPTで深く解析」を区別する。外部Providerへ送る場合は、送信前Previewで送信先・モデル・最小Context・センシティブ情報を表示し、確認操作後のみ実行する。結果はFactへ直接確定せず、Recommendation/Personal Inference候補として扱う。
