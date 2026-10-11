"""Positioned OCR observer for OSWorld screenshot bytes."""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Any

from canonical.runtime.positioned_ocr_tesseract_bridge import extract_positioned_text

MAX_SCREENSHOT_BYTES = 20_000_000
MAX_ITEMS = 512


class OCRObserverError(RuntimeError):
    pass


def _suffix(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"BM"):
        return ".bmp"
    raise OCRObserverError("SCREENSHOT_IMAGE_FORMAT_UNSUPPORTED")


def observe_screenshot(screenshot: bytes, *, psm: str = "6") -> dict[str, Any]:
    if not isinstance(screenshot, (bytes, bytearray)) or not screenshot:
        raise OCRObserverError("SCREENSHOT_BYTES_REQUIRED")
    data = bytes(screenshot)
    if len(data) > MAX_SCREENSHOT_BYTES:
        raise OCRObserverError("SCREENSHOT_TOO_LARGE")
    suffix = _suffix(data)
    with tempfile.TemporaryDirectory(prefix="brain-osworld-ocr-") as td:
        path = Path(td) / ("screen" + suffix)
        path.write_bytes(data)
        result = extract_positioned_text(path, psm=psm, timeout_seconds=180)
    items = list(result.get("text_items") or [])[:MAX_ITEMS]
    return {
        "schema": "PROJECT_BRAIN_OSWORLD_V21_POSITIONED_OCR_OBSERVATION_V1",
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "page_extent": result.get("page_extent"),
        "word_count": result.get("word_count"),
        "text_items": items,
        "psm": result.get("psm"),
        "capability_id": result.get("capability_id"),
        "terminal_semantic_authority": False,
    }
