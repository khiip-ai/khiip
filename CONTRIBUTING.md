# Contributing to Khiip

Thank you for your interest in Khiip — the substrate AI agents use to capture, store, and recall data from online sources.

This project is in **active early development.** We welcome contributions but expect rough edges. v0 is targeted for ~Week 7-8 of 2026; until then, the code is scaffolding + research + ADRs.

---

## Quick start

1. Read the [README](README.md) for project overview
2. Read [AGENTS.md](AGENTS.md) for the canonical instruction set + read order
3. Read [HANDOFF.md](HANDOFF.md) for current project state
4. Browse [docs/adr/](docs/adr/) for architectural decisions (most recent: ADR-0005)
5. Browse [docs/product/v0-spec.md](docs/product/v0-spec.md) for the v0 build plan

## Ways to contribute

### Issues

- **Bug reports** — once v0 ships. Until then, the code surface is too small for meaningful bugs
- **Feature requests** — open with [enhancement] prefix; include use case + acceptance criteria
- **Documentation improvements** — typos, clarifications, broken links: welcome anytime
- **Architecture questions / discussion** — open as Discussion, not Issue, until we have clear conventions

### Pull requests

- **Documentation PRs** (typos, clarifications) — welcome anytime, low ceremony
- **Code PRs** — please open an Issue or Discussion FIRST to align on approach. v0 has a constrained scope per [docs/product/v0-spec.md](docs/product/v0-spec.md); unsolicited code PRs may be declined if out of scope
- **Test PRs** — welcome; we're under-tested until v0 ships
- **All PRs:** sign-off via `git commit --signoff` (DCO compliance)

### Other contributions

- Star the repo (genuinely helps with discoverability)
- Share with people building AI agents who need a substrate layer
- Try Khiip when v0 ships and tell us what breaks

---

## Code conventions

These are aspirational until v0 ships; will be enforced via CI once code exists.

### Python (daemon, extractors)

- Python 3.11+
- `ruff` for linting + formatting (config in `pyproject.toml` when added)
- Type hints required for all public functions
- `pytest` for tests
- No `print()` in committed code — use `logging` module

### TypeScript (Obsidian plugin)

- TypeScript 5.x
- `eslint` + `prettier` (config when added)
- No `any` types — use `unknown` and narrow
- React for plugin UI components (Obsidian's plugin SDK)

### Markdown (docs)

- ATX-style headings (`# Heading` not underlines)
- Code blocks always with language specifier
- Wrap prose at ~100 columns (soft; semantic line breaks OK)
- Link to relative paths in repo (`[file.md](docs/file.md)`) not external URLs when referencing in-repo content

### Commits

- Commit messages follow Conventional Commits style: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `chore`, `test`, `refactor`, `style`, `perf`
- Scopes: `daemon`, `plugin`, `extractor`, `graph`, `recall`, `docs`, `adr`, etc.
- Example: `feat(extractor): add X-Article body parsing for engagement metrics`
- Sign-off line required: `git commit --signoff` adds DCO sign-off automatically

---

## Development setup

**v0 build hasn't started yet.** When it does (Week 1 per [docs/product/v0-spec.md](docs/product/v0-spec.md)), this section will document:

- Python virtualenv + dependency install
- Local daemon run instructions
- Obsidian plugin dev install (BRAT during private beta)
- Test corpus + running tests
- Pre-commit hook setup

Until then, contributions are limited to documentation + ADRs.

---

## Architectural Decision Records (ADRs)

Khiip uses ADRs (Architecture Decision Records) per the Nygard format to capture significant architectural decisions. See [docs/adr/](docs/adr/) for the full set.

**If you're proposing a significant change**, draft an ADR following the existing format:

```markdown
# ADR-NNNN — Short title

**Status:** Proposed
**Date:** YYYY-MM-DD
**Supersedes:** N/A or ADR-NNNN
**Superseded by:** N/A

## Context
[Why is this decision needed? What's the situation?]

## Decision
[What did we decide?]

## Consequences
[Positive / Negative / Neutral]

## References
[Related ADRs, external sources]
```

Submit as a PR adding `docs/adr/ADR-NNNN-slug.md` (NNNN is next available number).

---

## License

By contributing, you agree that your contributions are licensed under:

- **AGPL-3.0** for daemon + plugin + substrate code (the primary repository)
- **Apache 2.0** for SDK code (separate repository when published)

See [LICENSE](LICENSE) for full text. AGPL means: derivative works (including network/SaaS uses) must be open-sourced under AGPL-3.0. This is by design — Khiip's substrate is perpetually OSS per ADR-0002 Promise 1.

---

## Code of Conduct

This project follows the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md). By participating, you agree to abide by it.

In short: be kind, be specific, be willing to disagree without being personal. Disrespectful behavior gets a warning; repeated patterns get removed from the project space.

---

## Security

Found a security vulnerability? Please follow the disclosure process in [SECURITY.md](SECURITY.md) — do NOT open a public Issue.

---

## Getting help

- **General questions:** GitHub Discussions (when enabled post-v0)
- **Bugs:** GitHub Issues (post-v0)
- **Architecture proposals:** ADR PR per format above
- **Anything else:** hello@khiip.com

---

## Maintainers

Current sole maintainer: Khiip Team (handle `jttmw` on GitHub for org admin).

When the project grows to need additional maintainers, governance will be documented here.

---

*Khiip is in early development. Contribution conventions will evolve. Last updated 2026-05-17.*
