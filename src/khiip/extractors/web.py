"""Web extractor — generic article capture via trafilatura + httpx.

Per ADR-0007 Lens 4 (per-source extractor moat): trafilatura is the v0
primary for generic web. Bevendorff et al. 2023 benchmark trafilatura at
~93% F1 on real-web corpora vs. readability ~85% / boilerpipe ~83%.
Apache 2.0 license (compatible with both AGPL daemon + Apache SDK slots).

Output: title + description + author + body markdown + post-redirect
canonical URL. Generic web articles have no engagement counts, so
`engagement_at_capture` is left None.

**Known v0 limitations** (filed for v0.5):
- trafilatura 2.0's `output_format="markdown"` emits text without `[link](…)`
  or `![alt](…)` syntax. Link/image URLs are dropped from the body. Body text
  is still complete for embedding purposes; just don't expect roundtrippable
  Markdown. v0.5 candidate fix: post-process trafilatura's HTML output with
  `markdownify` for richer Markdown.
- No media binary download; images referenced inline (when they survive)
  remain as remote URLs subject to rot.
- No paywall detection; paywalled pages get whatever the unauthenticated
  fetch returns (often the teaser + paywall text).
- Single-source (trafilatura only). Multi-source fallback (trafilatura →
  readability → Jina Reader → ArchiveBox) lives in the "Extractor resilience
  strategy" follow-up.
"""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
import trafilatura
from trafilatura.settings import use_config

from khiip.extractors.base import CaptureData

_USER_AGENT = "khiip-daemon/0.0.1 (+https://github.com/khiip-ai/khiip)"

# trafilatura's default signal-based timeout breaks in worker threads
# (FastAPI runs handlers in a thread pool). Disable it.
_TRAF_CONFIG = use_config()
_TRAF_CONFIG.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")


class WebExtractor:
    """Generic web-article extractor.

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
        """True for any http(s) URL. Always last in the registry."""
        try:
            scheme = urlparse(url).scheme
            host = urlparse(url).hostname
        except ValueError:
            return False
        return scheme in ("http", "https") and bool(host)

    def extract(self, url: str) -> CaptureData:
        """Fetch + parse a web URL into CaptureData.

        Raises httpx.HTTPError on fetch failure (daemon turns into 502).
        Returns a CaptureData with possibly empty body_markdown for pages
        trafilatura can't extract (search results, login walls, SPAs);
        the capture still lands so the URL is recorded.
        """
        response = self._http.get(url)
        response.raise_for_status()
        return self._parse_html(response.text, canonical_url=str(response.url))

    def _parse_html(self, html: str, canonical_url: str) -> CaptureData:
        """Pure parse step — no HTTP. Used by tests + by extract()."""
        metadata = trafilatura.extract_metadata(html, default_url=canonical_url)
        body_markdown = trafilatura.extract(
            html,
            output_format="markdown",
            url=canonical_url,
            include_links=True,
            include_images=True,
            config=_TRAF_CONFIG,
        ) or ""

        now = datetime.now(timezone.utc)
        valid_from = _parse_metadata_date(metadata.date if metadata else None) or now

        return CaptureData(
            source=self.source,
            source_url=canonical_url,
            recorded_at=now,
            valid_from=valid_from,
            title=(metadata.title if metadata else None),
            description=(metadata.description if metadata else None),
            author=(metadata.author if metadata else None),
            body_markdown=body_markdown,
            extracted_payload={
                "html_bytes": len(html),
                "url": canonical_url,
                "hostname": metadata.hostname if metadata else None,
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
