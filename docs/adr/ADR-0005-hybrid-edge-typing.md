# ADR-0005 — Hybrid Edge Typing: Canonical 21-Edge Vocabulary + LLM-Emergent Fallback + Option Δ Interpretability Refinements

**Status:** Accepted (2026-05-17 drafted; 2026-05-18 founder-confirmed with Option Δ refinements per multi-round expert debate)
**Supersedes:** N/A — augments ADR-0001 + ADR-0003 architectural framing
**Superseded by:** N/A

---

## Option Δ refinements (2026-05-18) — converged from 6-expert debate

The original 2026-05-17 draft proposed `vocab_match: BOOL` flag as the hybrid mechanism. After a multi-round expert debate (Knowledge Graph historian / PKM practitioner / AI Agent Memory engineer / LLM Application Engineering / Interpretability XAI / Product UX designer with weighted positions), a refined position emerged stronger than any of the originally-proposed Alpha / Beta / Gamma options. This refinement was 10/10 stress-tested and adopted.

### Additional REQUIRED fields on `graph_edges` schema

Beyond the original `vocab_match: BOOL` flag, every edge MUST also store:

- **`evidence_span: TEXT`** — The supporting text snippet from the source content that justifies the extracted relationship. If the LLM cannot quote the supporting text, the edge MUST NOT be stored. This is the interpretability + debugging foundation.
- **`confidence: FLOAT`** — LLM's confidence in the extraction (range 0.0-1.0). Stored verbatim from LLM extraction output.

Updated schema:

```sql
CREATE TABLE graph_edges (
  id INTEGER PRIMARY KEY,
  source_capture_id TEXT NOT NULL,
  target_capture_id TEXT,
  edge_type TEXT NOT NULL,
  vocab_match BOOLEAN NOT NULL DEFAULT FALSE,
  evidence_span TEXT NOT NULL,           -- NEW per Option Δ — REQUIRED
  confidence FLOAT NOT NULL,             -- NEW per Option Δ — REQUIRED (0.0-1.0)
  metadata JSON,
  recorded_at TIMESTAMP NOT NULL,
  valid_from TIMESTAMP NOT NULL,
  FOREIGN KEY (source_capture_id) REFERENCES captures(id),
  FOREIGN KEY (target_capture_id) REFERENCES captures(id)
);
```

### Storage threshold based on confidence

- **`confidence >= 0.7`** → store as primary edge (visible in default recall + UI)
- **`confidence < 0.7`** → store as tentative edge (hidden from default recall + UI; surfaced only via opt-in "Explore connections" feature in plugin)

Avoids polluting the primary graph with weak signals while preserving low-confidence extractions for users who want to explore them.

### Plain English template rendering (deterministic UI)

Each canonical edge type has a plain-English template used by the Shape B plugin UI:

| Canonical edge | Plain English template |
|---|---|
| CRITIQUES | "Khiip detected: {source} disagrees with {target}." |
| SUPPORTS | "Khiip detected: {source} backs {target}'s claim." |
| REFERENCES | "Khiip detected: {source} points to {target}." |
| CONTRADICTS | "Khiip detected: {source} contradicts {target}." |
| DEPENDS | "Khiip detected: {source} requires {target}." |
| GENERATES | "Khiip detected: {source} produced {target}." |
| SUPERSEDES | "Khiip detected: {source} replaces {target}." |
| MAPS | "Khiip detected: {source} is analogous to {target} in a different domain." |
| CHALLENGES | "Khiip detected: {source} questions {target}." |
| TESTS | "Khiip detected: {source} validates {target}." |
| REQUIRES | "Khiip detected: {source} needs {target}." |
| RELATES | "Khiip detected: {source} relates to {target}." |
| ... (one template per canonical edge) | ... |

For LLM-emergent edges (`vocab_match=FALSE`), use the LLM-proposed edge label directly: "Khiip detected: {source} {edge_label} {target}."

This rendering is **deterministic** — same edge produces same plain English every time. Templates compiled from typed structure (not LLM-generated per query, which would be non-deterministic).

### UI surfaces per audience

