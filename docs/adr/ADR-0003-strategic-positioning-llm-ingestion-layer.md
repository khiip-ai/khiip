# ADR-0003 — Strategic Positioning: LLM Default Ingestion Layer

**Status:** Accepted as committed hypothesis (2026-05-16); revision triggers below
**Date:** 2026-05-16
**Supersedes:** N/A
**Partially-Supersedes:** ADR-0001 (strategic-lead framing only; technical sequencing B → A → C remains in force)
**Superseded by:** N/A
**Sources:** 4-expert deliberation on doc categorization (DOC1 Nygard / DOC2 OSS doc architecture / DOC3 strategic positioning / DOC4 cognitive load + IA) — outputs in tool-results dir.

---

## Context

ADR-0001 evaluated four product shapes (A developer API / B OSS plugin / C mass-market app / D integration layer) without committing to a strategic LEAD beyond the technical sequencing (B → A → C). Across sessions 2026-05-14 through 2026-05-16, the strategic positioning sharpened: ctx-WIP is positioning to become the substrate AI agents use to capture, store, and recall data from online sources — i.e., the "LLM default ingestion layer."

This framing was not fully anticipated by ADR-0001. Specifically:

1. **Competitive set expansion.** Original framing positioned Mem0/Zep/Letta as Shape A's primary competitive set. New framing adds Firecrawl, Jina Reader, Crawl4AI, Tavily, Exa as direct competitors — the "URL → LLM-ready content" tools AI builders currently compose into their stacks.

2. **Distribution channel evolution.** Original framing assumed Shape A distribution via developer channels (Latent Space, AI Engineer Summit, LangChain Discord). New framing adds MCP server distribution into Claude Desktop / Cursor / Windsurf / any MCP-aware client as a primary distribution channel — pull-through model rather than demand-gen alone.

3. **Moat strategy refinement.** Original moat thesis: bitemporal correctness + L0 immutability + typed graph (technical correctness). New framing adds composability + plugin ecosystem + MCP-standard adoption as compounding network-effect moats. These compound differently — technical moats are strong Day 1 but don't scale with adoption; ecosystem moats are weak Day 1 but dominant at scale.

4. **Strategic lead commitment.** Original framing did not name a strategic LEAD; four shapes were "in parallel evaluation." New framing commits Shape A as the strategic lead (long-term TAM + moat compounding + ecosystem play), while preserving Shape B as the technical ship-first surface (validates substrate quality via Obsidian J6 moat inheritance).

### Competitive landscape as of May 2026

- **Firecrawl** — converts URLs to LLM-ready markdown; growing fast; stateless (every call is fresh fetch); no temporal awareness; limited structured social capture
- **Jina Reader** — `r.jina.ai/{url}` pattern; lightweight; same statelessness
- **Crawl4AI** — OSS alternative to Firecrawl
- **Tavily / Exa / Perplexity Sonar** — real-time search + retrieval; different shape than persistent capture
- **Mem0 / Zep / Letta / Cognee** — agent memory; assume data already acquired; don't do capture
- **Anthropic MCP server ecosystem** — emerging standard for agent tool integration; pre-standardization moment

**The empty space:** No competitor combines structured multi-platform capture (X QRT chains + Reddit + IG + TikTok + web + PDF + video) + bitemporal correctness + persistent typed-edge knowledge graph + local-first option + unified API. The conjunction is uncontested as of May 2026.

### Karakeep as closest holistic competitor

Per 2026-05-16 verification of karakeep.app: Karakeep is a destination (bookmark store + UI + database) with its own AI tagging layer. It is parallel to ctx-WIP, not stacked beneath it. We don't integrate AS ctx-WIP with Karakeep; we compete on a different axis (substrate-layer vs destination). Karakeep has user-visible surface advantages (mobile apps, browser extensions, cloud beta + self-hosted Docker, 24K GitHub stars) but lacks bitemporal model + L0 immutability + typed graph + structured social capture depth.

## Decision

ctx-WIP positions as the **LLM default ingestion layer**: the substrate AI agents use to capture, store, and recall data from online sources.

**Strategic lead:** Shape A (developer API + MCP server) is the strategic lead. Long-term TAM is bigger than PKM tool space alone; moat compounding (ecosystem adoption + composability) is more durable; competitive positioning against fragmented current solutions (Firecrawl + Mem0 + Tavily + custom code) is genuinely empty.

