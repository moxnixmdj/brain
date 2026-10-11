from __future__ import annotations

import hashlib
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping

from PIL import Image

from canonical.runtime import native_artifact_render_preservation_proof_v1 as render
from canonical.runtime.bound_capabilities import image_ocr_tesseract_positioned as positioned

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_ARTIFACT_VISUAL_OBSERVER_V1"
CAPABILITY_ID = "professional.artifact.visual_observer.v1"

_SUPPORTED_NATIVE = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".pptx": "pptx",
    ".xlsx": "xlsx",
}
_SUPPORTED_IMAGE = {".png", ".jpg", ".jpeg"}


class ProfessionalArtifactVisualObserverError(ValueError):
    pass


def _safe_path(root: str | Path, raw: Any) -> Path:
    base = Path(root).resolve()
    p = (base / str(raw or "")).resolve()
    if p != base and base not in p.parents:
        raise ProfessionalArtifactVisualObserverError("PATH_OUTSIDE_REPOSITORY")
    return p


def _ink_fraction(im: Image.Image) -> float:
    rgb = im.convert("RGB")
    total = max(1, rgb.width * rgb.height)
    ink = 0
    for r, g, b in rgb.getdata():
        # Deliberately broad non-white observation. This is a blank-page
        # detector, not an aesthetic or semantic quality score.
        if min(r, g, b) < 245:
            ink += 1
    return ink / total


def _box(row: Mapping[str, Any], width: int, height: int) -> tuple[int, int, int, int]:
    b = row.get("box")
    if not isinstance(b, Mapping):
        raise ProfessionalArtifactVisualObserverError("OCR_LINE_BOX_MISSING")
    try:
        x0 = int(b["x0"])
        y0 = int(b["y0"])
        x1 = int(b["x1_exclusive"])
        y1 = int(b["y1_exclusive"])
    except Exception as exc:
        raise ProfessionalArtifactVisualObserverError("OCR_LINE_BOX_INVALID") from exc
    if x0 < 0 or y0 < 0 or x1 <= x0 or y1 <= y0 or x1 > width or y1 > height:
        raise ProfessionalArtifactVisualObserverError("OCR_LINE_BOX_OUT_OF_BOUNDS")
    return x0, y0, x1, y1


def _overlap_fraction(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    aa = (ax1 - ax0) * (ay1 - ay0)
    ba = (bx1 - bx0) * (by1 - by0)
    return inter / max(1, min(aa, ba))


def analyze_page(
    image_path: str | Path,
    ocr: Mapping[str, Any],
    *,
    require_text: bool = True,
    blank_ink_fraction: float = 0.001,
    minimum_line_confidence: float = 35.0,
    crop_guard_px: int = 2,
    max_line_overlap_fraction: float = 0.20,
) -> dict[str, Any]:
    src = Path(image_path)
    if not src.is_file():
        raise ProfessionalArtifactVisualObserverError("PAGE_IMAGE_MISSING")
    with Image.open(src) as raw:
        im = raw.convert("RGB")
    width, height = im.size
    if width <= 0 or height <= 0:
        raise ProfessionalArtifactVisualObserverError("PAGE_GEOMETRY_INVALID")

    if int(ocr.get("page_width") or -1) != width or int(ocr.get("page_height") or -1) != height:
        raise ProfessionalArtifactVisualObserverError("OCR_PAGE_GEOMETRY_MISMATCH")

    items = ocr.get("text_items")
    if not isinstance(items, list):
        raise ProfessionalArtifactVisualObserverError("OCR_TEXT_ITEMS_INVALID")

    ink_fraction = _ink_fraction(im)
    boxes: list[tuple[int, int, int, int]] = []
    confidences: list[float] = []
    crop_contacts: list[int] = []
    for i, row in enumerate(items):
        if not isinstance(row, Mapping):
            raise ProfessionalArtifactVisualObserverError("OCR_LINE_INVALID")
        box = _box(row, width, height)
        boxes.append(box)
        try:
            conf = float(row.get("confidence_mean"))
        except Exception as exc:
            raise ProfessionalArtifactVisualObserverError("OCR_LINE_CONFIDENCE_INVALID") from exc
        if not math.isfinite(conf):
            raise ProfessionalArtifactVisualObserverError("OCR_LINE_CONFIDENCE_NONFINITE")
        confidences.append(conf)
        x0, y0, x1, y1 = box
        if x0 <= crop_guard_px or y0 <= crop_guard_px or x1 >= width - crop_guard_px or y1 >= height - crop_guard_px:
            crop_contacts.append(i)

    overlaps: list[dict[str, Any]] = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            frac = _overlap_fraction(boxes[i], boxes[j])
            if frac > max_line_overlap_fraction:
                overlaps.append({"a": i, "b": j, "fraction": frac})

    min_conf = min(confidences) if confidences else None
    gates = {
        "PAGE_NOT_BLANK": ink_fraction >= blank_ink_fraction,
        "TEXT_PRESENT_WHEN_REQUIRED": (not require_text) or bool(items),
        "OCR_LINE_CONFIDENCE_BOUNDED": (not items) or (min_conf is not None and min_conf >= minimum_line_confidence),
        "TEXT_NOT_TOUCHING_HARD_CROP": not crop_contacts,
        "NO_MAJOR_OCR_LINE_OVERLAP": not overlaps,
    }
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": "PASS__BOUNDED_VISUAL_TECHNICAL_OBSERVATION" if passed else "FAIL_CLOSED",
        "pass": passed,
        "page_size": [width, height],
        "page_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        "ink_fraction": ink_fraction,
        "line_count": len(items),
        "minimum_line_confidence": min_conf,
        "crop_contact_line_indices": crop_contacts,
        "major_line_overlaps": overlaps,
        "gates": gates,
        "scope": (
            "OBJECTIVE_RENDERED_PAGE_TECHNICAL_OBSERVATION_ONLY__"
            "BLANKNESS_POSITIONED_TEXT_GEOMETRY_CROP_RISK_AND_MAJOR_LINE_OVERLAP__"
            "NO_AESTHETIC_SEMANTIC_RELEVANCE_OR_OWNER_PREFERENCE_AUTHORITY"
        ),
        "professional_quality_top": False,
        "owner_preference_equivalence": False,
        "benchmark_score_authority": False,
        "terminal_authority": False,
        "external_general_purpose_model_runtime_dependency_count": 0,
    }


