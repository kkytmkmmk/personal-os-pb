# Memory Quality Pipeline

Personal OS treats extracted information as a candidate until it passes a deterministic quality gate.

```text
raw entry / chunk
  -> entity mention
  -> Entity Resolution
  -> Fact candidate
  -> Evidence and truth review
  -> current/history resolution
  -> retrieval eligibility
  -> domain projection / chat context
```

ChatGPT export conversations are split at exchange boundaries (one user turn
plus its immediately following assistant turn). A long exchange may be split
into continuation chunks, but the next user turn is never joined into the same
chunk. Analysis Jobs run per active chunk and each Fact is re-anchored to the
exact source chunk. A local Personal-relevance prefilter skips clearly generic
reference turns before an LLM call. Legacy document-level Facts are kept as raw
history but quarantined from retrieval until re-analysis completes.

## Entity and relationship boundary

`entities.entity_type` distinguishes `person`, `fictional_character`, `project`, `organization`, `place`, `product`, `service`, `brand`, `asset`, and `unknown`. A mention is stored in `entity_mentions` even when it is not resolved as a Person. The People projection requires both `entity_type=person` and `subject_scope=person`.

For example, a character or project relationship is kept as source data, reclassified as reference/hobby when appropriate, and excluded from People and Retrieval. No proper name is hard-coded.

## Fact quality and correction

`facts.extraction_confidence` records model confidence. `truth_confidence` is calculated after Evidence and validation. `retrieval_eligibility` is one of `eligible`, `pending`, `excluded`, or `conflict`.

`memory-facts-jp-v3` first asks the extractor for only explicit facts stated by the user. The deterministic gate then recalculates trust from the quoted Evidence, independent source identities, contradiction count, speculation language, and whether a value is a future plan. The resulting support/contradiction counts and `trust_details_json` make the final state auditable without trusting a model's self-reported confidence.

`facts.personal_relevance` is one of `personal`, `linked_context`,
`archive_only`, or `unknown`. Only `personal` information can become current
Personal OS memory. `linked_context` is retained for comparison and planning
context but cannot become a current Fact by itself.
General knowledge, fictional characters, projects, organizations, and
unrelated reference text remain provenance/archive data; `unknown` is held
pending rather than promoted.

Entity type and Personal relevance are independent. A company can be the
owner's employer, a place can be a visited destination, and a product can be
owned or used. The quality gate reads the user's side of an imported exchange
before deciding relevance; assistant-only statements cannot establish a
personal Fact.

Automatic and manual changes are appended to `memory_corrections`; raw entries, documents, chunks, attachments, and Evidence are retained. The audit is idempotent and can be rerun with:

```text
POST /api/memory-quality/recheck
GET  /api/memory-quality
GET  /api/facts/{id}/corrections
```

Only `eligible` current Facts are used for domain projections and current-memory retrieval. Rejected, excluded, or unresolved Entity classifications are not used as current context.

`memory-quality-v2` keeps an unknown Relationship candidate pending instead of
rejecting it, avoids changing a shared Entity globally from one Fact, and
deduplicates identical correction transitions. Confirmed numeric candidates
that are at least an order of magnitude outside two or more prior values are
held as `conflict`.

The deterministic relevance benchmark is stored in
`benchmarks/memory_relevance_cases.json` and can be run without a DB or LLM:

```powershell
python tools/run_memory_quality_benchmark.py
```

Use `POST /api/memory-quality/resegment` to create turn-level source revisions,
quarantine coarse legacy Facts, and queue local re-analysis. This operation is
idempotent and preserves the original source and correction history.
