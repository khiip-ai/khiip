# ADR-0001 — Genesis: Khiip scaffolding + Phase 1 research kickoff

**Status:** Accepted (2026-05-15); partially superseded by ADR-0003 on 2026-05-16 (strategic-lead framing only; technical sequencing B → A → C remains in force); partially superseded by ADR-0006 on 2026-05-18 (Shape C/D weighting refinement); partially superseded by ADR-0008 on 2026-05-19 (standalone-product framing + canonical edge vocabulary)
**Supersedes:** N/A (project genesis)
**Superseded by:** N/A

---

## Context

Prior to project genesis, a private research codebase accumulated a multi-platform capture substrate intended for ongoing research use. The substrate as it stood at project-genesis time:

- Multi-platform capture: X (deep — full QRT body, X-Article body + embedded images, view/bookmark/quote counts), Reddit, Instagram, TikTok, Threads, Bluesky (via gallery-dl), YouTube/podcasts (yt-dlp + Faster-Whisper local), PDF (MarkItDown), general web (ArchiveBox + Wayback)
- Per-post engagement time-series with decay cadence (4h → daily → weekly → monthly → quarterly) + velocity-spike re-densification on >3× baseline
- Multi-vendor LLM dispatcher (Anthropic + OpenAI + Gemini; cost-logged; prompt-cached)
- Multi-vendor web search dispatcher (Brave + Exa + Anthropic-tool, with cross-vendor agreement scoring)
- Event-cluster resolution pipeline (given URL → finds related events via ensemble search → categorizes role → returns auto-resolve candidates)
- Typed knowledge graph with bitemporal `recorded_at` vs `valid_from` discipline
- L0 immutability + corrects/superseded_by chain
- Confidence labels (STABLE / PROVISIONAL / OPEN / WIP / AUDIT)
- Filesystem-canonical markdown + YAML + JSON-Schema validated

A multi-round multi-expert deliberation across 2026-05-14 and 2026-05-15 evaluated whether to productize this substrate as a standalone product. Findings:

1. **The conjunction is genuinely empty in the market.** No competitor combines bitemporal correctness + L0 immutable belief chain + typed semantic edge ontology + cross-platform web capture. Zep/Graphiti has bitemporal alone. Mem0 has distribution but shallow graph. Letta has agent runtime but no belief versioning. Anthropic Memory Tool is filesystem-level. OpenAI has explicitly ceded the memory problem to the ecosystem.

2. **AI-builder cohort emerged as the strongest anchor** in two independent expert lenses (niche validation + emergent threads analysis). Wallet $100-500/mo, ~30-80K addressable globally, current stack is duct-taped (Exa.ai + Jina Reader + custom scrapers + manual dedup), specific Discord channels and conferences map cleanly to GTM.

3. **Four product shapes surfaced**, not one. The substrate enables Shape A (developer API), Shape B (OSS package), Shape C (mass-market consumer app), Shape D (integration layer plugging into existing data sources). Shape D emerged 2026-05-15 from the "anti-AI consumer" + "plug into existing data" framing question and is potentially the strongest reframe (refined per ADR-0006).

4. **Anti-AI consumer positioning constraint surfaced** as load-bearing for Shape C/D — most everyday consumers in 2026 reject visible AI branding but accept invisible AI plumbing under clear-outcome experiences (Granola pattern).

## Decision

Scaffold a new standalone product/business — working name `ctx-WIP` at genesis; final name `Khiip` locked per ADR-0004.

**Lifecycle:** `active` from Day 1 (research-phase work begins immediately).

**Project type:** `research` initially (B2B API with external consumers pinning to versioned contracts needs ADR-per-decision discipline from Day 1). Graduate to `product` when lead shape locks and v0 build begins (Phase 4).

**Substrate-origin attribution:** capture pipeline patterns, bitemporal discipline, event-cluster resolution patterns derived from prior research codebase. Standalone repo is canonical work — no live dependency on the origin substrate (per ADR-0008 standalone-product lock).

**Research program structure:** 12 areas across 4 phases. Phase 1 wave 1 spawning Area 1B (persona × current-knowledge-management mapping) + Area 3 (pain point empirical surface) in parallel.

**What is NOT decided by this ADR:**
- Lead product shape (A / B / C / D / combination) — Phase 2 decision (resolved per ADR-0003 + ADR-0006)
- Hosted-SaaS vs OSS-only sequencing — Phase 2 hypothesis test (resolved per ADR-0003)
- Primary anchor persona — Phase 1B + Phase 4 decision
- Architecture details (storage, query interface, ingestion patterns) — Phase 3 Area 9 (resolved per ADR-0007)
- Pricing model — Phase 3 Area 10 (resolved per ADR-0002)
- Final product name — Phase 3 Area 12 (resolved per ADR-0004)
- Canonical edge vocabulary — Phase 3 Area 9 (resolved per ADR-0005 + ADR-0008)

## Consequences

### Positive

- Research-phase scaffold permits multi-expert deliberation discipline without committing to product shape prematurely
- Substrate-productization opportunity preserved at the moment competitive landscape research surfaced the genuinely empty conjunction (12-18 month moat lead window)
- Bitemporal + L0 immutability + typed-edge discipline carry forward as industry-standard patterns adapted to the standalone product
- Working-name placeholder at genesis allowed deliberate naming research (Phase 3 Area 12 → ADR-0004 Khiip)

### Negative

- Research-phase elapsed time ~3-4 weeks before v0 build begins; willingness-to-pay still SPECULATIVE until Phase 4 spec + first beta cohort
- Initial framing as "sibling of a methodology framework" partially superseded by ADR-0008 standalone-product lock; subsequent decision documents (ADRs 0005, 0007) authored under the framing-being-superseded but remain in force on their actual decisions

### Neutral

- Voice: professional (analytical-direct, em dashes allowed, structured choice presentation)

## References

- ADR-0003 — strategic positioning (LLM default ingestion layer; Shape A strategic lead; Shape B first ship)
- ADR-0004 — name lock (Khiip)
- ADR-0005 — hybrid edge typing (Option Δ; partially superseded by ADR-0008 on canonical-set spec)
- ADR-0006 — Shape D promoted as primary mass-market path
- ADR-0007 — graph layer architecture: custom SQLite
- ADR-0008 — standalone-product lock + Khiip-designed canonical edge vocabulary
