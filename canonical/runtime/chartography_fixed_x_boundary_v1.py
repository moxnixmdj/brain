from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from PIL import Image

from canonical.runtime.chartography_axis_calibration_v1 import infer_linear_axes, pixel_to_y, x_to_pixel
from canonical.runtime.chartography_positioned_ocr_v1 import extract_words

SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_FIXED_X_BOUNDARY_READER_V1"


class FixedXBoundaryError(ValueError):
    pass


def _mask_text(image: Image.Image, words: Iterable[Mapping[str, Any]]) -> Image.Image:
    out = image.convert("L").copy()
    pixels = out.load()
    for word in words:
        left = max(0, int(float(word["left"])) - 3)
        top = max(0, int(float(word["top"])) - 3)
        right = min(out.width, int(float(word["left"]) + float(word["width"])) + 3)
        bottom = min(out.height, int(float(word["top"]) + float(word["height"])) + 3)
        for y in range(top, bottom):
            for x in range(left, right):
                pixels[x, y] = 255
    return out


def solve_lowest_interior_boundary(
    image_path: str | Path,
    x_value: float,
    *,
    words: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    image = Image.open(image_path).convert("L")
    if words is None:
        words = extract_words(image_path, psm=11, min_confidence=0)["words"]
    calibration = infer_linear_axes(words, image_width=image.width, image_height=image.height)
    x_pixel = x_to_pixel(calibration, float(x_value))
    left, top, right, bottom = calibration["plot_bbox"]
    if not (left < x_pixel < right):
        raise FixedXBoundaryError("X_VALUE_OUTSIDE_PLOT")

    clean = _mask_text(image, words)
    pixels = clean.load()
    center = int(round(x_pixel))
    dark_y = []
    for y in range(max(0, int(top) + 4), min(clean.height, int(bottom) - 4)):
        hits = sum(
            pixels[x, y] < 90
            for x in range(max(0, center - 4), min(clean.width, center + 5))
        )
        if hits >= 2:
            dark_y.append(y)

    groups: list[list[int]] = []
    for y in dark_y:
        if not groups or y - groups[-1][-1] > 4:
            groups.append([y])
        else:
            groups[-1].append(y)

    y_ticks = [row["value"] for row in calibration["y"]["ticks"]]
    candidates = []
    for group in groups:
        py = sum(group) / len(group)
        if py - top < 0.025 * (bottom - top) or bottom - py < 0.025 * (bottom - top):
            continue
        value = pixel_to_y(calibration, py)
        if min(y_ticks) <= value <= max(y_ticks):
            candidates.append({"value": value, "pixel_y": py, "thickness": len(group)})
    if not candidates:
        raise FixedXBoundaryError("NO_INTERIOR_BOUNDARY")

    chosen = min(candidates, key=lambda row: row["value"])
    return {
        "schema": SCHEMA,
        "status": "PASS__LOWEST_INTERIOR_BOUNDARY",
        "x_value": float(x_value),
        "boundary_value": float(chosen["value"]),
        "candidates": sorted(candidates, key=lambda row: row["value"]),
        "axis_calibration": calibration,
        "model_dependency_count": 0,
        "external_model_runtime_dependency_count": 0,
        "producer_cognition": "BRAIN_OWNED_DETERMINISTIC_MECHANISM",
        "terminal_authority": False,
    }
