#!/usr/bin/env python3
"""Bounded local image observation adapter for HLE.

This is a tool adapter, not a claim of intrinsic Brain vision. It accepts only
provided data:image URIs, hashes the exact bytes, decodes with Pillow, and may
run a local OCR tool. It never reads gold and never performs web access.
"""
from __future__ import annotations

import base64
import hashlib
import io
import re
from typing import Any, Callable

SCHEMA = "PROJECT_BRAIN_HLE_IMAGE_OBSERVATION_V1"
_DATA_URI = re.compile(r"^data:(image/[A-Za-z0-9.+-]+);base64,([A-Za-z0-9+/=\r\n]+)$")


class HLEImageObservationError(ValueError):
    pass


def _clean_ocr(text: str, max_chars: int) -> str:
    if not isinstance(text, str):
        raise HLEImageObservationError("OCR_RESULT_NOT_STRING")
    text = "\n".join(" ".join(line.split()) for line in text.splitlines())
    text = "\n".join(line for line in text.splitlines() if line)
    return text[:max_chars]


def observe(
    *,
    image_data_uri: str,
    ocr_fn: Callable[[Any], str] | None = None,
    max_image_bytes: int = 12_000_000,
    max_pixels: int = 40_000_000,
    max_ocr_chars: int = 12_000,
) -> dict[str, Any]:
    if not isinstance(image_data_uri, str) or not image_data_uri:
        raise HLEImageObservationError("IMAGE_DATA_URI_REQUIRED")
    m = _DATA_URI.fullmatch(image_data_uri.strip())
    if not m:
        raise HLEImageObservationError("ONLY_BASE64_IMAGE_DATA_URI_SUPPORTED")
    mime = m.group(1).lower()
    try:
        raw = base64.b64decode(m.group(2), validate=True)
    except Exception as exc:
        raise HLEImageObservationError("IMAGE_BASE64_INVALID") from exc
    if not raw or len(raw) > max_image_bytes:
        raise HLEImageObservationError("IMAGE_SIZE_OUT_OF_BOUNDS")

    try:
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as im:
            im.load()
            width, height = im.size
            mode, fmt = im.mode, im.format
            if width <= 0 or height <= 0 or width * height > max_pixels:
                raise HLEImageObservationError("IMAGE_DIMENSIONS_OUT_OF_BOUNDS")
            image_for_ocr = im.copy()
    except HLEImageObservationError:
        raise
    except Exception as exc:
        raise HLEImageObservationError("IMAGE_DECODE_FAILED") from exc

    if ocr_fn is None:
        try:
            import pytesseract
            ocr_fn = lambda image: pytesseract.image_to_string(image, lang="eng")
        except Exception as exc:
            raise HLEImageObservationError("LOCAL_OCR_UNAVAILABLE") from exc

    try:
        ocr_text = _clean_ocr(ocr_fn(image_for_ocr), max_ocr_chars)
    except HLEImageObservationError:
        raise
    except Exception as exc:
        raise HLEImageObservationError("LOCAL_OCR_FAILED") from exc

    return {
        "schema": SCHEMA,
        "status": "OBSERVED",
        "mime": mime,
        "format": fmt,
        "width": width,
        "height": height,
        "mode": mode,
        "image_bytes": len(raw),
        "image_sha256": hashlib.sha256(raw).hexdigest(),
        "ocr_text": ocr_text,
        "ocr_text_sha256": hashlib.sha256(ocr_text.encode("utf-8")).hexdigest(),
        "ocr_chars": len(ocr_text),
        "gold_accessed": False,
        "external_reasoning_model_calls": 0,
        "local_ocr_tool_used": True,
        "intrinsic_brain_vision_claimed": False,
        "terminal_authority": False,
        "hard_nonclaim": "OCR_TEXT_IS_A_FALLIBLE_TOOL_OBSERVATION_NOT_A_PROOF_OF_IMAGE_SEMANTICS",
    }
