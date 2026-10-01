"""Deterministic bounded segmentation of spatially separated drawing-view regions."""
from __future__ import annotations

from typing import Any
import cv2
import numpy as np

from canonical.runtime.raw_drawing_primitives import normalize_ink_mask

SCHEMA = "BRAIN_DRAWING_VIEW_REGIONS_V1"


def segment_view_regions(
    image: np.ndarray[Any, Any],
    *,
    min_area: int = 100,
    dilation_px: int = 3,
    min_regions: int = 1,
    max_regions: int = 6,
) -> dict[str, Any]:
    if min_area <= 0 or dilation_px < 0 or min_regions <= 0 or max_regions < min_regions:
        raise ValueError("invalid segmentation parameters")

    mask = normalize_ink_mask(image)
    work = (mask * 255).astype(np.uint8)
    if dilation_px:
        k = 2 * dilation_px + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
        work = cv2.dilate(work, kernel, iterations=1)

    n, labels, stats, _ = cv2.connectedComponentsWithStats(work, connectivity=8)
    regions = []
    for label in range(1, n):
        x, y, w, h, area = (int(v) for v in stats[label])
        if area < min_area:
            continue
        # Report bbox against dilated grouping surface. This component groups
        # regions; downstream geometry must return to original primitives.
        regions.append({
            "x0": x,
            "y0": y,
            "x1_exclusive": x + w,
            "y1_exclusive": y + h,
            "group_area": area,
        })

    regions.sort(key=lambda r: (r["y0"], r["x0"], r["y1_exclusive"], r["x1_exclusive"]))

    if not (min_regions <= len(regions) <= max_regions):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "REGION_COUNT_OUTSIDE_BOUNDED_SCOPE",
            "region_count": len(regions),
            "regions": regions,
            "terminal_authority": False,
        }

    return {
        "schema": SCHEMA,
        "status": "SEGMENTED",
        "region_count": len(regions),
        "regions": regions,
        "view_identity": "UNASSIGNED",
        "terminal_authority": False,
        "scope": "SPATIALLY_SEPARATED_CLEAN_HIGH_CONTRAST_VIEW_REGIONS_ONLY",
    }
