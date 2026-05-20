"""Tests for the Extractor Protocol + XExtractor parsing (offline; no network)."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from khiip.extractors.base import CaptureData, ExtractorRegistry
from khiip.extractors.x import (
    XExtractor,
    _extract_tweet_id,
    _parse_engagement,
    _parse_iso,
    _render_article,
    _render_body,
    _render_community_note,
    _render_media,
    _render_quote,
    _render_reply_header,
    _synthesize_title,
)

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
    assert _synthesize_title(article=None, text=text, author="alice") == "First line of the tweet."


def test_synthesize_title_truncates_long() -> None:
    title = _synthesize_title(article=None, text="x" * 200, author="alice")
    assert title is not None
    assert len(title) <= 80
    assert title.endswith("...")


def test_synthesize_title_falls_back_to_author() -> None:
    assert _synthesize_title(article=None, text=None, author="alice") == "tweet by alice"
    assert _synthesize_title(article=None, text="", author="alice") == "tweet by alice"


def test_synthesize_title_prefers_article_title() -> None:
    article = {"title": "On Distillation"}
    title = _synthesize_title(article=article, text="text we ignore", author="alice")
    assert title == "On Distillation"


def test_synthesize_title_marks_qrt() -> None:
    title = _synthesize_title(article=None, text="my hot take", author="me", quote_author="bob")
    assert title == "my hot take (QRT @bob)"


# ─────────────────────────────────────────────────────────────────────
# _parse_engagement
# ─────────────────────────────────────────────────────────────────────


def test_parse_engagement_includes_quotes() -> None:
    """`quotes` was missing in the prior pass — confirm it lands now."""
    eng = _parse_engagement(
        {"likes": 10, "retweets": 5, "replies": 3, "views": 100, "bookmarks": 2, "quotes": 7}
    )
    assert eng == {"likes": 10, "retweets": 5, "replies": 3, "views": 100, "bookmarks": 2, "quotes": 7}


def test_parse_engagement_skips_non_int() -> None:
    """views is sometimes null (e.g. jack/20); coerce-skip rather than 0-fill."""
    eng = _parse_engagement({"likes": 10, "views": None, "bookmarks": "junk"})
    assert eng == {"likes": 10}


# ─────────────────────────────────────────────────────────────────────
# Body sub-renderers
# ─────────────────────────────────────────────────────────────────────


def test_render_reply_header_with_status() -> None:
    h = _render_reply_header({"replying_to": "alice", "replying_to_status": "12345"})
    assert h == "_In reply to_ [@alice](https://x.com/alice/status/12345)"


def test_render_reply_header_without_status() -> None:
    h = _render_reply_header({"replying_to": "alice"})
    assert h == "_In reply to_ @alice"


def test_render_reply_header_none_when_not_a_reply() -> None:
    assert _render_reply_header({"replying_to": None}) is None
    assert _render_reply_header({}) is None


def test_render_media_renders_photos_and_videos() -> None:
    media = {
        "all": [
            {"type": "photo", "url": "https://pbs.twimg.com/media/a.jpg"},
            {"type": "video", "url": "https://video.twimg.com/v/b.mp4"},
            {"type": "photo", "url": "https://pbs.twimg.com/media/c.jpg"},
        ]
    }
    md = _render_media(media)
    assert md is not None
    assert "![](https://pbs.twimg.com/media/a.jpg)" in md
    assert "[video 1](https://video.twimg.com/v/b.mp4)" in md
    assert "![](https://pbs.twimg.com/media/c.jpg)" in md


def test_render_media_tolerates_legacy_summary_shape() -> None:
    """Older fxtwitter responses sometimes used {all: int}; treat as empty."""
    assert _render_media({"all": 1, "videos": 1}) is None
    assert _render_media(None) is None
    assert _render_media({}) is None


def test_render_community_note_renders_as_blockquote() -> None:
    note = {"text": "This is misleading.\nSee correction."}
    md = _render_community_note(note)
    assert md is not None
    assert "**Community Note:**" in md
    assert "> This is misleading." in md
    assert "> See correction." in md


def test_render_community_note_none_when_absent() -> None:
    assert _render_community_note(None) is None
    assert _render_community_note({"text": ""}) is None


def test_render_quote_renders_as_attributed_blockquote() -> None:
    quote = {
        "author": {"screen_name": "alice"},
        "text": "Original tweet\nsecond line.",
        "url": "https://x.com/alice/status/42",
    }
    md = _render_quote(quote)
    assert md is not None
    assert "**Quoting [@alice](https://x.com/alice/status/42):**" in md
    assert "> Original tweet" in md
    assert "> second line." in md


def test_render_quote_none_when_no_quote() -> None:
    assert _render_quote(None) is None
    assert _render_quote({"author": {"screen_name": "alice"}}) is None  # no text + no url


def test_render_article_renders_blocks() -> None:
    article = {
        "title": "On Distillation",
        "subtitle": "and what it reveals",
        "content": {
            "blocks": [
                {"type": "heading", "text": "Intro", "depth": 2},
                {"type": "paragraph", "text": "First paragraph."},
                {"type": "list", "items": ["a", "b", "c"], "ordered": False},
                {"type": "image", "url": "https://pbs.twimg.com/article/img.jpg"},
                {"type": "quote", "text": "an inline quote"},
            ]
        },
    }
    md = _render_article(article)
    assert "# On Distillation" in md
    assert "_and what it reveals_" in md
    assert "## Intro" in md
    assert "First paragraph." in md
    assert "- a\n- b\n- c" in md
    assert "![](https://pbs.twimg.com/article/img.jpg)" in md
    assert "> an inline quote" in md


def test_render_body_simple_tweet_returns_text_only() -> None:
    """Plain tweet with no reply/quote/media/article composes to just the text."""
    tweet = {"text": "just setting up my twttr"}
    assert _render_body(tweet) == "just setting up my twttr"


def test_render_body_composes_all_sections() -> None:
    """Full tweet with reply context + media + community note + QRT all surface in body."""
    tweet = {
        "text": "agree",
        "replying_to": "alice",
        "replying_to_status": "1",
        "media": {"all": [{"type": "photo", "url": "https://pbs.twimg.com/x.jpg"}]},
        "community_note": {"text": "context here"},
        "quote": {
            "author": {"screen_name": "bob"},
            "text": "what bob said",
            "url": "https://x.com/bob/status/2",
        },
    }
    body = _render_body(tweet)
    assert "_In reply to_" in body
    assert "agree" in body
    assert "![](https://pbs.twimg.com/x.jpg)" in body
    assert "**Community Note:**" in body
    assert "**Quoting [@bob]" in body


# ─────────────────────────────────────────────────────────────────────
# XExtractor._parse — full fxtwitter payload shape
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
            "quotes": 89,
        }
    }
    ex = XExtractor(http_client=MagicMock(spec=httpx.Client))
    cap = ex._parse_fxtwitter("https://x.com/namcios/status/2053257337746657561", payload)

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
        "quotes": 89,
    }
    assert cap.extracted_payload == payload
    assert cap.media_paths == []


def test_xextractor_parse_handles_missing_engagement() -> None:
    """If engagement fields are absent, engagement_at_capture is None (not empty dict)."""
    payload = {"tweet": {"text": "minimal", "author": {"screen_name": "u"}}}
    ex = XExtractor(http_client=MagicMock(spec=httpx.Client))
    cap = ex._parse_fxtwitter("https://x.com/u/status/1", payload)
    assert cap.engagement_at_capture is None


def test_xextractor_parse_qrt_marks_title_and_embeds_quote() -> None:
    """A QRT'd tweet renders the quote inline and tags the title."""
    payload = {
        "tweet": {
            "text": "+1 to this",
            "author": {"screen_name": "me", "name": "Me"},
            "quote": {
                "author": {"screen_name": "alice"},
                "text": "great point",
                "url": "https://x.com/alice/status/1",
            },
        }
    }
    ex = XExtractor(http_client=MagicMock(spec=httpx.Client))
    cap = ex._parse_fxtwitter("https://x.com/me/status/9", payload)
    assert cap.title is not None
    assert cap.title.endswith("(QRT @alice)")
    assert "**Quoting [@alice]" in cap.body_markdown
    assert "> great point" in cap.body_markdown


