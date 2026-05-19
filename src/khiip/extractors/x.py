"""X (Twitter) extractor — fxtwitter primary; gallery-dl supplement (TODO).

Per ADR-0007 Lens 4 + Phase 3 Test 1 validation: X capture is Khiip's
highest-fidelity source. fxtwitter's `api.fxtwitter.com/i/status/{id}` returns
structured JSON with the full QRT chain + embedded X-Article body + view +
bookmark + quote counts. Test 1 measured: 42,675 bytes structured JSON
(fxtwitter) vs 2,625 bytes flat markdown (Jina Reader) — 16× capture-depth
gap that motivates this extractor.

**Current scope (this pass):**
- URL parser → tweet ID
- fxtwitter HTTP call → JSON (sends khiip UA; default httpx UA is 403'd)
- Body composition (in order):
    1. Reply-context header (`replying_to` + `replying_to_status`)
    2. Main tweet text (or article content blocks if `tweet.article`)
    3. Media (photos as `![](url)`, videos as `[video N](url)`)
    4. Community note (if present)
    5. QRT blockquote (one level deep)
- Engagement snapshot — likes/retweets/replies/views/bookmarks/quotes
- `extracted_payload` preserves the verbatim fxtwitter JSON

**Deferred to next pass:**
- gallery-dl integration for media binaries → populate `media_paths`
- Recursive QRT depth >1 (current scaffold renders one level)
- Article inline media blocks (currently rendered as `[image N]` placeholder)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from khiip.extractors.base import CaptureData

FXTWITTER_API = "https://api.fxtwitter.com/i/status/{tweet_id}"

# fxtwitter blocks the default `python-httpx/*` User-Agent (returns 403).
# Identify Khiip explicitly so the upstream operator can rate-limit / contact us.
_USER_AGENT = "khiip-daemon/0.0.1 (+https://github.com/khiip-ai/khiip)"

# X URL patterns: x.com/{user}/status/{id} or twitter.com/{user}/status/{id}
_TWEET_ID_PATTERN = re.compile(r"/status/(\d+)")

# Engagement keys we capture from a tweet (or its quote)
_ENGAGEMENT_KEYS = ("likes", "retweets", "replies", "views", "bookmarks", "quotes")


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
        """Parse fxtwitter JSON into CaptureData."""
        tweet = payload.get("tweet") or {}
        author = tweet.get("author") or {}

        recorded_at = datetime.now(timezone.utc)
        valid_from = _parse_iso(tweet.get("created_at")) or recorded_at

        engagement = _parse_engagement(tweet)
        quote = tweet.get("quote") if isinstance(tweet.get("quote"), dict) else None

        body_markdown = _render_body(tweet)

        title = _synthesize_title(
            article=tweet.get("article"),
            text=tweet.get("text"),
            author=author.get("name") or author.get("screen_name"),
            quote_author=(quote or {}).get("author", {}).get("screen_name") if quote else None,
        )

        return CaptureData(
            source="x",
            source_url=source_url,
            recorded_at=recorded_at,
            valid_from=valid_from,
            title=title,
            description=tweet.get("text"),
            author=author.get("screen_name"),
            body_markdown=body_markdown,
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


def _parse_engagement(tweet: dict[str, Any]) -> dict[str, int]:
    """Extract per-v0-spec engagement snapshot, coercing non-int values to skip."""
    return {
        k: int(tweet[k])
        for k in _ENGAGEMENT_KEYS
        if isinstance(tweet.get(k), int)
    }


def _synthesize_title(
    *,
    article: dict[str, Any] | None,
    text: str | None,
    author: str | None,
    quote_author: str | None = None,
) -> str | None:
    """Build a short title for the capture filename slug.

    Priority: article title (long-form posts) > first text line > author fallback.
    QRTs get a `(QRT @author)` suffix so they're distinguishable in the vault.
    """
    if isinstance(article, dict) and article.get("title"):
        base = str(article["title"]).strip()
    elif text:
        base = text.splitlines()[0]
    elif author:
        base = f"tweet by {author}"
    else:
        return None

    if quote_author:
        base = f"{base} (QRT @{quote_author})"

    if len(base) > 80:
        base = base[:77].rstrip() + "..."
    return base


# ─────────────────────────────────────────────────────────────────────
# Body rendering — composes markdown from tweet sub-structures
# ─────────────────────────────────────────────────────────────────────


def _render_body(tweet: dict[str, Any]) -> str:
    """Compose the full markdown body for the captured tweet."""
    parts: list[str] = []

    reply_header = _render_reply_header(tweet)
    if reply_header:
        parts.append(reply_header)

    article = tweet.get("article")
    if isinstance(article, dict):
        parts.append(_render_article(article))
    elif tweet.get("text"):
        parts.append(str(tweet["text"]))

    media_md = _render_media(tweet.get("media"))
    if media_md:
        parts.append(media_md)

    note_md = _render_community_note(tweet.get("community_note"))
    if note_md:
        parts.append(note_md)

    quote_md = _render_quote(tweet.get("quote"))
    if quote_md:
        parts.append(quote_md)

    return "\n\n".join(parts)


def _render_reply_header(tweet: dict[str, Any]) -> str | None:
    """Render `In reply to @author (status/id)` header when this tweet is a reply."""
    parent_author = tweet.get("replying_to")
    parent_status = tweet.get("replying_to_status")
    if not parent_author:
        return None
    if parent_status:
        return f"_In reply to_ [@{parent_author}](https://x.com/{parent_author}/status/{parent_status})"
    return f"_In reply to_ @{parent_author}"


def _render_media(media: Any) -> str | None:
    """Render media block from `tweet.media.all[]`.

    Photos → `![](url)`. Videos → `[video N](url)`. Returns None when no media.
    Defensive against the older fxtwitter summary shape (`{all: int}`) where
    `media.all` is an integer count rather than a list — those payloads
    pre-date the structured response and are treated as empty.
    """
    if not isinstance(media, dict):
        return None
    items = media.get("all")
    if not isinstance(items, list) or not items:
        return None

    lines: list[str] = []
    video_idx = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not isinstance(url, str):
            continue
        kind = item.get("type")
        if kind == "video" or kind == "gif":
            video_idx += 1
            lines.append(f"[video {video_idx}]({url})")
        else:
            lines.append(f"![]({url})")
    return "\n\n".join(lines) if lines else None


def _render_community_note(note: Any) -> str | None:
    """Render a Birdwatch / Community Note as a blockquote."""
    if not isinstance(note, dict):
        return None
    text = note.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
    quoted = "\n".join(f"> {line}" for line in text.splitlines())
    return f"**Community Note:**\n\n{quoted}"


def _render_quote(quote: Any) -> str | None:
    """Render a QRT'd tweet as an attributed blockquote (one level deep)."""
    if not isinstance(quote, dict):
        return None
    author = (quote.get("author") or {}).get("screen_name") or "unknown"
    text = quote.get("text") or ""
    url = quote.get("url") or ""
    if not text and not url:
        return None

    quoted = "\n".join(f"> {line}" for line in text.splitlines()) if text else "> _(no text)_"
    header = f"**Quoting [@{author}]({url}):**" if url else f"**Quoting @{author}:**"
    return f"{header}\n\n{quoted}"


