"""X (Twitter) extractor — fxtwitter primary; gallery-dl supplement (TODO).

Per ADR-0007 Lens 4 + Phase 3 Test 1 validation: X capture is Khiip's
highest-fidelity source. fxtwitter's `api.fxtwitter.com/i/status/{id}` returns
structured JSON with the full QRT chain + embedded X-Article body + view +
bookmark + quote counts. Test 1 measured: 42,675 bytes structured JSON
(fxtwitter) vs 2,625 bytes flat markdown (Jina Reader) — 16× capture-depth
gap that motivates this extractor.

**v0 Week 1 scope (this scaffold):**
- URL parser → extract tweet ID
- fxtwitter HTTP call → JSON
- Parse top-level fields into CaptureData
- TODO markers for QRT chain expansion + X-Article body + media download

**Deferred to next implementation pass:**
- gallery-dl integration for media binaries (per ADR-0007 capture pipeline)
- QRT chain depth handling
- X-Article block-level parsing (108-block render from fxtwitter `quote.article.content.blocks`)
- engagement_at_capture snapshot extraction (views / bookmarks / quotes)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from khiip.extractors.base import CaptureData, Extractor

FXTWITTER_API = "https://api.fxtwitter.com/i/status/{tweet_id}"

# fxtwitter blocks the default `python-httpx/*` User-Agent (returns 403).
# Identify Khiip explicitly so the upstream operator can rate-limit / contact us.
_USER_AGENT = "khiip-daemon/0.0.1 (+https://github.com/khiip-ai/khiip)"

# X URL patterns: x.com/{user}/status/{id} or twitter.com/{user}/status/{id}
_TWEET_ID_PATTERN = re.compile(r"/status/(\d+)")


class XExtractor:
    """Extractor for X (twitter.com / x.com) URLs.

    Implements the `Extractor` Protocol from `khiip.extractors.base`.
    """

    source: str = "x"

    def __init__(self, *, http_client: httpx.Client | None = None, timeout: float = 10.0) -> None:
        self._http = http_client or httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
        )

    def supports(self, url: str) -> bool:
        """True for x.com / twitter.com URLs that look like a status."""
        try:
            host = urlparse(url).hostname or ""
        except ValueError:
            return False
        return host in ("x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com") and "/status/" in url

    def extract(self, url: str) -> CaptureData:
        """Fetch + parse an X URL into CaptureData via the fxtwitter API."""
        tweet_id = _extract_tweet_id(url)
        if tweet_id is None:
            raise ValueError(f"could not extract tweet ID from URL: {url}")

        payload = self._fetch_fxtwitter(tweet_id)
        return self._parse(url, payload)

    # ─────────────────────────────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────────────────────────────

    def _fetch_fxtwitter(self, tweet_id: str) -> dict[str, Any]:
        """Call api.fxtwitter.com and return the parsed JSON."""
        response = self._http.get(FXTWITTER_API.format(tweet_id=tweet_id))
        response.raise_for_status()
        return response.json()

    def _parse(self, source_url: str, payload: dict[str, Any]) -> CaptureData:
        """Parse fxtwitter JSON into CaptureData. v0 Week 1 scope: top-level fields only."""
        tweet = payload.get("tweet") or {}
        author = tweet.get("author") or {}
        media = tweet.get("media") or {}

        recorded_at = datetime.now(timezone.utc)
        valid_from = _parse_iso(tweet.get("created_at")) or recorded_at

        # Engagement snapshot per v0 spec D8 — captured at save time
        engagement = {
            k: int(v)
            for k, v in {
                "likes": tweet.get("likes"),
                "retweets": tweet.get("retweets"),
                "replies": tweet.get("replies"),
                "views": tweet.get("views"),
                "bookmarks": tweet.get("bookmarks"),
            }.items()
            if isinstance(v, int)
        }

        # TODO: full QRT chain expansion + X-Article body parsing + media download
        # For Week 1 scaffold: include the raw fxtwitter payload in extracted_payload
        # so downstream consumers can re-parse without re-fetching.

        return CaptureData(
            source="x",
            source_url=source_url,
            recorded_at=recorded_at,
            valid_from=valid_from,
            title=_synthesize_title(tweet.get("text"), author.get("name") or author.get("screen_name")),
            description=tweet.get("text"),
            author=author.get("screen_name"),
            body_markdown=tweet.get("text", ""),
            extracted_payload=payload,
            engagement_at_capture=engagement or None,
            media_paths=[],  # TODO: download media via gallery-dl
        )


# ─────────────────────────────────────────────────────────────────────
# Module helpers
# ─────────────────────────────────────────────────────────────────────


def _extract_tweet_id(url: str) -> str | None:
    """Extract the numeric tweet ID from an X/Twitter URL."""
    match = _TWEET_ID_PATTERN.search(url)
    return match.group(1) if match else None


def _parse_iso(value: str | None) -> datetime | None:
    """Parse an ISO 8601 timestamp string, returning None on failure."""
    if not value:
        return None
    try:
        # fxtwitter uses RFC 822 / RFC 1123 format like "Mon, 18 May 2026 17:26:00 GMT"
        # but the field name `created_at` may also yield ISO from other sources.
        # Try ISO first, fall back to email-style parsing.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        try:
            from email.utils import parsedate_to_datetime

            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None


def _synthesize_title(text: str | None, author: str | None) -> str | None:
    """Build a short title for the capture filename slug."""
    if not text:
        return f"tweet by {author}" if author else None
    first_line = text.splitlines()[0]
    if len(first_line) > 80:
        first_line = first_line[:77].rstrip() + "..."
    return first_line


__all__ = ["XExtractor"]
