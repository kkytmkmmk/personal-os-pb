# 現時点の実行環境・技術制約

この文書は長期要件ではなく現在の実装制約を示す。

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

1. Memory Correctness
2. Entity / Timeline / Retrieval Correctness
3. Personal Inference Correctness
4. Local First / Security
5. Personal Reasoning / Recommendation
6. UI simplification
7. External Context
8. Visualization

## 5. 現段階で後回し

- Internet公開
- Cloud常時稼働
- 完全自動外部連携
- AIによる購入/契約等の自動実行
