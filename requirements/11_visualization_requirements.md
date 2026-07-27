# Visualization 要件

## 1. 目的

可視化は装飾ではなく、

- 今どうなっているか
- 何が変わったか
- 何を選んだか
- 結果どうだったか

を文章より速く理解できる場合に利用する。

## 2. Current State Card

Todayでは資産、住居、次の旅行、判断中事項等をカードで要約する。

## 3. Life Timeline

旅行、住居、資産、仕事、購入、Decision、Result等の重要イベントを横断的に時系列表示できることが望ましい。

Raw全件をTimelineへ並べるのではなく、重要イベントへ要約する。

## 4. Asset Timeline

資産推移と重要な投資Decision / Transactionを関連付けて見られることが望ましい。

## 5. Travel Map

行った場所、予定、候補、行きたい場所を状態を区別して地理的に確認できることが望ましい。

## 6. Decision Flow

```text
considered
→ decided
→ executed
→ result
```

の進行と未完了箇所を理解できること。

## 7. Personal Change

宿泊価格帯、旅行頻度、投資額等、十分な客観データがある指標について時系列変化を表示できること。

## 8. 不適切な可視化

以下は原則作らない。

- 根拠の弱い性格レーダーチャート
- 好感度% / 恋愛進展度%
- AI推測だけの人格スコア
- Fact confidenceを常時競わせるダッシュボード

## 9. Evidenceへ遡れる

グラフの重要点から、その値のFact / Decision / Raw Evidenceへ必要時に掘り下げられることが望ましい。

## 10. Adaptive Today / Domain表示

TodayはCurrent summary、次に考える候補（最大3件）、最近の変化、判断中/結果待ちを優先し、技術監査情報を常時表示しない。PCではCurrentとNext/Contextを並列表示し、iPhoneでは1列・折りたたみContextとする。資産・旅行・住居・人間関係・判断の各画面もSummary → Current → Change/Decision → History → Evidenceの順で深掘りできること。
