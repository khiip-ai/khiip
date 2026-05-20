"""YouTube extractor — yt-dlp → youtube-transcript-api → (key-gated) API v3 chain.

Per ADR-0007 Lens 4: YouTube is the "video + transcript + creator metadata"
archetype — the fourth and final v0 extractor archetype. Transcripts are
the load-bearing recall signal; metadata is the enrichment. The fallback
chain protects against three orthogonal failure modes:

1. **yt-dlp** (primary; Unlicense / public-domain dedication). Rich metadata
   via the YouTube player API + transcript via the timedtext URL it
   surfaces. Failure mode: YouTube changes its player API (frequent —
   yt-dlp ships patches but there's an outage window). Bonus: the only
   source that surfaces full engagement (views/likes/comments) on a
   single call.
2. **youtube-transcript-api + oEmbed** (fallback; MIT). Transcript via a
   different scraping path (talks directly to the timedtext endpoint
   rather than going through the player JSON) + thin metadata via
   YouTube oEmbed (official, no auth, free; gives title + author_name +
   author_url + thumbnail). Failure mode: timedtext endpoint shape
   changes — orthogonal to yt-dlp's player-API failure mode at the code
   path level even though both ultimately depend on YouTube serving
   captions.
3. **YouTube Data API v3** (operator-opt-in third fallback; MIT-licensed
   google-issued credential). Gated on `KHIIP_YOUTUBE_API_KEY` env var
   or `[extractors.youtube] api_key` in config.toml. Metadata via
   videos.list?part=snippet,statistics. Transcript NOT available via
   API v3 for arbitrary videos (captions.download requires the channel
   owner's OAuth token, not just an API key) — so body degrades to
   description-only on this branch. Documented operator trade-off:
   metadata resilience at the cost of transcript depth.

**v0 scope locks (per HANDOFF — accept the trade-offs as documented):**
- `supports(url)`: youtube.com, m.youtube.com, youtu.be (incl. /shorts/
  paths on youtube.com). music.youtube.com + embed-only URLs intentionally
  miss — v0.5 if telemetry signals demand.
- Transcript priority: manual subtitles > auto-generated > description-only.
- Engagement snapshot: views / likes / comments (matches the X precedent;
  YouTube hid dislike counts in 2021 so no dislike field).
- Thumbnail download = deferred to v0.5 (mirrors PDF figure-extraction
  deferral). Thumbnail URL is still surfaced in `extracted_payload`.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from khiip.extractors.base import CaptureData
from khiip.extractors.resilience import (
    FallbackFailed,
    FallbackSource,
    HealthStatus,
    try_fallback_chain,
)

logger = logging.getLogger("khiip.extractors.youtube")

_USER_AGENT = "khiip-daemon/0.0.1 (+https://github.com/khiip-ai/khiip)"

# Health-probe target: jawed/jNQXAC9IVRw — "Me at the zoo", the first
# YouTube video (2005). The YouTube analogue of jack/20 — iconic + stable +
# unlikely to be removed.
_HEALTH_PROBE_VIDEO_ID = "jNQXAC9IVRw"
_HEALTH_PROBE_TITLE_SUBSTR = "zoo"  # title is "Me at the zoo"; minimal sentinel

# Hosts we claim. `m.youtube.com` is the legacy mobile site (still active);
# `music.youtube.com` deliberately excluded — it's a different surface (album
# pages, music videos with separate metadata) — defer to v0.5.
_YOUTUBE_HOSTS = frozenset({
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "youtu.be", "www.youtu.be",
})

# Video ID extraction: covers /watch?v=, /shorts/, /embed/, and youtu.be/<id>.
_VIDEO_ID_PATTERN = re.compile(
    r"(?:/watch\?(?:[^#]*&)?v=|/shorts/|/embed/|youtu\.be/)([A-Za-z0-9_-]{6,})"
)

# YouTube oEmbed endpoint (free, no auth; thin metadata).
_OEMBED_URL = "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"

# YouTube Data API v3 videos.list — used when api_key is provided.
_API_V3_VIDEOS = "https://www.googleapis.com/youtube/v3/videos"

_ENGAGEMENT_KEYS_YTDLP = (
    ("view_count", "views"),
    ("like_count", "likes"),
    ("comment_count", "comments"),
)


class YouTubeExtractor:
    """YouTube extractor: 2-source chain (no key) or 3-source chain (key set).

    Registered between XExtractor and PdfExtractor in the default registry —
    YouTube URLs must beat WebExtractor's catch-all http(s) `supports()`.
    """

    source: str = "youtube"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        http_client: httpx.Client | None = None,
        ydl_factory: Any = None,
        transcript_api: Any = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        # No `Accept: application/json` on the default client — subtitle
        # fetches request VTT/SRT/json3 and some CDNs strictly enforce Accept.
        # Each method that needs JSON sets the Accept header per-request.
        self._http = http_client or httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )
        # Injection seams for hermetic tests; production: real yt-dlp +
        # real YouTubeTranscriptApi instantiated on demand.
        self._ydl_factory = ydl_factory  # callable: () -> YoutubeDL-compatible context manager
        self._transcript_api = transcript_api  # instance with .fetch(video_id, languages=)

    def supports(self, url: str) -> bool:
        """True for youtube.com / m.youtube.com / youtu.be URLs with an extractable video ID."""
        try:
            host = urlparse(url).hostname or ""
        except ValueError:
            return False
        if host not in _YOUTUBE_HOSTS:
            return False
        return _extract_video_id(url) is not None

    def extract(self, url: str) -> CaptureData:
        """Fetch + parse a YouTube URL via the fallback chain.

        Chain shape depends on api_key presence:
          - No key:  yt-dlp → youtube-transcript-api+oEmbed
          - Key set: yt-dlp → youtube-transcript-api+oEmbed → API v3 (description-only body)
        """
        video_id = _extract_video_id(url)
        if video_id is None:
            raise ValueError(f"could not extract video ID from URL: {url}")

        sources: list[FallbackSource[CaptureData]] = [
            FallbackSource(
                name="yt-dlp",
                fetch_fn=lambda _t: self._parse_ytdlp(url, video_id),
            ),
            FallbackSource(
                name="youtube-transcript-api+oembed",
                fetch_fn=lambda _t: self._parse_transcript_api_with_oembed(url, video_id),
            ),
        ]
        if self._api_key:
            sources.append(
                FallbackSource(
                    name="api-v3",
                    fetch_fn=lambda _t: self._parse_api_v3(url, video_id),
                )
            )
        source_name, capture_data = try_fallback_chain(sources, url)
        capture_data.extracted_payload.setdefault("_extractor_source", source_name)
        return capture_data

    def health_check(self) -> HealthStatus:
        """Probe yt-dlp + youtube-transcript-api library availability — LOCAL probe.

        Unlike X (probes fxtwitter) + web (probes example.com), an external
        probe against a real YouTube video is too CPU-heavy to belong on
        /health: yt-dlp.extract_info parses YouTube's player JSON, runs
        platform-specific extractors, sometimes negotiates JS challenges —
        easily 3-10 seconds per call, which blocks /health past any
        reasonable load-balancer timeout. Match PDF's local-probe pattern
        instead: verify the libraries import + instantiate. Catches the
        common deploy-time failure modes (missing dep, broken install) and
        leaves true upstream-availability signal to the captures themselves
        (a real yt-dlp failure during extract surfaces as `ExtractorError`
        → 502 anyway).
        """
        now = datetime.now(timezone.utc)
        fallback_count = 3 if self._api_key else 2
        # yt-dlp readiness: import + instantiate YoutubeDL with minimal opts
        if self._ydl_factory is None:
            try:
                import yt_dlp  # noqa: F401  (verifies import)

                yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}).__enter__().__exit__(None, None, None)
            except Exception as exc:
                return HealthStatus(
                    source=self.source,
                    ok=False,
                    degraded_reason=f"yt-dlp library readiness failed: {type(exc).__name__}",
                    last_checked=now,
                    fallback_count=fallback_count,
                )
        else:
            # Test-injected factory: confirm it produces a context manager that
            # responds to extract_info (mimic real yt-dlp's API surface). Use the
            # known probe video so the stub can be asserted against expectations.
            try:
                info = self._call_ytdlp(
                    f"https://www.youtube.com/watch?v={_HEALTH_PROBE_VIDEO_ID}"
                )
            except Exception as exc:
                return HealthStatus(
                    source=self.source,
                    ok=False,
                    degraded_reason=f"yt-dlp probe raised: {type(exc).__name__}",
                    last_checked=now,
                    fallback_count=fallback_count,
                )
            title = (info.get("title") or "") if isinstance(info, dict) else ""
            if _HEALTH_PROBE_TITLE_SUBSTR not in title.lower():
                return HealthStatus(
                    source=self.source,
                    ok=False,
                    degraded_reason=(
                        "yt-dlp returned unexpected title on probe "
                        "(stub sentinel mismatch — tests should set title containing 'zoo')"
                    ),
                    last_checked=now,
                    fallback_count=fallback_count,
                )
        return HealthStatus(
            source=self.source,
            ok=True,
            last_checked=now,
            fallback_count=fallback_count,
        )

    # ─────────────────────────────────────────────────────────────────
    # Source 1: yt-dlp (rich metadata + transcript URL → httpx-fetched json3)
    # ─────────────────────────────────────────────────────────────────

    def _parse_ytdlp(self, url: str, video_id: str) -> CaptureData:
        """Primary parser. yt-dlp metadata + json3 transcript fetch."""
        try:
            info = self._call_ytdlp(url)
        except Exception as exc:
            raise FallbackFailed(
                f"yt-dlp raised: {type(exc).__name__}: {exc}"
            ) from exc
        if not isinstance(info, dict):
            raise FallbackFailed("yt-dlp returned non-dict info")

        title = info.get("title") or video_id
        description = info.get("description") or ""
        author = info.get("uploader") or info.get("channel")
        upload_date_str = info.get("upload_date")  # YYYYMMDD per yt-dlp
        valid_from = _parse_ytdlp_date(upload_date_str)
        engagement = _ytdlp_engagement(info)

        transcript = self._fetch_transcript_from_ytdlp_info(info)
        if not transcript and not description.strip():
            raise FallbackFailed(
                "yt-dlp produced no transcript + no description — let next source try"
            )

        body = _compose_body(description, transcript)

        now = datetime.now(timezone.utc)
        return CaptureData(
            source=self.source,
            source_url=url,
            recorded_at=now,
            valid_from=valid_from or now,
            title=title,
            description=description or None,
            author=author,
            body_markdown=body,
            extracted_payload={
                "video_id": video_id,
                "channel_id": info.get("channel_id"),
                "channel_url": info.get("channel_url"),
                "duration_seconds": info.get("duration"),
                "thumbnail": info.get("thumbnail"),
                "categories": info.get("categories"),
                "tags": info.get("tags"),
                "transcript_available": bool(transcript),
            },
            engagement_at_capture=engagement or None,
        )

    def _call_ytdlp(self, url: str) -> dict[str, Any]:
        """Run yt-dlp.extract_info on `url`. Factored for test injection."""
        if self._ydl_factory is not None:
            with self._ydl_factory() as ydl:
                return ydl.extract_info(url, download=False)
        # Real production path.
        import yt_dlp

        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writeinfojson": False,
            "extract_flat": False,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    def _fetch_transcript_from_ytdlp_info(self, info: dict[str, Any]) -> str | None:
        """Extract + fetch + parse the best-available subtitle URL from yt-dlp info.

        Priority: manual `subtitles['en']` > automatic `automatic_captions['en']`.
        Format priority within a lang: json3 (easiest to parse) > vtt > srt.
        Returns None if no transcript track exists OR if the fetch fails (we
        prefer to let the rest of the branch continue with description-only
        body rather than raising — the transcript dimension is degraded, not
        capture-fatal).
        """
        for source_key in ("subtitles", "automatic_captions"):
            tracks = info.get(source_key) or {}
            if not isinstance(tracks, dict):
                continue
            for lang in _LANG_PRIORITY:
                lang_tracks = tracks.get(lang)
                if not isinstance(lang_tracks, list):
                    continue
                for fmt in ("json3", "vtt", "srt"):
                    for track in lang_tracks:
                        if isinstance(track, dict) and track.get("ext") == fmt and track.get("url"):
                            text = self._fetch_and_parse_subtitle(track["url"], fmt)
                            if text:
                                return text
        return None

    def _fetch_and_parse_subtitle(self, sub_url: str, fmt: str) -> str | None:
        """Fetch a subtitle URL + extract plain text. None on failure."""
        try:
            response = self._http.get(sub_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("subtitle fetch failed (%s): %s", fmt, exc)
            return None

        if fmt == "json3":
            try:
                data = response.json()
            except ValueError:
                return None
            return _parse_json3_transcript(data) or None
        if fmt == "vtt":
            return _parse_vtt_transcript(response.text) or None
        if fmt == "srt":
            return _parse_srt_transcript(response.text) or None
        return None

    # ─────────────────────────────────────────────────────────────────
    # Source 2: youtube-transcript-api (transcript) + oEmbed (thin metadata)
    # ─────────────────────────────────────────────────────────────────

    def _parse_transcript_api_with_oembed(self, url: str, video_id: str) -> CaptureData:
        """Fallback parser: youtube-transcript-api for body + oEmbed for metadata."""
        transcript = self._fetch_transcript_api(video_id)
        oembed = self._fetch_oembed(video_id)

        if not transcript and not (oembed and oembed.get("title")):
            raise FallbackFailed(
                "youtube-transcript-api gave no transcript + oEmbed gave no title"
            )

        title = (oembed or {}).get("title") or video_id
        author = (oembed or {}).get("author_name")
        body = _compose_body(description=None, transcript=transcript or "")

        now = datetime.now(timezone.utc)
        return CaptureData(
            source=self.source,
            source_url=url,
            recorded_at=now,
            valid_from=now,  # oEmbed surfaces no upload date
            title=title,
            description=None,
            author=author,
            body_markdown=body,
            extracted_payload={
                "video_id": video_id,
                "oembed": oembed,
                "transcript_available": bool(transcript),
            },
            engagement_at_capture=None,  # oEmbed has no engagement
        )

    def _fetch_transcript_api(self, video_id: str) -> str | None:
        """Pull transcript via youtube-transcript-api. None on any failure.

        Uses `_LANG_PRIORITY` to prefer English variants. The library raises
        TranscriptsDisabled / NoTranscriptFound / VideoUnavailable etc.; all
        treated as "no transcript here" rather than as fallback signals so
        the metadata path still succeeds.
        """
        api = self._transcript_api
        if api is None:
            try:
                from youtube_transcript_api import YouTubeTranscriptApi

                api = YouTubeTranscriptApi()
            except Exception as exc:
                logger.warning("youtube-transcript-api import failed: %s", exc)
                return None
        try:
            transcript = api.fetch(video_id, languages=list(_LANG_PRIORITY))
        except Exception as exc:
            logger.warning("youtube-transcript-api fetch failed: %s", exc)
            return None
        snippets = list(transcript)
        if not snippets:
            return None
        return " ".join(s.text.strip() for s in snippets if s.text and s.text.strip())

    def _fetch_oembed(self, video_id: str) -> dict[str, Any] | None:
        """Pull thin metadata via the public oEmbed endpoint. None on any failure."""
        try:
            response = self._http.get(_OEMBED_URL.format(video_id=video_id))
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("oembed fetch failed: %s", exc)
            return None
        return data if isinstance(data, dict) else None

    # ─────────────────────────────────────────────────────────────────
    # Source 3: YouTube Data API v3 (operator-opt-in; metadata-only body)
    # ─────────────────────────────────────────────────────────────────

    def _parse_api_v3(self, url: str, video_id: str) -> CaptureData:
        """API v3 fallback. Returns metadata + description-only body.

        The transcript is NOT available via API v3 for arbitrary videos —
        captions.download requires the channel owner's OAuth, not just an
        API key. Documented operator trade-off: this branch trades
        transcript depth for metadata resilience.
        """
        if not self._api_key:  # defensive — extract() only adds this source when key is set
            raise FallbackFailed("api-v3 source called without api_key — defensive guard")

        params = {
            "part": "snippet,statistics",
            "id": video_id,
            "key": self._api_key,
        }
        try:
            response = self._http.get(_API_V3_VIDEOS, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Surface only the status code — NEVER let `str(exc)` reach the
            # FallbackFailed message: httpx renders the full request URL
            # (including `?key=AIza...`), which would leak the operator's
            # API key into the 502 response body + daemon warning logs.
            raise FallbackFailed(
                f"api-v3 HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            # Same redaction discipline — httpx.RequestError.request.url may
            # also carry the key. Surface only the exception class name.
            raise FallbackFailed(
                f"api-v3 request error: {type(exc).__name__}"
            ) from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise FallbackFailed(
                f"api-v3 returned non-JSON: {type(exc).__name__}"
            ) from exc

        items = payload.get("items") if isinstance(payload, dict) else None
        if not items or not isinstance(items, list):
            raise FallbackFailed("api-v3 returned no items for video_id")

        item = items[0]
        snippet = item.get("snippet", {}) if isinstance(item, dict) else {}
        statistics = item.get("statistics", {}) if isinstance(item, dict) else {}

        title = snippet.get("title") or video_id
        description = snippet.get("description") or ""
        author = snippet.get("channelTitle")
        valid_from = _parse_iso_zulu(snippet.get("publishedAt"))
        engagement = _api_v3_engagement(statistics)

        # API v3 body = description-only (no transcript). Document the
        # degradation in extracted_payload so consumers know what kind of
        # CaptureData they're holding.
        body = _compose_body(description=description, transcript=None)

        now = datetime.now(timezone.utc)
        return CaptureData(
            source=self.source,
            source_url=url,
            recorded_at=now,
            valid_from=valid_from or now,
            title=title,
            description=description or None,
            author=author,
            body_markdown=body,
            extracted_payload={
                "video_id": video_id,
                "channel_id": snippet.get("channelId"),
                "transcript_available": False,
                "degraded_body": "description-only (api-v3 cannot fetch transcripts)",
                "api_v3_snippet": snippet,
                "api_v3_statistics": statistics,
            },
            engagement_at_capture=engagement or None,
        )


# ─────────────────────────────────────────────────────────────────────
# Module helpers
# ─────────────────────────────────────────────────────────────────────


# Preferred caption languages, in priority order. English variants first;
# v0 doesn't multi-lang; v0.5 candidate to honor a per-capture language hint.
_LANG_PRIORITY = ("en", "en-US", "en-GB")


def _extract_video_id(url: str) -> str | None:
    """Extract a YouTube video ID from a URL. None if not found."""
    match = _VIDEO_ID_PATTERN.search(url)
    return match.group(1) if match else None


def _parse_ytdlp_date(value: str | None) -> datetime | None:
    """yt-dlp `upload_date` is YYYYMMDD. UTC midnight assumed (no timezone in field)."""
    if not isinstance(value, str) or len(value) != 8 or not value.isdigit():
        return None
    try:
        return datetime(int(value[:4]), int(value[4:6]), int(value[6:8]), tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_iso_zulu(value: str | None) -> datetime | None:
    """Parse an ISO 8601 timestamp ending in Z. None on failure."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _ytdlp_engagement(info: dict[str, Any]) -> dict[str, int]:
    """Coerce-skip yt-dlp engagement keys (some videos hide like_count)."""
    out: dict[str, int] = {}
    for src, dst in _ENGAGEMENT_KEYS_YTDLP:
        v = info.get(src)
        if isinstance(v, int):
            out[dst] = v
    return out


