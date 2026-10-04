"""Deterministic chart-image primitive extraction for Project Brain.

This module is deliberately *not* a semantic chart QA system.  It converts one
local raster image into a content-addressed set of visual primitives that later
Brain reasoning can consume:

* positioned text via the already-pinned Tesseract bridge (optional);
* long horizontal/vertical/oblique line segments;
* best-effort plot-axis candidates;
* contour/rectangle regions;
* deterministic connected components;
* coarse dominant HSV colour bins.

No network calls, model APIs, learned weights, or benchmark-specific knowledge
are used.  Dependency drift fails closed.
"""
from __future__ import annotations

import hashlib
import math
import pathlib
from typing import Any

EXPECTED_CV2_VERSION = "4.6.0"
SCHEMA = "PROJECT_BRAIN_CHART_VISUAL_PRIMITIVES_V1"
CAPABILITY_ID = "image.chart.visual_primitives.opencv.v1"


def _deps():
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError("CHART_CV_DEPENDENCY_IMPORT_FAILED") from exc
    if str(cv2.__version__) != EXPECTED_CV2_VERSION:
        raise RuntimeError(
            f"OPENCV_VERSION_DRIFT:{cv2.__version__}!={EXPECTED_CV2_VERSION}"
        )
    return cv2, np


def _safe_path(root: str | pathlib.Path, raw: Any) -> pathlib.Path:
    base = pathlib.Path(root).resolve()
    path = (base / str(raw or "")).resolve()
    if path != base and base not in path.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not path.is_file():
        raise RuntimeError("IMAGE_NOT_FOUND")
    return path


def _decode(raw: bytes):
    cv2, np = _deps()
    buf = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if image is None or image.ndim != 3 or image.shape[2] != 3:
        raise RuntimeError("IMAGE_DECODE_FAILED")
    h, w = image.shape[:2]
    if h < 8 or w < 8 or h > 12000 or w > 12000:
        raise RuntimeError(f"IMAGE_EXTENT_OUT_OF_SCOPE:{w}x{h}")
    return image


def _edge_map(image):
    cv2, np = _deps()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    med = float(np.median(gray))
    lo = int(max(20.0, 0.66 * med))
    hi = int(min(255.0, max(lo + 1, 1.33 * med)))
    edges = cv2.Canny(gray, lo, hi, apertureSize=3, L2gradient=True)
    return gray, edges, {"low": lo, "high": hi}


def _line_segments(edges):
    cv2, np = _deps()
    h, w = edges.shape[:2]
    min_len = max(20, int(0.08 * max(h, w)))
    threshold = max(20, int(0.035 * max(h, w)))
    raw = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180.0,
        threshold=threshold,
        minLineLength=min_len,
        maxLineGap=max(4, int(0.01 * max(h, w))),
    )
    items: list[dict[str, Any]] = []
    if raw is not None:
        for entry in raw[:, 0, :]:
            x1, y1, x2, y2 = (int(v) for v in entry)
            dx, dy = x2 - x1, y2 - y1
            length = float(math.hypot(dx, dy))
            if length <= 0:
                continue
            angle = math.degrees(math.atan2(dy, dx))
            abs_axis = min(abs(angle), abs(abs(angle) - 180.0))
            if abs_axis <= 3.0:
                kind = "horizontal"
            elif abs(abs(angle) - 90.0) <= 3.0:
                kind = "vertical"
            else:
                kind = "oblique"
            items.append(
                {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "length_px": round(length, 4),
                    "angle_deg": round(angle, 4),
                    "kind": kind,
                }
            )
    items.sort(
        key=lambda x: (
            -float(x["length_px"]),
            str(x["kind"]),
            int(x["y1"]),
            int(x["x1"]),
            int(x["y2"]),
            int(x["x2"]),
        )
    )
    return items[:512]


def _axis_candidates(lines, width: int, height: int):
    horizontals = [x for x in lines if x["kind"] == "horizontal"]
    verticals = [x for x in lines if x["kind"] == "vertical"]

    def hscore(x):
        mid_y = (int(x["y1"]) + int(x["y2"])) / 2.0
        lower_bonus = 1.0 if mid_y >= height * 0.45 else 0.0
        return (lower_bonus, float(x["length_px"]), mid_y)

    def vscore(x):
        mid_x = (int(x["x1"]) + int(x["x2"])) / 2.0
        left_bonus = 1.0 if mid_x <= width * 0.55 else 0.0
        return (left_bonus, float(x["length_px"]), -mid_x)

    return {
        "x_axis": max(horizontals, key=hscore) if horizontals else None,
        "y_axis": max(verticals, key=vscore) if verticals else None,
        "heuristic_only": True,
    }