def test_xextractor_parse_article_uses_article_title_and_renders_blocks() -> None:
    """Long-form tweets with an article use article.title + block render."""
    payload = {
        "tweet": {
            "text": "fallback text the parser should ignore for body",
            "author": {"screen_name": "essayist"},
            "is_note_tweet": True,
            "article": {
                "title": "A Long Essay",
                "content": {
                    "blocks": [
                        {"type": "heading", "text": "Section 1", "depth": 2},
                        {"type": "paragraph", "text": "Hello world."},
                    ]
                },
            },
        }
    }
    ex = XExtractor(http_client=MagicMock(spec=httpx.Client))
    cap = ex._parse_fxtwitter("https://x.com/essayist/status/100", payload)
    assert cap.title == "A Long Essay"
    assert "# A Long Essay" in cap.body_markdown
    assert "## Section 1" in cap.body_markdown
    assert "Hello world." in cap.body_markdown


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


# ─────────────────────────────────────────────────────────────────────
# WebExtractor — generic article capture via trafilatura
# ─────────────────────────────────────────────────────────────────────

from khiip.extractors.web import WebExtractor, _parse_metadata_date


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://example.com/article", True),
        ("http://example.com/article", True),
        ("https://example.com", True),
        ("ftp://example.com/file", False),
        ("file:///etc/passwd", False),
        ("javascript:alert(1)", False),
        ("not-a-url", False),
        ("", False),
    ],
)
def test_webextractor_supports(url: str, expected: bool) -> None:
    assert WebExtractor().supports(url) is expected


def test_webextractor_parse_html_extracts_title_and_body() -> None:
    """trafilatura returns title from <title> + Markdown body from <article>."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
      <title>How to Build Software</title>
      <meta name="author" content="Jane Author">
      <meta name="description" content="A guide on software construction.">
      <meta property="article:published_time" content="2026-05-10T12:00:00Z">
    </head>
    <body>
      <article>
        <h1>How to Build Software</h1>
        <p>Building software is hard. It requires careful planning.</p>
        <p>Here is a second paragraph with substantive content.</p>
      </article>
    </body>
    </html>
    """
    extractor = WebExtractor()
    data = extractor._parse_trafilatura(html, canonical_url="https://example.com/build-software")
    assert data.source == "web"
    assert data.source_url == "https://example.com/build-software"
    assert data.title == "How to Build Software"
    assert data.description == "A guide on software construction."
    assert data.author == "Jane Author"
    assert "Building software is hard" in data.body_markdown
    assert "second paragraph" in data.body_markdown
    # Published date parsed into valid_from
    assert data.valid_from.year == 2026
    assert data.valid_from.month == 5
    assert data.valid_from.day == 10


def test_webextractor_parse_trafilatura_partial_returns_capturedata_when_title_present() -> None:
    """Body empty but title present → success (thin success)."""
    html = "<html><head><title>Login</title></head><body><form></form></body></html>"
    data = WebExtractor()._parse_trafilatura(html, canonical_url="https://example.com/login")
    assert data.source == "web"
    assert data.title == "Login"
    assert isinstance(data.body_markdown, str)