**Technical sequencing unchanged from ADR-0001:** Shape B (Obsidian plugin + standalone daemon) ships first because it inherits Obsidian's J6 (workflow continuity) moat for free (9/10 score on day one) and validates substrate quality. Shape A ships second on the same substrate. Shape C deferred until first two validate.

**Distribution path:**

```
Month 1-2:  Shape B v0 (Obsidian plugin + daemon)
            — validates substrate; inherits J6 moat
            
Month 3-4:  Shape A v0 (REST API + MCP server)
            — MCP server is load-bearing for pull-through distribution
            — MCP server addressable from Claude Desktop / Cursor /
              Windsurf / any MCP-aware client
              
Month 4-5:  LangChain integration (community PR submission to add
            ctx-WIP as memory/loader option)
            
Month 5-6:  LlamaIndex LlamaHub connector (similar PR submission)
            
Month 6-12: Become recognized memory-substrate option in agent-builder
            content (Latent Space podcast, AI Engineer Summit talks,
            framework documentation)
            
Year 2:     Integration into 2-3 major agent frameworks as standard
            memory/capture option (CrewAI, AutoGen, Pydantic-AI, etc.)
            
Year 3+:    Recognized "Stripe of agent memory" infrastructure;
            possible Anthropic/OpenAI dev rel recommendation
```

**Moat strategy (sequenced):**

- **Short-term (months 1-12):** Capture quality differentiation — structured social capture; X QRT chains + X-Article inline images + engagement metrics; gallery-dl + fxtwitter maintenance dedication. Execution moat; clonable in 3-6 months by motivated competitor.

- **Medium-term (year 1-2):** Architectural depth — bitemporal correctness + L0 immutability + corrects:/superseded_by: chain + typed-edge graph. Hard to retrofit; takes architectural commitment from Day 1.

- **Long-term (year 2-7+):** Composability + plugin ecosystem + MCP-standard adoption. Network effects compound. Switching cost grows with integration density. Stripe/Twilio/Vercel playbook applied to agent capture + memory infrastructure.

## Consequences

### Positive

- **Bigger TAM.** AI agent ecosystem ($8.3B 2025 → $12B 2026, ~45% CAGR per Precedence Research) vs PKM tool space alone. Riding category tailwind.
- **Genuinely empty competitive position.** No single tool combines capture + storage + recall + bitemporal + structured social + local-first. Conjunction is uncontested.
- **Architectural fit.** Substrate already has the right primitives. Not building NEW capability; surfacing existing capability under sharper positioning.
- **Distribution leverage.** MCP server addresses any MCP-aware client. Pull-through distribution higher-leverage than demand-gen-only.
- **Composability moat compounds.** Every downstream tool built on Khiip = switching-cost barrier.
- **Cross-shape leverage.** Shape A generates downstream tools that integrate with Shape B users. Shape B users invite friends to eventual Shape C. Each shape feeds the others; isolated competitor can't replicate without all three.

### Negative

- **Larger competitive set.** Now competing simultaneously with capture tools (Firecrawl/Jina), memory tools (Mem0/Zep), search tools (Tavily/Exa). Different cohorts with different conversion patterns.
- **Different GTM motion.** Pull-through (MCP distribution) requires different investment than demand-gen (content marketing). MCP server must ship with high polish.
- **ADR-0002 pricing assumption review required.** Shape A pricing ($49 Builder / $149 Studio / $500 Enterprise floor) was set against Mem0/Zep anchors. Firecrawl + Tavily have different pricing patterns. Revisit in Phase 2 strategic synthesis.
- **AGPL license interaction with MCP.** MCP servers run locally; AGPL "SaaS loophole" doesn't apply, but ensuring MCP wrapper code is properly licensed (AGPL daemon + Apache 2.0 MCP wrapper?) needs explicit decision in Phase 3 architecture.
- **Increased ecosystem dependency.** If MCP fragments or fails to standardize, distribution-channel assumption breaks. Mitigation: REST API distribution remains primary even if MCP fizzles.
- **Higher distribution risk from incumbents.** Anthropic / OpenAI shipping native first-party memory in their SDKs becomes existential threat (vs incidental concern under original framing).

### Neutral

