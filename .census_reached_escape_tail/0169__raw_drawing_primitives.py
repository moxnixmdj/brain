"""Deterministic raw technical-drawing normalization for a bounded clean-raster subset.

This is a Brain-owned implementation after white-box inspection of a permissive
OpenCV technical-drawing vectorization route.  It intentionally owns only:
- grayscale conversion;
- Otsu/adaptive binarization into a normalized ink mask;
- deterministic line/circle primitive extraction;
- stable sorted machine-readable output.

It does NOT interpret dimension text, semantic feature meaning, view identity, hidden
geometry, or arbitrary noisy drawings. Those remain explicit residuals.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import cv2
import numpy as np

SCHEMA = "BRAIN_RAW_DRAWING_PRIMITIVES_V1"


@dataclass(frozen=True)
class LinePrimitive:
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass(frozen=True)
class CirclePrimitive:
    cx: int
    cy: int
    radius: int


def _gray(image: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
    if image.ndim == 2:
        return image.astype(np.uint8, copy=False)
    if image.ndim == 3 and image.shape[2] in (3, 4):
        code = cv2.COLOR_BGRA2GRAY if image.shape[2] == 4 else cv2.COLOR_BGR2GRAY
        return cv2.cvtColor(image, code)
    raise ValueError(f"unsupported image shape: {image.shape}")


def normalize_ink_mask(
    image: np.ndarray[Any, Any],
    *,
    adaptive: bool = False,
) -> np.ndarray[Any, Any]:
    gray = _gray(image)
    if adaptive:
        # Fixed parameters are part of the declared bounded contract.
        mask = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 7
        )
    else:
        _, mask = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
        )
    return (mask > 0).astype(np.uint8)


def extract_primitives(
    image: np.ndarray[Any, Any],
    *,
    min_line_length: int = 20,
    max_line_gap: int = 3,
    line_threshold: int = 20,
    min_circle_radius: int = 3,
    max_circle_radius: int = 0,
) -> dict[str, Any]:
    if min_line_length <= 0 or max_line_gap < 0 or line_threshold <= 0:
        raise ValueError("invalid line detector parameters")
    if min_circle_radius < 0 or max_circle_radius < 0:
        raise ValueError("invalid circle detector parameters")

    mask = normalize_ink_mask(image)
    edges = (mask * 255).astype(np.uint8)

    lines_raw = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180.0,
        threshold=line_threshold,
        minLineLength=min_line_length,
        maxLineGap=max_line_gap,
    )
    lines: list[LinePrimitive] = []
    if lines_raw is not None:
        for x1, y1, x2, y2 in np.asarray(lines_raw).reshape(-1, 4):
            a = (int(x1), int(y1))
            b = (int(x2), int(y2))
            if b < a:
                a, b = b, a
            lines.append(LinePrimitive(a[0], a[1], b[0], b[1]))
    lines = sorted(set(lines), key=lambda x: (x.y1, x.x1, x.y2, x.x2))

    blur = cv2.GaussianBlur(_gray(image), (5, 5), 1.0)
    max_r = max_circle_radius or max(blur.shape[:2]) // 2
    circles_raw = cv2.HoughCircles(
        blur,
        cv2.HOUGH_GRADIENT,
        dp=1.0,
        minDist=max(2 * min_circle_radius, 8),
        param1=100,
        param2=18,
        minRadius=min_circle_radius,
        maxRadius=max_r,
    )
    circles: list[CirclePrimitive] = []
    if circles_raw is not None:
        for cx, cy, r in np.round(circles_raw[0]).astype(int):
            circles.append(CirclePrimitive(int(cx), int(cy), int(r)))
    circles = sorted(set(circles), key=lambda x: (x.cy, x.cx, x.radius))

    ys, xs = np.where(mask > 0)
    bbox = None
    if len(xs):
        bbox = {
            "x0": int(xs.min()),
            "y0": int(ys.min()),
            "x1_exclusive": int(xs.max()) + 1,
            "y1_exclusive": int(ys.max()) + 1,
        }

    return {
        "schema": SCHEMA,
        "status": "EXTRACTED",
        "shape": [int(mask.shape[0]), int(mask.shape[1])],
        "ink_pixels": int(mask.sum()),
        "ink_bbox": bbox,
        "lines": [asdict(x) for x in lines],
        "circles": [asdict(x) for x in circles],
        "normalized_mask": mask.tolist(),
        "terminal_authority": False,
        "scope": "CLEAN_HIGH_CONTRAST_RASTER_GEOMETRY_ONLY",
    }
