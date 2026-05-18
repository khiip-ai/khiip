# ADR-0008 — Khiip Standalone Product Lock + Khiip-Designed Canonical Edge Vocabulary (5+1)

**Status:** Accepted (2026-05-19)
**Supersedes:** N/A — confirms the standalone-product reality (org `khiip-ai/khiip` already exists at infra layer) + locks the Khiip-designed canonical edge vocabulary that replaces the implicit external-framework inheritance carried in ADR-0001 / ADR-0005
**Partial-supersedes:** ADR-0001 (genesis "consumes-from external substrate" framing for vocabulary specifically; technical sequencing for Shape A + B unchanged), ADR-0005 (Option Δ hybrid pattern stands; the "canonical = inherited 21" specification is replaced by the Khiip-designed 5+1)
**Superseded by:** N/A

---

## Context

Khiip's strategic positioning has resolved across prior ADRs (0001–0007) but a single inherited assumption ran through all of them: that Khiip's canonical edge vocabulary inherited a 21-edge typed taxonomy from an external personal-methodology framework. ADR-0005 (Option Δ) committed to "canonical = the inherited 21 + LLM-emergent labels via `vocab_match=FALSE`." v0 spec Week 6 schema codified this with a CHECK constraint enumerating the 21 codes.

2026-05-19 strategic clarification: **Khiip's primary purpose is to be a standalone product/business, published in its own GitHub organization at `github.com/khiip-ai/khiip`.** The original framing in ADRs 0001-0005 assumed Khiip would inherit a canonical edge vocabulary from a parent framework. That framing carried into v0 spec Week 6 (CHECK constraint enumerating 21 codes) but no longer aligned with Khiip-as-standalone-product needs.

Three converging analyses surfaced during the 2026-05-19 session pointed at the same architectural correction:

1. **Anchored vs un-anchored 6-expert deliberation on edge typing** (CONTRADICTS-template-mapping decision). The anchored run (with the inherited-21 + no-grow-lock context) produced 5/6 votes for "store CONTRADICTS as emergent (vocab_match=FALSE)." The un-anchored counterfactual (greenfield design framing; no inheritance context) produced **6/6 votes for "CONTRADICTS as first-class typed edge in a small Khiip-purpose-designed vocabulary."** Full inversion across every domain expert (Logic / KG-Ontology / LLM-Agent-Memory / PKM-Practice / Interpretability-UX / Schema-Governance), citing the same primary-source precedents (CITO / Wikidata / Schema.org / Tana / Mem0 / Graphiti) — opposite conclusions under different framing. The inherited-vocabulary assumption was actively flipping every domain expert's recommendation.

2. **Probe #1 — MCP enum vs freeform A/B** (72 calls across Claude Sonnet 4.5 + GPT-4o-mini, 18 scenarios × 2 tool surfaces). Empirically validated Lens 3's prediction: typed enum on MCP `recall_related.edge_type` achieves 94-100% agent intent-match; freeform string drops to 44.4% across both vendors. **A 50-percentage-point retrieval-correctness gap.** Specific drift patterns observed: REFERENCES intent drifted to CITES/POINTS_TO/SUPPORTS; QUESTIONS intent dispersed across CRITIQUES/METHOD_CONCERNS/CHALLENGES/CONTRADICTS with zero exact-match; EXTENDS intent dispersed across BUILDS_ON/EXTENDS_TO_DOMAIN/DEVELOPS/FURTHER_BEAUTIFIES. For Shape A AI-builder consumers ($49-$2K/mo revenue tier), this is a material API-surface defect.

3. **Workflow-driven minimum-viable vocabulary probe** (focused single-lens analysis, 2026-05-19). Worked backward from the 5 highest-revenue Shape A workflows (Conversational RAG memory / Fact-checking / Research synthesis / Competitive intel / Knowledge-worker decision support). Identified the typed-edge set required-by-≥3-workflows AND extraction-orthogonal-where-additive. Output: **5 typed + 1 escape** as the v0 launch vocabulary, with quarterly telemetry-gated proposal-review cadence for additive growth.

Together: the inherited 21-edge vocabulary served personal-methodology coherence that Khiip-as-standalone-product no longer needs. The product needs a tightly-designed vocabulary that maximizes Shape A retrieval correctness, minimizes LLM-extraction confusion, and grows additively via telemetry signal rather than committee intuition.

## Decision

### 1. Khiip is a standalone product/business — locked.

- Canonical repo: `github.com/khiip-ai/khiip`
- No live inheritance from any external methodology framework
- External-framework composition manifest deleted (was previously declaring inheritance)
- Internal agent-instruction docs boot order rewritten to remove external-framework references
- Patterns borrowed from research-substrate origins (bitemporal recording, append-only override chain, ULID + frontmatter conventions, Pydantic-validated schemas, multi-vendor LLM dispatcher) are industry-standard / not framework-specific; Khiip retains and credits the seed source in this ADR but operates independently
- Cross-org chronicle aggregation: out of scope; Khiip's CHRONICLE stays local to this repo

