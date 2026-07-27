# Population Benchmark / 世間比較 要件

## 1. 目的

Personal OSに保持している本人のCurrent / Historyと、公開統計・信頼できる調査による**Population Benchmark**を比較し、

**「自分が比較可能な集団とどの程度違うか」**

を直感的に理解できる可視化ページを提供したい。

この機能は、

- 優劣判定
- 正常 / 異常判定
- 人格評価
- 平均への同調を促すこと

を目的としない。

Population Benchmarkは意思決定のためのReferenceであり、目標値そのものではない。

## 2. 独立した比較ページ

独立したSecondary Pageとして**比較 / Benchmark**画面を提供する。

Primary Navigationへの常設は必須とせず、初期案では「その他 / 探索」配下から開く。

資産、住居、仕事等の各Domainから関連BenchmarkへDeep Linkできることが望ましい。

## 3. 表示したいこと

Benchmark Pageでは最低限、

- 自分の値
- 比較対象集団
- 平均 / 中央値等のReference
- 絶対差
- 比率 / 乖離率
- Reference period
- Source
- 更新日時
- 比較定義の一致度

を確認できること。

## 4. 「世間平均」を単一値として扱わない

全国全年齢の平均だけを「世間」とみなさない。

利用可能な統計Dimensionと本人の明示的Current Factを使い、可能な範囲で近いPopulation Segmentを選択する。

候補Dimension:

- age band
- household type
- household size
- employment status
- industry / occupation
- region
- worker / non-worker
- individual / household

本人について存在しない属性をAI推測で補完しない。

## 5. 比較指標候補

取得でき、定義を合わせられるものから段階的に対応する。

### Finance / Household

- annual income / salary
- financial assets
- savings
- liabilities
- household expenditure
- category expenditure
- housing expenditure
- savings-related indicators where definition is clear

### Work

- annual salary
- working hours
- paid leave granted
- paid leave taken
- paid leave utilization rate

### Life

- sleep time
- work time
- leisure time
- exercise / activity time where suitable statistics exist

### Housing

- rent / housing expenditure where definitions are compatible
- housing-related burden indicators where suitable public statistics exist

### Other

信頼できるPopulation Statisticsがあり、Personal Metricとの定義を一致させられるものを追加してよい。

## 6. Source Priority

Benchmark Sourceは以下を優先する。

1. Government official statistics
2. Public / quasi-public statistical institutions
3. Major research institutions with documented methodology
4. Other sources only when必要性とMethodologyを確認できる場合

出典不明のWeb記事、ランキング記事、SEO記事等の数値をBenchmark DBへ自動採用しない。

## 7. 初期Source候補

初期実装で調査・Adapter対象とする候補:

### e-Stat / 総務省統計局

- 家計調査
- 家計調査（貯蓄・負債編）
- 社会生活基本調査
- その他、比較に利用できる政府統計

機械判読可能なAPI / CSV / 統計表を優先する。

e-Stat API等で取得できる場合は、手作業でWebページをScrapeするより公式Machine-readable sourceを優先する。

### 国税庁

- 民間給与実態統計調査
- 給与水準・分布に関する公開統計

### J-FLEC

- 家計の金融行動に関する世論調査
- 金融資産、金融行動等の公開集計

### 厚生労働省 / e-Stat

- 就労条件総合調査等
- 労働時間、有給休暇等の公開統計

Source追加は、実際の公開形式、利用条件、定義、更新頻度を確認した上で行う。

## 8. 取得方式

Sourceごとに以下のいずれかを利用できる。

- official REST API
- official CSV / JSON / XML
- official XLSX等のDownload
- manual import of official published data

HTML Scrapingは、安定したMachine-readable Sourceがない場合のFallbackとし、サイト構造変更で壊れやすいことを考慮する。

## 9. Benchmark DataはLocal DBへ保存する

外部統計は画面表示のたびにWebへ取得しない。

取得したBenchmark DataはPersonal OSのLocal DBへReference Dataとして保存し、比較・可視化・履歴表示に利用する。

```text
Public Statistics
      ↓
Validate / Normalize
      ↓
Benchmark Reference Store
      ↓
Local Comparison
```

Population Benchmarkを本人のFactとして保存しない。

## 10. Personal DataとBenchmark Dataを分離する

Conceptually、以下を別Data Domainとして扱う。

```text
Personal Context
  Fact / Decision / Result / Raw

Population Reference
  Source / Series / Observation / Distribution
```

Benchmark値がPersonal Fact RetrievalのCurrentを上書きしないこと。

## 11. 必要なBenchmark Metadata

実装Schema名は設計事項だが、少なくとも以下を保持できること。

### Source

- source name
- publisher
- source URL / identifier
- methodology / notes
- source type
- retrieval mode
- expected update frequency
- last checked at
- last successful update at
- usage / attribution notes where necessary

### Series