- **Technical sequencing unchanged.** Shape B still ships first because it inherits Obsidian J6 moat. Shape A's strategic lead is about LONG-TERM positioning, not Month-1 deliverables.
- **JTBD wins unchanged.** J11 (temporal correctness for AI builders), J1 (loss prevention for mass-market), J6 (workflow continuity for power-users via Obsidian) all still in force.
- **Promise charter unchanged.** ADR-0002's 8 promises still load-bearing. Refined Promise 3 (split into content training / telemetry / aggregate research) still pending founder lock.
- **D4 + D7 architecture decisions unchanged.** Tiered LLM fallback (bundled small model → Ollama → BYOK → BM25); API key auto-generated at install.

## Alternatives considered

- **Status quo (4-shape parallel evaluation):** Rejected. Doesn't force architectural commitments (MCP, LangChain integration) needed for ecosystem play. Leaves competitive set under-specified. Future contributors can't tell what we're optimizing for.
- **Pure Shape B PKM-tool focus:** Rejected. Smaller TAM ceiling (Obsidian ~1.5M MAU; Karakeep ~24K stars). Weaker moat — capture quality is execution-moat that motivated competitor clones in 3-6 months.
- **Pure Shape C consumer-app focus:** Rejected. Requires mobile UX investment we don't have at v0. Apple Notes + Apple Intelligence is invisible incumbent for 75%+ of US mobile users — wrong fight at this stage.
- **Lead with Shape A but reverse technical sequencing (A ships first, then B):** Rejected. Loses Obsidian J6 moat inheritance for Shape B; loses fast time-to-first-feedback via Obsidian plugin marketplace. Strategic lead doesn't require first-ship; technical sequencing decisions in ADR-0001 hold.
- **Direct Firecrawl competition without MCP / agent-memory framing:** Rejected. Firecrawl is well-funded and rapidly closing feature gaps; competing head-on on capture-only is a losing position. The MCP + persistent memory + bitemporal differentiation is what makes ctx-WIP not-Firecrawl.

## Revision triggers

This positioning is committed as a hypothesis. Revisit when any fires:

1. **First 5 paying customers reveal positioning misfit.** If AI builders consistently say "this isn't the substrate we needed" or "we'd rather Firecrawl + custom memory," the LLM-default-ingestion-layer hypothesis is wrong.
2. **Firecrawl ships bitemporal + structured social capture.** Closes the architectural-depth gap. Forces ctx-WIP to re-differentiate.
3. **Anthropic / OpenAI ships native long-term memory in SDKs.** Changes competitive landscape for agent memory; ctx-WIP needs to position as cross-provider neutral layer.
4. **MCP standardization fails or fragments.** Distribution-channel assumption breaks. REST API + framework integrations become sole distribution.
5. **6 months elapsed (by 2026-11-16) without measurable progress toward "default substrate" recognition** (no major framework integration shipped, no MCP server distribution traction, <100 paying API customers). Reassess positioning vs alternative paths.
6. **Founder bandwidth diverges from required GTM motion.** Pull-through MCP distribution requires consistent ecosystem investment. If solo + AI-augmented capacity is genuinely insufficient and hiring isn't viable, reassess scope.

## Strategy doc trigger

Per the 2026-05-16 4-expert deliberation: do NOT create `docs/strategy/` directory yet. Trigger to create `docs/strategy/positioning.md` and migrate elaboration content from this ADR:

- This ADR exceeds ~300 lines OR
- Positioning content needs to update faster than ADR supersession discipline allows (more than ~quarterly revision) OR
- Future ADR-0004+ on related strategic decisions creates pattern of cross-referencing the same elaboration content

When any of those triggers fires, migrate ELABORATION content to `docs/strategy/positioning.md`; this ADR stays as the immutable decision record; strategy doc holds the living elaboration; cross-link both ways.

## References

- ADR-0001 — Genesis (status updated 2026-05-16 to reflect partial supersession of strategic-lead framing)
- ADR-0002 — Pricing + Promises + Free-layer scope (pricing assumptions to revisit against expanded competitive set per Consequences above)
- JTBD framework v0.1 (internal methodology doc) — load-bearing for evaluating positioning fit
- `~/.claude/plans/productize-capture-substrate-strategic-positioning-quiet-falcon.md` — prior strategic-positioning analysis
- 4-expert doc-categorization deliberation outputs (in tool-results) — Nygard / OSS doc architecture / strategic positioning / cognitive load + IA
- karakeep.app fetch 2026-05-16 — confirmed competitive position as destination not layer
- `CHRONICLE.md` entries 2026-05-15 (v3) + 2026-05-16 — strategic discussion thread distilled into this ADR
