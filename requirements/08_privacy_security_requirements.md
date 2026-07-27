# プライバシー / セキュリティ要件

## 1. Local First

現時点ではPersonal OSデータをローカル環境で保持することを基本とする。

個人情報を外部サービスへ送信することを前提にしない。

## 2. 外部AIへ勝手に送信しない

ローカル解析失敗やAPI Key存在を理由に、OpenAIやGemini等へ自動送信しない。

外部AIへ送信する場合はユーザーが許可した範囲だけに限定する。

特に、ChatGPT全履歴、人間関係、健康、スクリーンショット、資産、給与は慎重に扱う。

## 3. Providerの自動選択もLocal Firstに従う

`auto` 相当の自動Provider選択では、利用可能なLocal処理を優先する。

Cloud Providerは明示選択、または用途別Fallback許可がある場合のみ利用する。

## 4. 必要以上の外部送信を避ける

外部AI利用時も目的に必要なContextだけを送信する。

Personal OS全履歴を個別相談のために無条件送信しない。

## 5. センシティブ情報の推測を抑制する

健康・人間関係等についてAI推測を本人Factとして固定しない。

健康では症状、処方薬、受診、検査結果、医師から明示された診断等の明示情報を中心に扱う。

人物では性格分析、好感度、恋愛進展度、心理状態等を恒久Factとして保存しない。

## 6. AI自己汚染を防ぐ

Assistantが生成した推測・要約・人物像をユーザー本人のEvidenceとして再利用し、人格推定を自己強化しない。

## 7. 原文と派生データの関係を追跡する

Fact削除・修正時もRawが残る場合があるため、削除単位を区別できる構造を持つ。

想定単位:

- Factのみ
- Evidenceのみ
- 添付画像
- Raw
- 特定人物に関する関連データ
- すべての関連データ

## 8. データ削除仕様を明確化する

「AIの記憶から外す」「Rawを物理削除する」「Backupからも消す」は別操作として意味を区別する。

削除UI・保持期間・Backup反映は実装前に詳細仕様を定義する。

## 9. 日常画面でセンシティブ情報を過剰表示しない

Home等で必要以上に露出しない。

## 10. LAN利用でも認証を考慮する

資産、健康、人間関係、Gmail、Photos等を扱う段階では、同一LANでも無認証アクセスを前提にしない。

Local Authentication / Session管理を導入できる構造とする。

## 11. Secret管理

API Key、OAuth Token等をソース、通常ログ、共有Backupへ平文混入させない。

## 12. External Integration前のSecurity Gate

Gmail、Photos、金融データ等を本格連携する前に少なくとも以下を確認する。

- Authentication
- Session management
- CSRF等のWeb保護
- Secret保護
- DB / Attachment / Backupアクセス保護
- External send control
- Export / Delete

## 13. 外部公開は現時点の対象外

Internet公開・Cloud常時稼働・外出先アクセスは現段階の主要要件ではない。

公開する場合は認証、認可、通信暗号化、保存時暗号化、Secret管理、Session管理、外部API送信制御、監査ログを別途必須化する。

## 15. 日常UIの送信確認

Local Firstの通常動作では外部送信を行わない。外部AIによる深い解析をユーザーが選択した場合も、最初の操作はPreviewに留め、確認後に最小限のContextだけを送信する。送信対象と結果のProvider/モデル/時刻を後から監査できること。

## 14. TBD

- Local DB暗号化要否
- 添付画像暗号化要否
- 完全削除の定義
- Backupからの削除ポリシー
- 認証方式