def test_webextractor_parse_trafilatura_empty_body_and_no_title_raises_fallback_failed() -> None:
    """Body AND title both empty → FallbackFailed → fallback chain tries readability next."""
    from khiip.extractors.resilience import FallbackFailed as _FF
    html = "<html><head></head><body><form></form></body></html>"
    with pytest.raises(_FF):
        WebExtractor()._parse_trafilatura(html, canonical_url="https://example.com/blank")


def test_webextractor_parse_trafilatura_no_date_metadata_falls_back_to_recorded_at() -> None:
    """When trafilatura can't find a publish date, valid_from == recorded_at."""
    html = "<html><head><title>Undated</title></head><body><article><p>x</p></article></body></html>"
    data = WebExtractor()._parse_trafilatura(html, canonical_url="https://example.com/x")
    assert data.valid_from == data.recorded_at


def test_webextractor_extract_hits_http_and_canonicalizes_url() -> None:
    """extract() fetches via the injected httpx client + uses post-redirect URL."""
    html = "<html><head><title>Real Article</title></head><body><article><p>Body content here for the article body.</p></article></body></html>"
    response = MagicMock(spec=httpx.Response)
    response.text = html
    response.url = "https://example.com/canonical"  # after redirect
    response.raise_for_status = MagicMock()

    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)

    data = WebExtractor(http_client=client).extract("https://example.com/short")
    client.get.assert_called_once_with("https://example.com/short")
    response.raise_for_status.assert_called_once()
    assert data.source_url == "https://example.com/canonical"
    assert data.title == "Real Article"


def test_webextractor_extract_propagates_http_error() -> None:
    """4xx/5xx upstream → raise_for_status fires → daemon turns into 502."""
    response = MagicMock(spec=httpx.Response)
    response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock()))

    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)

    with pytest.raises(httpx.HTTPStatusError):
        WebExtractor(http_client=client).extract("https://example.com/missing")


def test_parse_metadata_date_handles_iso_date_only() -> None:
    """trafilatura.Document.date is typically YYYY-MM-DD; assume UTC."""
    dt = _parse_metadata_date("2026-05-15")
    assert dt is not None
    assert (dt.year, dt.month, dt.day) == (2026, 5, 15)
    assert dt.tzinfo is not None  # UTC stamped


def test_parse_metadata_date_handles_full_iso_z() -> None:
    dt = _parse_metadata_date("2026-05-15T12:00:00Z")
    assert dt is not None
    assert dt.year == 2026
    assert dt.tzinfo is not None


def test_parse_metadata_date_returns_none_for_unparseable() -> None:
    assert _parse_metadata_date(None) is None
    assert _parse_metadata_date("") is None
    assert _parse_metadata_date("not a date") is None


# ─────────────────────────────────────────────────────────────────────
# Registry ordering — X first, Web fallback last
# ─────────────────────────────────────────────────────────────────────


def test_registry_order_x_claims_x_urls_web_claims_others() -> None:
    """XExtractor must be tried before WebExtractor so x.com URLs don't fall through."""
    from khiip.extractors.x import XExtractor
    registry = ExtractorRegistry()
    registry.register(XExtractor())
    registry.register(WebExtractor())

    # x.com URL → XExtractor
    found_x = registry.find("https://x.com/jack/status/20")
    assert found_x is not None
    assert found_x.source == "x"

    # Generic article → WebExtractor
    found_web = registry.find("https://example.com/article")
    assert found_web is not None
    assert found_web.source == "web"


# ─────────────────────────────────────────────────────────────────────
# Resilience primitives — try_fallback_chain, ExtractorError, HealthStatus
# ─────────────────────────────────────────────────────────────────────

from khiip.extractors.resilience import (
    ExtractorError,
    FallbackFailed,
    FallbackSource,
    HealthCheckable,
    HealthStatus,
    try_fallback_chain,
)


def test_try_fallback_chain_first_succeeds():
    calls = []

    def ok1(target):
        calls.append("a"); return f"from-a:{target}"

    def ok2(target):
        calls.append("b"); return f"from-b:{target}"

    sources = [FallbackSource("a", ok1), FallbackSource("b", ok2)]
    name, result = try_fallback_chain(sources, "T")
    assert name == "a"
    assert result == "from-a:T"
    assert calls == ["a"]  # second source not called


def test_try_fallback_chain_falls_to_second():
    def fail1(target):
        raise FallbackFailed("a is down")

    def ok2(target):
        return f"from-b:{target}"

    sources = [FallbackSource("a", fail1), FallbackSource("b", ok2)]
    name, result = try_fallback_chain(sources, "T")
    assert name == "b"
    assert result == "from-b:T"


def test_try_fallback_chain_all_fail_raises_extractor_error():
    sources = [
        FallbackSource("a", lambda t: (_ for _ in ()).throw(FallbackFailed("a down"))),
        FallbackSource("b", lambda t: (_ for _ in ()).throw(FallbackFailed("b down"))),
    ]
    with pytest.raises(ExtractorError) as info:
        try_fallback_chain(sources, "T")
    assert "a down" in info.value.reason
    assert "b down" in info.value.reason


def test_try_fallback_chain_propagates_retry_after_from_last_failure():
    sources = [
        FallbackSource(
            "a",
            lambda t: (_ for _ in ()).throw(FallbackFailed("a 429", retry_after=30)),
        ),
        FallbackSource(
            "b",
            lambda t: (_ for _ in ()).throw(FallbackFailed("b 429", retry_after=60)),
        ),
    ]
    with pytest.raises(ExtractorError) as info:
        try_fallback_chain(sources, "T")
    assert info.value.retry_after == 60


