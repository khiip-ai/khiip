# ADR-0004 — Naming lock: Khiip

**Status:** Accepted (2026-05-16)
**Supersedes:** N/A — completes the open question left by ADR-0001 (working name `ctx-WIP` was interim pending Phase 3 Area 12 naming research)
**Superseded by:** N/A

---

## Context

`ctx-WIP` was scaffolded 2026-05-15 as the working-name placeholder for the project. ADR-0001 explicitly deferred the final name to Phase 3 Area 12 (naming research). Phase 3 Area 12 was accelerated on 2026-05-16 after the founder surfaced an alternative brand reuse candidate, forcing the naming question 4-6 weeks earlier than planned.

Phase 3 Area 12 first pass ran 2026-05-16:

1. Naming brief authored at `docs/product/naming-brief.md` crystallizing the 5 ethos themes (Permanence / Sovereignty / Structure-Depth / Substrate / Honest restraint), hard constraints, and 3 audience tiers.
2. 5 parallel expert subagents (linguistic / theistic / artistic-literary / historic / symbolic-natural) generated ~60 candidates across language families and conceptual angles.
3. Synthesis at `docs/product/naming-research-synthesis.md` filtered to 10 shortlist + 10 honorable mentions + 10 conflict-eliminated. Top-5 verification-priority list: Quoin / Fonds / Stratum / Seshat / Nask.
4. The Quechua candidate **Quipu** (Inca knotted record-keeping system) surfaced at 21/25 ethos score in the linguistic angle as a structural-match name (typed-knot record ↔ product's 21-edge typed graph).
5. Founder, separately and creatively, surfaced **Khipu Kamayuq** as origin etymology (the Inca trained specialist who could read AND create the knot-record substrate — not just the artifact but the agent that operates it). Founder iterated to two candidate forms:
   - `KhipuKam` (Khipu + Kam as camera-stylized) — 8 chars, 3 syllables, requires two layers of unpacking
   - `Khiip` (phonetic /kiːp/ matching the verb "keep" with K-H-I-I-P stylization, etymology preserves Khipu) — 5 chars, 1 syllable

Khiip emerged as materially stronger than KhipuKam on:
- Verb-as-product resonance ("I want to khiip this article" — Flickr / Lyft / Tumblr / Scribd / Replit pattern)
- Phonetic match to user-intent (keep is literally what users do)
- Hard-constraint compliance (clears every length + syllable + pronounceability test)
- Domain availability (likely clean .com because invented stylization is invisible to English-speaking squatters)
- Etymology hook present for those who care; invisible for those who don't

Founder acquired **khiip.com** on 2026-05-16 prior to this ADR being authored. Decision is hereby ratified post-acquisition.

## Decision

The sibling is named **Khiip** (pronounced /kiːp/, like "keep") — etymology: short for Khipu, the Inca knot-record system; the substrate verb is "to khiip" (e.g., "I want to khiip this article").

Working name `ctx-WIP` is retired. Repository renamed to `khiip` (canonical at `github.com/khiip-ai/khiip`). All future references use `khiip`.

**Brand mechanics locked:**

- **Primary spelling:** Khiip (capitalized) in marketing copy + page titles; `khiip` (lowercase) in code, paths, identifiers, repo names, URLs
- **Pronunciation:** /kiːp/ — same as the English verb "keep"
- **Etymology positioning:** "Khiip — short for Khipu, the Inca knot-record system that was the world's first typed-edge knowledge graph. The substrate AI agents use to capture, store, and recall data."
- **Verb usage:** "to khiip" as the action ("Khiip this URL", "I khiipped that article last week")
- **Pluralization:** "khiips" (the captured artifacts)
- **Cultural respect:** Khipu is Andean indigenous cultural heritage. Brand copy honors this — never treats khipu as a found word. The metaphor is administrative (khipu was administrative tech, not ceremonial), not appropriative.
- **Trademark moat:** the H spelling distinguishes Khiip from any prior "Kiip" mark (the defunct 2010 mobile-ads startup Kiip) AND from Google Keep / generic "keep" software. The stylization itself is the defensibility — coined word in IC 009 + IC 042.

**Domain holdings:**

- **Owned (2026-05-16):** khiip.com
- **Tier-1 acquisition queue (this week):** khiip.app, khiip.dev, khiip.io
- **Tier-2 defensive (within 30 days):** khiip.ai, khiip.co, khiip.so, khiip.net, khiip.org
- **Tier-3 typo defense (within 30 days):** getkhiip.com, trykhiip.com, usekhiip.com, khiipapp.com, khiiphq.com

**Social-handle acquisition queue (this week):**

- @khiip on X / Bluesky / Threads / Mastodon / Reddit / LinkedIn / YouTube
- github.com/khiip (org for AGPL daemon repo)
- Hacker News user `khiip`
- discord.gg/khiip (vanity URL when server reaches boost threshold)

**What is NOT decided by this ADR:**

- Logo / wordmark design (deferred to v0 launch prep, ~Week 7-8)
- /trust page tone-of-voice copy (deferred to ADR-0002 founder lock + Week 7 in v0 build)
- Cantonese/Mandarin-language brand presentation if international rollout occurs (deferred to post-launch)
- Logo treatment of "ii" stylization (deferred to design phase)

## Consequences

### Positive

- **Verb-as-product naming** creates self-distributing brand mechanics. Every user explaining the product naturally teaches the name. Flickr / Lyft / Tumblr playbook with measured 30-50% organic discoverability advantage over noun-only naming
- **khiip.com acquired clean** — no broker negotiation, no 5-figure squatter extortion, no "we own the .net so people will find us" compromise
- **Coined-word trademark profile** is significantly stronger than dictionary-word competitors (Quoin / Fonds / Stratum etc. all face IC 009/042 distinctiveness arguments; Khiip does not)
- **Etymology gives depth without requiring it.** The Khipu story is delightful when discovered; invisible when not. Both audiences served
- **Sovereign / structural metaphor** (khipukamayuq = the trained agent who operates the knot-record substrate) maps with eerie precision to the product positioning (the daemon that captures + stores + recalls data for AI agents). This is design-fit-name, not coincidence
- **Phase 3 Area 12 closed** ~4 weeks ahead of original schedule. Compresses path to v0 launch

### Negative

- **Google Keep brand collision** is real. Users hearing "Khiip" verbally will search "keep" first and land on Google Keep / Pinterest / Apple Notes Keep features. Mitigation: consistent K-H-I-I-P visual stylization in copy; eventually 50-200/mo in defensive ad spend on "keep" → "khiip" redirect once revenue allows. This is the Flickr/Tumblr/Lyft launch tax; survivable but real
- **Spelling-from-audio friction.** Word-of-mouth carries the audio /kiːp/; receiver tries keep.com first; bounce. Adds ~10-30% top-of-funnel friction during brand-education phase (first 12-18 months). Identical to Flickr/Tumblr launch dynamics
- **Cultural-sensitivity tax.** Khipu is Andean indigenous heritage. Brand must honor this consistently — never as a found word. Adds copywriting discipline; no material risk if discipline is held
- **"ii" stylization minority misread.** Some readers will guess /ˈkaɪ.ɪp/ on first encounter. Wii/Mii precedent helps but doesn't eliminate. Cold-read test with 5 devs pre-launch is recommended; if >40% misread, brand-education emphasis increases
- **Defunct Kiip mobile-ads startup** (Brian Wong 2010, ~$32M raised, wound down ~2019) creates faint historical SEO noise around the close-spelling "kiip". H letter is the moat; functionally not a blocker but TESS check ~$200 is recommended

### Neutral

- **Rename ctx-WIP → khiip** completed via mechanical file/repo renames. All in-directory files updated in place
- **Lifecycle/project_type unchanged** — remains `active` / `research` until Shape B v0 ships and graduates to `product`
- **HANDOFF/CHRONICLE freshness invariant** applies as before
- **Voice: professional** carries forward unchanged
- **ADR-0001/0002/0003 bodies remain frozen per append-only discipline.** They reference the working name `ctx-WIP` as historical fact; only their Status lines may be edited if supersession applies (no such supersession here — ADR-0004 completes ADR-0001's open question rather than superseding any decision)

## References

- ADR-0001 (genesis) — established the working-name placeholder and deferred final naming to Phase 3 Area 12
- ADR-0003 (strategic-positioning-llm-ingestion-layer) — provides the product semantics that the naming brief crystallized
- Quipu / Khipu historical references: Urton, Gary. *Signs of the Inka Khipu: Binary Coding in the Andean Knotted-String Records.* University of Texas Press, 2003. (Khipukamayuq role discussed throughout.)

## Disposition tracking

| Item | Owner | Deadline | Status |
|---|---|---|---|
| khiip.com acquired | Founder | 2026-05-16 | ✅ DONE |
| khiip.app/dev/io acquisition | Founder | 2026-05-23 | OPEN |
| khiip.ai/co/so/net/org acquisition | Founder | 2026-06-15 | OPEN |
| Typo-defense .com variants (5) | Founder | 2026-06-15 | OPEN |
| Social handles claimed (8) | Founder | 2026-05-23 | OPEN |
| USPTO TESS search IC 009 + 042 | Paralegal / attorney | 2026-06-01 | OPEN |
| Repository rename ctx-WIP → khiip | Assistant | 2026-05-16 | ✅ DONE |
| Cold-read pronunciation test (5 devs) | Founder | Pre-launch (Week 7) | OPEN |