- metric key / name
- domain
- unit
- statistic type
- definition
- population scope
- segment dimensions
- geography
- frequency

### Observation

- reference period
- published at
- value
- statistic type
- segment values
- sample size where available
- revision / version
- imported at
- provenance
- source raw reference / checksum where useful

### Refresh Run

- source
- started / finished
- result
- new / revised observations count
- failure reason
- parser / adapter version

## 12. Statistic Typeを区別する

以下を混同しない。

- mean
- median
- percentile
- proportion
- count
- distribution
- index

UIにも「平均」「中央値」「分布」等を明示する。

## 13. MeanとMedian

平均と中央値の両方が利用可能な場合、可能であれば両方表示する。

金融資産、所得等の偏りが大きい可能性がある指標について、平均だけを代表値として扱わない。

中央値がSourceにない場合、勝手に生成しない。

## 14. Definition Matching

Personal MetricとBenchmark Metricの定義を比較前に照合する。

混同してはいけない例:

- individual vs household
- gross vs net
- annual vs monthly
- current balance vs annual flow
- financial assets vs total assets
- savings vs assets
- consumption expenditure vs total spending
- rent vs housing expenditure
- employee salary vs household income
- nominal vs real

定義が一致しない場合は比較を拒否するか、**参考比較**であることを明示する。

## 15. Comparison Compatibility

比較ごとに内部的なCompatibilityを持つことが望ましい。

例:

- `exact` — 定義・単位・対象が一致
- `comparable` — 小さな差異があるが合理的に比較可能
- `reference_only` — 大まかな参考に限定
- `incompatible` — 比較しない

通常UIでは技術語をそのまま出さず、

- 同条件に近い統計
- 参考値
- 比較できません

等で表現してよい。

## 16. Cohort Matching

本人のCurrent FactとBenchmark DimensionをLocal側でMatchingする。

例:

```text
明示的な年齢帯
+
世帯形態
+
雇用状態
↓
利用可能な最も近いPopulation Segment
```

最も細かいSegmentが常に最善とは限らない。Sample SizeやSource Qualityも考慮する。

本人の属性を外部サービスへ送ってSegmentを検索する方式をDefaultにしない。

## 17. Fallback Segment

完全一致Segmentがない場合、段階的にDimensionを緩めてよい。

例:

```text
年齢 + 世帯形態 + 雇用
↓ unavailable
年齢 + 世帯形態
↓ unavailable
世帯形態
↓ unavailable
全国
```

どのSegmentを採用したかUIから確認可能にする。

## 18. Difference Calculation

最低限以下を算出可能にする。

### Absolute Difference

```text
personal - benchmark
```

### Ratio

```text
personal / benchmark
```

### Percentage Difference

```text
(personal - benchmark) / benchmark
```

Benchmarkが0等で不適切な場合は比率計算を行わない。

## 19. Percentile

Source DataとしてPercentileまたはDistributionが存在する場合、Population内の位置を表示してよい。

例:

- 上位20%相当
- 中央付近

ただし平均値だけからPercentileを推定しない。

## 20. Standardized Score

MeanとStandard Deviationが適切に提供され、Distribution上の解釈が妥当な場合のみ、Z-score等を内部利用してよい。

Standard Deviationがない状態で正規分布を仮定し、見かけ上のPercentileや偏差値を生成しない。

## 21. Benchmark Page UI

Benchmark PageはDomain横断Summaryと個別指標を持つ。

初期案:

```text
比較 / Benchmark

[資産] [仕事] [生活] [住居]

年間給与
あなた            Reference
────●────────|────────
                中央 / 平均

差: +xx%
対象: ○○歳代・給与所得者
基準年: YYYY
Source: ○○
```

実値は実際のData Definitionに合わせる。

## 22. Distribution優先

Distribution Dataが取得できる場合、単純な平均棒グラフより、Population Distribution上にPersonal Markerを置く表現を優先する。

```text
低い ───── median ───────── 高い
                         ▲ you
```

平均 / 中央値だけしかない場合は、それらとの比較を表示する。

## 23. Divergence Visualization

乖離状況を、

- Difference
- Ratio
- Percentage Difference
- Percentile where supported

で表示する。

Domain横断Summaryでは、異なる単位の指標をそのまま足し合わせない。

Distributionがある指標についてNormalized Positionを並べることは可能だが、根拠の弱い総合スコアへ合成しない。

## 24. Neutral Language

Benchmarkは価値判断ではない。

推奨:

- 「同条件平均より23%高い」
- 「中央値より低い位置」
- 「比較対象は単身世帯・○○年代」

避ける:

- 「優秀です」
- 「平均以下なので危険です」
- 「正常 / 異常です」
- 「この数値に近づくべきです」

指標によって高い / 低いの望ましさが逆になるため、自動的にGood / Bad Colorへ変換しない。

## 25. Time Series

Personal HistoryとBenchmark Historyが双方存在する場合、同じTime Axisで比較できることが望ましい。

