# 現時点の実行環境・技術制約

この文書は長期要件ではなく現在の実装制約を示す。

最終更新日: 2026-08-02

## 1. 利用環境

- Windows PC
- ローカルWebアプリ
- 同一Wi-Fi内iPhone

## 2. Data Store

現行はSQLite。長期要件として固定しない。

## 3. Local AI Hardware

- NVIDIA GeForce RTX 2070 SUPER
- VRAM 8GB

特定モデル名を要件には固定しない。

## 4. 現在の優先順位

1. Production usability / data safety
2. Memory correctness
3. Today Action Center / Review Inbox simplification
4. Entity / Timeline / Retrieval correctness
5. Personal Inference correctness
6. Local First / Security
7. Personal Reasoning / Recommendation
8. External Context
9. Visualization

## 5. 現段階で後回し

- Internet公開
- Cloud常時稼働
- 完全自動外部連携
- AIによる購入/契約等の自動実行

## 6. 次回見直し条件

- 本人がProductionで1週間程度利用した
- 重大なData Correctness問題が発生した
- 外部連携へ着手する
- Cloud公開方針を変更する