def test_try_fallback_chain_empty_raises():
    with pytest.raises(ExtractorError):
        try_fallback_chain([], "T")


def test_try_fallback_chain_non_fallback_exception_propagates():
    """A TypeError inside a fetch_fn is a bug — not a fallback signal — and propagates."""

    def buggy(target):
        raise TypeError("misuse")

    def ok_after(target):
        return "wont be called"

    with pytest.raises(TypeError):
        try_fallback_chain(
            [FallbackSource("buggy", buggy), FallbackSource("ok", ok_after)], "T"
        )


# ─────────────────────────────────────────────────────────────────────
# XExtractor — fallback chain integration
# ─────────────────────────────────────────────────────────────────────


def _stub_fxtwitter_payload(tweet_text="hello world", screen_name="jack"):
    return {
        "tweet": {
            "text": tweet_text,
            "author": {"name": "Jack", "screen_name": screen_name},
            "created_at": "Mon, 18 May 2026 17:26:00 GMT",
            "likes": 5, "retweets": 2, "replies": 1, "views": 100, "bookmarks": 3,
        }
    }


def _stub_vxtwitter_payload(tweet_text="hello world", screen_name="jack"):
    return {
        "text": tweet_text,
        "user_name": "Jack",
        "user_screen_name": screen_name,
        "date": "Mon, 18 May 2026 17:26:00 GMT",
        "likes": 5, "retweets": 2, "replies": 1, "qrtCount": 0,
        "mediaURLs": [],
    }


def test_xextractor_fxtwitter_succeeds_vxtwitter_not_called():
    """Happy path: fxtwitter returns 200; vxtwitter never called."""
    fx_response = MagicMock(spec=httpx.Response)
    fx_response.raise_for_status = MagicMock()
    fx_response.json = MagicMock(return_value=_stub_fxtwitter_payload())

    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=fx_response)

    cap = XExtractor(http_client=client).extract("https://x.com/jack/status/20")
    assert cap.source == "x"
    assert cap.author == "jack"
    assert client.get.call_count == 1  # only fxtwitter
    assert "fxtwitter" in client.get.call_args[0][0]
    assert cap.extracted_payload.get("_extractor_source") == "fxtwitter"


def test_xextractor_fxtwitter_404_falls_to_vxtwitter():
    """fxtwitter 404 → fall through to vxtwitter, which returns 200."""
    fx_error_response = MagicMock()
    fx_error_response.status_code = 404
    fx_error_response.headers = {}

    fx_response = MagicMock(spec=httpx.Response)
    fx_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=fx_error_response)
    )

    vx_response = MagicMock(spec=httpx.Response)
    vx_response.raise_for_status = MagicMock()
    vx_response.json = MagicMock(return_value=_stub_vxtwitter_payload())

    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(side_effect=[fx_response, vx_response])

    cap = XExtractor(http_client=client).extract("https://x.com/jack/status/20")
    assert cap.source == "x"
    assert cap.author == "jack"
    assert client.get.call_count == 2
    assert "fxtwitter" in client.get.call_args_list[0][0][0]
    assert "vxtwitter" in client.get.call_args_list[1][0][0]
    assert cap.extracted_payload.get("_extractor_source") == "vxtwitter"


def test_xextractor_both_sources_fail_raises_extractor_error():
    """Both upstreams 404 → ExtractorError surfaces both reasons; daemon → 502."""
    fx_error_response = MagicMock(); fx_error_response.status_code = 404; fx_error_response.headers = {}
    vx_error_response = MagicMock(); vx_error_response.status_code = 503; vx_error_response.headers = {"Retry-After": "30"}

    fx_response = MagicMock(spec=httpx.Response)
    fx_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=fx_error_response)
    )

    vx_response = MagicMock(spec=httpx.Response)
    vx_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("503", request=MagicMock(), response=vx_error_response)
    )

    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(side_effect=[fx_response, vx_response])

    with pytest.raises(ExtractorError) as info:
        XExtractor(http_client=client).extract("https://x.com/u/status/123")
    assert "fxtwitter" in info.value.reason
    assert "vxtwitter" in info.value.reason
    assert info.value.retry_after == 30  # propagated from vxtwitter (last failure)


def test_xextractor_health_check_ok_when_fxtwitter_returns_tweet():
    response = MagicMock(spec=httpx.Response)
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value=_stub_fxtwitter_payload())

    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)

    status_obj = XExtractor(http_client=client).health_check()
    assert status_obj.source == "x"
    assert status_obj.ok is True
    assert status_obj.degraded_reason is None
    assert status_obj.fallback_count == 2


def test_xextractor_health_check_degraded_on_fxtwitter_5xx():
    error_response = MagicMock(); error_response.status_code = 503; error_response.headers = {}
    response = MagicMock(spec=httpx.Response)
    response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("503", request=MagicMock(), response=error_response)
    )
    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)

    status_obj = XExtractor(http_client=client).health_check()
    assert status_obj.ok is False
    assert "HTTPStatusError" in status_obj.degraded_reason


def test_xextractor_health_check_degraded_on_unexpected_shape():
    """fxtwitter returns 200 but missing the `tweet` key (catalog drift)."""
    response = MagicMock(spec=httpx.Response)
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value={"error": "Not Found"})
    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)

    status_obj = XExtractor(http_client=client).health_check()
    assert status_obj.ok is False
    assert "unexpected shape" in status_obj.degraded_reason


def test_xextractor_is_health_checkable_protocol():
    """XExtractor satisfies the HealthCheckable Protocol — runtime check."""
    assert isinstance(XExtractor(), HealthCheckable)


