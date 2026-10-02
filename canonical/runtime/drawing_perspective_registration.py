"""Fail-closed projective rectification for technical drawing pages/regions.

Closes a bounded part of M1A registration beyond simple rotation:
- explicit four-corner homography; or
- auto-detected unique dominant quadrilateral page/frame.

No semantic view identity is inferred here. If a unique quadrilateral cannot be
established, the route fails closed instead of inventing a perspective transform.
"""
from __future__ import annotations

from typing import Any, Sequence
import math

import cv2
import numpy as np

from canonical.runtime.raw_drawing_primitives import normalize_ink_mask

SCHEMA = "BRAIN_DRAWING_PERSPECTIVE_REGISTRATION_V1"


def _order_corners(points: np.ndarray) -> np.ndarray:
    pts = np.asarray(points, dtype=np.float32).reshape(4, 2)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).reshape(-1)
    ordered = np.zeros((4, 2), dtype=np.float32)
    ordered[0] = pts[np.argmin(s)]   # top-left
    ordered[2] = pts[np.argmax(s)]   # bottom-right
    ordered[1] = pts[np.argmin(d)]   # top-right
    ordered[3] = pts[np.argmax(d)]   # bottom-left
    if len({tuple(map(float, p)) for p in ordered}) != 4:
        raise ValueError("corners are not four distinct points")
    return ordered


def _target_size(c: np.ndarray) -> tuple[int, int]:
    tl, tr, br, bl = c
    w = max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl))
    h = max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr))
    wi, hi = int(round(float(w))), int(round(float(h)))
    if wi < 8 or hi < 8:
        raise ValueError("rectified target too small")
    return wi, hi


def _quad_score(quad: np.ndarray, image_area: float) -> float:
    area = abs(float(cv2.contourArea(quad.astype(np.float32))))
    if image_area <= 0:
        return 0.0
    return area / image_area


def detect_unique_dominant_quadrilateral(
    image: np.ndarray[Any, Any],
    *,
    min_area_fraction: float = 0.20,
    ambiguity_ratio: float = 0.85,
) -> dict[str, Any]:
    if not (0.0 < min_area_fraction < 1.0):
        raise ValueError("min_area_fraction must be in (0,1)")
    if not (0.0 < ambiguity_ratio < 1.0):
        raise ValueError("ambiguity_ratio must be in (0,1)")
    mask = normalize_ink_mask(image)
    work = (mask * 255).astype(np.uint8)
    contours, _ = cv2.findContours(work, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = mask.shape
    image_area = float(h * w)
    candidates: list[tuple[float, np.ndarray]] = []
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        if peri <= 0:
            continue
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue
        quad = approx.reshape(4, 2).astype(np.float32)
        score = _quad_score(quad, image_area)
        if score >= min_area_fraction:
            candidates.append((score, quad))
    candidates.sort(key=lambda x: -x[0])
    if not candidates:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "NO_DOMINANT_QUADRILATERAL"}
    if len(candidates) > 1 and candidates[1][0] >= candidates[0][0] * ambiguity_ratio:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "AMBIGUOUS_QUADRILATERAL",
            "best_area_fraction": candidates[0][0],
            "second_area_fraction": candidates[1][0],
        }
    ordered = _order_corners(candidates[0][1])
    return {
        "schema": SCHEMA,
        "status": "DETECTED",
        "corners": ordered.tolist(),
        "area_fraction": candidates[0][0],
        "terminal_authority": False,
    }


def rectify_perspective(
    image: np.ndarray[Any, Any],
    *,
    corners: Sequence[Sequence[float]] | None = None,
    min_area_fraction: float = 0.20,
) -> dict[str, Any]:
    if not isinstance(image, np.ndarray) or image.ndim not in (2, 3):
        raise ValueError("image must be a 2D or 3D numpy array")
    if corners is None:
        detected = detect_unique_dominant_quadrilateral(
            image, min_area_fraction=min_area_fraction
        )
        if detected["status"] != "DETECTED":
            return detected
        src = _order_corners(np.asarray(detected["corners"], dtype=np.float32))
        route = "AUTO_UNIQUE_DOMINANT_QUADRILATERAL"
    else:
        try:
            src = _order_corners(np.asarray(corners, dtype=np.float32))
        except Exception as exc:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "error": f"INVALID_EXPLICIT_CORNERS:{type(exc).__name__}",
            }
        route = "EXPLICIT_CORNERS"

    try:
        width, height = _target_size(src)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": f"INVALID_TARGET_GEOMETRY:{type(exc).__name__}",
        }

    dst = np.asarray(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(src, dst)
    det = float(np.linalg.det(matrix))
    if not math.isfinite(det) or abs(det) < 1e-12:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "SINGULAR_HOMOGRAPHY"}

    border = 255 if image.ndim == 2 else tuple([255] * image.shape[2])
    rectified = cv2.warpPerspective(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border,
    )
    return {
        "schema": SCHEMA,
        "status": "REGISTERED",
        "route": route,
        "source_corners": src.tolist(),
        "output_size": [height, width],
        "homography": matrix.tolist(),
        "registered_image": rectified,
        "terminal_authority": False,
        "scope": "SINGLE_PROJECTIVE_QUADRILATERAL_RECTIFICATION_ONLY",
    }