def _observe_ocr(page: Path) -> dict[str, Any]:
    return positioned.run({"path": page.name, "language": "eng"}, page.parent)


def _render_pages(src: Path, root: Path) -> list[Path]:
    ext = src.suffix.lower()
    if ext in _SUPPORTED_IMAGE:
        return [src]
    fmt = _SUPPORTED_NATIVE.get(ext)
    if fmt is None:
        raise ProfessionalArtifactVisualObserverError("FORMAT_UNSUPPORTED:" + ext)
    payload = src.read_bytes()
    pdf = render._to_pdf(payload, fmt, root, "artifact")
    return render._rasterize(pdf, root, "artifact_page")


def run(args: dict[str, Any], root: str | Path) -> dict[str, Any]:
    src = _safe_path(root, args.get("path"))
    if not src.is_file():
        raise ProfessionalArtifactVisualObserverError("ARTIFACT_MISSING")
    require_text = bool(args.get("require_text", True))

    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        pages = _render_pages(src, temp)
        rows: list[dict[str, Any]] = []
        for page in pages:
            ocr = _observe_ocr(page)
            rows.append(analyze_page(page, ocr, require_text=require_text))

    passed = bool(rows) and all(row.get("pass") is True for row in rows)
    return {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": "PASS__BOUNDED_PROFESSIONAL_ARTIFACT_VISUAL_OBSERVATION" if passed else "FAIL_CLOSED",
        "pass": passed,
        "source_path": str(src.relative_to(Path(root).resolve())),
        "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        "page_count": len(rows),
        "pages": rows,
        "composed_verified_substrates": [
            "canonical/runtime/native_artifact_render_preservation_proof_v1.py",
            "image.extract.ocr.tesseract.positioned.tsv",
        ],
        "scope": (
            "BRAIN_GENERATED_RENDERED_PAGE_OBSERVATION_FOR_COMMON_PROFESSIONAL_ARTIFACTS__"
            "TECHNICAL_READABILITY_FLOOR_ONLY__NO_HOLISTIC_AESTHETIC_OR_SEMANTIC_TOP_CLAIM"
        ),
        "professional_quality_top": False,
        "owner_preference_equivalence": False,
        "benchmark_score_authority": False,
        "terminal_authority": False,
        "incremental_spend_usd": 0,
        "external_general_purpose_model_runtime_dependency_count": 0,
    }
