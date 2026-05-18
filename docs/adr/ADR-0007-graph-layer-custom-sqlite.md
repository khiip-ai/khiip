# ADR-0007 — Graph Layer Architecture: Custom SQLite (Graphiti + Kuzu Rejected)

**Status:** Accepted (2026-05-18)
**Supersedes:** N/A — confirms the implicit SQLite assumption in the v0 spec Week 6 `graph_edges` schema; adds three architectural patterns (GraphLayer contract, append-only edges with override chain, exact-string entity resolution for v0) that were not previously specified
**Partial-supersedes:** N/A
**Superseded by:** N/A

---

## Context

Phase 3 hands-on testing (per `docs/research/competitive-validation-synthesis-2026-05-16.md`) included Test 3 — "Zep Graphiti edge typing flexibility install + test custom Pydantic types" — to inform the decision: **adopt Graphiti as Khiip's graph layer (integrate) vs build custom SQLite graph (compete)**.

Initial empirical surface (Pydantic interface test in venv, 2026-05-18) suggested Graphiti was significantly more viable than originally framed:
- `EntityEdge` ships with bitemporal fields (`valid_at`, `invalid_at`, `created_at`, `expired_at`, `reference_time`)
- Custom Pydantic edge types validate cleanly with Option Δ required fields (`evidence_span: str`, `confidence: float [0,1]`, `vocab_match: bool`)
- `edge_type_map` + `RELATES_TO` fallback IS the hybrid model from ADR-0005
- Kuzu (file-based embedded graph DB) listed as supported backend per Graphiti docs — eliminates the Neo4j-server objection for local-first daemon

This reframed Test 3 from a "confirm-build" lookup into a genuine build-vs-integrate fork. Per founder default-mode (multi-expert deliberation for non-trivial architectural decisions), six weighted expert lenses ran Round 1 in parallel:

| Lens | Weight | Vote | Confidence |
|---|---:|:---:|:---:|
| Graph DB architect | 0.20 | B | MEASURED |
| Local-first software engineer | 0.20 | B | ~70% |
| OSS dependency risk analyst | 0.15 | B | high |
| Extraction quality engineer | 0.15 | B | 0.85 |
| Interpretability + Option Δ implementer | 0.15 | B | firm |
| Build velocity + Week 6 owner | 0.15 | B | high |

**Round 1 produced unanimous convergence on Option B (custom SQLite).** Three falsifiable probes were executed before lock; all confirmed the consensus.

### Decisive empirical findings

