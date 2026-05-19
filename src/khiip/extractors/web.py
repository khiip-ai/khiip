"""Web extractor — generic article capture; trafilatura → readability fallback chain.

Per ADR-0007 Lens 4 (per-source extractor moat): trafilatura is the v0
primary for generic web — Bevendorff et al. 2023 benchmark at ~93% F1
on real-web corpora (vs. readability ~85% / boilerpipe ~83%). When
trafilatura fails or returns empty (paywall heuristics, unusual page
structure, parser drift), readability-lxml + markdownify is the fallback.
Different algorithms (statistical vs. heuristic-scoring) give genuinely
orthogonal failure modes. Both run locally — no third-party dependency
for the fallback path.

The chain produces a CaptureData with title + description + author + body
markdown + post-redirect canonical URL. Generic web articles have no
engagement counts, so `engagement_at_capture` is left None.

**Bonus**: the readability fallback emits RICHER markdown than trafilatura
primary because `markdownify` preserves `[link](url)` and `![alt](img)`
syntax that trafilatura 2.0's `output_format="markdown"` strips. When
trafilatura wins, we accept that trade-off; v0.5 candidate: post-process
trafilatura's HTML output with markdownify for parity.

**Known v0 limitations** (filed for v0.5):
- No media binary download; images referenced inline remain as remote
  URLs subject to rot.
- No paywall detection; paywalled pages get whatever the unauthenticated
  fetch returns (often the teaser + paywall text).
- Two-source chain (trafilatura + readability) — Jina Reader + ArchiveBox
  as third + fourth sources land alongside the broader resilience-strategy
  follow-up.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
import markdownify
import trafilatura
from readability import Document
from trafilatura.settings import use_config

from khiip.extractors.base import CaptureData
from khiip.extractors.resilience import (
    FallbackFailed,
    FallbackSource,
    HealthStatus,
    try_fallback_chain,
)

_USER_AGENT = "khiip-daemon/0.0.1 (+https://github.com/khiip-ai/khiip)"

# trafilatura's default signal-based timeout breaks in worker threads
# (FastAPI runs handlers in a thread pool). Disable it.
_TRAF_CONFIG = use_config()
_TRAF_CONFIG.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")

# Liveness probe: example.com is IANA-managed + intentionally stable +
# returns a small but real article-like body that trafilatura can extract.
_HEALTH_PROBE_URL = "https://example.com/"


class WebExtractor:
    """Generic web-article extractor with trafilatura → readability fallback.

    Registers LAST in the default ExtractorRegistry so domain-specific extractors
    (XExtractor for x.com/twitter.com; future YouTube/PDF) get first refusal on
    their URLs before WebExtractor's catch-all `supports(url)`.
    """

    source: str = "web"

    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._http = http_client or httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )

    def supports(self, url: str) -> bool:
        """True for any http(s) URL with a hostname. Always last in the registry."""
        try:
            scheme = urlparse(url).scheme
            host = urlparse(url).hostname
        except ValueError:
            return False
        return scheme in ("http", "https") and bool(host)

    def extract(self, url: str) -> CaptureData:
        """Fetch + parse a web URL via the fallback chain.

        Chain: trafilatura (primary, ~93% F1) → readability-lxml + markdownify
        (fallback, orthogonal algorithm + richer markdown). On both failing,
        raises ExtractorError → daemon maps to 502.
        """
        html, canonical_url = self._fetch(url)
        sources: list[FallbackSource[CaptureData]] = [
            FallbackSource(
                name="trafilatura",
                fetch_fn=lambda _t: self._parse_trafilatura(html, canonical_url),
            ),
            FallbackSource(
                name="readability",
                fetch_fn=lambda _t: self._parse_readability(html, canonical_url),
            ),
        ]
        source_name, capture_data = try_fallback_chain(sources, url)
        capture_data.extracted_payload.setdefault("_extractor_source", source_name)
        return capture_data

    def health_check(self) -> HealthStatus:
        """Probe https://example.com/ + trafilatura.extract; verify body non-empty.

        Uses a 5s short-timeout (separate from extract()'s 30s) so /health
        fails fast on a hung network rather than blocking the liveness probe.
        """
        now = datetime.now(timezone.utc)
        try:
            response = self._http.get(_HEALTH_PROBE_URL, timeout=httpx.Timeout(5.0))
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return HealthStatus(
                source=self.source,
                ok=False,
                degraded_reason=f"example.com unreachable: {type(exc).__name__}",
                last_checked=now,
                fallback_count=2,
            )

        body = trafilatura.extract(response.text, config=_TRAF_CONFIG) or ""
        if not body.strip():
            return HealthStatus(
                source=self.source,
                ok=False,
                degraded_reason="trafilatura returned empty body on example.com (parser drift?)",
                last_checked=now,
                fallback_count=2,
            )
        return HealthStatus(
            source=self.source,
            ok=True,
            last_checked=now,
            fallback_count=2,
        )

    # ─────────────────────────────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────────────────────────────

    def _fetch(self, url: str) -> tuple[str, str]:
        """One HTTP fetch used by both sources. Returns (html, canonical_url)."""
        response = self._http.get(url)
        response.raise_for_status()
        return response.text, str(response.url)

    def _parse_trafilatura(self, html: str, canonical_url: str) -> CaptureData:
        """Primary parser; raises FallbackFailed if extraction produced nothing useful."""
        metadata = trafilatura.extract_metadata(html, default_url=canonical_url)
        body_markdown = trafilatura.extract(
            html,
            output_format="markdown",
            url=canonical_url,
            include_links=True,
            include_images=True,
            config=_TRAF_CONFIG,
        ) or ""

        title = metadata.title if metadata else None
        if not body_markdown.strip() and not (title and title.strip()):
            # Both empty → likely a non-article page (search, login, SPA);
            # let readability try a different algorithm before giving up.
            raise FallbackFailed("trafilatura returned empty body + no title")

        now = datetime.now(timezone.utc)
        valid_from = _parse_metadata_date(metadata.date if metadata else None) or now

        return CaptureData(
            source=self.source,
            source_url=canonical_url,
            recorded_at=now,
            valid_from=valid_from,
            title=title,
            description=(metadata.description if metadata else None),
            author=(metadata.author if metadata else None),
            body_markdown=body_markdown,
            extracted_payload={
                "html_bytes": len(html),
                "url": canonical_url,
                "hostname": metadata.hostname if metadata else None,
            },
        )

    def _parse_readability(self, html: str, canonical_url: str) -> CaptureData:
        """Fallback parser: readability-lxml + markdownify.

        Different algorithm from trafilatura (heuristic scoring vs. statistical
        model). Produces richer Markdown — markdownify preserves `[link](url)`
        and `![alt](img)` syntax.
        """
        try:
            doc = Document(html)
            raw_title = doc.short_title() or doc.title() or ""
            # readability returns the literal "[no-title]" placeholder when no title
            # is parseable; treat that as "no useful title" rather than a real one.
            title = raw_title.strip() or None
            if title == "[no-title]":
                title = None
            summary_html = doc.summary(html_partial=True)
        except Exception as exc:  # pragma: no cover — defensive against readability internals
            raise FallbackFailed(f"readability parser raised: {type(exc).__name__}") from exc

        body_markdown = markdownify.markdownify(summary_html, heading_style="ATX").strip()
        if not body_markdown and not (title and title.strip()):
            raise FallbackFailed("readability returned empty body + no title")

        now = datetime.now(timezone.utc)
        return CaptureData(
            source=self.source,
            source_url=canonical_url,
            recorded_at=now,
            valid_from=now,
            title=title,
            description=None,  # readability doesn't surface description metadata
            author=None,  # readability doesn't surface author metadata
            body_markdown=body_markdown,
            extracted_payload={
                "html_bytes": len(html),
                "url": canonical_url,
            },
        )


def _parse_metadata_date(date_str: str | None) -> datetime | None:
    """trafilatura returns YYYY-MM-DD; best-effort parse to UTC datetime."""
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


__all__ = ["WebExtractor"]
