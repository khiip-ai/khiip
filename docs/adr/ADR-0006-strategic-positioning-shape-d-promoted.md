# ADR-0006 — Strategic Positioning Refinement: Shape D Promoted as Primary Mass-Market Path; Shape C Downgraded to ~20% Probability Future Option

**Status:** Accepted (2026-05-18)
**Supersedes:** N/A — refines ADR-0001 + ADR-0003 strategic-positioning framing on mass-market path; technical architecture in ADR-0003 (Shape A strategic lead, Shape B first ship) remains in force
**Partial-supersedes:** ADR-0001 (Four product shapes section) — Shape C/D weighting updated; technical sequencing for Shape A + B unchanged
**Superseded by:** N/A

---

## Context

ADR-0001 (genesis) identified four product shapes for evaluation: Shape A (developer API for AI builders), Shape B (OSS package + Obsidian plugin), Shape C (mass-market consumer PKM app), Shape D (integration layer that writes to user's existing data sources).

ADR-0003 (2026-05-16) locked strategic positioning as "LLM default ingestion layer" with sequencing: Shape B first (validates substrate) → Shape A strategic lead (revenue path) → Shape C deferred (gated on B+A validation).

Shape D was mentioned in ADR-0001 but did NOT receive explicit treatment in ADR-0003. The strategic positioning analysis at the time focused on Shape A (AI builder API) as the strategic lead because:
- Wallet-per-user is highest for AI builders ($100-$2K/mo)
- The "LLM default ingestion layer" framing aligns most cleanly with Shape A
- Shape A had highest technical defensibility via substrate moat

Shape C (mass-market hosted app) was implicitly treated as the "eventual mass-market path" because that's the conventional progression for OSS infrastructure → mass-market consumer apps (PostHog at $1.25B, Cal.com at $230M, Plausible at $3M ARR all followed this pattern).

A multi-message strategic conversation 2026-05-18 surfaced that the conventional Shape C path may not be the right mass-market expansion for Khiip specifically. Founder articulated:

> "Audience C down the road is maybe create a system that writes to where a user would most likely already have their notes or document system. or we have an app that is hosted for people to use for more everyday users. not sure what this shape looks like."

This bifurcated the previously-conflated "Shape C" into two distinct shapes with different architectures + business models:

1. **Shape C (original framing):** Hosted Khiip app — Khiip cloud-stores user data; native mobile + web app; commodified PKM/bookmarking competitor (Pocket / Instapaper / Readwise / Matter category)
2. **Shape D (newly distinguished):** Integration layer — Khiip captures + processes content and writes to wherever the user already keeps things (Notion / Apple Notes / Google Drive / OneNote / Logseq / etc.); user's data stays in their existing system

These are different products with materially different strategic implications. The 2026-05-18 conversation analyzed them across architectural fit, market dynamics, build complexity, and alignment with Khiip's strategic positioning per ADR-0003.

## Decision

**Shape D promoted to primary mass-market expansion path.** Shape C downgraded to ~20% probability future option.

### Reframed shape definitions (replaces ADR-0001 four-shape definitions for Shape C/D specifically)

**Shape A (UNCHANGED per ADR-0003):** Developer API + MCP server for AI builders. REST + MCP. $49-$2K/mo. Hosted SaaS. Strategic LEAD for revenue.

**Shape B (UNCHANGED per ADR-0003):** Self-hosted OSS package + Obsidian plugin + daemon. Free OSS + optional paid hosted. Ships first to validate substrate quality.

**Shape C (DOWNGRADED per this ADR):** Hosted mass-market consumer app (Pocket-replacement category). Probability of building: ~20%. Triggers: massive Shape A + B success + clear competitive opening + dedicated team to compete with Readwise/Matter/etc. + capital for marketing spend. Default expectation: Shape D captures most of the mass-market need; Shape C only built if a specific mass-market gap remains.

**Shape D (PROMOTED per this ADR):** Integration layer that captures content from anywhere and writes it to the user's existing PKM/notes/document system. Probability of building: ~70% conditional on Shape A + B success. Trigger: post Shape A revenue validation + specific user demand for destinations (most likely first: Notion).

### Architecture for Shape D

Same Khiip daemon (Shape B foundation) with destination-specific write adapters:

| Destination | Write surface | Estimated build per integration | Tier |
|---|---|---|---|
| Obsidian / Logseq / plain Markdown vault | Filesystem (already supported) | n/a (works at v0) | n/a |
| Notion | Public API | 2-3 weeks | Tier 1 (most-requested) |
| Google Drive / Google Docs | Drive API + Docs API + OAuth | 2-3 weeks | Tier 1 |
| Apple Notes | CloudKit / AppleScript bridging | 4-6 weeks (no public API) | Tier 2 |
| Microsoft OneNote | Graph API | 2-3 weeks | Tier 2 |
| Tana | Tana Input API | 1-2 weeks | Tier 3 (smaller user base) |
| Mem.ai | API | 1-2 weeks | Tier 3 |
| Roam Research | API + datalog | 2-3 weeks | Tier 3 |
| Evernote | API (declining service) | 2 weeks | Tier 4 (low priority — declining) |

Tier 1 destinations cover ~60% of PKM-tool market share (Notion ~30M MAU, Google Docs ~1B+ users). Build Tier 1 first; Tier 2-4 driven by user demand.

### Business model for Shape D

Per-destination subscription model (different from Shape A's API tiers or Shape B's per-individual tiers):

- **Free (Shape B baseline):** Captures to user's filesystem (Markdown vault) — works for Obsidian / Logseq / any Markdown PKM
- **Khiip Connect Pro:** ~$15/mo. Includes 1 cloud destination (Notion OR Google Drive OR OneNote). All Khiip's capture quality + bitemporal + typed graph translated to destination's native format
- **Khiip Connect Plus:** ~$25/mo. Up to 3 cloud destinations + cross-destination sync
- **Khiip Connect Enterprise:** Custom. Multiple destinations + team workspaces + audit logs + SSO when destinations support it

Pricing TBD at Shape D v0 spec authoring; numbers above are illustrative. Architecture is per-destination subscription rather than per-feature.

### Strategic positioning per Shape

| Shape | Positioning narrative | Buyer | Revenue model |
|---|---|---|---|
| **A** | "API for AI memory infrastructure" | AI builders | $49-$2K/mo SaaS |
| **B** | "Capture anything; store locally; recall by meaning" | Obsidian power-users + self-hosters | Free + $8-49 LTD + hosted free + $8-16/mo Personal/Power |
| **C** (deferred) | "Save anything from anywhere; access from any device" | Mass-market consumers replacing Pocket | $5-15/mo (if built) |
| **D** (promoted) | "Capture quality you can't build yourself, writing to wherever you already keep things" | PKM users who already use Notion / Apple Notes / Google Drive | $15-25/mo per destination |

### Why Shape D fits Khiip's strategic positioning better than Shape C

Six dimensions:

| Dimension | Shape C (hosted) | Shape D (integration) |
|---|---|---|
| **Match to "Local by Default" Promise 2** | ❌ Cloud-locked | ✅ User's data stays in their system |
| **Anti-extraction protection** | ⚠️ Khiip cloud = single point of vendor lock-in | ✅ User can leave anytime (their data is in their PKM tool) |
| **Architectural alignment with substrate thesis** | ❌ Khiip becomes destination | ✅ Khiip stays substrate; routes to destinations |
| **Competitive density** | Very high (Readwise / Matter / Instapaper / Reader / Anytype) | Low (no one specifically does multi-destination capture quality) |
| **Marketing spend required** | High (mass-market acquisition) | Lower (target PKM communities directly) |
| **Revenue per user** | $5-15/mo (commodity pricing) | $15-25/mo (unique value) |

Shape D matches the strategic positioning of ADR-0003 ("LLM default ingestion layer") and the architectural commitments of ADR-0002 (Promise 2: Local by Default; Promise 6: Your Data, Your Export). Shape C fights against both.

### Why we're not killing Shape C entirely

~20% probability retained because:
- If Shape D fails to capture mass-market for unforeseen reasons, Shape C is the backup path
- If Pocket's mass-market vacuum remains uncaptured by competitors, opportunity may emerge
- If specific market signals indicate mass-market consumer wants "all-in-one Khiip app" instead of "Khiip writes to my existing system," reconsider
- Strategic optionality has zero cost as long as no architectural commitments are made

Trigger to revisit Shape C: emergence of large-cohort user research showing >50% of mass-market PKM-curious users specifically want hosted-app pattern over integration pattern. Realistically, this would only emerge from extensive customer research in Year 2+.

## Consequences

### Positive

- **Strategic clarity** — Shape A (revenue lead) + Shape B (validation foundation) + Shape D (mass-market expansion) is a coherent three-shape strategy aligned with substrate positioning
- **Competitive differentiation preserved** — Shape D is uncontested; Shape C would have been crowded
- **Promise 2 (Local by Default) preserved at scale** — Shape D writes to user's system; user data sovereignty maintained
- **Architectural reuse** — Shape D extends Shape B's daemon via write adapters; no separate codebase
- **Revenue economics improved** — Shape D's $15-25/mo per destination beats Shape C's $5-15/mo commodity pricing
- **Acquisition optionality** — at maturity, Shape D could be acquired by Notion / Google / Microsoft as part of their PKM strategy; Shape C would compete with Readwise/Matter for same acquirer base
- **Distribution alignment** — Shape D targets PKM communities where Khiip already has Shape B presence (Obsidian power-users → Notion crossover users)

### Negative

- **Per-destination build cost** — each integration is 2-6 weeks of work; building 5 destinations is a major Month 9-15 commitment
- **Ongoing maintenance burden** — each destination API can break, change, or rate-limit. Maintaining 5+ integrations indefinitely is real operational cost
- **Apple Notes specifically is technically hard** — no public API; CloudKit/AppleScript bridging is fragile. Apple Notes users may have to wait years for support
- **Some users won't migrate from Pocket-replacement expectations** — those who specifically want "single app where everything lives" won't be served by Shape D; they'd need Shape C
- **Marketing complexity** — explaining "Khiip writes to your Notion" is more nuanced than "save articles to read later"; education cost is higher

### Neutral

- **ADR-0003 strategic positioning text references Shape C without distinguishing from Shape D** — those references stay as historical record; ADR-0006 (this ADR) is the canonical refinement going forward
- **v0-spec.md Future Shapes Roadmap section** updated to reflect Shape D promotion (downstream update, not part of this ADR)
- **Pricing structure for Shape D deferred to Shape D v0 spec authoring** — numbers above are illustrative; will be refined Month 9+
- **Build sequencing** — Shape D first destination earliest Month 9-12 (post Shape A revenue validation); not pulled forward into Khiip v0 or v0.5

## References

- `docs/adr/ADR-0001-genesis.md` — original four-shape definitions (Shape C/D distinction was less explicit)
- `docs/adr/ADR-0003-strategic-positioning-llm-ingestion-layer.md` — strategic positioning; Shape A as lead, Shape B as ship-first, Shape C as deferred
- `docs/adr/ADR-0002-pricing-promises-free-layer.md` — Promise 2 (Local by Default) + Promise 6 (Data Portability); architectural commitments Shape D honors better than Shape C
- 2026-05-18 strategic conversation in CHRONICLE — full deliberation transcript including the Shape D vs Shape C analysis
- Pocket shutdown analysis (July 2025) — original mass-market trigger
- Readwise / Matter / Instapaper / Anytype competitive landscape — what Shape C would have to fight; Shape D sidesteps

## Disposition tracking

| Item | Owner | Deadline | Status |
|---|---|---|---|
| Update v0-spec.md "Future Shapes Roadmap" section per Shape D promotion + Shape C downgrade | Assistant | 2026-05-18 | IN PROGRESS this session |
| Update HANDOFF.md "Cross-sibling context" or shape-summary references | Assistant | 2026-05-18 | IN PROGRESS this session |
| Update README.md Strategic positioning section | Assistant | 2026-05-18 | IN PROGRESS this session |
| Author Shape D v0 spec when Shape A revenue validation completes | Founder + Assistant | Month 9-12 | OPEN |
| Conduct user research on Shape D destination priority (Notion vs Google vs Apple Notes vs others) | Founder | Month 6-9 | OPEN |
| Build Shape D first destination | Founder + Assistant | Month 9-12 estimate | OPEN |
| Revisit Shape C trigger evaluation annually | Founder | Year 2 onward | OPEN |
