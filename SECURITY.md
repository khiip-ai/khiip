# Security Policy

## Reporting a Vulnerability

If you believe you've found a security vulnerability in Khiip, please report it via one of these channels (in order of preference):

1. **Email:** [security@khiip.com](mailto:security@khiip.com) — preferred
2. **GitHub Security Advisories:** [Report a vulnerability](https://github.com/khiip-ai/khiip/security/advisories/new) — uses GitHub's coordinated disclosure infrastructure
3. **PGP-encrypted email:** PGP key will be published here at `security@khiip.com` once we ship v0

**Please DO NOT report security vulnerabilities via public GitHub Issues, Discussions, social media, or other public channels.** We need a private window to triage + remediate before disclosure.

## What to include

To help us triage quickly, please include:

- **Description** of the vulnerability
- **Steps to reproduce** (minimal repro case if possible)
- **Affected versions** of Khiip (daemon version, plugin version, deployment context)
- **Impact assessment** (what an attacker could do)
- **Suggested remediation** if you have one
- **Disclosure timeline preference** (we follow industry-standard 90-day coordinated disclosure by default)
- **Credit preference** (named acknowledgment in security advisory, or anonymous)

## Our commitment

- **Acknowledgment within 48 hours** of report (24 hours during workdays)
- **Initial triage assessment within 7 days** (severity classification, affected components, scoping)
- **Regular status updates** during remediation
- **Coordinated disclosure** — we credit researchers (with their consent) in the GitHub Security Advisory + release notes
- **90-day disclosure window standard** — we'll request extension only if remediation requires it; we won't unreasonably delay disclosure

## Scope

### In scope

- Khiip daemon (Python; AGPL-3.0)
- Khiip Obsidian plugin (TypeScript; AGPL-3.0)
- Khiip SDK packages when published (Apache 2.0)
- Khiip-hosted infrastructure when launched (cloud daemon, sync, etc.)
- Any official Khiip deployment artifacts (PyInstaller binaries, Docker images, npm packages, PyPI packages)
- Khiip documentation site at https://khiip.com when launched

### Out of scope

- **Vulnerabilities in user-provided LLM endpoints** — Khiip dispatches to user-configured LLM providers (Anthropic/OpenAI/Gemini/Ollama); vulnerabilities in those services should be reported to the respective vendor
- **Vulnerabilities in capture sources** — Khiip captures content from third-party sites (X, web, YouTube, etc.); vulnerabilities in those sites are out of scope
- **Vulnerabilities in user vault files** — Khiip writes to user-controlled filesystem; vulnerabilities in user's text editor / vault management are out of scope
- **Social engineering attacks** — phishing of Khiip employees / users (none yet; flagged for when we hire)
- **Physical attacks** on user devices

## Severity classification

We use a CVSS 3.1-aligned classification:

| Severity | Examples | Target response |
|---|---|---|
| **Critical** | Remote code execution; arbitrary file write to system paths; credentials exfiltration | Patch within 7 days |
| **High** | Authentication bypass; data exfiltration from user vault; privilege escalation | Patch within 14 days |
| **Medium** | XSS in plugin UI; information disclosure (non-credential); denial of service | Patch within 30 days |
| **Low** | Minor information disclosure; non-exploitable bugs with security implications | Patch in next regular release |

## Bug bounty

**No formal bug bounty program at this time.** When Khiip reaches revenue scale, we will likely launch a program via HackerOne or similar. Until then, we will credit researchers publicly (with consent) and may offer modest acknowledgment compensation case-by-case.

## Security disclosure history

When vulnerabilities are responsibly disclosed and remediated, we will list them here with credit to the researcher (with their consent). This section is empty as of 2026-05-17.

## PGP key

PGP key for `security@khiip.com` will be published here once issued. For pre-launch reports, encrypted communication can be coordinated via email.

## Related resources

- [security.txt at https://khiip.com/.well-known/security.txt](https://khiip.com/.well-known/security.txt) — when published; follows RFC 9116
- [Khiip Privacy Policy](https://khiip.com/privacy) — when published
- [Khiip Promises](https://khiip.com/trust) — when published; immutable trust commitments per ADR-0002

---

*Khiip security policy v1.0; last updated 2026-05-17. Will be updated as project matures + security program formalizes.*
