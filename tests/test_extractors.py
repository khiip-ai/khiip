"""Tests for the Extractor Protocol + XExtractor parsing (offline; no network)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import httpx
import pytest

from khiip.extractors.base import CaptureData, ExtractorRegistry
from khiip.extractors.x import XExtractor, _extract_tweet_id, _parse_iso, _synthesize_title


# ─────────────────────────────────────────────────────────────────────
# XExtractor.supports — URL pattern matching
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://x.com/user/status/123", True),
        ("https://www.x.com/user/status/123", True),
        ("https://twitter.com/user/status/123", True),
        ("https://www.twitter.com/user/status/123", True),
        ("https://mobile.twitter.com/user/status/123", True),
        ("https://x.com/user/profile", False),  # no /status/
        ("https://example.com/user/status/123", False),  # wrong host
        ("https://github.com/khiip-ai/khiip", False),
        ("not a url", False),
    ],
)
def test_xextractor_supports(url: str, expected: bool) -> None:
    ex = XExtractor(http_client=MagicMock(spec=httpx.Client))
    assert ex.supports(url) is expected


# ─────────────────────────────────────────────────────────────────────
# _extract_tweet_id
# ─────────────────────────────────────────────────────────────────────


def test_extract_tweet_id_finds_numeric_id() -> None:
    assert _extract_tweet_id("https://x.com/foo/status/1234567890") == "1234567890"
    assert _extract_tweet_id("https://twitter.com/bar/status/9999/something") == "9999"


def test_extract_tweet_id_returns_none_on_no_match() -> None:
    assert _extract_tweet_id("https://x.com/foo/profile") is None
    assert _extract_tweet_id("https://example.com/post/123") is None


# ─────────────────────────────────────────────────────────────────────
# _synthesize_title
# ─────────────────────────────────────────────────────────────────────


def test_synthesize_title_uses_first_line() -> None:
    text = "First line of the tweet.\nSecond line goes here."
    assert _synthesize_title(text, "alice") == "First line of the tweet."


def test_synthesize_title_truncates_long() -> None:
    text = "x" * 200
    title = _synthesize_title(text, "alice")
    assert title is not None
    assert len(title) <= 80
    assert title.endswith("...")


def test_synthesize_title_falls_back_to_author() -> None:
    assert _synthesize_title(None, "alice") == "tweet by alice"
    assert _synthesize_title("", "alice") == "tweet by alice"


# ─────────────────────────────────────────────────────────────────────
# XExtractor._parse — fxtwitter JSON shape
# ─────────────────────────────────────────────────────────────────────


def test_xextractor_parse_returns_capture_data() -> None:
    """Given a representative fxtwitter payload, parse produces full CaptureData."""
    payload = {
        "tweet": {
            "text": "An example tweet body about Khiip.",
            "created_at": "Mon, 18 May 2026 17:26:00 GMT",
            "author": {"screen_name": "namcios", "name": "Felipe Demartini"},
            "likes": 2272,
            "retweets": 171,
            "replies": 168,
            "views": 1161874,
            "bookmarks": 4749,
            "media": {"all": 1, "videos": 1},
        }
    }
    ex = XExtractor(http_client=MagicMock(spec=httpx.Client))
    cap = ex._parse("https://x.com/namcios/status/2053257337746657561", payload)

    assert isinstance(cap, CaptureData)
    assert cap.source == "x"
    assert cap.source_url == "https://x.com/namcios/status/2053257337746657561"
    assert cap.author == "namcios"
    assert cap.title is not None
    assert "An example tweet body" in cap.title
    assert cap.body_markdown == "An example tweet body about Khiip."
    assert cap.engagement_at_capture == {
        "likes": 2272,
        "retweets": 171,
        "replies": 168,
        "views": 1161874,
        "bookmarks": 4749,
    }
    assert cap.extracted_payload == payload
    assert cap.media_paths == []


def test_xextractor_parse_handles_missing_engagement() -> None:
    """If engagement fields are absent, engagement_at_capture is None (not empty dict)."""
    payload = {"tweet": {"text": "minimal", "author": {"screen_name": "u"}}}
    ex = XExtractor(http_client=MagicMock(spec=httpx.Client))
    cap = ex._parse("https://x.com/u/status/1", payload)
    assert cap.engagement_at_capture is None


# ─────────────────────────────────────────────────────────────────────
# ExtractorRegistry
# ─────────────────────────────────────────────────────────────────────


def test_registry_dispatch_to_matching_extractor() -> None:
    reg = ExtractorRegistry()
    reg.register(XExtractor(http_client=MagicMock(spec=httpx.Client)))

    assert reg.find("https://x.com/foo/status/123") is not None
    assert reg.find("https://example.com/article") is None
    assert len(reg) == 1


def test_registry_rejects_non_extractor() -> None:
    class NotAnExtractor:
        pass

    reg = ExtractorRegistry()
    with pytest.raises(TypeError):
        reg.register(NotAnExtractor())  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────
# _parse_iso
# ─────────────────────────────────────────────────────────────────────


def test_parse_iso_handles_rfc822_format() -> None:
    """fxtwitter returns RFC 822 dates like 'Mon, 18 May 2026 17:26:00 GMT'."""
    result = _parse_iso("Mon, 18 May 2026 17:26:00 GMT")
    assert result is not None
    assert result.year == 2026
    assert result.month == 5


def test_parse_iso_handles_iso_format() -> None:
    result = _parse_iso("2026-05-18T17:26:00+00:00")
    assert result is not None
    assert result.year == 2026


def test_parse_iso_returns_none_on_garbage() -> None:
    assert _parse_iso(None) is None
    assert _parse_iso("not a date at all") is None
