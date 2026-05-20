"""PDF extractor — markitdown → pdfplumber fallback chain.

Per ADR-0007 Lens 4 (per-source extractor moat): PDFs are the "scholarly
+ official document" archetype — long-form, structured, often the
authoritative source. markitdown (Microsoft, MIT) is the v0 primary
because it pairs pdfminer.six text extraction with Microsoft's broader
document-conversion plumbing, and its output is already Markdown.
pdfplumber (MIT, table-aware) is the fallback: when markitdown returns
nothing usable, pdfplumber's layout-aware parser often still recovers
text + tables from oddly-typeset academic PDFs. Both libraries are
permissive-licensed; no AGPL transitive deps.

**v0 scope locks (per HANDOFF — accept the trade-offs as documented):**
- `supports(url)` matches URL-path-suffix `.pdf` only. PDFs served at
  extension-less endpoints (e.g. `arxiv.org/pdf/<id>` without `.pdf`)
  are intentionally missed in v0; a `HEAD`-request Content-Type check
  defers to v0.5 if telemetry signals it matters.
- Per-page rendering = full text. Embedder truncates at its sequence
  limit (same as `WebExtractor`).
- Figure / equation image extraction = deferred to v0.5. Text + tables
  only; image blocks skipped.

**Metadata trade-off**: markitdown does NOT surface PDF /Info (Title,
Author, CreationDate) — only the body markdown. pdfplumber does. So
both parser branches read PDF metadata via a separate pdfplumber call
on the same bytes — the fallback chain governs ONLY body extraction,
not metadata. Metadata-read failures degrade gracefully to None (we
don't fail the capture if /Info is missing or corrupt).
"""

from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
import pdfplumber
from markitdown import MarkItDown

from khiip.extractors.base import CaptureData
from khiip.extractors.resilience import (
    ExtractorError,
    FallbackFailed,
    FallbackSource,
    HealthStatus,
    try_fallback_chain,
)

_USER_AGENT = "khiip-daemon/0.0.1 (+https://github.com/khiip-ai/khiip)"

# PDF magic bytes. `%PDF-` (5 bytes) prefix per the spec; the next bytes
# are the version (e.g. `1.7`) but the prefix alone is the conventional check.
_PDF_MAGIC = b"%PDF-"

# PDF date format per the spec: "D:YYYYMMDDHHmmSSOHH'mm'" where O is +/-/Z.
# Example: "D:20250115120000Z" or "D:20250115120000+05'00'".
# Anchored at both ends so trailing garbage rejects the parse — metadata is
# best-effort enrichment, but a permissive parse silently swallowing junk
# input is the worse failure mode (carries forward a misleading valid_from).
_PDF_DATE_RE = re.compile(
    r"^D:(?P<year>\d{4})(?P<month>\d{2})?(?P<day>\d{2})?"
    r"(?P<hour>\d{2})?(?P<minute>\d{2})?(?P<second>\d{2})?"
    r"(?P<tz>[Z+\-]?)(?P<tz_h>\d{2})?'?(?P<tz_m>\d{2})?'?$"
)


