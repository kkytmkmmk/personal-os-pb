# Visualization 要件

## 1. 目的

可視化は、

- 今どうなっているか
- 何が変わったか
- 何を選んだか
- 結果どうだったか
- 自分の情報がどのように蓄積・関連しているか

を文章より速く理解できる場合に利用する。

可視化には、意思決定を助ける**実用的可視化**と、蓄積されたPersonal Contextを眺めて探索する**遊び的可視化**の両方を含める。

遊び的可視化はCore Decision Engineではなく、Personal OSを使い続ける楽しさ・探索性・自己理解を高める補助機能として扱う。

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
- 異なる単位の指標を根拠なく合成した「総合偏差値」

## 9. Evidenceへ遡れる

グラフの重要点から、その値のFact / Decision / Raw Evidenceへ必要時に掘り下げられることが望ましい。

## 10. Adaptive Today / Domain表示

Todayでは、Current StateやChangeを文章より速く理解できる場合にCardやTimelineを使用してよい。Todayの主Action数、補助候補、表示順の詳細は `12_daily_action_review_inbox_requirements.md` を正本とする。主Action以外の補助候補は、同要件に従って主導線を圧迫しない範囲で表示できる。PCではCurrentとContextを並列表示し、iPhoneでは1列・折りたたみContextとする。資産・旅行・住居・人間関係・判断の各画面もSummary → Current → Change/Decision → History → Evidenceの順で深掘りできること。

---

# 3D Personal Space / Information Universe

## 11. 位置づけ

Personal OSに蓄積された情報を3次元空間へ配置し、**「自分の情報宇宙を眺める」**ための探索画面を提供したい。

仮称:

- Personal Space
- Memory Space
- Personal Universe
- Personal Graph

名称は実装時に調整してよい。

この機能は分析結果を厳密な数値として提示することよりも、

- データが蓄積されていく感覚
- 自分の関心や生活領域の広がり
- Decision / Result / Fact等のつながり
- 過去と現在の情報の距離感

を直感的かつ楽しく探索できることを重視する。

主要な相談・記録・判断導線を複雑にしない独立したSecondary Experienceとする。

## 12. Navigation

3D Personal SpaceをPrimary Navigationへ必須追加しない。

初期案では、PC/iPhoneとも「その他 / 探索」配下の**可視化**から開ける独立ページとする。

Domain画面、Decision画面、検索結果等から、対象Nodeを中心にPersonal Spaceを開けるDeep Linkを将来的に許容する。

## 13. 表示対象

初期実装の主要Node候補:

- Fact
- Decision
- Recommendation
- Plan
- Result

将来的な候補:

- Entry / Raw Source
- Evidence
- Person
- Travel / Place
- Attachment
- Conversation-derived memory
- Personal Inference
- External Context

全件表示を要件にしない。大量データでは代表Node、Current、重要Decision、検索近傍等に制限してよい。

## 14. Domain Color Palette

Domainは一貫した色で表す。

初期Palette案:

| Domain | 色名 | HEX |
|---|---|---|
| finance / money | Emerald | `#22C55E` |
| travel | Sky Blue | `#38BDF8` |
| housing | Amber | `#F59E0B` |
| relationship / people | Rose | `#F472B6` |
| work | Indigo | `#6366F1` |
| health | Coral Red | `#EF4444` |
| life | Yellow | `#EAB308` |
| learning | Teal | `#14B8A6` |
| hobby | Violet | `#A855F7` |
| food | Lime | `#84CC16` |
| shopping | Copper | `#C2410C` |
| other | Slate | `#94A3B8` |

色だけで意味を伝えない。Shape、Label、Icon、Opacity等を併用し、色覚特性に依存しすぎないこと。

Theme変更時もDomain間の識別性を維持する。

## 15. Object Type Encoding

DomainはColor、情報種別はShape等の別Encodingで区別する。

初期案:

| Object | Visual案 |
|---|---|
| Fact | Sphere |
| Decision | Diamond / Octahedron |
| Recommendation | Ring / Outlined Node |
| Plan | Cube |
| Result | Filled Node + Result marker |
| Personal Inference | Semi-transparent Node |

3Dライブラリやアクセシビリティ上の制約により簡略化してよい。

## 16. Node Size

Node Sizeには説明可能な意味を持たせる。

候補:

- Evidence数
- 関連Node数 / connectivity
- 参照回数
- Decision / Resultとの接続数
- ユーザーが明示した重要度

初期実装ではEvidence数またはConnectivityを優先する。

AIが推測した「人生にとっての重要度」をNode Sizeとして断定しない。

## 17. Brightness / Opacity / Glow

補助表現の初期案:

