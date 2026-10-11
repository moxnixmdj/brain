from __future__ import annotations

import csv
import io
import pathlib
import subprocess
from typing import Any

from canonical.runtime.bound_capabilities.image_ocr_tesseract import verify_dependency_surface

SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_POSITIONED_OCR_V1"


class PositionedOCRError(ValueError):
    pass


def parse_tsv(raw: str, *, min_confidence: float = 0.0) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(raw), delimiter="\t")
    required = {
        "level", "page_num", "block_num", "par_num", "line_num", "word_num",
        "left", "top", "width", "height", "conf", "text",
    }
    if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
        raise PositionedOCRError("TESSERACT_TSV_SCHEMA_INVALID")
    out: list[dict[str, Any]] = []
    for row in reader:
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        try:
            conf = float(row["conf"])
            left, top = int(row["left"]), int(row["top"])
            width, height = int(row["width"]), int(row["height"])
        except Exception as exc:
            raise PositionedOCRError("TESSERACT_TSV_ROW_INVALID") from exc
        if conf < min_confidence or width <= 0 or height <= 0:
            continue
        out.append({
            "text": text,
            "confidence": conf,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "cx": left + width / 2.0,
            "cy": top + height / 2.0,
            "block_num": int(row["block_num"]),
            "par_num": int(row["par_num"]),
            "line_num": int(row["line_num"]),
            "word_num": int(row["word_num"]),
        })
    return out


def extract_words(
    image_path: str | pathlib.Path,
    *,
    psm: int = 11,
    min_confidence: float = 0.0,
) -> dict[str, Any]:
    src = pathlib.Path(image_path).resolve(strict=True)
    if psm not in {3, 6, 7, 11}:
        raise PositionedOCRError("PSM_OUTSIDE_PINNED_SCOPE")
    dependency = verify_dependency_surface()
    proc = subprocess.run(
        ["tesseract", str(src), "stdout", "-l", "eng", "--psm", str(psm), "tsv"],
        text=True,
        capture_output=True,
        timeout=180,
    )
    if proc.returncode != 0:
        raise PositionedOCRError("TESSERACT_TSV_FAILED:" + proc.stderr[-800:])
    words = parse_tsv(proc.stdout, min_confidence=min_confidence)
    if not words:
        raise PositionedOCRError("NO_POSITIONED_OCR_WORDS")
    return {
        "schema": SCHEMA,
        "status": "PASS__POSITIONED_OCR_OBSERVATION",
        "source_path": str(src),
        "psm": psm,
        "word_count": len(words),
        "words": words,
        "dependency": dependency,
        "producer_cognition": False,
        "semantic_authority": False,
        "terminal_authority": False,
    }
