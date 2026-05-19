"""Extractor Protocol: per-source capture extractors.

Each platform (X, web, PDF, YouTube, etc.) has a dedicated Extractor that:
1. Decides whether it `supports` a given URL
2. Fetches the content via the platform's most-deterministic API
3. Returns a typed `CaptureData` for the daemon to write to vault + index

Per ADR-0007 Lens 4 + Phase 3 Test 1 validation: Khiip's moat is curated
per-source extractors, NOT generic LLM extraction (which Mem0 #4573 proved
fails at 97.8% junk rate). Each Extractor's job is to produce
**deterministic** structured output from a platform-specific API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass
class CaptureData:
    """The structured output of an Extractor.

    The daemon converts this into:
    - A markdown file in the vault (via filesystem.write_capture)
    - A row in the `captures` SQLite table (via storage/db.py)
    - Optionally: rows in `embeddings` + `graph_edges` (downstream pipelines)
    """

    # Identity
    source: str  # 'x' | 'web' | 'pdf' | 'youtube' | ...
    source_url: str  # canonical URL the capture came from

    # Bitemporal per ADR-0005 D8
    recorded_at: datetime  # when Khiip fetched
    valid_from: datetime  # when the content was true in the world (often == recorded_at;
    #                       differs for archive captures + scheduled-publish content)

    # Content
    title: str | None = None
    description: str | None = None
    author: str | None = None
    body_markdown: str = ""

    # Platform-specific raw payload (preserved verbatim in frontmatter for re-extraction)
    extracted_payload: dict[str, Any] = field(default_factory=dict)

    # Engagement / interaction metadata (e.g. X views/bookmarks/retweets at capture time)
    # Per v0 spec D8: `engagement_at_capture` snapshot. Refresh cadence deferred to v1.
    engagement_at_capture: dict[str, int] | None = None

    # Media (relative paths from vault root; e.g. "captures/x/media/{ULID}/image.jpg")
    media_paths: list[str] = field(default_factory=list)


@runtime_checkable
class Extractor(Protocol):
    """Protocol every per-source extractor implements.

    Implementations register themselves with the daemon's `ExtractorRegistry`
    (in extractors/__init__.py). The daemon dispatches by calling `supports`
    on each registered extractor until one matches.
    """

    #: Human-readable source name used in `CaptureData.source` and vault subfolder.
    source: str

    def supports(self, url: str) -> bool:
        """Return True iff this extractor handles the given URL."""
        ...

    def extract(self, url: str) -> CaptureData:
        """Fetch + parse the URL into a CaptureData. May raise on fetch failure."""
        ...


class ExtractorRegistry:
    """Ordered list of registered extractors. Daemon uses first matching `supports`."""

    def __init__(self) -> None:
        self._extractors: list[Extractor] = []

    def register(self, extractor: Extractor) -> None:
        if not isinstance(extractor, Extractor):
            raise TypeError(
                f"{type(extractor).__name__} does not implement the Extractor Protocol"
            )
        self._extractors.append(extractor)

    def find(self, url: str) -> Extractor | None:
        """Return the first registered extractor that supports `url`, or None."""
        for extractor in self._extractors:
            if extractor.supports(url):
                return extractor
        return None

    def __iter__(self):
        return iter(self._extractors)

    def __len__(self) -> int:
        return len(self._extractors)


__all__ = ["CaptureData", "Extractor", "ExtractorRegistry"]
