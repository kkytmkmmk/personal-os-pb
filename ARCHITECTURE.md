# Personal OS コード構成

## Canonical rebuild layers

```text
raw entries / attachments
          |
 documents -> chunks -> fact_evidence -> facts -> fact_currentness
       |           |             |        |
       |           |             |        +--> Money / Travel / Housing / People projections
       |           |             +--> retrieval -> recommendations -> plans -> decisions -> results
       |           +--> analysis_jobs
       +--> import_jobs
 attachments -> attachment_derivatives (OCR/Vision)
```

`facts` is the canonical structured-memory write target. Legacy tables remain only for migration compatibility. Each new Fact receives an independent `fact_evidence` provenance row, and each analysis attempt is an `analysis_jobs` row keyed by provider, model, prompt version, and content hash.

完全バックアップはSQLiteだけではなく、DB・添付画像・manifest・schema migration一覧・SHA-256を一つの`.posbackup`にまとめます。原文、Fact、Evidence、DecisionはDB内、画像本体はbundle内の添付領域から復元します。

## 現状

現在の実行入口は `app.py` です。SQLite の初期化・migration、facts の正規化と時系列管理、LLM Provider、解析 Job、画像取込、HTTP API、静的ファイル配信を一つのモジュールで提供しています。`static/index.html` には画面のHTML、CSS、API呼び出し、画面更新JavaScriptがまとまっています。

この構成は初期開発とローカル実行には向いていますが、変更時の影響範囲は広めです。現時点では次の信用境界を関数・テーブル・独立モジュールで固定しています。

- `facts` を新規構造化情報の正本とし、legacyは一方向migration/旧API互換に限定
- LLM Provider選択と用途別クラウドfallback許可を分離
- `analysis_jobs` のclaim/retry/lock/priorityと`import_jobs`のcheckpointを永続化
- 添付ファイルを先に保存し、OCR結果を`attachment_derivatives`へ保持してからFact候補を生成
- Retrievalは質問のdomain/語を使い、current Fact、Decision、履歴、FTS/semantic、原文を別グループで返す
- Privacy削除はpreviewを必須導線にし、対象Fact・派生データ・物理添付を同じ操作範囲にする

## 目標構成

```text
personal_os/
  app.py                 # 起動、HTTPサーバー、worker起動だけ
  config.py              # 環境変数・設定値・パス
  db/
    connection.py        # SQLite接続、トランザクション
    schema.py             # CREATE/ALTERとschema version
    repositories.py       # entries/documents/facts/decisions
  memory/
    facts.py              # fact_key、current truth、timeline、review
    categories.py         # カテゴリ正規化
    proposals.py          # CONFIRM/NEVER_AUTO
  llm/
    provider.py           # Provider Protocolと選択
    local_ollama.py       # Ollama chat/vision/unload
    cloud.py              # OpenAI/Geminiとfallback許可
  jobs/
    analysis.py           # analysis_jobs、lock、retry、pause/resume
    backup.py             # SQLite backupと世代保持
  ingest/
    chatgpt.py            # ZIP import
    screenshots.py        # multipart、添付保存、Vision抽出
  projections/
    domains.py            # Money/Travel/Housing/People/Today
  http/
    routes.py             # API route/controller
    responses.py          # JSON/static response
static/
  index.html              # 画面のHTML/CSS
  app.js                  # 画面状態とAPIクライアント
  features/               # domainごとの画面更新
tests/
  test_memory_model.py
  test_api_contracts.py
```

## 実装済みの分離

次の2つを最初の独立モジュールとして実装しました。

- `personal_os/llm_ollama.py`: Ollamaのnative/OpenAI互換chat、Vision画像入力、GPUメモリ解放
- `personal_os/ingest.py`: multipart解析とPNG/JPEG/WebPのシグネチャ検証
- `personal_os/ocr.py`: ローカルOCR、文字量・信頼度によるOCR/Vision振り分け

`app.py`のOllama payload、multipart判定、OCR処理は上記モジュールへ分離しました。DB migration、repository相当のquery、worker、HTTP routeは既存APIを壊さず段階移行するため、現段階では`app.py`のサービス層に残しています。

分野画面の集計は複製テーブルを作らず、`domain_projection()`が確認済みcurrent fact・履歴・`finance_transactions`・`decisions`を読み取り、`summary` projectionを返します。Moneyは残高種別・総資産・月間積立・取引、Travelは訪問地・希望地・ホテル・費用・マイル、Housingは候補と家賃差額、Peopleは人物数とタイムライン件数を提供します。相談時の不足情報候補もcurrent factの有無から決定的に計算し、保存は行いません。

金融取引は`validate_transaction_candidate()`を信用境界とします。LLMの`type=transaction`だけでは登録せず、本人性・実取引性・固定enum・金額・通貨・根拠をルールで確認します。`finance_transactions`にはactor、is_actual、transaction_kind、eligibility_state、eligibility_reason、raw_amount_text、normalized_amountを保持し、判断不能な新規候補は`finance_transaction_candidates`に分離します。Moneyの共通取得処理は`auto_confirmed`/`confirmed`かつ本人・実取引の行だけを返します。既存行は起動時に再評価し、削除せず`excluded`/`pending`へ状態変更します。

## 今後の保守性改善

1. `memory/facts.py` と`db/repositories.py`を切り出し、正本Factの読み書きを一か所へ集約する。
2. `jobs/analysis.py`、`jobs/backup.py`、`ingest/chatgpt.py`を切り出し、workerとHTTP Handlerの依存をなくす。
3. `http/routes.py`を導入し、大きなroute分岐を小さなcontrollerへ移す。
4. インラインJavaScriptを`static/app.js`と機能別ファイルへ移す。

各段階で既存の`/api/*` URL、SQLite schema、`facts`のcanonicalルールを変更せず、`py_compile`、ユニットテスト、起動後のAPI smoke testを通します。

## 運用上の境界

- APIには現在認証がないため、外部公開せずLANまたはリバースプロキシの認証下で使う。
- wildcard CORSは許可せず、同一originまたは明示した`allowed_origins`だけを受け付ける。
- `GET /api/health`でDB、Job、backup、bind/CORS境界を確認する。
- 本番は8787・検証は8877に固定し、検証DBの結果を本番DBへ自動コピーしない。
- ChatGPT ZIPとJSON配列は逐次読みし、250会話ごとにcommitする。再実行は`external_id`で既取込分を再利用する。