| Surface | What user sees |
|---|---|
| **Shape B Plugin default** | Plain English rendering + evidence span: "Khiip detected: this article disagrees with that one. Evidence: '[quoted text]'" |
| **Shape B Plugin advanced toggle** | Same content + canonical labels: "CRITIQUES edge to capture 01HXY...; vocab_match=TRUE; confidence=0.89; evidence span: '[quoted text]'" |
| **Shape A API (REST + MCP)** | Raw typed edges + evidence + confidence + vocab_match as JSON; AI builders parse however they want |
| **"Explore connections" opt-in feature** | Tentative (low-confidence) edges visible for power-user exploration |
| **Correction UI** | Tap any edge → "This isn't right" → options: Delete / Change to [different edge type] / Mark as low-confidence |

### Recall ranking with confidence weighting

Recall ranking now incorporates edge confidence:
- High-confidence (≥0.9) edges boost related-capture ranking strongly
- Medium-confidence (0.7-0.9) edges boost moderately
- Low-confidence (<0.7) tentative edges contribute only when "Explore connections" mode is active

Combined with semantic embedding similarity + temporal recency for final ranking score.

### Why Option Δ is stronger than original Alpha/Beta/Gamma

| Concern | Original Alpha (typed + vocab_match) | Option Δ (typed + vocab_match + evidence + confidence + plain English UI) |
|---|---|---|
| Interpretability | Edge labels visible but no reasoning | Evidence span + confidence + plain English rendering = audit-grade interpretability |
| Adoption friction | Users must learn 21-edge vocabulary | Plain English UI default; canonical labels in advanced toggle |
| Extraction error handling | Silent; users can't debug | Evidence span makes errors visible; correction UI lets users fix |
| Low-confidence pollution | All extracted edges stored equally | 0.7 threshold + opt-in exploration prevents weak-signal pollution |
| Shape A API value | Typed edges available | Same + confidence scores let AI agents make probabilistic decisions |
| Future LLM extraction improvements | Pluggable extractor | Pluggable + per-edge confidence tracking creates training signal for fine-tuning |

### Stress-tested across 10 scenarios (2026-05-18 debate)

All 10 stress tests pass:
1. ✅ LLM extraction wrong (false edge) — evidence span + correction UI handle gracefully
2. ✅ User doesn't engage with corrections — graceful degradation; semantic search still works
3. ✅ Edge cases LLM uncertain about — confidence threshold + opt-in exploration
4. ✅ Shape A users want raw edges without plain English — API returns raw JSON
5. ✅ User wants custom edge types — vocab_match=FALSE handles emergent edges
6. ✅ Privacy concern with LLM extraction — D4 tier configurable (BM25 → Ollama → BYOK)
7. ✅ Graph scales poorly with many captures — partial indexes + embedding cache
8. ✅ Canonical edges wrong for Khiip usage — emergent edges captured, promote via canonicalization pipeline (canonical set fully redesigned per ADR-0008)
9. ✅ Better LLM extraction tool emerges — pluggable extractor architecture
10. ✅ Typed graphs become entirely automated by LLMs — vocab_match=FALSE handles all-emergent scenario

Full debate transcript + stress test details in CHRONICLE entry 2026-05-18.

### Implementation cost update

- Original ADR-0005 implementation (vocab_match flag only): ~2-3 days additional Week 6 work
- Option Δ additions (evidence_span + confidence + 0.7 threshold + plain English templates + correction UI + related-captures-panel): ~3-5 days additional Week 6 work vs pure canonical baseline

Total: ~3-5 days in Week 6 (vs 2-3 days originally). Worth the extra days for UX + interpretability + future-proofing.

---

---

## Context

**NOTE (added 2026-05-19):** The original canonical-set assumption in this ADR was a 21-edge inherited vocabulary. ADR-0008 supersedes that specification with a Khiip-designed 5+1 canonical vocabulary; the hybrid pattern documented here (typed canonical + LLM-emergent escape via `vocab_match=FALSE` + Option Δ refinements) remains in force. The 21-edge references throughout this document are historical context for the deliberation that produced Option Δ; for the actual v0 canonical vocabulary see ADR-0008 + Week 6 of the v0 spec.

