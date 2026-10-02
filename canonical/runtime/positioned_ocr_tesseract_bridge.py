#!/usr/bin/env python3
"""Pinned positioned OCR bridge for M1A engineering drawing annotation.

This adapter closes only the mechanical interface between the already-verified
Tesseract OCR surface and the annotation/geometry-association pipeline.

It extracts Tesseract TSV word boxes, validates them against the TSV page
extent, groups words deterministically into text lines, and emits the exact
x0/y0/x1_exclusive/y1_exclusive box contract consumed downstream.

It has no engineering-semantic authority.
"""
from __future__ import annotations

import csv
import hashlib
import io
import pathlib
import subprocess
from typing import Any

from canonical.runtime.bound_capabilities.image_ocr_tesseract import (
    CAPABILITY_ID as BASE_OCR_CAPABILITY_ID,
    verify_dependency_surface,
)

CAPABILITY_ID = "image.extract.ocr.tesseract.positioned"
SCHEMA = "BRAIN_PINNED_POSITIONED_OCR_TESSERACT_V1"
_ALLOWED_PSM = {"3", "6", "7", "11"}


def _safe_path(root: str | pathlib.Path, raw: Any) -> pathlib.Path:
    root_path = pathlib.Path(root).resolve()
    path = (root_path / str(raw or "")).resolve()
    if path != root_path and root_path not in path.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return path


def _int_field(row: dict[str, str], name: str) -> int:
    raw = row.get(name)
    try:
        value = int(str(raw))
    except Exception as exc:
        raise RuntimeError(f"OCR_TSV_INVALID_INTEGER:{name}:{raw}") from exc
    return value


def _parse_tsv(tsv: str) -> tuple[tuple[int, int], list[dict[str, Any]]]:
    reader = csv.DictReader(io.StringIO(tsv), delimiter="\t")
    required = {
        "level", "page_num", "block_num", "par_num", "line_num", "word_num",
        "left", "top", "width", "height", "conf", "text",
    }
    if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
        raise RuntimeError("OCR_TSV_HEADER_INVALID")

    page_extent: tuple[int, int] | None = None
    words: list[dict[str, Any]] = []
    for row in reader:
        level = _int_field(row, "level")
        left = _int_field(row, "left")
        top = _int_field(row, "top")
        width = _int_field(row, "width")
        height = _int_field(row, "height")
        if min(left, top, width, height) < 0:
            raise RuntimeError("OCR_TSV_NEGATIVE_GEOMETRY")

        if level == 1:
            if width <= 0 or height <= 0:
                raise RuntimeError("OCR_TSV_PAGE_EXTENT_INVALID")
            observed = (width, height)
            if page_extent is None:
                page_extent = observed
            elif observed != page_extent:
                raise RuntimeError("OCR_TSV_MULTI_PAGE_OR_INCONSISTENT_EXTENT")
            continue

        if level != 5:
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        if width <= 0 or height <= 0:
            raise RuntimeError("OCR_TSV_WORD_EXTENT_INVALID")
        try:
            conf = float(str(row.get("conf")))
        except Exception as exc:
            raise RuntimeError("OCR_TSV_CONFIDENCE_INVALID") from exc
        if conf < 0 or conf > 100:
            raise RuntimeError("OCR_TSV_CONFIDENCE_OUT_OF_RANGE")

        words.append({
            "page_num": _int_field(row, "page_num"),
            "block_num": _int_field(row, "block_num"),
            "par_num": _int_field(row, "par_num"),
            "line_num": _int_field(row, "line_num"),
            "word_num": _int_field(row, "word_num"),
            "text": text,
            "confidence": conf,
            "x0": left,
            "y0": top,
            "x1_exclusive": left + width,
            "y1_exclusive": top + height,
        })

    if page_extent is None:
        raise RuntimeError("OCR_TSV_PAGE_EXTENT_MISSING")
    page_w, page_h = page_extent
    for word in words:
        if (
            word["x0"] < 0
            or word["y0"] < 0
            or word["x1_exclusive"] <= word["x0"]
            or word["y1_exclusive"] <= word["y0"]
            or word["x1_exclusive"] > page_w
            or word["y1_exclusive"] > page_h
        ):
            raise RuntimeError("OCR_TSV_WORD_BOX_OUT_OF_BOUNDS")
    return page_extent, words


