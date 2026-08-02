# UI / UX 要件

## 1. Personal OSを管理している感覚を減らす

ユーザーが意識する主操作は、

- 今を見る
- 相談する
- 記録する
- 提案を見る
- 判断する

とする。

Fact、Evidence、解析Job、Provider、Prompt version等は通常ナビの中心に置かない。

## 2. 起動直後は「今の自分」と次の候補

Current State、最近の変化、Decision中のこと、次の旅行等を簡潔に表示する。

## 3. 相談を主要入口にする

多数の画面を巡回しなくても自然文で情報検索・提案・計画ができること。

## 4. 入力を軽くする

自然文、スクリーンショット、コピー&ペースト、Importを中心とし、分類フォームを要求しない。

## 5. 入力後に待たせない

Rawを先に保存し、AI解析は後続処理とする。

## 6. AI処理状態は簡潔にする

通常画面では未解析、解析中、解析済み、要確認程度でよい。詳細は管理へ分離する。

## 7. 人間確認を割り込ませすぎない

自動解決可能なら自動処理、後で解決可能なら保留、重要かつ解決不能なものだけ確認する。

## 8. 情報は段階的に開示する

```text
現在値
↓
履歴
↓
Evidence
↓
原文
```

のように必要時だけ深掘りできること。

## 9. 提案理由は必要時に確認できる

最初からEvidence一覧を見せず、理由→根拠→原文へ段階的に開ける。

## 10. 信頼度を過度に意識させない

通常UIに数値confidenceを常時表示しない。重要な暫定・矛盾のみ簡潔に示す。

## 11. 相談 → 提案 → 計画 → 判断 → 実行 → 結果を自然につなぐ

内部Workflow名ではなく、ユーザーの行動に沿った言葉で現在位置が分かること。

## 12. 既知情報を再入力させない

出発地、家賃、資産、過去旅行等を再質問しない。

## 13. PC / iPhone対応

スマホでは相談、メモ、スクショ、Current確認、提案確認を少ない操作で行えること。

## 14. エラーで入力を失わない

OCR/LLM失敗でもRawは保持し再解析可能にする。

## 15. AI抽出の誤りを修正できる

修正前、修正内容、現在採用値、元Evidenceを追跡できること。

## 16. 日常画面と管理画面を明確に分離する

日常の主要ナビは原則:

- 今日
- 相談
- 記憶
- 資産
- 旅行
- 住居
- 人間関係
- 判断

管理系:

- 取込
- AI設定
- 解析状況
- 記憶品質
- バックアップ
- データメンテナンス
- カテゴリー等の詳細設定

チェックイン・質問セットを主要ナビにしない。

## 17. UIは日本語を基本とする

内部識別子は英語でよい。

## 18. グラフィカル表示は「理解を速くする」ために使う

装飾ではなく、Current / Change / History / Decisionを理解しやすくする場合に利用する。

主要候補:

- Current Stateカード
- Life Timeline
- Asset Timeline
- Travel Map
- Decision Flow
- Personal Change

性格レーダーチャート、好感度スコア等、根拠の弱い人格可視化は行わない。

## 最終原則

**「入力させる」「管理させる」「確認させる」を減らし、「見る」「相談する」「提案を受ける」「判断する」を中心にする。**

## UI/UX vNext 正本（2026-07-26）

本節はPC/iPhoneのAdaptive UIに関する現行正本とする。既存の管理・取込・品質監査機能は削除せず、日常導線から分離して管理メニューへ置く。

### 日常導線

通常利用の中心を `今日 → 相談 → 記録 → 提案 → 計画 → 判断 → 結果` とする。Todayの具体的な構成、主Action、補助候補の扱いは `12_daily_action_review_inbox_requirements.md` を正本とする。Fact一覧、Provider、解析設定、監査メタデータ、詳細Decision入力は管理・詳細画面へ移す。

### Adaptive navigation

PCのPrimary navigationは「今日・相談・記憶・資産・旅行・住居・人間関係・判断」の一つだけを表示し、取込・AI設定・解析状況・品質監査・バックアップ等は「管理」に分離する。iPhoneは横スクロールの主要ナビを使わず、画面下部固定の「今日・相談・＋・判断・その他」とする。「＋」はメモ、スクリーンショット、判断、相談のBottom Sheetを開く。

### Progressive disclosure / input

通常表示は結論・Current値・重要な理由とし、根拠・原文・Fact ID・confidence・Extractor・Model・Prompt versionは「根拠を見る」「詳細」の下に隠す。メモ・相談・判断はcategory/kind/tagを必須にせず自然文を受け、未送信DraftをsessionStorage等に保持する。日常フローのprompt/confirm/alertはModal/Bottom Sheetまたは画面内Statusへ置き換える。

### PC / iPhone acceptance

PC（1280x720/1440x900）はCurrentとNext/Contextを2列で確認でき、iPhone（390x844/375x667）は1列、44px以上の操作領域、safe-area、body横スクロールなし、キーボード表示中も送信可能であること。相談画面はPCでは回答70%/Context30%、iPhoneでは回答を優先しContextを折りたたむ。

### 外部解析の明示

Local Firstの通常相談と、ユーザーが明示的に押す「ChatGPTで深く解析」を区別する。外部送信はPreviewと確認後だけ行い、最小Context・送信先・モデル・送信対象を表示し、結果はFactへ直接確定せずExternal Reasoning/Recommendation候補として監査可能にする。

## 探索・比較のSecondary Page（2026-07-27 vNext）

3D Personal SpaceとPopulation Benchmarkは、Today / 相談 / 記憶 / 判断のPrimary Flowを阻害しないSecondary Experienceとして扱う。

## Today / Review Inboxとの境界（2026-08-02）

日常画面と管理画面の分離、Progressive Disclosure、Mobile/PC対応、Draft保護、入力喪失防止、内部値を通常表示しないこと、Today・記録・相談中心は本書の横断原則とする。Today Action Centerと確認Inboxに固有の構造・優先順位・状態は `12_daily_action_review_inbox_requirements.md` を正本とし、本書へ全文重複させない。

初期Navigation案:

```text
その他 / 探索
├ 可視化（Personal Space）
└ 比較（Benchmark）
```

PCでは3D探索やDistribution表示等の情報量を活かし、iPhoneでは要約、Filter、Node選択、Personal Marker等を優先して簡略化する。

Benchmark Pageでは「自分」「比較対象」「Reference period」「Source」「乖離」を同じ視界で理解できること。平均・中央値・Percentile等のStatistic Typeを混同せず、Good / Badの価値判断色を自動付与しない。

3D Personal Spaceでは遊び要素を許容するが、センシティブ本文や具体的金融値をCanvas上へ無条件表示しない。3Dが利用できない環境でも通常の検索・一覧・Domain UIから同じ情報へアクセスできること。