- **Brightness**: 新しさ / Current性
- **Opacity**: Historical / superseded / provisional等
- **Glow**: recently added / active Decision / unresolved / Result missing / search hit

Glowを大量に常時表示せず、注目Nodeや最近変化したNodeを中心に使う。

## 18. Spatial Layout

位置は完全Randomにしない。

初期実装は**Category Cluster + Local Relationship**を推奨する。

```text
Domain Anchor
   ↓
Category Cluster
   ↓
Cluster内部で関係性・時間・接続を反映
```

例えばfinance / travel / housing / relationship等の大きなClusterを作り、その内部にNodeを配置する。

## 19. Stable Layout

同じ情報を開くたびにNode位置が大きく変わらないことが望ましい。

- stable IDから初期seedを生成する
- Domain Anchorを固定する
- Layout Algorithm versionを管理する

等により、ユーザーが「この辺に旅行情報がある」のような空間認知を持てることを目指す。

Layout Algorithmを大きく変更した場合は再配置してよい。

## 20. Semantic Layoutの将来拡張

将来的にはEmbedding等を利用し、意味的に近い情報を近距離へ配置してよい。

ただし、3次元上の近さを因果関係や確定した心理構造として解釈しない。

次元削減方式を利用する場合も、表示上は「意味的な類似に基づく配置」であることを説明可能にする。

## 21. Edge

関連情報をEdgeで結ぶ。

主なRelation候補:

- Fact → Evidence
- Fact → related Fact
- Recommendation → Plan
- Plan → Decision
- Decision → Execution
- Decision → Result
- Person → Event / Memory
- Travel Plan → Travel Result
- Personal Inference → Supporting User Evidence

全Edgeを常時表示しない。

Defaultでは弱く表示または非表示とし、選択Nodeの近傍、検索結果、Lifecycle等を必要時に強調する。

## 22. Edge Style

Relation Typeを色だけでなく線種・太さでも区別できること。

例:

- general relation: thin neutral
- support evidence: solid
- contradiction: dashed
- Decision lifecycle: stronger line
- selected path: highlight

「緑=良い / 赤=悪い」の単純な価値判断にはしない。

## 23. Interaction

PCでは最低限以下を行えること。

- rotate
- zoom
- pan
- node select
- node focus
- search
- domain filter
- object type filter
- time range filter
- current / history filter
- edge on/off

Node選択時はSide Panel等で概要を表示し、必要時に通常のFact / Decision / Evidence画面へ遷移できること。

## 24. Explore Mode

探索Preset候補:

- 最近追加
- 今月
- Current Facts
- Decisions
- Results
- 旅行
- 資産
- 人間関係
- このNodeの近傍
- ResultがまだないDecision

Presetは固定分析結果ではなく表示フィルタとして扱う。

## 25. Animation

遊び要素として、

- slow floating
- smooth cluster transition
- focus animation
- fade
- optional auto rotate

等を利用してよい。

Animationは停止できることが望ましく、`prefers-reduced-motion` 等を考慮する。

## 26. Sensitive Information

3D空間にセンシティブな本文や具体値を無条件表示しない。

特に、

- health
- relationship
- detailed financial values
- private notes

はDefault Labelを抽象化できること。

例:

- 「健康情報」
- 「資産Fact」
- 「人物メモ」

詳細はNode選択後に段階的に表示する。

## 27. Mobile

3D Personal SpaceはPCをPrimary Experienceとする。

iPhoneでは負荷に応じ、

- Node上限
- Edge上限
- Label省略
- animation削減
- simplified rendering / 2.5D

を許容する。

スマホでも最低限、閲覧、Node選択、Search、Filter、通常画面への遷移が可能であることが望ましい。

## 28. Accessibility / Fallback

3D表示だけを唯一の情報アクセス方法にしない。

同じ対象を、検索結果・一覧・Timeline等からも確認できること。

KeyboardだけでもFilterや選択対象一覧へアクセスできる代替UIを持つことが望ましい。

## 29. Performance

3D可視化によって通常のPersonal OS操作を重くしない。

必要に応じて、

- top-N selection
- clustering
- level of detail
- lazy expansion
- GPU capability detection
- animation reduction

を利用する。

全Memoryを一括描画することをDone条件にしない。

## 30. 3D可視化の初期Acceptance

PrototypeをDoneにする最低条件:

- 少なくともFact / Decision / Resultを区別して表示できる
- Domain Colorが一貫している
- Node選択から元情報へ遡れる
- SearchまたはDomain Filterが使える
- Node位置がReloadごとに完全Randomにならない
- Current / Historicalを視覚的に区別できる
- センシティブな具体値をDefault Labelへ露出しない
- 3D非対応・低性能環境でも通常のPersonal OS機能を利用できる

「3D Canvasが表示されるだけ」ではDoneにしない。