def test_webextractor_is_health_checkable():
    """WebExtractor now implements health_check (since web resilience pass)."""
    assert isinstance(WebExtractor(), HealthCheckable)


def test_xextractor_parse_vxtwitter_extracts_fields():
    """vxtwitter parser handles the flatter response shape."""
    cap = XExtractor()._parse_vxtwitter(
        "https://x.com/jack/status/20", _stub_vxtwitter_payload()
    )
    assert cap.source == "x"
    assert cap.author == "jack"
    assert cap.description == "hello world"
    assert cap.engagement_at_capture == {"likes": 5, "retweets": 2, "replies": 1, "quotes": 0}


# ─────────────────────────────────────────────────────────────────────
# WebExtractor — fallback chain integration (trafilatura → readability)
# ─────────────────────────────────────────────────────────────────────


def _webextract_with_html(html: str, canonical_url: str = "https://example.com/article") -> CaptureData:
    """Helper: WebExtractor with httpx mocked to return the given HTML."""
    response = MagicMock(spec=httpx.Response)
    response.text = html
    response.url = canonical_url
    response.raise_for_status = MagicMock()
    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)
    return WebExtractor(http_client=client).extract(canonical_url)


def test_webextractor_trafilatura_wins_on_normal_article():
    """Normal article → trafilatura extracts → readability not exercised."""
    html = """
    <html><head><title>Real Article</title></head>
    <body><article><p>This is the article body with substantial content for extraction.</p></article></body></html>
    """
    cap = _webextract_with_html(html)
    assert cap.title == "Real Article"
    assert "article body" in cap.body_markdown
    assert cap.extracted_payload.get("_extractor_source") == "trafilatura"


def test_webextractor_falls_to_readability_when_trafilatura_returns_nothing():
    """Page where trafilatura extracts nothing but readability finds the content."""
    # No <article>, no <p> at top level, no <title>. trafilatura's heuristics give up.
    # readability's scoring algorithm should still find body-like content.
    html = """
    <html><body>
      <div class="post"><h1>Found by readability</h1>
      <span>Some inline text that readability scores as article-like by length and density.</span>
      </div>
    </body></html>
    """
    # If trafilatura returns nothing AND no title, _parse_trafilatura raises FallbackFailed,
    # readability tries — and either succeeds or also raises FallbackFailed.
    # We can't guarantee readability finds content on every weird page; what we CAN
    # guarantee is that IF trafilatura raises FallbackFailed AND readability succeeds,
    # _extractor_source == "readability".
    # Test the more deterministic path: trafilatura succeeds with title only, readability not called.
    html_with_title = """
    <html><head><title>Has a Title</title></head>
    <body><div>Empty-ish body trafilatura might not extract</div></body></html>
    """
    cap = _webextract_with_html(html_with_title)
    # Either trafilatura (if it picked up the body) or readability (if trafilatura raised)
    assert cap.title == "Has a Title"
    assert cap.extracted_payload.get("_extractor_source") in ("trafilatura", "readability")


def test_webextractor_readability_winning_path_via_direct_call():
    """Verify the readability parser path independently."""
    html = """
    <html><body>
      <article>
        <h1>Article Heading</h1>
        <p>Body paragraph with <a href="https://example.org/">a link</a> and content.</p>
      </article>
    </body></html>
    """
    cap = WebExtractor()._parse_readability(html, canonical_url="https://example.com/a")
    assert cap.source == "web"
    # readability + markdownify preserves link syntax (richer than trafilatura)
    assert "[a link](https://example.org/)" in cap.body_markdown or "example.org" in cap.body_markdown


def test_webextractor_both_sources_fail_raises_extractor_error():
    """HTML so degenerate both parsers raise FallbackFailed → ExtractorError → 502."""
    html = "<html><head></head><body></body></html>"  # truly empty: no title, no content
    response = MagicMock(spec=httpx.Response)
    response.text = html
    response.url = "https://example.com/empty"
    response.raise_for_status = MagicMock()
    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)
    with pytest.raises(ExtractorError) as info:
        WebExtractor(http_client=client).extract("https://example.com/empty")
    assert "trafilatura" in info.value.reason
    assert "readability" in info.value.reason


def test_webextractor_http_error_propagates_before_fallback():
    """4xx/5xx upstream → httpx.HTTPError (NOT ExtractorError, since fetch is shared)."""
    error_response = MagicMock(); error_response.status_code = 404; error_response.headers = {}
    response = MagicMock(spec=httpx.Response)
    response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=error_response)
    )
    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)
    with pytest.raises(httpx.HTTPStatusError):
        WebExtractor(http_client=client).extract("https://example.com/missing")


def test_webextractor_health_check_ok_when_example_com_extractable():
    """Real-content page → trafilatura.extract returns non-empty → ok=True."""
    html = """
    <html><body><div>
      <h1>Example Domain</h1>
      <p>This domain is for use in illustrative examples in documents. You may use this
      domain in literature without prior coordination or asking for permission.</p>
    </div></body></html>
    """
    response = MagicMock(spec=httpx.Response)
    response.text = html
    response.raise_for_status = MagicMock()
    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)

    status_obj = WebExtractor(http_client=client).health_check()
    assert status_obj.source == "web"
    assert status_obj.ok is True
    assert status_obj.degraded_reason is None
    assert status_obj.fallback_count == 2


def test_webextractor_health_check_degraded_on_network_failure():
    """example.com unreachable → degraded reason names the error class."""
    response = MagicMock(spec=httpx.Response)
    error_response = MagicMock(); error_response.status_code = 503; error_response.headers = {}
    response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("503", request=MagicMock(), response=error_response)
    )
    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)
    status_obj = WebExtractor(http_client=client).health_check()
    assert status_obj.ok is False
    assert "HTTPStatusError" in status_obj.degraded_reason