class PdfExtractor:
    """PDF extractor with markitdown → pdfplumber fallback chain.

    Registered AFTER XExtractor (which claims x.com/twitter.com) but BEFORE
    WebExtractor (whose catch-all http(s) `supports()` would otherwise claim
    PDF URLs first).
    """

    source: str = "pdf"

    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        timeout: float = 60.0,
    ) -> None:
        # PDFs run larger than HTML — default timeout is wider than WebExtractor's
        # 30s to cover slow CDN downloads of long papers.
        self._http = http_client or httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )
        # MarkItDown instance is reusable + cheap to construct; cache one.
        self._mid = MarkItDown()

    def supports(self, url: str) -> bool:
        """True for http(s) URLs whose path ends with `.pdf` (case-insensitive)."""
        try:
            parsed = urlparse(url)
        except ValueError:
            return False
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        return parsed.path.lower().endswith(".pdf")

    def extract(self, url: str) -> CaptureData:
        """Fetch + parse a PDF via the fallback chain.

        Chain: markitdown (primary, Markdown output already) → pdfplumber
        (fallback, layout-aware). On both failing, raises ExtractorError →
        daemon maps to 502. The bytes are fetched ONCE and shared across
        branches; the chain governs only the BODY parser choice.
        """
        pdf_bytes, canonical_url = self._fetch(url)

        # Pre-validate: if the upstream did not return a PDF (e.g. a paywall
        # HTML page redirected behind a `.pdf` URL), neither parser will give
        # us a useful result. Fail fast with a clear reason instead of letting
        # markitdown silently regurgitate the input as text.
        if not pdf_bytes.startswith(_PDF_MAGIC):
            raise ExtractorError(
                f"upstream did not return a PDF (got {len(pdf_bytes)} bytes, no %PDF- header): {url}",
                reason="non-pdf-response",
            )

        sources: list[FallbackSource[CaptureData]] = [
            FallbackSource(
                name="markitdown",
                fetch_fn=lambda _t: self._parse_markitdown(pdf_bytes, canonical_url, url),
            ),
            FallbackSource(
                name="pdfplumber",
                fetch_fn=lambda _t: self._parse_pdfplumber(pdf_bytes, canonical_url, url),
            ),
        ]
        source_name, capture_data = try_fallback_chain(sources, url)
        capture_data.extracted_payload.setdefault("_extractor_source", source_name)
        return capture_data

    def health_check(self) -> HealthStatus:
        """Probe the parsers against a deterministic in-process PDF.

        Unlike XExtractor (probes fxtwitter) and WebExtractor (probes
        example.com), PDF parsing is purely local — there is no external
        upstream to ping. The probe verifies the LIBRARY availability +
        round-trip correctness by parsing a hand-crafted minimal PDF
        containing a known sentinel string. If the parser is missing,
        broken, or silently returns mismatched text, /health reports
        degraded so the operator can investigate before a real capture
        fails.
        """
        now = datetime.now(timezone.utc)
        try:
            result = self._mid.convert_stream(io.BytesIO(_HEALTH_PROBE_PDF))
        except Exception as exc:  # pragma: no cover — defensive against parser internals
            return HealthStatus(
                source=self.source,
                ok=False,
                degraded_reason=f"markitdown raised on probe: {type(exc).__name__}",
                last_checked=now,
                fallback_count=2,
            )

        text = (result.text_content or "").strip()
        if _HEALTH_PROBE_SENTINEL not in text:
            return HealthStatus(
                source=self.source,
                ok=False,
                degraded_reason=(
                    "markitdown returned unexpected text on probe "
                    "(parser drift?) — sentinel not found"
                ),
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

    def _fetch(self, url: str) -> tuple[bytes, str]:
        """One HTTP fetch shared by both parsers. Returns (pdf_bytes, canonical_url).

        v0.5 follow-up: cap by max-bytes + switch to httpx `client.stream()` so a
        500MB thesis doesn't balloon RSS. Acceptable for v0 (papers are typically
        <50MB) but flag the next time we touch resilience-strategy.
        """
        response = self._http.get(url)
        response.raise_for_status()
        return response.content, str(response.url)

    def _parse_markitdown(
        self, pdf_bytes: bytes, canonical_url: str, original_url: str
    ) -> CaptureData:
        """Primary parser. Raises FallbackFailed if markitdown gives no body."""
        try:
            result = self._mid.convert_stream(io.BytesIO(pdf_bytes))
        except Exception as exc:
            raise FallbackFailed(
                f"markitdown raised: {type(exc).__name__}: {exc}"
            ) from exc

        body = (result.text_content or "").strip()
        if not body:
            raise FallbackFailed("markitdown returned empty body")

        title, author, creation = _read_pdf_metadata(pdf_bytes)
        if not title:
            title = _filename_from_url(original_url)

        now = datetime.now(timezone.utc)
        return CaptureData(
            source=self.source,
            source_url=canonical_url,
            recorded_at=now,
            valid_from=creation or now,
            title=title,
            description=None,
            author=author,
            body_markdown=body,
            extracted_payload={
                "pdf_bytes": len(pdf_bytes),
                "url": canonical_url,
            },
        )

    def _parse_pdfplumber(
        self, pdf_bytes: bytes, canonical_url: str, original_url: str
    ) -> CaptureData:
        """Fallback parser: layout-aware text + table extraction."""
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page_chunks: list[str] = []
                for page in pdf.pages:
                    text = (page.extract_text() or "").strip()
                    if text:
                        page_chunks.append(text)
                    for raw_table in page.extract_tables() or []:
                        rendered = _render_table_as_markdown(raw_table)
                        if rendered:
                            page_chunks.append(rendered)
                metadata = dict(pdf.metadata or {})
                page_count = len(pdf.pages)
        except Exception as exc:
            raise FallbackFailed(
                f"pdfplumber raised: {type(exc).__name__}: {exc}"
            ) from exc

        if not page_chunks:
            raise FallbackFailed("pdfplumber returned no extractable text")

        body = "\n\n".join(page_chunks)
        # `.strip() or None` discipline (matches WebExtractor) — pdfplumber
        # occasionally surfaces whitespace-only /Info strings that shouldn't
        # crowd out the URL-filename fallback.
        raw_title = metadata.get("Title")
        title = (raw_title.strip() if isinstance(raw_title, str) else None) or _filename_from_url(original_url)
        raw_author = metadata.get("Author")
        author = (raw_author.strip() if isinstance(raw_author, str) else None) or None
        creation = _parse_pdf_date(metadata.get("CreationDate"))
        now = datetime.now(timezone.utc)
        return CaptureData(
            source=self.source,
            source_url=canonical_url,
            recorded_at=now,
            valid_from=creation or now,
            title=title,
            description=None,
            author=author,
            body_markdown=body,
            extracted_payload={
                "pdf_bytes": len(pdf_bytes),
                "url": canonical_url,
                "page_count": page_count,
            },
        )


# ─────────────────────────────────────────────────────────────────────
# Module helpers
# ─────────────────────────────────────────────────────────────────────


def _read_pdf_metadata(
    pdf_bytes: bytes,
) -> tuple[str | None, str | None, datetime | None]:
    """Pull /Info Title + Author + CreationDate via pdfplumber.

    Used by the markitdown branch (which only returns body markdown).
    Failures degrade to (None, None, None) — metadata is enrichment, not
    capture-critical.
    """
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            md = dict(pdf.metadata or {})
    except Exception:
        return None, None, None
    title = md.get("Title") or None
    author = md.get("Author") or None
    creation = _parse_pdf_date(md.get("CreationDate"))
    return title, author, creation


def _filename_from_url(url: str) -> str | None:
    """Derive a fallback title from the URL path, e.g. `2310.06770.pdf` → `2310.06770`."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if not parsed.path:
        return None
    name = parsed.path.rsplit("/", 1)[-1]
    if name.lower().endswith(".pdf"):
        name = name[:-4]
    return name or None


def _parse_pdf_date(value: Any) -> datetime | None:
    """Parse a PDF /Info date string into a UTC datetime.

    PDF spec date format: `D:YYYYMMDDHHmmSS[+-Z]HH'mm'`. Many fields are
    optional from the right; we accept date-only and time-only suffixes.
    Returns None on any parse failure — metadata is best-effort.
    """
    if not isinstance(value, str):
        return None
    match = _PDF_DATE_RE.match(value.strip())
    if not match:
        return None
    parts = match.groupdict()
    try:
        year = int(parts["year"])
        month = int(parts["month"] or 1)
        day = int(parts["day"] or 1)
        hour = int(parts["hour"] or 0)
        minute = int(parts["minute"] or 0)
        second = int(parts["second"] or 0)
    except (TypeError, ValueError):
        return None

    tz_sign = parts.get("tz") or ""
    if tz_sign in ("", "Z"):
        tzinfo = timezone.utc
    else:
        try:
            tz_h = int(parts.get("tz_h") or 0)
            tz_m = int(parts.get("tz_m") or 0)
        except (TypeError, ValueError):
            return None
        offset_minutes = (tz_h * 60 + tz_m) * (-1 if tz_sign == "-" else 1)
        from datetime import timedelta

        tzinfo = timezone(timedelta(minutes=offset_minutes))

    try:
        return datetime(year, month, day, hour, minute, second, tzinfo=tzinfo)
    except ValueError:
        return None


def _render_table_as_markdown(rows: list[list[str | None]] | None) -> str | None:
    """Render a pdfplumber-extracted table as a GFM pipe table.

    pdfplumber returns rows-of-cells with possible None entries. We render
    the first row as the header, a separator, then the remaining rows.
    Returns None if the table is empty or has no usable cells.
    """
    if not rows:
        return None
    # Normalize: drop fully-empty rows, coerce cells to strings.
    cleaned: list[list[str]] = []
    for row in rows:
        if not row:
            continue
        cells = ["" if c is None else str(c).replace("\n", " ").replace("|", "\\|").strip() for c in row]
        if any(cells):
            cleaned.append(cells)
    if not cleaned:
        return None

    width = max(len(r) for r in cleaned)
    cleaned = [r + [""] * (width - len(r)) for r in cleaned]

    header = cleaned[0]
    sep = ["---"] * width
    out_rows = [header, sep] + cleaned[1:]
    return "\n".join("| " + " | ".join(r) + " |" for r in out_rows)


# ─────────────────────────────────────────────────────────────────────
# Health-probe PDF — deterministic, in-process, ~600 bytes
# ─────────────────────────────────────────────────────────────────────


_HEALTH_PROBE_SENTINEL = "Khiip PDF Health Probe"


def _build_probe_pdf(
    text: str = _HEALTH_PROBE_SENTINEL,
    *,
    title: str | None = None,
    author: str | None = None,
    creation_date: str | None = None,
) -> bytes:
    """Construct a minimal valid PDF with a single line of extractable text.

    Optionally include /Info Title + Author + CreationDate for tests that
    exercise the metadata path. The generator stays in the module (not a
    test fixture) so the health probe + tests share one source of truth.
    """
    objs: list[bytes] = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")  # 1
    objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")  # 2
    objs.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
    )  # 3
    stream_content = f"BT /F1 24 Tf 100 700 Td ({text}) Tj ET".encode("latin-1")
    objs.append(
        b"<< /Length " + str(len(stream_content)).encode() + b" >>\n"
        b"stream\n" + stream_content + b"\nendstream"
    )  # 4
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")  # 5

    info_obj_num: int | None = None
    if any(v is not None for v in (title, author, creation_date)):
        info_parts: list[bytes] = []
        if title is not None:
            info_parts.append(b"/Title (" + title.encode("latin-1") + b")")
        if author is not None:
            info_parts.append(b"/Author (" + author.encode("latin-1") + b")")
        if creation_date is not None:
            info_parts.append(b"/CreationDate (" + creation_date.encode("latin-1") + b")")
        objs.append(b"<< " + b" ".join(info_parts) + b" >>")
        info_obj_num = len(objs)

    out = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = [0]
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_offset = len(out)
    out += b"xref\n"
    out += f"0 {len(objs) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    trailer = f"<< /Size {len(objs) + 1} /Root 1 0 R"
    if info_obj_num is not None:
        trailer += f" /Info {info_obj_num} 0 R"
    trailer += " >>"
    out += f"trailer\n{trailer}\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    return out


_HEALTH_PROBE_PDF = _build_probe_pdf()


__all__ = ["PdfExtractor"]