**1. Kuzu was archived October 2025.** Kùzu Inc was acquired by Apple; the upstream repository (`kuzudb/kuzu`) is read-only ([The Register](https://www.theregister.com/2025/10/14/kuzudb_abandoned/), [BigGo](https://biggo.com/news/202510130126_KuzuDB-embedded-graph-database-archived), [Graphiti Issue #1132](https://github.com/getzep/graphiti/issues/1132)). The community fork (`Kineviz/bighorn`) has sparse activity and is not a credible 5-year-horizon successor. Without Kuzu, Graphiti's only remaining backends for embedded use are: Neo4j (server-class), FalkorDB (Docker required), FalkorDB Lite (unshipped feature request as of [Graphiti Issue #1240](https://github.com/getzep/graphiti/issues/1240)), or Amazon Neptune (cloud). All contradict Khiip's PyInstaller local-first daemon distribution.

**2. `add_triplet` does NOT bypass Graphiti's LLM resolution pipeline.** Per Zep docs at `help.getzep.com/graphiti/working-with-data/adding-fact-triples` and source inspection of `graphiti_core/utils/maintenance/edge_operations.py`: manually inserted triplets still invoke `resolve_extracted_edges()`, which calls `llm_client.generate_response()` against `prompt_library.dedupe_edges.resolve_edge()`. Khiip's deterministic edges from per-source extractors (fxtwitter, MarkItDown, yt-dlp, gallery-dl) would be subject to LLM re-judgment and possible invalidation. This is the exact failure surface Khiip's per-source-extractor moat exists to avoid (see Mem0 GitHub Issue #4573: 97.8% junk rate from generic-LLM extraction on 10,134 production entries).

**3. Edge dedup at ~0.9 embedding similarity collapses legitimate distinct-source provenance.** Graphiti's hybrid-search dedup merges edges with similar fact text within an entity pair. The same factual claim cited by two different sources (e.g., a tweet AND a PDF) would collapse to one edge, destroying the multi-source provenance Khiip's bitemporal invariant promises.

**4. Custom Pydantic edge attributes are dropped on first-time edges.** [Graphiti Issue #1111](https://github.com/getzep/graphiti/issues/1111) — open user report. Khiip would ship a daemon where `evidence_span` is `NULL` on most early edges. Violates Option Δ Promise #1.

**5. `posthog >= 3.0.0` is a required dependency** of `graphiti-core` per PyPI. Bundling a telemetry vendor in the dep tree of an AGPL daemon whose commercial promises include data ownership is a TRUST.md liability.

**6. Cypher semantics block in-place edge-type mutation.** Kuzu/Neo4j relationship types are immutable; user correction `CON → REQ` becomes delete-then-recreate, which loses the stable UUID that correction-UI round-trip requires. SQLite UPDATE is one statement.

**7. `fact` field is LLM-generated output.** Option Δ Promise #3 requires plain-English rendering as a *deterministic template* from `(canonical_edge_type, mechanism, source, target)`. Graphiti's `fact` is the *output* of an extraction LLM call. Achievable in Graphiti only by storing template-rendered string in `attributes["display_fact"]` and ignoring the library's `fact` — convention-not-invariant.

### Falsifiable probes executed pre-lock

**Probe 1 — v0-spec Week 6 bitemporal scope:** v0 spec line 348 — *"v0 plugin UI does NOT expose bitemporal queries directly"*; bitemporal queries deferred to premium "Time machine" feature Month 4-6. **v0 requires bitemporal recording only** (stored `recorded_at` + `valid_from` fields), NOT auto-invalidation/contradiction-detection. This eliminates the strongest surviving counter to Option B — Graphiti's bitemporal contradiction-detection engine is precisely the capability v0 does not need.

**Probe 2 — canonical vocabulary → SQLite enum fit:** Trivial. `TEXT NOT NULL CHECK (edge_type IN (<canonical set>))` paired with `vocab_match BOOLEAN NOT NULL DEFAULT 1`. The canonical set used at this ADR's authoring was a 21-edge inherited vocabulary; later replaced by the Khiip-designed 5+1 set per ADR-0008. The probe finding holds for either set — SQLite handles enum constraints trivially regardless of cardinality.

**Probe 3 — SQLite `WITH RECURSIVE` benchmark at Option Δ schema, 50K-edge scale:** 200 random 2-hop CON traversals with `confidence > 0.7` + point-in-time filter against synthetic 5000-node / 50000-edge graph (21 canonical edge types, 15% `vocab_match=0`, 5% invalidated). Indexes on `(src, edge_type, valid_to)`, `(dst, edge_type, valid_to)`, `(confidence, valid_from)`. Results:

```
p50:  0.005 ms      p95:  0.010 ms      p99:  0.024 ms
max:  0.109 ms      mean: 0.006 ms
```

Microseconds, not milliseconds — three orders of magnitude faster than Lens 1's "single-digit ms" prediction. Performance headroom for 500K-edge scale (power-user with 5000 captures × 100 edges per capture).

## Decision

**Khiip v0 graph layer is custom SQLite. Graphiti + Kuzu is rejected.**

### Specific commitments

**1. Storage substrate.** Single `~/.local/share/khiip/index.db` SQLite file. The `graph_edges` table schema specified in `docs/product/v0 spec` Week 6 (lines 213-238) stands as authoritative.

**2. GraphLayer contract interface (NEW per this ADR).** Per P1 (Decouple Everything), the graph layer sits behind a Python Protocol:

```python
class GraphLayer(Protocol):
    def insert_edge(self, edge: Edge) -> EdgeId: ...
    def query_edges(self, src: Optional[NodeId], dst: Optional[NodeId],
                    edge_type: Optional[str], min_confidence: float = 0.7,
                    as_of: Optional[Timestamp] = None,
                    include_emergent: bool = False) -> list[Edge]: ...
    def traverse(self, src: NodeId, edge_types: list[str],
                 max_depth: int = 2, min_confidence: float = 0.7,
                 as_of: Optional[Timestamp] = None) -> list[Path]: ...
    def override_edge(self, edge_id: EdgeId, override: EdgeOverride) -> EdgeId: ...
    def health_check(self) -> HealthStatus: ...
```

v0 ships `SqliteGraphLayer`. If a future trigger fires (e.g., FalkorDB Lite ships in Graphiti stable, OR Khiip crosses the scale where SQLite traversal degrades), an alternative implementation slots in behind the same contract per P4 — no consumer code changes.

**3. Append-only edges with `overrides: uuid` chain (NEW per this ADR — REPLACES in-place mutation in v0-spec Week 6 line 267).** When a user corrects an edge (changes type, edits fact text, marks low-confidence), Khiip writes a NEW edge with `overrides: <original_edge_id>` and leaves the original untouched. The "current state view" is derived: for each `(src, dst, edge_type)` tuple, the most recent edge in any override chain wins. Aligns with append-only calibration pattern (override_log discipline). Sidesteps Cypher's ALTER-relationship-type limitation entirely (would have been a problem in Option A regardless). Cleaner audit trail than in-place UPDATE.

Schema delta vs v0-spec Week 6:

```sql
ALTER TABLE graph_edges ADD COLUMN overrides INTEGER REFERENCES graph_edges(id);
CREATE INDEX idx_graph_edges_overrides ON graph_edges(overrides);
-- Note: no rows are ever UPDATE'd after insert except in the supersession case
-- (append-only discipline: superseded_by is the only legal in-place field flip).
-- Khiip pattern: use the overrides chain instead; superseded_by is a query-time
-- derivation from the chain head.
```

**4. Exact-string entity resolution for v0 + manual merge UI (NEW per this ADR).** Per Lens 5 + P2 (Visible, Inspectable State): exact-string match on canonical entity name produces visible duplicates (e.g., "Tesla Inc" vs "Tesla" vs "TSLA" appear as three nodes in the plugin); user merges them via "Merge with..." action in the Khiip sidebar. Defers embedding-based / LLM-disambiguated entity resolution to v0.5. Rationale: visible-but-mergeable duplicates beat invisible wrong-merges (Graphiti's silent embedding dedup at ~0.9 similarity threshold).

**5. 2-hop traversal cap via `WITH RECURSIVE` + `depth <= 2`.** Probe 3 confirms p99 < 0.024 ms at 50K-edge scale on this query shape. Deeper traversals are out of scope for v0 recall surface; if a v1+ "Explore connections" feature warrants 3+ hops, the GraphLayer contract supports arbitrary depth — implementation just gets a depth parameter wired into the CTE.

**6. Reserve `graph_backend` config key.** v0 ships `graph_backend = "sqlite"` only. Reserved for future swap (no other values legal at v0).

**7. No additional storage process.** Khiip remains a single-process daemon with one SQLite file (`index.db`). Backup story stays trivial: `cp ~/.local/share/khiip/index.db ~/backups/` works. Vault is authoritative; SQLite is rebuildable from vault per v0-spec architecture diagram.

### Explicit non-decisions (deferred to future ADRs if/when triggers fire)

- **Bitemporal contradiction-detection / auto-invalidation.** Deferred to "Time machine" premium feature Month 4-6 (per v0-spec line 346). At that time, evaluate: build on Khiip's SQLite graph layer, OR migrate to a graph engine that ships this (Graphiti+FalkorDB-Lite-if-shipped, or others).
- **Embedding-based entity resolution.** Deferred to v0.5. Probe + adopt approach (e.g., `sentence-transformers` for similarity, LLM for disambiguation prompts) when v0 captures cross 1000+ entities.
- **Graph migration to non-SQLite backend.** Triggered by ANY of: SQLite `WITH RECURSIVE` p99 > 100ms in production telemetry; user demand for >3-hop traversal as default recall surface; FalkorDB Lite ships in Graphiti stable AND the LLM-resolution / dedup-collapse concerns are addressed (verify via fresh deliberation).

## Consequences

### Positive

- **Stack ownership.** Every byte of the graph layer's resolution/dedup/recall path is Khiip code. No upstream library can silently change the meaning of stored edges between Khiip versions. Bitemporal `recorded_at` invariant preserved by construction.
- **Single-process, single-file daemon.** Operationally trivial. `cp index.db` backup works. User can `rm -rf ~/.local/share/khiip` and rebuild from vault. PyInstaller bundling stays clean (sqlite3 is Python stdlib; zero native-dep matrix to manage).
- **Debuggability.** When an edge isn't returning, `sqlite3 index.db "SELECT * FROM graph_edges WHERE ..."` answers in 10 seconds. No layer boundary to read source across.
- **Per-source-extractor moat preserved.** Khiip's curated extractors (fxtwitter, MarkItDown, yt-dlp, gallery-dl) produce edges with deterministic `evidence_span` and high `confidence`, which round-trip without LLM re-judgment.
- **Option Δ promises satisfied by construction.** `evidence_span`, `confidence`, `vocab_match` are typed columns; plain-English templates render deterministically; correction UI maps to single UPDATE+INSERT transactions.
- **Migration asymmetry favors us.** If a future ADR moves us to a different graph engine, exporting `SELECT * FROM graph_edges` and replaying inserts against the new engine is straightforward. The reverse (escaping a graph library's opinionated schema back to raw tables) is materially harder.
- **No new transitive dep tree.** Zero new dependencies, zero new telemetry vendor in the daemon supply chain.

### Negative

- **We own the bitemporal contradiction-detection engine if/when we need it.** Naive `valid_to = NULL` schemas with contradiction-on-insert require careful design (overlapping intervals, lost updates on concurrent invalidation, Allen-relation gaps are real risks). Mitigation: deferred to Month 4-6 "Time machine" feature; v0 ships recording only.
- **We own entity resolution.** Exact-string match is the v0 baseline. Embedding-based + LLM-disambiguated resolution is a v0.5 build. Mitigation: visible duplicates with merge UI is acceptable for power-users (P2 visibility); not acceptable for mass-market Shape C/D, but those are not v0 targets.
- **We do not get free hybrid BM25 + semantic + graph-distance reranking** that Graphiti's `search()` provides. Mitigation: v0-spec already commits to tiered recall (bundled embedding → Ollama → BYOK → BM25); hybrid ranking is a v0.5+ refinement when telemetry shows the need.
- **We diverge from one industry pattern.** Some agent-memory companies adopt Graphiti as their graph substrate. Khiip's pitch ("substrate-not-destination" per ADR-0003) is differentiated by NOT being Graphiti-shaped — but if AI builders evaluating Khiip expect a Graphiti-compatible API surface, we have to articulate the difference clearly in Shape A docs.

### Architectural follow-ups (to be tracked, not decided here)

- **v0 spec Week 6 update:** add GraphLayer contract interface skeleton + append-only-with-overrides-chain pattern + entity-resolution v0 stance + canonical edge vocabulary per ADR-0008.
- **`SqliteGraphLayer` test suite:** ~25-30 cases per v0-spec Week 6 line 271, augmented with override-chain correctness tests and 2-hop traversal benchmarks.
- **Telemetry instrumentation:** capture p50/p95/p99 of graph traversal queries to validate Probe 3's prediction holds under real load; ship in Week 7 Promise 3 telemetry pipeline.

---

## Multi-expert deliberation methodology metadata

**Pattern invoked:** weighted parallel expert lenses (6 lenses, single round, supplemented by 3 falsifiable probes). Same pattern that produced ADR-0005 Option Δ.

**Lens weights:** Graph DB architect 0.20 / Local-first engineer 0.20 / OSS-risk analyst 0.15 / Extraction quality 0.15 / Interpretability + Option Δ 0.15 / Build velocity + Week 6 owner 0.15 = 1.00.

**Round count:** 1 round + 3 falsifiable probes. Round 2 cross-examination was considered but skipped given unanimous Round 1 convergence with high confidence; probes addressed the one surviving counter-position (under-pricing Graphiti's bitemporal/dedup engine) and confirmed it does not apply at v0 scope.

**Companion-distillation:** none authored (Round 1 consensus + probes were decisive; no novel analytical framework emerged that warrants standalone distillation per the ADR-0005 lock-cascade-deliberation pattern).

**Methodology observation:** the initial Test 3 finding ("Graphiti is more viable than expected") was a Pydantic-interface-surface test that did not exercise runtime behavior. The Pydantic models validated cleanly in isolation, but the `add_triplet` → `resolve_extracted_edges` → LLM call path was invisible at that test level. The multi-expert deliberation surfaced the runtime concern (Lens 4) that the empirical Pydantic test missed. Pattern: **type-system tests are insufficient to evaluate runtime-coupling concerns**; future "library viability" probes should include at least one end-to-end behavior check before drawing conclusions.

---

*Companion artifacts: `docs/research/phase-3-hands-on-results-2026-05-18.md` (Phase 3 test outcomes including Test 3 + Round 1 deliberation summary). Updates downstream: `docs/product/v0 spec` Week 6 section (GraphLayer contract + append-only + entity-resolution patterns).*