def _regions(gray, width: int, height: int):
    cv2, np = _deps()
    # Invert so typical dark ink becomes foreground. Otsu is deterministic.
    _, binary = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )
    image_area = width * height
    components: list[dict[str, Any]] = []
    for idx in range(1, int(n)):
        x, y, w, h, area = (int(v) for v in stats[idx])
        if area < max(4, image_area // 200000):
            continue
        if area > image_area * 0.8:
            continue
        cx, cy = (float(v) for v in centroids[idx])
        components.append(
            {
                "x0": x,
                "y0": y,
                "x1_exclusive": x + w,
                "y1_exclusive": y + h,
                "area_px": area,
                "centroid_x": round(cx, 4),
                "centroid_y": round(cy, 4),
            }
        )
    components.sort(
        key=lambda z: (-int(z["area_px"]), int(z["y0"]), int(z["x0"]))
    )

    contours, _ = cv2.findContours(
        binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )
    rectangles: list[dict[str, Any]] = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < max(16.0, image_area * 0.00002):
            continue
        peri = float(cv2.arcLength(contour, True))
        if peri <= 0:
            continue
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue
        x, y, w, h = (int(v) for v in cv2.boundingRect(approx))
        if w < 3 or h < 3:
            continue
        fill = area / float(max(1, w * h))
        rectangles.append(
            {
                "x0": x,
                "y0": y,
                "x1_exclusive": x + w,
                "y1_exclusive": y + h,
                "contour_area_px": round(area, 4),
                "bounding_fill_ratio": round(fill, 6),
            }
        )
    rectangles.sort(
        key=lambda z: (
            -float(z["contour_area_px"]),
            int(z["y0"]),
            int(z["x0"]),
        )
    )
    return components[:512], rectangles[:256]


def _dominant_colours(image):
    cv2, np = _deps()
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # Deterministic coarse histogram: H 12 bins, S 4 bins, V 4 bins.
    hbin = np.minimum(hsv[:, :, 0] // 15, 11).astype(np.int32)
    sbin = np.minimum(hsv[:, :, 1] // 64, 3).astype(np.int32)
    vbin = np.minimum(hsv[:, :, 2] // 64, 3).astype(np.int32)
    code = hbin * 16 + sbin * 4 + vbin
    counts = np.bincount(code.reshape(-1), minlength=192)
    total = int(code.size)
    order = np.argsort(-counts, kind="stable")
    out: list[dict[str, Any]] = []
    for c in order[:16]:
        count = int(counts[int(c)])
        if count <= 0:
            continue
        h = int(c) // 16
        rem = int(c) % 16
        s = rem // 4
        v = rem % 4
        out.append(
            {
                "h_bin": h,
                "s_bin": s,
                "v_bin": v,
                "pixel_count": count,
                "fraction": round(count / total, 8),
            }
        )
    return out


def extract_visual_primitives(
    image_path: str | pathlib.Path,
    *,
    include_ocr: bool = True,
    ocr_psm: str = "6",
) -> dict[str, Any]:
    path = pathlib.Path(image_path)
    raw = path.read_bytes()
    image = _decode(raw)
    height, width = (int(x) for x in image.shape[:2])
    gray, edges, canny = _edge_map(image)
    lines = _line_segments(edges)
    components, rectangles = _regions(gray, width, height)

    ocr: dict[str, Any] | None = None
    if include_ocr:
        from canonical.runtime.positioned_ocr_tesseract_bridge import (
            extract_positioned_text,
        )
        ocr = extract_positioned_text(path, psm=str(ocr_psm))

    return {
        "schema": SCHEMA,
        "status": "EXTRACTED",
        "capability_id": CAPABILITY_ID,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "width": width,
        "height": height,
        "opencv_version": EXPECTED_CV2_VERSION,
        "canny_thresholds": canny,
        "lines": lines,
        "axes": _axis_candidates(lines, width, height),
        "connected_components": components,
        "rectangles": rectangles,
        "dominant_hsv_bins": _dominant_colours(image),
        "positioned_ocr": ocr,
        "network_required": False,
        "external_model_required": False,
        "terminal_semantic_authority": False,
        "scope": (
            "DETERMINISTIC_RASTER_TO_VISUAL_PRIMITIVES_ONLY__"
            "NO_CHART_QA_OR_PROFESSIONAL_JUDGMENT_CREDIT"
        ),
    }


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    src = _safe_path(root, args.get("path"))
    return extract_visual_primitives(
        src,
        include_ocr=bool(args.get("include_ocr", True)),
        ocr_psm=str(args.get("ocr_psm") or "6"),
    )
