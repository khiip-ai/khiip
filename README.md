# Khiip

> The substrate AI agents use to capture, store, and recall data from online sources.

**Khiip** (pronounced /kiːp/, like *"keep"*) — short for **Khipu**, the Inca knot-record system that was the world's first typed-edge knowledge graph.

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_3.0-blue.svg)](LICENSE)
[![Status: Pre-launch](https://img.shields.io/badge/Status-Pre--launch-orange.svg)](#current-status)
[![Code of Conduct](https://img.shields.io/badge/Code_of_Conduct-Contributor_Covenant_2.1-purple.svg)](CODE_OF_CONDUCT.md)

---

## What Khiip is

A capture + storage + recall substrate. You point Khiip at a URL, PDF, X thread, YouTube video, or other online content — Khiip captures it fully, stores it permanently in your own filesystem, and lets you (or your AI agents) recall it later by meaning, structure, or time.

Khiip is **the layer, not the destination.** Other tools (Obsidian, Logseq, LangChain agents, custom scripts) sit on top and consume what Khiip captures.

**Verb usage:** *to khiip* — "I want to khiip this article" / "khiip that thread for later"

**Plural:** *khiips* — the captured artifacts in your vault

---

## What Khiip does

| Capability | What it means |
|---|---|
| **Multi-platform capture** | X (full QRT chains + X-Article body + embedded media + engagement metrics), web articles, PDFs, YouTube (metadata + transcripts). Reddit, Instagram, TikTok, Threads, Bluesky on roadmap |
| **Local-first storage** | Captures land in your filesystem as Markdown + YAML frontmatter + media files. Your vault is authoritative. You can `rm -rf` Khiip's daemon store and rebuild from your vault |
| **Bitemporal model** | Every capture records both `recorded_at` (when Khiip fetched) and `valid_from` (when data was true in the world). Point-in-time queries answer "what did this article say on date X" |
| **Typed knowledge graph** | 5 first-class edge types (SUPPORTS, CONTRADICTS, SUPERSEDES, ELABORATES, REFERENCES) + RELATES escape for novel relationships (per [ADR-0008](docs/adr/ADR-0008-standalone-vocabulary.md)). Hybrid model gives you deterministic queries AND novel-relationship coverage |
| **Tiered AI recall** | Bundled embedding model → local LLM (Ollama) → BYOK (OpenAI/Anthropic/Gemini) → BM25 keyword fallback. Quality scales with what you configure; works out of box without any AI |
| **Open + portable** | AGPL-3.0 daemon + Apache 2.0 SDK. No vendor lock-in. Filesystem-canonical. Export in Markdown, YAML, or JSON at any time |

---

## Strategic positioning

Khiip is the **LLM default ingestion layer** — the substrate AI agents use to capture, store, and recall data. Three product shapes sequenced:

- **Shape B** (ships first, Month 1-2): Obsidian plugin + Python daemon. Power-users + self-hosters.
- **Shape A** (strategic lead, Month 3-5): REST API + MCP server. AI builders integrating Khiip into agent workflows.
- **Shape D** (Month 9-12, gated on B+A validation): Integration layer that writes to your existing PKM (Notion / Apple Notes / Google Drive). Mass-market consumer path.

Same daemon, multiple surfaces. See [ADR-0003](docs/adr/ADR-0003-strategic-positioning-llm-ingestion-layer.md) for full positioning.

---

## Current status

**Pre-launch.** All foundational ADRs LOCKED; Week 1 v0 build unblocked on architectural-decision grounds.

- ✅ Strategic positioning locked (ADR-0003)
- ✅ Name + brand locked (ADR-0004)
- ✅ Pricing + 8 immutable promises locked (ADR-0002)
- ✅ Hybrid edge typing + Option Δ interpretability locked (ADR-0005)
- ✅ Shape D promoted as primary mass-market path (ADR-0006)
- ✅ Graph layer architecture locked: custom SQLite (ADR-0007)
- ✅ Standalone-product lock + Khiip-designed 5+1 canonical vocabulary (ADR-0008)
- ✅ v0 product spec promoted to load-bearing
- ⏳ Week 1 v0 build kickoff
- ⏳ Public launch (Week 7-8 target)

---

## Read order for deeper context

If you're evaluating Khiip as a contributor, integrator, or potential user, read the architectural decision records in this order:

| File | What it tells you |
|---|---|
| **[docs/adr/ADR-0001-genesis.md](docs/adr/ADR-0001-genesis.md)** | Why this project exists |
| **[docs/adr/ADR-0003-strategic-positioning-llm-ingestion-layer.md](docs/adr/ADR-0003-strategic-positioning-llm-ingestion-layer.md)** | Strategic positioning + competitive landscape + Shape A/B sequencing |
| **[docs/adr/ADR-0002-pricing-promises-free-layer.md](docs/adr/ADR-0002-pricing-promises-free-layer.md)** | Pricing model + 8 immutable promises + free-vs-paid feature scope |
| **[docs/adr/ADR-0004-naming-lock-khiip.md](docs/adr/ADR-0004-naming-lock-khiip.md)** | Name + brand mechanics + etymology |
| **[docs/adr/ADR-0005-hybrid-edge-typing.md](docs/adr/ADR-0005-hybrid-edge-typing.md)** | Edge typing architecture: canonical + LLM-emergent hybrid + Option Δ interpretability refinements |
| **[docs/adr/ADR-0006-strategic-positioning-shape-d-promoted.md](docs/adr/ADR-0006-strategic-positioning-shape-d-promoted.md)** | Mass-market path: Shape D promoted; Shape C downgraded |
| **[docs/adr/ADR-0007-graph-layer-custom-sqlite.md](docs/adr/ADR-0007-graph-layer-custom-sqlite.md)** | Graph layer architecture: custom SQLite + append-only correction chain |
| **[docs/adr/ADR-0008-standalone-vocabulary.md](docs/adr/ADR-0008-standalone-vocabulary.md)** | Standalone-product lock + Khiip-designed canonical edge vocabulary (5 typed + RELATES escape) |
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | How to contribute (when v0 ships) |

---

## Get involved

Khiip is in **early development** — code surface is currently scaffolding + ADRs. Until v0 ships (target Week 7-8 of 2026):

- ⭐ **Star the repo** if you want to follow along
- 💬 **Watch the repo** for releases (you'll get notified when v0 ships)
- 📧 **Get on the launch list** by emailing hello@khiip.com with subject "launch list"
- 🐛 **Issues + PRs** — see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines (low ceremony until v0)
- 🔒 **Security disclosures** — see [SECURITY.md](SECURITY.md)
- 🤝 **Code of Conduct** — [Contributor Covenant 2.1](CODE_OF_CONDUCT.md)

---

## Why "Khiip"?

The Inca **khipu** (or *quipu*) was a knotted-cord recording system used from approximately 2500 BCE to the 17th century to encode numerical, narrative, and relational information. Each cord type, knot placement, and color encoded different categories of data. The **khipukamayuq** was the trained specialist who could read and create the records — essentially the human "agent" interacting with the structured substrate.

Khiip is the digital equivalent: a substrate that captures information from anywhere on the internet and stores it in a structured, typed, queryable form — for AI agents (the modern khipukamayuq) to read and create.

The "ii" spelling distinguishes from the homophonous "keep" while preserving the Khipu etymological root. Pronounced /kiːp/ — same as "keep."

---

## License

Daemon, plugin, and substrate code: **AGPL-3.0** (see [LICENSE](LICENSE))

SDK code (separate repository when published): **Apache 2.0**

The substrate is permanently open-source per [Promise 1](docs/adr/ADR-0002-pricing-promises-free-layer.md) of the immutable promise charter. We cannot retroactively close the substrate license; AGPL-3.0 for distributed code is irrevocable.
