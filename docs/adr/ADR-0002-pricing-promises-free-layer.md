# ADR-0002 — Pricing model + immutable promises + free-layer scope

**Status:** Accepted (2026-05-18; founder-locked all 8 decisions per `docs/adr/ADR-0002-decision-prep.md` recommendations with refinements documented below)
**Date:** 2026-05-15 (proposed); 2026-05-18 (accepted)
**Supersedes:** N/A
**Superseded by:** N/A
**Sources:** 4-expert deliberation (P1 pricing model architecture + P2 immutable promise discipline + P3 free-vs-paid layer design + P4 pricing psychology + competitive positioning) — outputs persisted to tool-results dir. Founder lock conversation 2026-05-18 covering license defensibility analysis + multi-audience cohort sizing + path-conditional optimization framework + Shape D vs Shape C reframing.

---

## Lock confirmations (2026-05-18)

All 8 open questions resolved. Decisions below are now LOCKED and constrain all future commercial + community-trust artifacts.

### D1 — License: AGPL-3.0 daemon + Apache 2.0 SDK ✅ CONFIRMED AS DRAFTED

**Rationale (from 2026-05-18 founder discussion):** Khiip's code is not deeply defensible (capture engine is mostly composed of wrappers around existing OSS libraries — gallery-dl, fxtwitter, MarkItDown, yt-dlp, ArchiveBox). Real moat shifts over time: month 0-6 execution lead → month 6-18 capture depth + integrations → year 2+ network effects + ecosystem position + brand. Code itself is NOT the moat. Therefore: closed-source doesn't add moat (since code isn't the differentiator); AGPL protects against AWS/Anthropic/OpenAI cloud-incumbent extraction without losing OSS distribution engine; Apache SDK enables AI builder integration without copyleft contamination. Matches Plausible / Karakeep / Cal.com / PostHog / Firecrawl precedent at scale.

### D2 — PBC corporate structure ⏳ DEFER until trigger event

**Rationale:** Founder has sizable runway; no immediate revenue pressure forcing incorporation now. Pre-incorporation, Promise 1 (perpetual copyleft) binding force comes from AGPL LICENSE file (legally binding for distributed code) + public commitment via /trust page + community contributor expectations. PBC charter adds ~20% additional binding force at $2-5K cost; not worth the cost pre-revenue. Triggers to revisit: first paying customer / first Stripe account / first hire / first VC conversation / $5K MRR.

**Canadian residency note:** Founder is Canadian. Before defaulting to Delaware PBC at incorporation trigger, evaluate Canadian alternatives: British Columbia Benefit Company Act (analog of Delaware PBC; provincial); federal Canada Business Corporations Act (CBCA) + benefit provision; or US Delaware PBC if customer base is primarily US-based. Tax + cap-table implications differ materially between options. Engage Canadian corporate counsel at incorporation trigger.

### D3 — Specific pricing ✅ CONFIRMED Shape A + B; ⏳ DEFER Shape C

**Shape B pricing locked:** $0 (free local + hosted free) / $8 Personal / $16 Power / $49 LTD per ADR-0002 draft. Anchoring rationale unchanged.

**Shape A pricing locked:** $0 (self-hosted) / $49 Builder / $149 Studio / $500/mo Enterprise floor (publicly disclosed). Graph features included at Builder tier (per D6). Anchoring rationale unchanged.

**Shape C pricing DEFERRED.** Per 2026-05-18 strategic refinement (codified in ADR-0006), Shape C (mass-market hosted app) probability is now ~20%; Shape D (integration layer that writes to user's existing PKM system) is the primary mass-market path. Shape D pricing structure differs (per-destination subscription model) and will be set at Shape D v0 spec authoring, not at this lock. The Shape C pricing in ADR-0002 draft ($4.99/$39.99/$19.99 LTD) is preserved as historical reference but not locked.

### D4 — LTD window: 90 days OR 500 customers, whichever first ✅ CONFIRMED AS DRAFTED

**Rationale unchanged:** matches Obsidian Catalyst pattern; balances revenue capture with avoiding indefinite LTD overhang on recurring-revenue economics; sunsets cleanly without "extending one more month" temptation.

### D5 — Free-tier limits: 500 captures / 2GB / 2 devices / 200 AI queries per month ✅ CONFIRMED AS DRAFTED

**Rationale unchanged:** calibrated to ~$0.15 PUPM marginal cost (sustainable for hosted free at scale); appropriately tight to drive paid conversion without being so restrictive that free users abandon before product proves value. Promise 4 permits expansion only — these limits can only GROW for free users, never shrink. 30-day cohort data review post-launch to evaluate expansion if needed.

### D6 — Graph features INCLUDED at Builder tier ($49/mo) ✅ CONFIRMED — LOAD-BEARING

**Rationale unchanged + reinforced:** This is the load-bearing anti-Mem0 competitive positioning. Mem0's $19→$249 graph cliff is the canonical complaint pattern in agent-memory tooling. Zep responded by including graph at all tiers from $25/mo and is taking share. Khiip's Builder tier including graph features (with hybrid edge typing per ADR-0005 + Option Δ interpretability refinements 2026-05-18) is the explicit differentiation. Once published in pricing page + launch tweet, IRREVERSIBLE per Promise 5 grandfather discipline.

### D7 — Refined Promise 3 + Promise 7 wording ⚠️ REFINED per 2026-05-17 decision prep + 2026-05-18 surfaces clarification

**Promise 3 (refined — split into 3 categories):**

> **Promise 3 — No AI Training on Your Content**
>
> Your captures, notes, graphs, and interactions will NEVER be used to train, fine-tune, or evaluate any AI model — ours or anyone else's. This is permanent and absolute; it cannot be enabled even with explicit consent.
>
> Two related but distinct categories of data use, each with their own default and consent model:
>
> **(a) Anonymous telemetry** (feature usage events, error reports, performance metrics) — default ON, transparent in product, one-click opt-out at any time. This data is aggregated and never contains content from your captures.
>
> **(b) Aggregate research data** (anonymized cohort patterns at minimum k-anonymity=50) — default OPT-IN, requires affirmative consent during onboarding, withdrawable at any time. This data may be used to publish research, inform Khiip product decisions, or in future enable aggregated insights products for B2B customers — but only after explicit user consent.
>
> Category (a) cannot be moved to consent-required without major version notice; category (b) cannot be moved to default-on; category "your content for AI training" cannot be moved to anything except permanent prohibition.

**Promise 7 (refined — segment-specific defaults + new ingestion surface clarification):**

> **Promise 7 — Transparent AI Defaults**
>
> AI behavior is segment-appropriate but always transparent:
>
> **(a) Self-hosted deployments** — All AI features default OFF. You enable each feature explicitly. Local-by-default discipline applies to AI processing too.
>
> **(b) Hosted users on paid tiers** — AI features the user has paid for are ON by default with prominent in-product controls to disable individually or globally. New AI features added to your tier ship in opt-in alert: a notification with "Enable" / "Skip" choice; no silent activation.
>
> **(c) Free hosted users** — AI features included in free tier are ON by default with prominent controls. AI features that are paid-tier-only are blocked (not "off" — there's no option to enable; you must upgrade).
>
> **(d) Mobile / mass-market (Shape C, deferred)** — AI features ON by default per segment-appropriate UX. Granular controls available in Settings.
>
> **(e) MCP server + iOS Shortcut + webhook surfaces (added 2026-05-18)** — AI features triggered via these surfaces inherit the same per-tier defaults as (a)-(d). MCP queries that invoke LLM-extraction inherit user's configured LLM tier (per D4 — bundled / Ollama / BYOK / BM25). iOS Shortcut and webhook captures use the same conservative-default behavior (capture + index; no auto-summarization unless explicit instruction).
>
> All segments: NEW AI features added post-launch follow opt-in alert pattern; never silent activation. Removal of AI features requires 90-day notice per Promise 5 grandfathering.

### D8 — Promises surface architecture ✅ CONFIRMED — 4-layer at launch + PBC layer at incorporation

**Locked 4-layer architecture at v0 launch:**

1. **AGPL-3.0 LICENSE file** in repo — legally binding for distributed code; effectively irreversible (relicensing requires contributor unanimous consent)
2. **ToS + Privacy Policy** — FTC + GDPR enforceable
3. **/trust page** on khiip.com landing — community-screenshot-archivable; plain language
4. **TRUST.md** in OSS repo — version-controlled commit history is public evidence

**5th layer added at incorporation (per D2 triggers):**

5. **PBC corporate charter** (or Canadian equivalent per D2 note) — corporate fiduciary duty layer naming perpetual OSS substrate as corporate purpose

All four (or five) layers must say the same thing. Cross-references create web of accountability — changing one without changing the others creates visible inconsistency. Plausible / PostHog / Cal.com discipline.

---

## Implications for v0 build + launch

- AGPL-3.0 LICENSE file added to github.com/khiip-ai/khiip during launch prep (Week 7-8 per v0-spec.md)
- ToS + Privacy Policy drafted Week 7-8 (with Anthropic content filter awareness — Privacy Policy + ToS may trigger similar filter issues as CODE_OF_CONDUCT did; use link-to-canonical templates where possible OR draft incrementally outside of single-LLM-call context)
- /trust page drafted as part of Week 8 launch site
- TRUST.md authored alongside /trust page
- Pricing page published Week 8 with all locked numbers (Shape A + B; Shape C deferred)
- Promise 3 + Promise 7 refined wording used in all 4 layers consistently
- PBC layer deferred until trigger event fires

---

## Context

ctx-WIP is a multi-platform capture + intelligence + recall substrate. Three product shapes sequenced: Shape B (Obsidian plugin + standalone daemon) → Shape A (REST API for AI-builders) → Shape C (mass-market iOS, deferred).

The pricing + open-source + immutable-promise architecture is load-bearing because **broken trust costs more than any revenue gained from violation.** The Smart Connections cautionary tale (Dec 2025): 786K Obsidian-plugin downloads, GPLv3 → MIT+noncompete, paywalled previously-free local Ollama support. Community revolt on GitHub #1293/#1294. ~50K-150K active users displaced and actively seeking GPLv3 alternatives. Cost: probably permanent loss of the community trust that built the user base.

Other cautionary tales: Cursor July 2025 credit-pool surprise (CEO public apology); Notion May 2025 AI bundling (documented churn); Mem0 $19→$249 graph-memory cliff (canonical complaint pattern); HashiCorp Aug 2023 BSL relicensing (OpenTofu fork; Terraform community permanently split); Reddit June 2023 API pricing (killed Apollo; mass r/AskHistorians dark protest); Cal.com April 2026 closed-source move (community backlash despite goodwill).

Successful counter-examples: Plausible (4-year run from $4.8K → $3.1M ARR with two price increases, zero revolt, grandfather discipline); Obsidian (free for personal use since 2020, never broken; commercial license requirement REMOVED Feb 2025 — promises only expanded); Cal.com / PostHog / Karakeep (OSS-first + paid hosted, proven playbook); Tailscale (free tier only ever EXPANDED — 3 users/100 devices → 6 users/unlimited devices); Granola ($0 → $1.5B in 18 months by NOT overclaiming AI).

This ADR locks the commercial model + community-trust architecture before any code ships. It is intended to be referenced from public artifacts (License file, ToS, Promises page, TRUST.md in repo) and to constrain all future commercial decisions.

## Decision

Locked architecture across three dimensions: (1) OSS license, (2) immutable promise charter, (3) free vs paid feature scope.

### Decision 1 — OSS License: AGPL-3.0 for substrate + Apache 2.0 for SDK

**Daemon + Obsidian plugin + capture engine + storage + bitemporal model + 21-edge graph + local embeddings: AGPL-3.0.**

Rationale:
- Closes the SaaS loophole that GPLv3 leaves open (any cloud wrapper must contribute back or negotiate commercial license)
- OSI-approved (avoids the Smart Connections "non-OSS" / "MIT+noncompete" backlash framing)
- Proven by Plausible (~$3M ARR), PostHog ($16M ARR Series B at $1.25B Oct 2025), Cal.com, Karakeep (24K stars, growing)
- Allows ctx-WIP to publish a commercial license for AGPL-incompatible enterprise integrators without dual-license toxicity
- Counter-point: Google's policy bans AGPL-licensed software internally. This is a feature for ctx-WIP — Google is not the target customer; Google as a competitor cannot wrap ctx-WIP cheaply

**Python SDK + TypeScript SDK: Apache 2.0.**

Rationale:
- AI-builders integrating ctx-WIP need to embed the SDK in their own products without copyleft contamination of their codebase
- Apache 2.0 is the permissive standard for developer SDKs (FastAPI, LangChain, LlamaIndex all permissive)
- The substrate stays AGPL; the integration layer is permissive
- Pattern precedent: HashiCorp's OSS Vault SDK (MPL) vs Vault server (BSL); MongoDB driver libraries (Apache 2.0) vs server (SSPL)

**Mobile apps (Shape C, deferred): Likely proprietary at v0.**

Rationale:
- AI-tool-generated code for iOS/Android may have IP entanglements complicating OSS distribution
- App Store review process + native quality bar requires dedicated focus that doesn't benefit from external contributions at MVP
- Revisit post-v0 if community pressure for open mobile clients builds

### Decision 2 — Immutable Promise Charter: 8 commitments

Per Expert P2's stress-tested charter. Each promise has refined wording, explicit failure modes, and evolution paths that allow strengthening but not weakening.

**Promise 1 — Perpetual Copyleft Substrate**
> "The ctx-WIP substrate — capture engine, storage layer, graph model, bitemporal index, and local embedding pipeline — will always be distributed under an OSI-approved copyleft license. We will never move it to a proprietary, source-available, or non-OSI-approved license."

- Surface: AGPL-3.0 LICENSE file (legally binding; cannot be retroactively closed for distributed code) + Public Benefit Corporation charter naming "perpetual OSS substrate" as corporate purpose + TRUST.md + Promises page
- Failure mode: Switching to BSL/SSPL/MIT+noncompete on the substrate; relicensing future code to remove copyleft
- Evolution path: Can ONLY upgrade to a more permissive OSI license; cannot weaken to proprietary

**Promise 2 — Local by Default**
> "Your data lives on your device. No content is transmitted to ctx-WIP servers or any third party without your explicit per-feature consent. Local embedding and search are computed on-device."

- Surface: Privacy Policy (FTC-enforceable per Jan 2024 guidance) + ToS + Promises page + first-run onboarding UI
- Failure mode: Any default-on telemetry, embedding API call, or content transmission without opt-in
- Evolution path: Cloud Sync and cloud AI features can be added as explicit opt-ins; default must always remain local

**Promise 3 — No Training on Your Data**
> "ctx-WIP will never use your captures, notes, graphs, or interactions to train, fine-tune, or evaluate any AI model — ours or anyone else's — without your explicit per-feature affirmative consent. Default opt-out is permanent unless you actively change it."

- Surface: ToS clause (FTC-enforceable; Figma class-action November 2025 + Adobe class-action December 2025 establish enforcement template) + Privacy Policy + Promises page
- Failure mode: Any model training/evaluation use without per-user affirmative consent; retroactive ToS expansion of data use
- Evolution path: Can add explicit opt-in "contribute to model improvement" program with separate consent + dedicated data handling policy

**Promise 4 — Free Features Stay Free**
> "Every feature available to free users at public launch is listed in our public changelog and will remain free permanently. We add paid features; we do not subtract free ones. This list is dated and version-controlled."

- Surface: ToS clause (with dated feature list) + Promises page + public changelog + TRUST.md
- Failure mode: Moving any feature from the dated free list to a paid tier; restricting free-tier access below launch baseline
- Evolution path: Free tier can EXPAND; paid tier adds new features only; free tier list amended only by adding to it
- This is the explicit anti-Smart-Connections promise

**Promise 5 — Your Price Is Locked**
> "If you subscribe, your price will not increase for as long as you maintain a continuous active subscription. If you cancel and resubscribe, current pricing applies. For service discontinuation, see Promise 8."

- Surface: ToS + billing confirmation email + Promises page
- Failure mode: Increasing price for a subscriber without consent; requiring resubscription to "grandfather" rate
- Evolution path: New subscribers pay new prices; grandfathered cohort tracked by billing system; can REDUCE prices for all subscribers without condition
- Plausible pattern (raised twice 2019→2021→2024 with grandfather, zero revolt)

**Promise 6 — Your Data, Your Export**
> "You can export all your data at any time in Markdown, YAML, and JSON formats using our documented schema. If we add new data structures, we ship the export format update within 30 days. We will never introduce proprietary formats that cannot be exported."

- Surface: ToS + Promises page + export UI (the feature IS the promise surface)
- Failure mode: Removing export capability; introducing data structure with no export path; delaying export updates >30 days
- Evolution path: Export formats can EXPAND; schema can evolve with migration tools; never contract

**Promise 7 — All AI Is Opt-In**
> "Every AI feature — local or cloud — requires explicit activation per feature. AI features are never enabled by default. If we introduce a new AI capability, it ships disabled. You turn it on; we don't."

- Surface: Promises page + TRUST.md + product behavior (verifiable in product)
- Failure mode: Any AI feature enabled by default at install/update; AI processing without per-feature activation
- Evolution path: Can add MORE AI features; cannot change default-disabled policy; can offer "enable all AI" opt-in convenience
- This is the Granola template applied at the architectural level: AI is supporting infrastructure, never the headline experience

**Promise 8 — 180-Day Shutdown Floor**
> "If we ever discontinue ctx-WIP or any core feature, we will provide minimum 180 days' public notice before shutdown. During that window, full export functionality remains available. We will not delete your data without minimum 180 days' notice from announcement."

- Surface: ToS clause (legally binding) + Promises page
- Failure mode: Announcing shutdown <180 days to deletion; disabling export during notice period; acqui-hire bypassing notice (Omnivore pattern)
- Evolution path: Notice period can only INCREASE; can add "data archive" options during window
- Pocket gave 47 days; Omnivore gave 17. 180 days is the right floor for years-of-thinking knowledge artifacts

**Three-layer surface architecture for promises:**

Layer 1 (legally binding, hardest to reverse): AGPL-3.0 LICENSE file + PBC corporate charter naming substrate's perpetual OSS status as corporate purpose

Layer 2 (FTC/GDPR-binding): ToS + Privacy Policy clauses for promises 2, 3, 5, 6, 8

Layer 3 (community-visible, screenshot-archivable): `/trust` page on landing site (plain language, 8 commitments, each with explicit "what counts as breaking this" definition) + TRUST.md in OSS repo (mirrors Promises page, version-controlled, commit history is public evidence)

All three layers must say the same thing. Cross-references create a web of accountability — changing one without changing the others creates visible inconsistency.

**Promises explicitly NOT made:**
- "We will never be acquired" (cannot be controlled by founders post-investment)
- "We will never raise prices" (inflation; impossible over decades — Promise 5 grandfather discipline is the substitute)
- "We will always be available in country X" (sanctions/regulatory risk)
- "We will always be ad-free" (forecloses sponsored OSS integrations; better promise: "no ads in product UI")
- "We will never use AI" (Promise 7 opt-in is the substitute)
- "Specific feature X will always be in free tier" (Promise 4's dated list handles this correctly)

### Decision 3 — Free vs Paid Feature Scope

Three-bucket classification per Expert P3.

**Bucket A — Always Free (locked Day 1, cannot be paywalled):**
- OSS daemon code (AGPL-3.0)
- OSS Obsidian plugin code (AGPL-3.0)
- Local AI features (Ollama, LM Studio, any local OpenAI-compatible endpoint) — explicit anti-Smart-Connections positioning
- Self-hosted daemon — full feature parity with cloud (no second-class self-hosters)
- All capture tracks (gallery-dl, fxtwitter, yt-dlp, MarkItDown, RSS, ArchiveBox) when running locally
- Schema export in Markdown/YAML/JSON at any time, any tier
- Webhooks (outbound, to user-defined endpoints)
- API access for personal automation (1K requests/month to local daemon)
- Community support (Discord/GitHub Issues) until ~10K active users
- Configuration and sync protocol specification (anti-Logseq-closed-RTC-pattern — even if hosted sync is paid, the protocol is open)

**Bucket B — Free with Limits (paid removes/expands):**
- Cloud-hosted daemon (we run infrastructure): free = 500 captures/month, 2GB storage, 2-device sync
- Cloud LLM features (semantic search via cloud Haiku 4.5): free = 200 queries/month
- Multi-device cloud sync: free = 2 devices
- Email-to-vault forwarder: free = 1 forwarder address, 50 emails/month
- Cloud audio transcription (hosted Faster-Whisper): free = 60 minutes/month
- Version history / snapshot retention: free = 30 days
- Public link sharing: free = unlimited links, 1K public reads/month
- Wayback Machine submissions: free = 100/month
- Capture queue priority: free = best-effort queue

**Bucket C — Paid Only (no free tier):**
- Multi-device cloud sync beyond 2 devices
- Managed backup + disaster recovery (point-in-time restore, RTO/RPO SLA)
- Team workspaces (multi-user shared collections)
- Priority support with email SLA (24-hour response)
- Pass-through paid API integrations (Apify for Track 4 inbound-QRT watch — 1:1 cost + thin margin pass-through)
- Cloud transcription above 60 minutes/month
- SOC 2 / audit log export / SCIM provisioning (enterprise tier only)
- Custom domain for public link sharing
- White-label / OEM licensing (negotiated per deal)
- Enterprise SAML SSO

### Decision 4 — Specific Pricing

**Shape B (Obsidian plugin + daemon):**

| Tier | Monthly | Annual | One-time | Limits |
|---|---|---|---|---|
| Free local | $0 forever | — | — | Plugin + daemon, fully local, perpetual |
| Hosted free | $0 | — | — | 2 devices, 500 captures/mo, 2GB, 0 cloud AI |
| Personal | $8/mo | $72/yr (25% off) | — | Unlimited devices+captures+storage, 200 cloud AI ops/mo |
| Power | $16/mo | $128/yr | — | + 10K cloud AI ops/mo, priority support |
| **Launch LTD** | — | — | **$49** | Local daemon + plugin license PERPETUAL — does NOT include cloud sync, hosted API, cloud LLM. **Window: 90 days OR 500 customers, whichever first.** Sunset cleanly. |

Anchoring rationale (Expert P4): Below Readwise ($9.99), above Obsidian Sync ($4). $8/mo is the confident midpoint; $7.99 reads as "I'm not sure I'm worth $8." Annual at $72 reads cleanly ("less than $80/yr"). Power at $16 sits in "Cursor mental bucket" ($20).

**Shape A (Developer API for AI-builders):**

| Tier | Monthly | Annual | Limits |
|---|---|---|---|
| Self-hosted | $0 unlimited | — | Full functionality, runs on user's infrastructure |
| Hosted free | $0 | — | 10K memory ops/mo, 1 project, community support |
| Builder | $49/mo | $470/yr (20% off) | 500K memory ops/mo, 5 projects, **graph features INCLUDED**, email support |
| Studio | $149/mo | $1,430/yr (20% off) | 5M memory ops/mo, unlimited projects, Slack support, 50ms SLA |
| Enterprise | **From $500/mo (publicly disclosed floor)** | Contact | Custom ops, SLA contract, on-prem AGPL daemon option, SSO, SOC 2, dedicated onboarding |

**Critical positioning decision:** Graph/temporal features (J11 win) are INCLUDED at Builder tier ($49/mo), NOT gated to Studio or Enterprise. This is the explicit anti-Mem0 positioning. Mem0's $19→$249 cliff (graph features locked at $249 Pro) is the canonical complaint pattern; Zep responded by offering graph at all tiers from $25/mo and is taking share. ctx-WIP's positioning: "All the features Mem0 Pro has at $149 instead of $249. No cliff. Graph features included from Builder tier."

Anchoring rationale: Cursor + Copilot at $19-20/mo establish the "AI dev tool worth paying for" floor. $49 Builder is 2.5x that — justified because Shape A buyers are building products with this, not using it as a tool. $149 Studio undercuts Mem0 Pro by $100. $500 enterprise floor disclosed publicly removes mystery (Plausible discipline).

**Shape C (Mass-market iOS, deferred):**

| Tier | Monthly | Annual | One-time | Limits |
|---|---|---|---|---|
| Free trial | $0 | — | — | 30-day full, then 1 device + 500 notes |
| Premium | $4.99/mo | $39.99/yr (33% off) | — | Unlimited + 100 cloud AI ops/mo |
| Family | $9.99/mo | $79.99/yr | — | Up to 6 accounts |
| Local-only | — | — | $19.99 | No sync, no cloud AI, offline perpetual |

Anchoring rationale: Bear $29.99/yr as "honest indie" floor; Day One $49.99/yr Silver as "premium consumer" ceiling. $39.99/yr sits between, signals "deliberate premium over Bear without reaching Day One territory." Local-only one-time captures subscription-refusing cohort with $0 marginal cost.

### Decision 5 — Pricing-Change Governance

**Grandfather clause (Promise 5):** Existing subscribers keep their tier price for as long as they maintain continuous subscription. Cancel + resubscribe = current price. Plausible pattern.

**90-day advance notice for any pricing change.** Notice via email to all affected tier subscribers + public blog post. Cursor gave zero days; Reddit gave 60 days; 90 days is the minimum that gives users time to evaluate alternatives.

**180-day notice for service discontinuation (Promise 8).** Pocket gave 47; Omnivore gave 17. 180 is the right floor for knowledge management.

**Maximum price increase: CPI + 5%/year for grandfathered subscribers.** Allows real cost adjustments while capping extraction.

**No retroactive paywalling of free features (Promise 4).** The dated free-feature list is locked.

**Usage-based billing requires opt-in hard caps.** If Shape A ever introduces overage, every account must set a hard monthly spend cap. Cursor's failure was no cap. Default behavior: pause cloud features at limit, never charge without explicit confirmation click.

**Public RFC for major changes.** 30-day public RFC period before changes finalize that affect what "free" means or remove features from any tier. Adding features = no process required.

## Consequences

### Positive

- **Anti-Smart-Connections positioning baked in.** Promise 1 + Promise 4 + AGPL license + dated free-feature list = ctx-WIP cannot make the Smart Connections move structurally. This is itself a competitive trust signal for the ~50K-150K displaced users who specifically distrust closed-core moves.
- **Anti-Mem0 positioning baked into Shape A.** Graph features at Builder tier ($49) instead of Pro tier ($249) is the explicit competitive differentiator. The acquisition message writes itself.
- **Granola template applied.** Promise 7 (AI opt-in) + outcome-led positioning + AI-as-engine-not-headline = the $1.5B template applied to ctx-WIP's category.
- **Plausible-style trust compounding.** Promise 5 grandfather + 90-day notice + transparent pricing rationale = community supports price increases over time (Plausible raised twice in 5 years with zero revolt).
- **Cal.com OSS-first growth playbook.** AGPL substrate + paid hosted = proven model; Cal.com / PostHog / Plausible / Karakeep all validate this.
- **Unit economics locked at design time.** Bucket B free-tier limits calibrated to actual cloud cost (R2 $0.015/GB, Haiku 4.5 $0.0006/query). 2GB free + 200 AI queries free = $0.15 PUPM marginal cost — manageable customer acquisition cost.
- **Future flexibility preserved within constraints.** Promises CAN be expanded in user favor (free tier limits raised, more features added free, longer grandfather terms). Promises cannot be contracted.

### Negative

- **AGPL forecloses Google as enterprise customer** (their internal policy bans AGPL). Acceptable — Google is not the target buyer; their potential competitive use is what AGPL prevents.
- **No unlimited free cloud LLM.** Some users will hit the 200 AI queries/mo limit and complain. Acceptable — cost containment requires this; the upsell ($16/mo Power tier with 10K ops) is a clean conversion path.
- **No LTD for Shape A or C.** Some early supporters will request lifetime deals; honoring would be economically toxic for cloud-cost features. Acceptable — Shape B local-only LTD captures the "I want to support you" cohort; cloud features must be subscription-funded.
- **PBC corporate structure adds incorporation overhead.** Public Benefit Corporation in Delaware (or equivalent) requires legal setup beyond standard LLC. Estimated $2-5K legal cost + ongoing reporting requirements. Acceptable — this is the structural protection that makes Promise 1 hard to reverse beyond just license terms.
- **Specific free-tier limits (500 captures/2GB/2 devices/200 AI queries) are calibrated to Day-1 estimates.** May need expansion if too restrictive vs adoption metrics. Promise 4 and Tailscale precedent both allow EXPANSION; cannot contract.

### Neutral

- All pricing tiers labeled PROVISIONAL until first 90 days of paying-customer behavior. Specific dollar amounts may shift ±$1-2/mo in either direction based on conversion data.
- Lifetime deal window is intentionally limited (90 days OR 500 customers, whichever first). Sunset cleanly per Obsidian Catalyst pattern; do not extend or repeat.
- Documentation overhead: TRUST.md + Promises page + ToS + Privacy Policy + LICENSE = 5 cross-referenced public artifacts to maintain consistency. Manageable but real.

## Open questions for founder approval

1. **License confirmation:** AGPL-3.0 for daemon/plugin/substrate + Apache 2.0 for SDK. Confirm or reconsider.
2. **PBC corporate structure:** Pursue Delaware Public Benefit Corporation incorporation now (before any users) for Promise 1 binding force, OR defer until first commercial revenue (cheaper but weaker promise binding)?
3. **Specific pricing locked:** Shape B at $8/$16/$49 LTD; Shape A at $49/$149/$500 floor; Shape C at $4.99/$39.99/$19.99 LTD. Confirm or adjust.
4. **LTD window:** 90 days OR 500 customers (whichever first) — comfortable with this scoping?
5. **Free tier limits:** 500 captures/2GB/2 devices/200 AI queries for Shape B hosted free. Calibrate? Tighter? More generous?
6. **API tier graph-feature inclusion at Builder ($49):** This is the load-bearing competitive positioning vs Mem0. Confirm comfortable with this commitment (cannot retroactively gate graph features later).
7. **8-promise charter:** Specific wording per Decision 2 above. Any promises to add, remove, or reword?
8. **Promises surface architecture:** AGPL LICENSE + PBC charter + ToS/Privacy Policy + /trust page + TRUST.md — comfortable with this 3-layer stack, or cut/add layers?

## References

- Expert P1 (pricing model architecture) — full output in tool-results
- Expert P2 (immutable promise discipline) — full output in tool-results
- Expert P3 (free vs paid layer design) — full output in tool-results
- Expert P4 (pricing psychology + competitive positioning) — full output in tool-results
- ADR-0001 (genesis) — load-bearing decision context
- `docs/methodology/jtbd-framework.md` — JTBD framework v0.1; informs which jobs justify which paid features
- Smart Connections #1293/#1294 — primary cautionary case
- Plausible/Cal.com/PostHog/Karakeep pricing pages — primary positive precedents
- ADR Nygard format per `./AGENTS.md`

## Status

**Accepted (2026-05-18).** All 8 founder decisions locked per "Lock confirmations (2026-05-18)" section near top of file. The public-facing artifacts (AGPL-3.0 LICENSE, TRUST.md, /trust page, ToS draft, Privacy Policy draft) follow as Week 7-8 launch prep work.

Subsequent supersession requires new ADR with `Supersedes: ADR-0002` and explicit reasoning + community RFC if Promise 4/5/6/7 evolution is involved.
