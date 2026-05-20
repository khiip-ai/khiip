"""Per-source capture extractors.

Each extractor implements the `Extractor` Protocol from `extractors.base`.
The daemon uses `ExtractorRegistry` to dispatch a URL to the matching
extractor based on `supports(url)`.

v0 Week 1: X extractor scaffold (fxtwitter top-level fields).
Roadmap: web (ArchiveBox + Readability + MarkItDown), PDF (MarkItDown),
YouTube (yt-dlp metadata + auto-subs). Reddit / IG / TikTok / Threads /
Bluesky in v0.5.
"""

from khiip.extractors.base import CaptureData, Extractor, ExtractorRegistry
from khiip.extractors.pdf import PdfExtractor
from khiip.extractors.web import WebExtractor
from khiip.extractors.x import XExtractor

__all__ = [
    "CaptureData",
    "Extractor",
    "ExtractorRegistry",
    "PdfExtractor",
    "WebExtractor",
    "XExtractor",
]