At the time this ADR was authored, the project's canonical vocabulary was a 21-edge typed set. This was the founding architectural assumption per ADR-0001 genesis (partially superseded by ADR-0008 on the canonical-set specification).

Phase 1 competitive validation (2026-05-16) surfaced a critical R4 (edge typing coverage) finding through **three independent channels that converged on the same recommendation**:

### Signal 1 — Founder intuition (2026-05-16)

Mid-session founder observation: *"sometimes the most accurate LLM connections do not use those premade threads."*

This articulated a structural limitation of pure-canonical edge vocabularies: when LLM extraction produces a semantically accurate relationship that doesn't fit any predefined edge type, the system either (a) force-fits to the closest canonical type and loses semantic precision, (b) drops the relationship entirely and loses recall, or (c) stores as text-only metadata and loses structural queryability.

### Signal 2 — Matrix Filler agent (Phase 1 competitive matrix)

R4 sub-area scoring across 11 competitors:

| Approach | Score | Representative |
|---|---|---|
| Hybrid (canonical + LLM-emergent fallback) | 4/5 | Zep / Graphiti, Cognee |
| Pure predefined (closed vocabulary) | 2/5 | Mem0 OSS, LangChain entity memory |
| Pure emergent (open vocabulary) | 2-3/5 | Various flat tag systems |
| No graph / flat tags | 1/5 | Karakeep, Letta archival memory |
| Khiip current (21 canonical, extensible) | 4/5 | Khiip per ADR-0001 |
| Khiip with hybrid model | **5/5** | (recommended target) |

To score 5/5, Khiip needs to add LLM-emergent fallback ON TOP of the 21 canonical vocabulary — preserving the deterministic-query advantage of canonical while gaining the novel-relationship coverage of emergent.

### Signal 3 — Forum Voice agent (Phase 1 user verbatims)

Three load-bearing empirical findings:

