"""Bounded deterministic deskew registration for engineering drawing rasters.

This component estimates a single global rotation from line geometry and only
registers drawings whose dominant primitives are near orthogonal axes. It does
not infer view identity, semantic feature meaning, local warps, perspective
distortion, or arbitrary non-axis-aligned layouts.
"""
from __future__ import annotations

from typing import Any
import math
import statistics

import cv2
import numpy as np

from canonical.runtime.raw_drawing_primitives import normalize_ink_mask

SCHEMA = "BRAIN_DRAWING_VIEW_REGISTRATION_V1"


def _axis_deviation_deg(angle_deg: float) -> float:
    """Fold a line angle to deviation from the nearest 90-degree axis."""
    return ((angle_deg + 45.0) % 90.0) - 45.0


def register_global_axis_deskew(
    image: np.ndarray[Any, Any],
    *,
    max_abs_angle_deg: float = 15.0,
    min_line_length: int = 20,
    hough_threshold: int = 20,
    max_line_gap: int = 5,
) -> dict[str, Any]:
    if max_abs_angle_deg <= 0 or max_abs_angle_deg > 30:
        raise ValueError("max_abs_angle_deg must be in (0, 30]")
    if min_line_length <= 0 or hough_threshold <= 0 or max_line_gap < 0:
        raise ValueError("invalid line-detection parameters")
    if not isinstance(image, np.ndarray) or image.ndim not in (2, 3):
        raise ValueError("image must be a 2D or 3D numpy array")

    mask = normalize_ink_mask(image)
    work = (mask * 255).astype(np.uint8)
    edges = cv2.Canny(work, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180.0,
        threshold=hough_threshold,
        minLineLength=min_line_length,
        maxLineGap=max_line_gap,
    )

    if lines is None:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "NO_USABLE_LINES",
            "terminal_authority": False,
        }

    weighted_deviations: list[float] = []
    usable_line_count = 0
    # OpenCV 4 commonly returns N×1×4 while OpenCV 5 may return N×4.
    # Normalize both exact API surfaces before consuming line tuples.
    normalized_lines = np.asarray(lines).reshape(-1, 4)
    for x1, y1, x2, y2 in normalized_lines:
        dx = float(x2 - x1)
        dy = float(y2 - y1)
        length = math.hypot(dx, dy)
        if length < min_line_length:
            continue
        angle = math.degrees(math.atan2(dy, dx))
        deviation = _axis_deviation_deg(angle)
        # Length weighting without floating-point optimizer state.
        repeats = max(1, int(length // 10.0))
        weighted_deviations.extend([deviation] * repeats)
        usable_line_count += 1

    if not weighted_deviations:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "NO_USABLE_LINES",
            "terminal_authority": False,
        }

    estimated_rotation_deg = float(statistics.median(weighted_deviations))
    if abs(estimated_rotation_deg) > max_abs_angle_deg:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "ROTATION_OUTSIDE_BOUNDED_SCOPE",
            "estimated_rotation_deg": estimated_rotation_deg,
            "usable_line_count": usable_line_count,
            "terminal_authority": False,
        }

    h, w = image.shape[:2]
    center = (w / 2.0, h / 2.0)
    matrix = cv2.getRotationMatrix2D(center, estimated_rotation_deg, 1.0)
    border = 255 if image.ndim == 2 else (255, 255, 255)
    registered = cv2.warpAffine(
        image,
        matrix,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border,
    )

    return {
        "schema": SCHEMA,
        "status": "REGISTERED",
        "estimated_rotation_deg": estimated_rotation_deg,
        "usable_line_count": usable_line_count,
        "registered_image": registered,
        "terminal_authority": False,
        "scope": "SINGLE_GLOBAL_ROTATION_DESKEW_FOR_ORTHOGONAL_LINE_DOMINATED_DRAWINGS_WITHIN_DECLARED_ANGLE_BOUND",
    }