これにより、

- 自分だけが変わったのか
- 社会側の基準も変化したのか

を分けて見られる。

## 26. Historical Benchmarkを保持する

新しい統計を取得しても、過去Reference Periodを削除しない。

```text
2024 benchmark
2025 benchmark
2026 benchmark
```

のように履歴を保持する。

同じReference Periodの修正版についてもRevisionを追跡可能にする。

## 27. Freshness

Benchmark Dataには最低限、

- reference period
- published at
- last checked
- last successful update

を持たせる。

UIでは必要に応じて、

- 最新
- 更新確認待ち
- 古いReference

等を表示する。

## 28. Refresh Policy

SourceごとにExpected Update Frequencyを持つ。

例:

- monthly
- quarterly
- yearly
- several years
- manual / irregular

全Sourceを毎日取得しない。

元統計の公表頻度に合わせ、必要な時だけ更新確認する。

## 29. Refresh Trigger

以下を組み合わせてよい。

- 管理画面の「Benchmarkを更新」
- アプリ起動時のDue Check
- Background Job while app is running
- 将来の明示的Scheduled Job

更新がDueでも、通常のToday / Consultation表示をBlockしない。

## 30. Update Pipeline

```text
Source due?
↓
Check official source
↓
New / revised publication?
↓
Fetch
↓
Parse
↓
Schema / definition validation
↓
Store new observation
↓
Recalculate local comparison
```

Format変更やDefinition変更が検出された場合、既存Referenceを壊さずReview対象にする。

## 31. Update Failure

外部Sourceの取得に失敗しても既存Benchmark Dataを削除しない。

```text
Refresh failed
↓
Last valid reference remains available
```

Failure reasonとLast successful updateを確認可能にする。

## 32. Methodology Change

統計の分類、母集団、調査方法、項目定義が変わる可能性を考慮する。

Definition / Metadataが変わった場合、同一Seriesとして無条件に継続しない。

必要ならSeries versionを分ける。

## 33. No Personal Data Outbound

Benchmark更新は原則、

```text
Public Source
→ Personal OS
```

の一方向取得とする。

外部Sourceへ本人の、

- 資産
- 年収
- 年齢
- 健康
- 人間関係
- Personal Inference

等を送信して「似た人の統計」を問い合わせない。

Population Segmentの選択はLocal側で行う。

## 34. Benchmark RetrievalとPersonal Retrievalの分離

Benchmark Referenceは通常のPersonal Fact Retrievalへ自動混入させない。

相談に有効な場合のみ、

```text
Personal Context
+
Population Reference Context
```

として区別してReasoningへ渡す。

## 35. Recommendation利用

BenchmarkをRecommendation Contextとして利用してよい。

ただし、

```text
Population average
=
ユーザーが目指すべき値
```

とは解釈しない。

例:

「支出を減らした方がいい？」

に対して、本人の支出推移、Current Constraints、Decision / ResultをPrimary Contextとし、Population BenchmarkはReferenceとして補助する。

## 36. Source Quality / Provenance

すべてのBenchmark表示から、必要時に以下へ遡れること。

- publisher
- source / dataset
- reference period
- statistic type
- target population
- definition
- published date
- retrieved date
- source URL / identifier

Source Qualityを内部的に管理してよい。

例:

- official
- quasi_official
- research
- other

通常表示では公的・高品質Sourceを優先する。

## 37. Source Adapterの責務

各Source Adapterは、

- retrieve
- parse
- normalize
- provenance
- definition/version detection

までを担当する。

「Webページから数字らしいものを拾ってDBへ入れる」だけの実装にしない。

## 38. Initial Implementation Priority

初期実装では、すべてのBenchmark Domainを一度に実装しない。

Priority案:

1. 年間給与 / 所得関連
2. 金融資産 / 貯蓄関連
3. 家計支出
4. 労働時間 / 有給
5. 生活時間
6. Housing比較可能指標

実装しやすさより、Personal Metricと定義を安全に一致させられることを優先する。

## 39. Initial Acceptance

Benchmark機能をDoneとする最低条件:

- 少なくとも2つ以上の異なるMetricでOfficial Sourceを取得または正式Importできる
- Benchmark DataがLocal DBへ保存される
- Source / Reference Period / Statistic Typeへ遡れる
- 同じ統計を毎画面Web取得しない
- Personal MetricとBenchmark Definitionを照合する
- 平均と中央値を区別する
- Comparison Segmentを表示する
- Difference / Ratioの少なくとも一方を正しく表示する
- 外部取得失敗時もLast valid Benchmarkが残る
- 新しいReference Periodを追加しても過去値を保持する
- BenchmarkをPersonal Factとして保存しない
- 外部SourceへPersonal Contextを送信しない
- Mobileでも主要比較を読める

「平均値を1個ハードコードして表示するだけ」ではDoneにしない。
