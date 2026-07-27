# Requirements v3 主な変更点

今回の見直しでは、既存要件の方向性を維持しつつ、直近の実装レビューと議論を反映した。

主な追加・強化:

1. Personal OSを `Personal Context Engine` と明確化
2. Raw原文を推論時にも利用する `Structured Retrieval + Source Retrieval`
3. Source Role（user / assistant等）とAI自己汚染防止
4. Personal InferenceをFactから分離し、expiry / re-evaluationを要件化
5. 長期ビジョンとしてEvidenceベースのDigital Twin / Personal Modelを追加
6. 「次に作りたそうなシステム」の生成型Recommendationを追加
7. Current Timelineの登録順非依存・semantic equalityを明文化
8. Entity MentionとRelationship Personの分離を強化
9. Local FirstをProvider自動選択レベルまで明確化
10. External Contextを「実際に何をしたか」のEvidence補完として整理
11. Life Timeline / Travel Map / Decision Flow等の可視化要件を追加
12. Done過大判定を防ぐDefinition of Done / Acceptance Criteriaを追加
13. 外部連携前のLocal Authentication / Security Gateを追加

## 2026-07-26 UI/UX vNext

- PC/iPhoneでPrimary navigationを分離し、iPhoneは固定Bottom navigationと「＋」Bottom Sheetを使う
- TodayをCurrent/Next/Recent change/Pending decision中心へ整理し、管理情報を日常画面から隠す
- 相談・記録・判断のDraft保持、Progressive disclosure、外部ChatGPT解析の明示PreviewをUI正本へ追加
- Acceptance viewportとアクセシビリティ（44px、aria、focus、safe-area、横スクロール禁止）を明文化

## Consultation Cycle completion (2026-07-26)

- 相談APIが`response_type`とRecommendation Candidateを返す
- Recommendation保存後にのみPlanを生成する状態遷移へ変更
- Plan→Decision候補→本人確定→Execution→Result→Later EvaluationをCycle API/UIへ接続
- `cycle_stage` / `available_actions` と不正遷移拒否を追加
- Todayに進行中Cycleと次のActionを表示

## 2026-07-27 Visualization / Population Benchmark vNext

- Visualizationを実用系だけでなく探索・遊び要素まで拡張し、3D `Personal Space / Information Universe` を正式要件化
- Domain Color、Object Shape、Node Size、Brightness / Opacity / Glow、Edge、Stable Layout、Mobile / Accessibilityを定義
- 3DはPrimary Flowではなく「その他 / 探索」配下のSecondary Experienceとした
- `12_population_benchmark_requirements.md` を追加し、公的統計のLocal DB保持、Provenance、Definition Matching、Cohort Matching、Mean / Median / Distribution、乖離可視化を要件化
- Benchmark Sourceはe-Stat / 総務省統計局、国税庁、J-FLEC、厚生労働省等のOfficial / high-quality sourceを優先
- Benchmarkは適宜Refreshし、Reference Period / Revision履歴を保持。取得失敗時はLast valid referenceを維持
- Benchmark取得でPersonal Contextを外部へ送らず、Population Segmentの選択・比較はLocal側で行う
- Benchmarkを目標値・正常値として扱わず、中立的なReferenceとして表示する