def _render_article(article: dict[str, Any]) -> str:
    """Render an X-Article's title + block content into markdown."""
    lines: list[str] = []
    title = article.get("title")
    if isinstance(title, str) and title.strip():
        lines.append(f"# {title.strip()}")
    subtitle = article.get("subtitle")
    if isinstance(subtitle, str) and subtitle.strip():
        lines.append(f"_{subtitle.strip()}_")

    content = article.get("content") or {}
    blocks = content.get("blocks") if isinstance(content, dict) else None
    if isinstance(blocks, list):
        image_idx = 0
        for block in blocks:
            if not isinstance(block, dict):
                continue
            rendered, image_idx = _render_article_block(block, image_idx)
            if rendered:
                lines.append(rendered)

    return "\n\n".join(lines)


def _render_article_block(block: dict[str, Any], image_idx: int) -> tuple[str | None, int]:
    """Render a single article block to markdown. Returns (md, new_image_idx)."""
    btype = block.get("type")
    text = block.get("text", "")

    if btype == "heading":
        depth = block.get("depth", 1)
        try:
            depth = max(1, min(6, int(depth)))
        except (TypeError, ValueError):
            depth = 2
        return f"{'#' * depth} {text}".rstrip(), image_idx
    if btype == "paragraph":
        return str(text), image_idx
    if btype == "image":
        image_idx += 1
        url = block.get("url")
        if isinstance(url, str):
            return f"![]({url})", image_idx
        return f"[image {image_idx}]", image_idx
    if btype == "list":
        items = block.get("items")
        if isinstance(items, list):
            ordered = bool(block.get("ordered"))
            prefix = "1." if ordered else "-"
            lines = [f"{prefix} {item}" for item in items if isinstance(item, str)]
            return "\n".join(lines) if lines else None, image_idx
        return None, image_idx
    if btype == "quote":
        return f"> {text}", image_idx

    # Unknown block type — fall back to its `text` if present, else skip
    return (str(text) if text else None), image_idx


__all__ = ["XExtractor"]