def _api_v3_engagement(stats: dict[str, Any]) -> dict[str, int]:
    """Coerce API v3 statistics (returned as strings) to ints. Skip missing."""
    mapping = {"viewCount": "views", "likeCount": "likes", "commentCount": "comments"}
    out: dict[str, int] = {}
    for src, dst in mapping.items():
        v = stats.get(src)
        if isinstance(v, str) and v.isdigit():
            out[dst] = int(v)
        elif isinstance(v, int):
            out[dst] = v
    return out


def _compose_body(description: str | None, transcript: str | None) -> str:
    """Compose the markdown body: description on top, transcript below under a heading."""
    parts: list[str] = []
    if description and description.strip():
        parts.append(description.strip())
    if transcript and transcript.strip():
        parts.append(f"## Transcript\n\n{transcript.strip()}")
    return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────────────────
# Subtitle parsers (json3 / vtt / srt → plain text)
# ─────────────────────────────────────────────────────────────────────


def _parse_json3_transcript(data: Any) -> str:
    """YouTube's json3 caption format. Concatenate seg.utf8 across events."""
    if not isinstance(data, dict):
        return ""
    events = data.get("events")
    if not isinstance(events, list):
        return ""
    pieces: list[str] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        segs = ev.get("segs")
        if not isinstance(segs, list):
            continue
        for seg in segs:
            if isinstance(seg, dict):
                utf8 = seg.get("utf8")
                if isinstance(utf8, str):
                    pieces.append(utf8)
    return " ".join(p.strip() for p in pieces if p.strip())


_VTT_CUE_HEADER = re.compile(r"^\d{1,2}:\d{2}:\d{2}\.\d+\s+-->\s+\d{1,2}:\d{2}:\d{2}\.\d+")


def _parse_vtt_transcript(text: str) -> str:
    """WebVTT format. Strip cue headers + metadata; keep text lines."""
    if not text:
        return ""
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("WEBVTT") or line.startswith("NOTE") or line.startswith("STYLE"):
            continue
        if _VTT_CUE_HEADER.match(line):
            continue
        # Strip VTT inline tags like <c.colorE5E5E5>, <00:00:05.000>, <i>, etc.
        line = re.sub(r"<[^>]+>", "", line)
        if line:
            lines.append(line)
    return " ".join(lines)


_SRT_INDEX = re.compile(r"^\d+$")
_SRT_TIME = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}")


def _parse_srt_transcript(text: str) -> str:
    """SRT format. Strip cue indexes + timecodes; keep text lines."""
    if not text:
        return ""
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if _SRT_INDEX.match(line) or _SRT_TIME.match(line):
            continue
        lines.append(line)
    return " ".join(lines)


__all__ = ["YouTubeExtractor"]