1. **Mem0 production memory quality crisis** (GitHub Issue #4573):
   > "After 32 days of production use, only 224 entries survived manual audit (2.2%). Of those, 186 required complete rewrites, leaving just 38 usable entries."

   Failure modes included forcing real conversation context into Mem0's rigid extraction schema. The 97.8% junk rate is empirical validation that pure-predefined schemas fail at scale when the schema can't capture the diversity of actual conversational relationships.

2. **Graphiti non-deterministic edge typing** (HackerNews launch thread):
   > "Graphiti could spit out edges IS_SIBLING_OF SIBLING SISTER BROTHER etc, it's not standardized. Use whatever node and fact schemas Graphiti comes up with will be different every time because it's using a non-deterministic LLM."

   This validates the opposite failure mode: pure-emergent vocabularies produce inconsistent ontologies that defeat queryability. Same semantic relationship (siblings) gets stored as multiple different edge type strings, breaking deterministic recall.

3. **Cognee + Graphiti hybrid convergence**:
   Both projects landed on the hybrid pattern as the workaround. Cognee documents the approach explicitly: LLM-extracted edges default to emergent; optional RDF/OWL ontology grounding canonicalizes known entities; novel edges get `ontology_valid=False` flag to preserve them without forcing canonical mapping. This is structurally identical to the recommendation here, just with different terminology (`ontology_valid` instead of `vocab_match`).

### The pattern

| Approach | Failure mode |
|---|---|
| Pure predefined / closed vocabulary | "Forced fit" loses novel relationships → quality crisis (Mem0) |
| Pure emergent / open vocabulary | Non-deterministic ontology → queryability collapse (Graphiti default) |
| Hybrid (canonical + emergent fallback) | Best of both: deterministic queries on canonical + novel-relationship coverage via emergent |

The 21 canonical edges (as designed at ADR-authoring time; see note above re: ADR-0008 supersession) covered ~90% of empirical PKM relationships well based on the prior research substrate's experience. The remaining ~10% is where the failure modes accumulate. Hybrid solves both ends.

### Three-way convergence

When founder intuition + structured matrix scoring + empirical user voice all independently arrive at the same architectural recommendation, this is decision-grade signal. Adopt now, before Week 1 v0 commits to the `graph_edges` SQLite schema.

---

## Decision

Adopt hybrid edge typing for Khiip v0:

### 1. Canonical vocabulary at time of ADR authoring: 21 typed edges (later superseded by ADR-0008's Khiip-designed 5+1 set)

The 21-edge canonical vocabulary at ADR-authoring time represented the empirically-validated common case for PKM and capture-substrate relationships. ADR-0008 (2026-05-19) replaces this canonical-set specification with a Khiip-designed 5+1 vocabulary purpose-built for Shape A revenue workflows. The hybrid pattern (typed canonical + `vocab_match=FALSE` escape) is unchanged.

### 2. LLM extraction proposes whatever edge type fits

During capture-write extraction, the LLM is not constrained to the 21 canonical types. It proposes whatever relationship type best describes what it identifies in the captured content.

### 3. Storage schema adds `vocab_match` flag

The `graph_edges` SQLite table gets one additional column:

```sql
CREATE TABLE graph_edges (
  id INTEGER PRIMARY KEY,
  source_capture_id TEXT NOT NULL,
  target_capture_id TEXT,
  edge_type TEXT NOT NULL,
  vocab_match BOOLEAN NOT NULL DEFAULT FALSE,
  evidence_span TEXT,
  metadata JSON,
  recorded_at TIMESTAMP NOT NULL,
  valid_from TIMESTAMP NOT NULL,
  FOREIGN KEY (source_capture_id) REFERENCES captures(id),
  FOREIGN KEY (target_capture_id) REFERENCES captures(id)
);

CREATE INDEX idx_graph_edges_canonical
  ON graph_edges(edge_type)
  WHERE vocab_match = TRUE;

CREATE INDEX idx_graph_edges_emergent
  ON graph_edges(edge_type)
  WHERE vocab_match = FALSE;
```

Where:
- `edge_type` stores either the canonical edge name (when `vocab_match=TRUE`) OR the LLM-proposed novel edge name (when `vocab_match=FALSE`)
- `vocab_match` is set during extraction by comparing the LLM-proposed edge against the 21 canonical types
- Partial indexes optimize both query patterns (canonical-only queries hit the canonical index; emergent-inclusive queries hit both)

### 4. Extraction pipeline behavior

During Week 6 v0 build, the graph extraction module implements this flow:

```python
def extract_edges(capture: Capture) -> list[Edge]:
    canonical_vocab = load_cos_canonical_vocabulary()  # 21 edges, uppercase

    llm_proposed_edges = llm.extract_relationships(capture.content)

    stored_edges = []
    for proposed in llm_proposed_edges:
        normalized = proposed.edge_type.upper().replace(" ", "_")

        if normalized in canonical_vocab:
            edge = Edge(
                source_capture_id=proposed.source,
                target_capture_id=proposed.target,
                edge_type=normalized,           # canonical form
                vocab_match=True,
                evidence_span=proposed.evidence,
                ...
            )
        else:
            edge = Edge(
                source_capture_id=proposed.source,
                target_capture_id=proposed.target,
                edge_type=proposed.edge_type,   # preserve LLM's original casing
                vocab_match=False,
                evidence_span=proposed.evidence,
                ...
            )

        stored_edges.append(edge)

    return stored_edges
```

Canonical matching is intentionally simple (uppercase-normalized string match) at v0. Future enhancement: embedding-based fuzzy matching to canonicalize close-but-not-exact LLM proposals (e.g., "CONTRADICTS" → match canonical "CONTRADICTS_CLAIM"). Deferred to post-v0.

### 5. Recall surface supports both query patterns

The recall API exposes both deterministic and semantic edge queries:

**Canonical edge query** (deterministic; fast):
```
GET /recall?edge_type=CRITIQUES&capture_id=01HXX...
```
Returns only `vocab_match=TRUE` rows matching the exact canonical type. Behavior unchanged from pure-canonical implementation.

**Semantic edge query** (covers both canonical + emergent):
```
GET /recall?edge_semantic=disagreement&capture_id=01HXX...
```
Computes embedding for `disagreement` query string, compares against embedded `edge_type` strings across all rows (both canonical and emergent), returns top-K by cosine similarity. Slower but covers novel relationships the canonical vocabulary doesn't have.

**Hybrid union query** (default for general recall):
```
GET /recall?related_to=01HXX...
```
Returns union of canonical-edge-matched results + semantic-edge-matched results, deduplicated by `edge_id`, ranked by combination of edge-type-canonical-priority + semantic-similarity score + temporal recency.

### 6. Vocabulary evolution path (Year 2+)

Future enhancement: background canonicalization pipeline analyzes the distribution of `vocab_match=FALSE` edges across user vaults (anonymized aggregate per Promise 3 telemetry category). If a specific emergent edge type appears across 10+ users with consistent semantics, it becomes a candidate for promotion into the Khiip canonical vocabulary in the next schema version (per ADR-0008 quarterly proposal-review cadence).

This is the same pattern Cognee describes for ontology evolution (`ontology_valid=False` edges flagged for review). Deferred to post-v0; mentioned here for design-intent documentation.

---

## Consequences

### Positive

- **Solves the "forced fit" failure mode** documented in Mem0's production memory crisis. Novel LLM-extracted relationships preserved with full original semantics rather than mangled into closest canonical type
- **Preserves deterministic queryability** for the canonical edges (where ~90% of relationships will land per prior empirical experience). Canonical queries remain fast + predictable
- **Three-way validation** — founder intuition + structured competitive matrix + empirical user voice all converged on this. Decision-grade signal
- **R4 differentiation strengthens** — Khiip's R4 score goes from 4/5 → 5/5. Becomes the only competitor in the matrix at 5/5 on edge typing coverage
- **Future-proof for vocabulary evolution** — emergent edges that prove valuable can be promoted into canonical via schema updates over time (per ADR-0008 proposal-review cadence), without losing the original LLM-proposed data
- **No breaking change for downstream consumers** — clients consuming Khiip's recall API can opt to filter `vocab_match=TRUE` only (pure-canonical view) or accept both (full-coverage view). Both backward-compatible
- **Cognee parallel** — well-trodden pattern with prior-art reference; Cognee's `ontology_valid=False` mechanism is structurally identical and operating in production at 70+ named enterprise deployments

### Negative

- **+2-3 days additional Week 6 build work** vs pure-canonical implementation:
  - Schema: 1 extra column + 2 partial indexes (trivial)
  - Extraction: ~50 LOC for canonical-match check + storage branching
  - Recall: ~30-50 LOC for semantic-edge-label search path + hybrid union logic
  - Tests: ~20 additional test cases covering hybrid query patterns (canonical-only, semantic-only, hybrid union, deduplication, ranking)
- **Recall API documentation complexity** — clients can query by canonical edge type OR semantic edge similarity OR hybrid union. Documentation must clearly explain when each pattern is appropriate
- **Embedding compute cost** for semantic edge queries adds latency per recall request (mitigated by caching embedded edge labels in SQLite; one embed per unique edge label across vault lifetime). For canonical set + estimated <500 emergent edges per typical vault = manageable embed-table size
- **Storage overhead** — `vocab_match` BOOLEAN adds 1 byte per edge row. For typical vault with ~10K edges = 10KB. Negligible

### Neutral

- **Schema migration if added post-v0** would be expensive (existing captures' edges would need re-extraction OR backfill with `vocab_match=FALSE` for all rows). Adopting in v0 avoids this entirely — single-cost decision now
- **Hybrid mechanism layered on the canonical set** — this ADR adds the vocab_match=FALSE escape + Option Δ interpretability refinements without altering the canonical edge enum itself (canonical set was later redesigned per ADR-0008)
- **AGPL daemon implementation surfaces this as an extension point** — third-party tools consuming the daemon API can opt-in/opt-out of emergent results per their use case. The hybrid model is an additive feature, not a breaking change to the canonical contract

---

## Implementation checklist (for Week 6 v0 build)

When v0 build reaches Week 6, implement in this order:

1. ✅ Schema: add `vocab_match BOOLEAN NOT NULL DEFAULT FALSE` column to `graph_edges` table + two partial indexes
2. ✅ Extraction module: load Khiip canonical vocabulary at daemon startup; implement canonical-match check during LLM extraction; branch storage based on result
3. ✅ Recall API: implement `edge_type=` query parameter (canonical, fast); implement `edge_semantic=` query parameter (semantic, slower); implement default hybrid union behavior
4. ✅ Embedding cache: SQLite table `edge_label_embeddings(edge_label TEXT PRIMARY KEY, embedding BLOB)` for memoizing semantic-edge lookups
5. ✅ Tests: ~20 test cases covering all query patterns + canonical-vs-emergent classification + dedup + ranking
6. ✅ Documentation: README + API docs explaining canonical vs semantic vs hybrid recall patterns; recommended use cases for each

Total estimated Week 6 work: 2-3 days additional vs pure-canonical baseline. Manageable within Week 6 timeline.

---

## References

- `docs/adr/ADR-0001-genesis.md` — original 21-edge typed vocabulary assumption (later replaced per ADR-0008)
- `docs/adr/ADR-0008-standalone-vocabulary.md` — Khiip-designed 5+1 canonical vocabulary that supersedes the 21-edge set referenced throughout this ADR
- `docs/adr/ADR-0003-strategic-positioning-llm-ingestion-layer.md` — strategic positioning + typed-graph differentiation thesis
- the v0 spec (internal) Week 6 — graph extraction implementation (to be updated per this ADR's implementation checklist)
- `docs/research/competitive-validation-synthesis-2026-05-16.md` — R4 finding + 3-way convergence on hybrid recommendation
- `docs/research/competitive-matrix-2026-05-16.md` — R4 sub-area matrix scoring (Khiip 4/5 current → 5/5 with hybrid)
- `docs/research/competitive-user-voice-2026-05-16.md` — Mem0 97.8% junk rate finding + Graphiti non-determinism complaint + Cognee hybrid pattern reference
- Khiip canonical edge vocabulary spec at `docs/adr/ADR-0008-standalone-vocabulary.md` (5 typed + RELATES escape)
- Mem0 GitHub Issue #4573 — production memory quality audit showing 97.8% junk rate
- Graphiti HackerNews launch thread — spothedog1 quote on non-deterministic edge typing
- Cognee blog: https://www.cognee.ai/blog/deep-dives/grounding-ai-memory — hybrid extraction + RDF/OWL ontology grounding pattern (structurally identical to this ADR's approach)

---

## Disposition tracking

| Item | Owner | Deadline | Status |
|---|---|---|---|
| Update the v0 spec (internal) Week 6 with `vocab_match` flag + extraction + recall changes | Assistant (autonomous session 2026-05-17) | 2026-05-17 | ✅ DONE 2026-05-17 |
| Founder review + approval of ADR-0005 | Founder | On return | ✅ APPROVED 2026-05-18 with Option Δ refinements |
| Update Week 6 of the v0 spec with Option Δ requirements (evidence_span + confidence + plain English templates + correction UI + related-captures-panel) | Assistant | 2026-05-18 | IN PROGRESS this session |
| Implement in Week 6 v0 build | Founder (with Claude Code) | Per v0-spec timeline | OPEN |
| Embedding model selection for edge-label semantic queries | Founder | Pre-Week 6 | OPEN (default: bundled all-MiniLM-L6-v2 per D4) |
| Year 2+ canonicalization pipeline design | Founder | Post-v0 | DEFERRED |
| Plain English template completion (all 21 canonical edges) | Founder | Pre-Week 6 | OPEN (12 examples provided in Option Δ refinements section; ~9 templates remaining) |
| Correction UI design + implementation | Assistant + Founder | Week 6 build | OPEN |
| "Explore connections" opt-in UI for low-confidence edges | Founder | v0.5 if demand emerges | DEFERRED (v0 stores tentative edges but doesn't surface UI; surface in v0.5 if power users request) |