def _group_lines(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int, int, int], list[dict[str, Any]]] = {}
    for word in words:
        key = (
            int(word["page_num"]),
            int(word["block_num"]),
            int(word["par_num"]),
            int(word["line_num"]),
        )
        grouped.setdefault(key, []).append(word)

    lines: list[dict[str, Any]] = []
    for key in sorted(grouped):
        members = sorted(
            grouped[key],
            key=lambda x: (int(x["word_num"]), int(x["x0"]), int(x["y0"]), str(x["text"])),
        )
        text = " ".join(str(x["text"]) for x in members).strip()
        if not text:
            continue
        box = {
            "x0": min(int(x["x0"]) for x in members),
            "y0": min(int(x["y0"]) for x in members),
            "x1_exclusive": max(int(x["x1_exclusive"]) for x in members),
            "y1_exclusive": max(int(x["y1_exclusive"]) for x in members),
        }
        weighted_area = sum(
            max(1, (int(x["x1_exclusive"]) - int(x["x0"])) * (int(x["y1_exclusive"]) - int(x["y0"])))
            for x in members
        )
        weighted_conf = sum(
            float(x["confidence"])
            * max(1, (int(x["x1_exclusive"]) - int(x["x0"])) * (int(x["y1_exclusive"]) - int(x["y0"])))
            for x in members
        ) / weighted_area
        lines.append({
            "source_id": "ocr_line:" + ":".join(str(x) for x in key),
            "text": text,
            "box": box,
            "confidence": round(weighted_conf, 6),
            "word_count": len(members),
            "tsv_line_key": {
                "page_num": key[0],
                "block_num": key[1],
                "par_num": key[2],
                "line_num": key[3],
            },
        })
    return lines


def extract_positioned_text(
    image_path: str | pathlib.Path,
    *,
    psm: str = "6",
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    psm = str(psm)
    if psm not in _ALLOWED_PSM:
        raise RuntimeError("OCR_PSM_OUTSIDE_VERIFIED_SCOPE")

    dependency = verify_dependency_surface()
    src = pathlib.Path(image_path)
    if not src.is_file():
        raise RuntimeError("IMAGE_NOT_FOUND")

    proc = subprocess.run(
        ["tesseract", str(src), "stdout", "-l", "eng", "--psm", psm, "tsv"],
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
    )
    if proc.returncode != 0:
        raise RuntimeError("TESSERACT_TSV_FAILED:" + proc.stderr[-800:])

    page_extent, words = _parse_tsv(proc.stdout)
    lines = _group_lines(words)
    raw = src.read_bytes()
    return {
        "schema": SCHEMA,
        "status": "EXTRACTED",
        "capability_id": CAPABILITY_ID,
        "base_ocr_capability_id": BASE_OCR_CAPABILITY_ID,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "language": "eng",
        "psm": psm,
        "page_extent": {"width": page_extent[0], "height": page_extent[1]},
        "word_count": len(words),
        "text_items": lines,
        "dependency": dependency,
        "box_contract": "X0_Y0_X1_EXCLUSIVE_Y1_EXCLUSIVE",
        "deterministic_line_grouping": "PAGE_BLOCK_PARAGRAPH_LINE_THEN_WORD_NUMBER",
        "terminal_semantic_authority": False,
        "scope": "PINNED_TESSERACT_TSV_POSITIONED_TEXT_EXTRACTION_ONLY__NO_ENGINEERING_SEMANTIC_AUTHORITY",
    }


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    src = _safe_path(root, args.get("path"))
    return extract_positioned_text(
        src,
        psm=str(args.get("psm") or "6"),
        timeout_seconds=int(args.get("timeout_seconds") or 180),
    )
