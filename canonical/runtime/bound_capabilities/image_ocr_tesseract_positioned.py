"""Pinned positioned OCR TSV bridge for CAD M1A.

This adapter closes only the interface between the already-pinned Tesseract OCR
surface and the drawing annotation pipeline. It does not add engineering
semantic authority. It emits deterministic line-grouped text observations with
exclusive image-coordinate boxes.

Any malformed, non-finite, negative, or out-of-bounds geometry fails closed.
"""
from __future__ import annotations

import csv
import hashlib
import io
import math
import pathlib
import subprocess
from typing import Any

from canonical.runtime.bound_capabilities.image_ocr_tesseract import (
    CAPABILITY_ID as BASE_CAPABILITY_ID,
    verify_dependency_surface,
)

CAPABILITY_ID = "image.extract.ocr.tesseract.positioned.tsv"
SCHEMA = "PROJECT_BRAIN_POSITIONED_OCR_TSV_BRIDGE_V1"
ALLOWED_PSM = ("3", "6", "7", "11")


def _safe_path(root: Any, raw: Any) -> pathlib.Path:
    base = pathlib.Path(root).resolve()
    p = (base / str(raw or "")).resolve()
    if p != base and base not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _int(row: dict[str, str], key: str, *, minimum: int | None = None) -> int:
    raw = row.get(key)
    try:
        value = int(str(raw))
    except Exception as exc:
        raise RuntimeError(f"TSV_INTEGER_INVALID:{key}:{raw}") from exc
    if minimum is not None and value < minimum:
        raise RuntimeError(f"TSV_INTEGER_OUT_OF_RANGE:{key}:{value}")
    return value


def _conf(row: dict[str, str]) -> float:
    raw = row.get("conf")
    try:
        value = float(str(raw))
    except Exception as exc:
        raise RuntimeError(f"TSV_CONFIDENCE_INVALID:{raw}") from exc
    if not math.isfinite(value):
        raise RuntimeError("TSV_CONFIDENCE_NONFINITE")
    return value


def parse_tsv_positioned(tsv_text: str) -> dict[str, Any]:
    if not isinstance(tsv_text, str):
        raise RuntimeError("TSV_NOT_TEXT")
    reader = csv.DictReader(io.StringIO(tsv_text), delimiter="\t")
    required = {
        "level", "page_num", "block_num", "par_num", "line_num", "word_num",
        "left", "top", "width", "height", "conf", "text",
    }
    if reader.fieldnames is None or not required <= set(reader.fieldnames):
        raise RuntimeError("TSV_HEADER_INVALID")
    rows = [dict(r) for r in reader]

    page_rows = [r for r in rows if _int(r, "level", minimum=1) == 1]
    if len(page_rows) != 1:
        raise RuntimeError(f"TSV_PAGE_COUNT_INVALID:{len(page_rows)}")
    page = page_rows[0]
    page_num = _int(page, "page_num", minimum=1)
    page_left = _int(page, "left", minimum=0)
    page_top = _int(page, "top", minimum=0)
    page_width = _int(page, "width", minimum=1)
    page_height = _int(page, "height", minimum=1)
    if page_left != 0 or page_top != 0:
        raise RuntimeError("TSV_PAGE_ORIGIN_INVALID")

    groups: dict[tuple[int, int, int, int], list[dict[str, Any]]] = {}
    for row in rows:
        if _int(row, "level", minimum=1) != 5:
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        p = _int(row, "page_num", minimum=1)
        if p != page_num:
            raise RuntimeError("TSV_MULTIPAGE_WORD_INVALID")
        block = _int(row, "block_num", minimum=0)
        par = _int(row, "par_num", minimum=0)
        line = _int(row, "line_num", minimum=0)
        word = _int(row, "word_num", minimum=0)
        left = _int(row, "left", minimum=0)
        top = _int(row, "top", minimum=0)
        width = _int(row, "width", minimum=1)
        height = _int(row, "height", minimum=1)
        right = left + width
        bottom = top + height
        if right > page_width or bottom > page_height:
            raise RuntimeError(
                f"TSV_BOX_OUT_OF_BOUNDS:{left}:{top}:{right}:{bottom}:"
                f"{page_width}:{page_height}"
            )
        groups.setdefault((p, block, par, line), []).append(
            {
                "text": text,
                "word_num": word,
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "confidence": _conf(row),
            }
        )

    text_items: list[dict[str, Any]] = []
    total_words = 0
    for key in sorted(groups):
        words = sorted(
            groups[key],
            key=lambda w: (
                int(w["word_num"]),
                int(w["left"]),
                int(w["top"]),
                str(w["text"]),
            ),
        )
        total_words += len(words)
        x0 = min(int(w["left"]) for w in words)
        y0 = min(int(w["top"]) for w in words)
        x1 = max(int(w["right"]) for w in words)
        y1 = max(int(w["bottom"]) for w in words)
        confidences = [float(w["confidence"]) for w in words]
        p, block, par, line = key
        text_items.append(
            {
                "text": " ".join(str(w["text"]) for w in words),
                "box": {
                    "x0": x0,
                    "y0": y0,
                    "x1_exclusive": x1,
                    "y1_exclusive": y1,
                },
                "source_id": f"ocr:p{p}:b{block}:par{par}:l{line}",
                "word_count": len(words),
                "confidence_min": min(confidences),
                "confidence_mean": sum(confidences) / len(confidences),
            }
        )

    combined = "\n".join(x["text"] for x in text_items)
    return {
        "schema": SCHEMA,
        "page_num": page_num,
        "page_width": page_width,
        "page_height": page_height,
        "text_items": text_items,
        "word_count": total_words,
        "line_count": len(text_items),
        "text": combined,
        "terminal_semantic_authority": False,
    }


