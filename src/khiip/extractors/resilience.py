"""Resilience primitives shared across all per-source extractors.

Per HANDOFF "Extractor resilience strategy" (architectural follow-up;
must land before Week 7-8 launch): every external-dep extractor is an
outage risk. fxtwitter rate-limits + 403s; trafilatura hits paywalls;
yt-dlp breaks on YouTube schema changes; MarkItDown chokes on scanned
PDFs. The fix is uniform across all 4 archetypes (X / web / PDF /
YouTube): a per-source fallback chain + structured failure surface +
optional health-check + (deferred) TTL cache.

This module defines the primitives. Each Extractor wires its own
fallback list inside its `extract()` method.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable


class FallbackFailed(Exception):
    """A single source in the fallback chain failed; outer code tries the next.

    Catch + re-raise this from inside a fetch_fn to signal "skip me, try the
    next source." Anything else (TypeError, KeyError, ...) propagates as a
    bug.
    """

    def __init__(self, message: str, *, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ExtractorError(Exception):
    """All fallback sources exhausted. Daemon maps to 502 (or per-extractor status)."""

    def __init__(
        self,
        message: str,
        *,
        reason: str,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.retry_after = retry_after


T = TypeVar("T")


@dataclass
class FallbackSource(Generic[T]):
    """One entry in a fallback chain.

    `fetch_fn(target)` returns a parsed result on success, or raises
    `FallbackFailed` to advance to the next source. Any other exception
    is treated as a bug and propagates.
    """

    name: str
    fetch_fn: Callable[[str], T]


def try_fallback_chain(
    sources: list[FallbackSource[T]],
    target: str,
) -> tuple[str, T]:
    """Try each source in order. Return (winning_source_name, result).

    Raises ExtractorError if every source raises FallbackFailed.
    Non-FallbackFailed exceptions propagate immediately (they signal a bug,
    not a transient upstream issue).
    """
    if not sources:
        raise ExtractorError("no sources in fallback chain", reason="empty-chain")

    failures: list[tuple[str, str]] = []
    last_retry_after: int | None = None
    for source in sources:
        try:
            return source.name, source.fetch_fn(target)
        except FallbackFailed as exc:
            failures.append((source.name, str(exc)))
            if exc.retry_after is not None:
                last_retry_after = exc.retry_after

    detail = "; ".join(f"{name}: {msg}" for name, msg in failures)
    raise ExtractorError(
        f"all sources failed for {target}",
        reason=detail,
        retry_after=last_retry_after,
    )


@dataclass
class HealthStatus:
    """Result of an extractor's optional health probe."""

    source: str
    ok: bool
    degraded_reason: str | None = None
    last_checked: datetime | None = None
    fallback_count: int | None = None  # how many sources are in the chain


@runtime_checkable
class HealthCheckable(Protocol):
    """Optional sibling of the Extractor Protocol.

    Extractors opt in by implementing `health_check()`. The daemon surfaces
    results on `/health` so operators can spot a degraded source before
    captures start failing.
    """

    source: str

    def health_check(self) -> HealthStatus: ...


__all__ = [
    "ExtractorError",
    "FallbackFailed",
    "FallbackSource",
    "HealthCheckable",
    "HealthStatus",
    "try_fallback_chain",
]