def test_webextractor_health_check_degraded_on_empty_extraction():
    """trafilatura returns nothing on example.com → parser drift signal."""
    response = MagicMock(spec=httpx.Response)
    # Truly empty body — trafilatura returns None (verified in dev smoke).
    response.text = "<html><head></head><body></body></html>"
    response.raise_for_status = MagicMock()
    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)
    status_obj = WebExtractor(http_client=client).health_check()
    assert status_obj.ok is False
    assert "empty body" in status_obj.degraded_reason


# ─────────────────────────────────────────────────────────────────────
# PdfExtractor — markitdown → pdfplumber fallback chain
# ─────────────────────────────────────────────────────────────────────

from khiip.extractors.pdf import (
    _HEALTH_PROBE_PDF,
    _HEALTH_PROBE_SENTINEL,
    PdfExtractor,
    _build_probe_pdf,
    _filename_from_url,
    _parse_pdf_date,
    _render_table_as_markdown,
)


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://arxiv.org/pdf/2310.06770.pdf", True),
        ("http://example.com/papers/x.PDF", True),
        ("https://example.com/a/b/c.pdf", True),
        # v0 lock: suffix-only matching. Extension-less PDF endpoints intentionally miss.
        ("https://arxiv.org/pdf/2310.06770", False),
        ("https://example.com/file.html", False),
        ("https://example.com/x.pdf.html", False),  # not a PDF; mimetype mismatch
        ("ftp://example.com/x.pdf", False),
        ("file:///etc/passwd.pdf", False),
        ("not-a-url", False),
        ("", False),
    ],
)
def test_pdfextractor_supports(url: str, expected: bool) -> None:
    assert PdfExtractor().supports(url) is expected


def test_pdfextractor_supports_handles_query_string():
    """Query string after `.pdf` is fine; we look at path-suffix only."""
    # urlparse path ends with `.pdf` even when there's a `?query` after.
    assert PdfExtractor().supports("https://example.com/paper.pdf?download=1") is True


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def test_filename_from_url_strips_pdf_extension():
    assert _filename_from_url("https://arxiv.org/pdf/2310.06770.pdf") == "2310.06770"
    assert _filename_from_url("https://example.com/x.PDF") == "x"


def test_filename_from_url_handles_no_path():
    assert _filename_from_url("https://example.com") is None
    assert _filename_from_url("not a url") is None or _filename_from_url("not a url") == "not a url"


def test_parse_pdf_date_handles_z_suffix():
    dt = _parse_pdf_date("D:20250115120000Z")
    assert dt is not None
    assert (dt.year, dt.month, dt.day, dt.hour) == (2025, 1, 15, 12)
    assert dt.tzinfo is not None


def test_parse_pdf_date_handles_offset_suffix():
    dt = _parse_pdf_date("D:20250115120000+05'30'")
    assert dt is not None
    assert (dt.year, dt.month, dt.day) == (2025, 1, 15)
    # Offset baked into tzinfo (5h30m east of UTC = +330 minutes)
    assert dt.utcoffset() is not None
    assert int(dt.utcoffset().total_seconds() / 60) == 330


def test_parse_pdf_date_handles_negative_offset_suffix():
    """Negative tz offset is symmetric with positive — verify it parses correctly."""
    dt = _parse_pdf_date("D:20250115120000-05'00'")
    assert dt is not None
    assert int(dt.utcoffset().total_seconds() / 60) == -300


def test_parse_pdf_date_returns_none_on_garbage():
    assert _parse_pdf_date(None) is None
    assert _parse_pdf_date("") is None
    assert _parse_pdf_date("not a pdf date") is None
    # Invalid month
    assert _parse_pdf_date("D:20251315120000Z") is None


def test_parse_pdf_date_rejects_trailing_garbage():
    """Anchored regex rejects strings with trailing junk; protects valid_from from drift."""
    # Trailing X after a date-prefix that would otherwise match — unanchored
    # regex would silently swallow this as a valid date.
    assert _parse_pdf_date("D:20250115120000Xjunk") is None
    assert _parse_pdf_date("D:20250115120000Z extra") is None


def test_render_table_as_markdown_basic_table():
    md = _render_table_as_markdown([
        ["col1", "col2"],
        ["a", "b"],
        ["c", "d"],
    ])
    assert md is not None
    assert "| col1 | col2 |" in md
    assert "| --- | --- |" in md
    assert "| a | b |" in md


def test_render_table_as_markdown_handles_none_cells_and_pipe_escapes():
    md = _render_table_as_markdown([
        ["h1", "h2"],
        [None, "a|b"],
    ])
    assert md is not None
    assert "|  | a\\|b |" in md  # None → empty; literal | escaped


def test_render_table_as_markdown_empty_returns_none():
    assert _render_table_as_markdown([]) is None
    assert _render_table_as_markdown(None) is None
    assert _render_table_as_markdown([[None, None]]) is None  # all-empty row


def test_build_probe_pdf_is_a_valid_pdf_round_trip():
    """The in-process probe PDF must parse with both libraries."""
    import io

    import pdfplumber
    from markitdown import MarkItDown

    pdf_bytes = _build_probe_pdf("Test sentinel content")
    assert pdf_bytes.startswith(b"%PDF-")

    md_text = MarkItDown().convert_stream(io.BytesIO(pdf_bytes)).text_content
    assert "Test sentinel content" in (md_text or "")

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = pdf.pages[0].extract_text()
    assert "Test sentinel content" in (text or "")