def run(args: dict[str, Any], root: Any) -> dict[str, Any]:
    src = _safe_path(root, args.get("path"))
    if not src.is_file():
        raise RuntimeError("IMAGE_NOT_FOUND")
    language = str(args.get("language") or "eng")
    if language != "eng":
        raise RuntimeError("OCR_LANGUAGE_OUTSIDE_PINNED_SCOPE")
    psm_values = args.get("psm_values") or list(ALLOWED_PSM)
    if (
        not isinstance(psm_values, list)
        or not psm_values
        or any(str(x) not in set(ALLOWED_PSM) for x in psm_values)
    ):
        raise RuntimeError("OCR_PSM_OUTSIDE_VERIFIED_SCOPE")
    normalized = [str(x) for x in psm_values]

    dependency = verify_dependency_surface()
    attempts: list[dict[str, Any]] = []
    parsed: list[tuple[int, str, dict[str, Any], str]] = []
    for order, psm in enumerate(normalized):
        proc = subprocess.run(
            ["tesseract", str(src), "stdout", "-l", "eng", "--psm", psm, "tsv"],
            text=True,
            capture_output=True,
            timeout=180,
        )
        attempt: dict[str, Any] = {
            "psm": psm,
            "returncode": proc.returncode,
            "stderr": proc.stderr[-800:],
        }
        if proc.returncode == 0:
            try:
                positioned = parse_tsv_positioned(proc.stdout)
                attempt.update(
                    {
                        "parse_status": "PASS",
                        "word_count": positioned["word_count"],
                        "line_count": positioned["line_count"],
                        "text_bytes": len(positioned["text"].encode("utf-8")),
                    }
                )
                parsed.append((order, psm, positioned, proc.stdout))
            except RuntimeError as exc:
                attempt.update({"parse_status": "FAIL_CLOSED", "parse_error": str(exc)})
        attempts.append(attempt)

    if not parsed:
        raise RuntimeError("TESSERACT_POSITIONED_TSV_FAILED_ALL_PSM")

    order, selected_psm, best, raw_tsv = max(
        parsed,
        key=lambda row: (
            int(row[2]["word_count"]),
            len(str(row[2]["text"])),
            int(row[2]["line_count"]),
            -int(row[0]),
        ),
    )
    source_bytes = src.read_bytes()
    return {
        **best,
        "adapter": "bound_capability_bridge",
        "capability_id": CAPABILITY_ID,
        "base_capability_id": BASE_CAPABILITY_ID,
        "source_path": str(src.relative_to(pathlib.Path(root).resolve())),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "language": "eng",
        "selected_psm": selected_psm,
        "tsv_sha256": hashlib.sha256(raw_tsv.encode("utf-8")).hexdigest(),
        "attempts": attempts,
        "dependency": dependency,
        "terminal_semantic_authority": False,
        "scope": (
            "PINNED_ENGLISH_RASTER_POSITIONED_TEXT_EXTRACTION_ONLY__"
            "DETERMINISTIC_LINE_GROUPING__NO_ENGINEERING_SEMANTIC_AUTHORITY"
        ),
    }