### 2. Canonical edge vocabulary — Khiip-designed 5 typed + 1 escape

Replaces the 21-edge external inheritance specified in ADR-0005.

| Code | Semantics | Plain-English template (ADR-0005 Δ Promise #3) | Workflow coverage |
|---|---|---|---|
| `SUPPORTS` | Source asserts target's claim is true | "Khiip detected: {source} backs up {target}" | Fact-checking, Research synthesis, KW decision support |
| `CONTRADICTS` | Source asserts target is wrong (mutually exclusive at same time) | "Khiip detected: {source} disagrees with {target}" | All 5 workflows (highest-leverage edge) |
| `SUPERSEDES` | Source replaces target as the newer authoritative version | "Khiip detected: {source} replaces {target} (newer)" | RAG memory, Fact-checking, Competitive intel, KW decision support |
| `ELABORATES` | Source adds detail to target without taking a truth stance | "Khiip detected: {source} adds detail to {target}" | Research synthesis, Competitive intel, KW decision support |
| `REFERENCES` | Source mentions or cites target (pointer-only; no semantic stance) | "Khiip detected: {source} mentions {target}" | Extraction-orthogonal; nice-to-have across all 5 |
| `RELATES` | Escape hatch — relationship exists but doesn't match any typed edge | "Khiip detected: {source} relates to {target}: {extracted_text}" | Per ADR-0005 Option Δ; preserves novel semantics |

**5 typed + 1 escape = 6 total.** Down from 21 inherited.

### 3. Edges explicitly DROPPED from earlier proposals

- `QUESTIONS` — collapses into `CONTRADICTS` at lower `confidence` (confidence field already encodes the hedge from "definite contradiction" to "questioning challenge"; no need for a separate edge type)
- `EXTENDS` — highest extraction-confusion risk per Probe #1 evidence (drifts to BUILDS_ON / EXTENDS_TO_DOMAIN / DEVELOPS); collapses into `ELABORATES` with `extracted_text` preserving the "future direction" nuance for rare consumers that need it
- All other inherited 21 codes (IDE / ISO / INS / GEN / CON / TRN / DUA / COM / MAP / ANA / EXP / INV / MOT / OPR / VAL / TEN / CHA + SUP / REQ / TES + SUP_V where not absorbed into the 5) — were designed for personal-methodology research artifacts (theses / patterns / L3 syntheses) and don't earn their keep in Khiip's product domain (capture-to-capture relations between online sources)

### 4. Hybrid pattern (per ADR-0005 Option Δ) stands

The architectural shape locked by ADR-0005 (typed canonical + LLM-emergent escape hatch + REQUIRED `evidence_span` + REQUIRED `confidence` + plain-English template rendering + correction UI) is preserved. Only the *canonical set* is redesigned.

### 5. Composition trade-off audit (pairwise extraction-confusion risk)

| Pair | Overlap risk | Mitigation |
|---|---|---|
| SUPPORTS ↔ ELABORATES | HIGH | Extractor prompt: SUPPORTS = "asserts the claim is true"; ELABORATES = "adds detail without taking a truth stance" |
| CONTRADICTS ↔ SUPERSEDES | MEDIUM | Disambiguate by temporal signal: same-fact-different-time → SUPERSEDES; same-time-different-claim → CONTRADICTS |
| SUPPORTS ↔ REFERENCES | LOW | REFERENCES is pointer-only; no semantic stance |
| Others | LOW or NONE | (per probe audit) |

### 6. Proposal-review cadence (post-v0)

Additive growth only; telemetry-gated. To promote a new typed edge from the RELATES escape into the canonical enum:

1. **Frequency floor:** candidate semantic appears in ≥5% of RELATES edges across ≥3 distinct customer workspaces in the trailing quarter (measured by clustering `extracted_text` on RELATES rows)
2. **Distinct-intent test:** candidate does not pairwise-overlap with any existing typed edge by >15% under a held-out extractor eval (Probe #1 methodology re-run)
3. **Workflow attribution:** at least one named workflow class can articulate a query that's impossible / lossy with current canonical + RELATES
4. **No removals for 12 months** after a typed edge ships (consumer stability promise; downgrades to RELATES are a breaking MCP change)
5. **Renames allowed only at major version** (`khiip-mcp/v2`), never in-place

Telemetry hook: every RELATES write emits `extracted_text` to a quarterly clustering job; clusters crossing the floor surface as edge-proposal candidates for review. Vocabulary is **observably evolved, not committee-evolved**.

## Consequences

### Positive

- **Shape A MCP API surface clarity** — typed enum gives 94-100% agent intent-match per Probe #1, vs 44.4% for freeform; consumer integration code is stable + self-documenting
- **LLM extraction precision** — tight vocabulary (6 distinct semantics) minimizes confusion vs 22 overlapping types; defensive extractor prompts handle the two real overlaps (SUPPORTS/ELABORATES + CONTRADICTS/SUPERSEDES)
- **Workflow coverage proven** — every retained edge is workflow-required by ≥3 of 5 Shape A revenue workflows OR is extraction-orthogonal; no speculative additions
- **Khiip-purpose-designed, not framework-inherited** — vocabulary serves product needs not personal-methodology coherence; aligns with standalone-product positioning per this ADR
- **Bitemporal moat unlocked** — SUPERSEDES as first-class is what makes Khiip's bitemporal architecture pay off for Shape A consumers (RAG memory, fact-checking, competitive intel all need it); without SUPERSEDES the bitemporal columns are infrastructure with no consumer-facing semantics
- **Reversibility preserved** — RELATES escape + extracted_text + telemetry-gated promotion gate means novel semantics surface organically; vocabulary grows additively per evidence
- **Operationally simpler** — 6 plain-English templates vs 21; correction-UI dropdown is focused (sub-paralysis); MCP enum is enumerable

### Negative

- **No external-framework interop dependency** — Khiip operates standalone. Acceptable per standalone-product framing.
- **Migration story for any existing edges** — none in production yet; the 5+1 design lands before any v0 captures, so no data-migration cost from the inherited-21 spec
- **Researchers who expect richer adversarial taxonomies** (CITO 7-way disagree/dispute/refute/critique/parody/ridicule/repliesTo split, or AIF rebut/undercut/undermine triplet) will find Khiip coarser than academic argumentation ontologies. Mitigation: extracted_text preserves the nuance for downstream consumers that want to re-classify; promotion gate exists if telemetry shows demand
- **Lens 1 (KG/Ontology) un-anchored steelman wanted a slightly larger vocabulary** (SUPPORTS / CONTRADICTS / ELABORATES / REFERENCES / SIMILAR_TO with freeform `subtype`). Workflow probe's "what does the workflow actually require" analysis pruned to 5; if Probe #1-style telemetry shows SIMILAR_TO recurring strongly, it's a promotion candidate

### Migration / cleanup actions completed in this session

- Deleted external-framework composition manifest
- Rewrote internal agent-instruction docs boot order to remove external-framework references
- Updated working documentation to remove external-framework references
- Marked the prior internal canonical-edge-template mapping doc SUPERSEDED (its 21-canonical mapping is obsolete per this ADR; new vocabulary spec lives in this ADR + the v0 spec Week 6)
- ADR-0005 Status line updated to "partially superseded by ADR-0008 on canonical-set specification; hybrid pattern + Option Δ promises remain in force"
- v0 spec Week 6 `graph_edges` CHECK constraint enum updated to 5+1; plain-English template section rewritten

### Migration actions NOT taken (deliberately)

- ADR-0001 / ADR-0005 prose body NOT edited — append-only invariant per ADR discipline. Only Status lines flipped per supersession protocol.
- CHRONICLE.md entries NOT edited — historical record of how the decisions unfolded; preserves the calibration data for future learning
- `docs/research/phase-3-hands-on-results-2026-05-18.md` NOT edited — historical research output

## Multi-expert deliberation methodology metadata

**Process used to produce this ADR:**
- Anchored 6-expert Round 1 deliberation on CONTRADICTS template (5/6 vote (c) emergent + Option Ε registry pattern surfaced)
- Meta-debate on deliberation effectiveness (verdict: ~20% of value from deliberation, 80% from baseline reasoning; recommended tiered process for remaining decisions)
- Un-anchored 6-expert counterfactual Round 1 (6/6 vote (d) typed CONTRADICTS in small vocabulary; full inversion of anchored convergence)
- Comparison + load-bearing analysis (verdict: inherited 21-edge framing actively flips conclusions across all 6 lenses; lock is load-bearing as tradeoff between product-effectiveness and cross-org coherence, not architectural truth)
- Probe #1 — MCP enum vs freeform A/B (Claude + GPT-4o-mini, 72 calls; 50pp intent-match gap)
- Founder strategic clarification (Khiip = standalone product)
- Focused single-lens workflow probe (workflow-driven minimum-viable vocabulary; output: 5+1)

**Total session cost:** ~5-7 hours of deliberation + probes for ~6 architectural decisions cascade. Significant per-decision investment justified by load-bearing nature of vocabulary architecture (consumer-facing API surface; expensive to change post-launch).

**Reusable patterns captured:**
- Anchored-vs-unanchored counterfactual deliberation as a tool for diagnosing inherited-assumption load-bearing-ness
- Probe #1 (MCP enum vs freeform A/B) as a re-runnable methodology for future schema-evolution decisions
- Workflow-driven minimum-viable vocabulary analysis as a vocabulary-design protocol

---

*Companion artifacts: the v0 spec (internal) Week 6 (updated graph_edges schema + plain-English templates per this ADR), `docs/research/phase-3-hands-on-results-2026-05-18.md` (Probe #1 substrate), session 2026-05-19 CHRONICLE entry (full deliberation trace).*