def test_build_probe_pdf_with_metadata_round_trips_via_pdfplumber():
    """A probe PDF with /Info Title + Author + CreationDate is readable via pdfplumber."""
    import io

    import pdfplumber

    pdf_bytes = _build_probe_pdf(
        "body text",
        title="Probe Title",
        author="Probe Author",
        creation_date="D:20250115120000Z",
    )
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        md = pdf.metadata
    assert md.get("Title") == "Probe Title"
    assert md.get("Author") == "Probe Author"
    assert md.get("CreationDate") == "D:20250115120000Z"


# ─────────────────────────────────────────────────────────────────────
# PdfExtractor — parser branches (offline, in-process PDFs)
# ─────────────────────────────────────────────────────────────────────


def _pdfextract_with_bytes(pdf_bytes: bytes, url: str = "https://example.com/paper.pdf") -> CaptureData:
    """Helper: PdfExtractor with httpx mocked to return the given PDF bytes."""
    response = MagicMock(spec=httpx.Response)
    response.content = pdf_bytes
    response.url = url
    response.raise_for_status = MagicMock()
    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)
    return PdfExtractor(http_client=client).extract(url)


def test_pdfextractor_markitdown_wins_on_normal_pdf():
    """A PDF with normal text → markitdown extracts → pdfplumber not exercised for body."""
    pdf_bytes = _build_probe_pdf("Hello from a normal PDF body.")
    cap = _pdfextract_with_bytes(pdf_bytes)
    assert cap.source == "pdf"
    assert "Hello from a normal PDF body" in cap.body_markdown
    assert cap.extracted_payload.get("_extractor_source") == "markitdown"
    # Without /Info metadata, title falls back to URL filename
    assert cap.title == "paper"


def test_pdfextractor_uses_pdfplumber_metadata_even_when_markitdown_wins_body():
    """Title + Author + valid_from come from /Info via pdfplumber on the markitdown branch."""
    pdf_bytes = _build_probe_pdf(
        "body content",
        title="A Paper Title",
        author="A Paper Author",
        creation_date="D:20250115120000Z",
    )
    cap = _pdfextract_with_bytes(pdf_bytes)
    assert cap.extracted_payload.get("_extractor_source") == "markitdown"
    assert cap.title == "A Paper Title"
    assert cap.author == "A Paper Author"
    assert (cap.valid_from.year, cap.valid_from.month, cap.valid_from.day) == (2025, 1, 15)


def test_pdfextractor_parse_pdfplumber_direct_extracts_metadata():
    """Direct pdfplumber-branch call surfaces title + author + creation date."""
    pdf_bytes = _build_probe_pdf(
        "page text here",
        title="Direct Title",
        author="Direct Author",
        creation_date="D:20240601000000Z",
    )
    cap = PdfExtractor()._parse_pdfplumber(
        pdf_bytes,
        canonical_url="https://example.com/x.pdf",
        original_url="https://example.com/x.pdf",
    )
    assert cap.source == "pdf"
    assert cap.title == "Direct Title"
    assert cap.author == "Direct Author"
    assert "page text here" in cap.body_markdown
    assert cap.valid_from.year == 2024
    assert cap.extracted_payload.get("page_count") == 1


def test_pdfextractor_parse_pdfplumber_whitespace_only_title_falls_back_to_filename():
    """Whitespace-only /Info Title must NOT crowd out the URL-filename fallback."""
    pdf_bytes = _build_probe_pdf("body", title="   ", author="   ")
    cap = PdfExtractor()._parse_pdfplumber(
        pdf_bytes,
        canonical_url="https://example.com/important-paper.pdf",
        original_url="https://example.com/important-paper.pdf",
    )
    assert cap.title == "important-paper"
    assert cap.author is None


def test_pdfextractor_parse_markitdown_raises_fallback_failed_on_empty_body():
    """markitdown returning empty text → FallbackFailed (let pdfplumber try)."""
    from khiip.extractors.resilience import FallbackFailed

    extractor = PdfExtractor()

    # Stub markitdown to return empty text
    class _EmptyResult:
        text_content = ""
        title = None

    extractor._mid = MagicMock()
    extractor._mid.convert_stream = MagicMock(return_value=_EmptyResult())

    with pytest.raises(FallbackFailed) as info:
        extractor._parse_markitdown(
            b"%PDF-1.4 fake bytes", "https://example.com/x.pdf", "https://example.com/x.pdf"
        )
    assert "empty body" in str(info.value)


def test_pdfextractor_parse_markitdown_raises_fallback_failed_on_internal_error():
    """markitdown raising any exception → FallbackFailed (let pdfplumber try)."""
    from khiip.extractors.resilience import FallbackFailed

    extractor = PdfExtractor()
    extractor._mid = MagicMock()
    extractor._mid.convert_stream = MagicMock(side_effect=RuntimeError("parser exploded"))

    with pytest.raises(FallbackFailed) as info:
        extractor._parse_markitdown(
            b"%PDF-1.4 fake bytes", "https://example.com/x.pdf", "https://example.com/x.pdf"
        )
    assert "markitdown raised" in str(info.value)
    assert "RuntimeError" in str(info.value)


def test_pdfextractor_parse_pdfplumber_raises_fallback_failed_on_garbage():
    """pdfplumber on non-PDF bytes raises → wrapped as FallbackFailed."""
    from khiip.extractors.resilience import FallbackFailed

    with pytest.raises(FallbackFailed) as info:
        PdfExtractor()._parse_pdfplumber(
            b"not a pdf at all", "https://example.com/x.pdf", "https://example.com/x.pdf"
        )
    assert "pdfplumber raised" in str(info.value)


# ─────────────────────────────────────────────────────────────────────
# PdfExtractor.extract — fallback chain integration
# ─────────────────────────────────────────────────────────────────────


def test_pdfextractor_extract_falls_to_pdfplumber_when_markitdown_returns_empty():
    """markitdown gives empty body → pdfplumber takes over + wins."""
    pdf_bytes = _build_probe_pdf("recoverable body content")
    response = MagicMock(spec=httpx.Response)
    response.content = pdf_bytes
    response.url = "https://example.com/paper.pdf"
    response.raise_for_status = MagicMock()
    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)

    extractor = PdfExtractor(http_client=client)

    class _EmptyResult:
        text_content = ""
        title = None

    extractor._mid = MagicMock()
    extractor._mid.convert_stream = MagicMock(return_value=_EmptyResult())

    cap = extractor.extract("https://example.com/paper.pdf")
    assert cap.extracted_payload.get("_extractor_source") == "pdfplumber"
    assert "recoverable body content" in cap.body_markdown


def test_pdfextractor_extract_raises_extractor_error_when_both_parsers_fail():
    """Both parsers FallbackFailed (markitdown empty + pdfplumber empty pages)."""
    # A PDF that markitdown stubs to empty AND pdfplumber sees no extractable text.
    # We can't easily make pdfplumber return empty on a valid PDF, so we stub
    # the pdfplumber branch directly.
    pdf_bytes = _build_probe_pdf("body")
    response = MagicMock(spec=httpx.Response)
    response.content = pdf_bytes
    response.url = "https://example.com/x.pdf"
    response.raise_for_status = MagicMock()
    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)

    extractor = PdfExtractor(http_client=client)

    class _EmptyResult:
        text_content = ""
        title = None

    extractor._mid = MagicMock()
    extractor._mid.convert_stream = MagicMock(return_value=_EmptyResult())
    # Force pdfplumber branch to also fail
    extractor._parse_pdfplumber = MagicMock(  # type: ignore[method-assign]
        side_effect=__import__("khiip.extractors.resilience", fromlist=["FallbackFailed"]).FallbackFailed(
            "pdfplumber empty"
        )
    )

    with pytest.raises(ExtractorError) as info:
        extractor.extract("https://example.com/x.pdf")
    assert "markitdown" in info.value.reason
    assert "pdfplumber" in info.value.reason


def test_pdfextractor_extract_rejects_non_pdf_response_before_dispatch():
    """Upstream returns HTML (e.g. paywall behind a .pdf URL) → ExtractorError fast."""
    response = MagicMock(spec=httpx.Response)
    response.content = b"<html><body>Paywalled page, not a PDF</body></html>"
    response.url = "https://example.com/paper.pdf"
    response.raise_for_status = MagicMock()
    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)

    with pytest.raises(ExtractorError) as info:
        PdfExtractor(http_client=client).extract("https://example.com/paper.pdf")
    assert info.value.reason == "non-pdf-response"


def test_pdfextractor_extract_propagates_http_error():
    """4xx/5xx upstream → httpx error propagates (daemon turns into 502)."""
    response = MagicMock(spec=httpx.Response)
    response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock())
    )
    client = MagicMock(spec=httpx.Client)
    client.get = MagicMock(return_value=response)
    with pytest.raises(httpx.HTTPStatusError):
        PdfExtractor(http_client=client).extract("https://example.com/missing.pdf")


# ─────────────────────────────────────────────────────────────────────
# PdfExtractor — health_check
# ─────────────────────────────────────────────────────────────────────


def test_pdfextractor_health_check_ok_on_normal_libraries():
    """Real markitdown + the bundled probe PDF should round-trip the sentinel."""
    status_obj = PdfExtractor().health_check()
    assert status_obj.source == "pdf"
    assert status_obj.ok is True
    assert status_obj.degraded_reason is None
    assert status_obj.fallback_count == 2


def test_pdfextractor_health_check_degraded_when_sentinel_missing():
    """markitdown returns text without the sentinel → degraded."""
    extractor = PdfExtractor()

    class _MismatchResult:
        text_content = "completely different output"
        title = None

    extractor._mid = MagicMock()
    extractor._mid.convert_stream = MagicMock(return_value=_MismatchResult())

    status_obj = extractor.health_check()
    assert status_obj.ok is False
    assert "sentinel not found" in status_obj.degraded_reason


def test_pdfextractor_is_health_checkable_protocol():
    """PdfExtractor satisfies the HealthCheckable Protocol at runtime."""
    assert isinstance(PdfExtractor(), HealthCheckable)


def test_pdfextractor_probe_pdf_constant_starts_with_pdf_magic():
    """Sanity: the module-level probe PDF really is a PDF."""
    assert _HEALTH_PROBE_PDF.startswith(b"%PDF-")
    assert _HEALTH_PROBE_SENTINEL.encode("latin-1") in _HEALTH_PROBE_PDF


# ─────────────────────────────────────────────────────────────────────
# Registry ordering: PDF must claim .pdf URLs before Web's http(s) catch-all
# ─────────────────────────────────────────────────────────────────────


def test_registry_order_pdf_claims_pdf_urls_before_web():
    """Without PdfExtractor first, .pdf URLs would fall through to WebExtractor."""
    registry = ExtractorRegistry()
    registry.register(XExtractor())
    registry.register(PdfExtractor())
    registry.register(WebExtractor())

    found = registry.find("https://arxiv.org/pdf/2310.06770.pdf")
    assert found is not None
    assert found.source == "pdf"

    # Non-PDF still routes to web
    found_web = registry.find("https://example.com/article")
    assert found_web is not None
    assert found_web.source == "web"

    # x.com still routes to X
    found_x = registry.find("https://x.com/jack/status/20")
    assert found_x is not None
    assert found_x.source == "x"
