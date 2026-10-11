from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping

from PIL import Image

from canonical.runtime.chartography_axis_calibration_v1 import infer_linear_axes, pixel_to_x, pixel_to_y
from canonical.runtime.chartography_positioned_ocr_v1 import extract_words
from canonical.runtime.chartography_semantic_utils_v1 import (
    format_requested_rounding,
    line_groups,
    numeric_overlap,
    prompt_numbers,
)

SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_SERIES_INTERSECTION_V1"


class SeriesIntersectionError(ValueError):
    pass


def _distance(a, b) -> float:
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def _dominant_swatch_color(image: Image.Image, box: tuple[int, int, int, int]):
    rgb = image.convert("RGB")
    left, top, right, bottom = box
    counts: dict[tuple[int, int, int], int] = {}
    for y in range(max(0, top), min(rgb.height, bottom)):
        for x in range(max(0, left), min(rgb.width, right)):
            color = rgb.getpixel((x, y))
            if max(color) - min(color) < 45:
                continue
            if min(color) > 235:
                continue
            quantized = tuple(min(255, int(round(v / 16.0) * 16)) for v in color)
            counts[quantized] = counts.get(quantized, 0) + 1
    if not counts:
        raise SeriesIntersectionError("LEGEND_SWATCH_COLOR_NOT_FOUND")
    return max(counts, key=counts.get)


def _swatch_occupancy(image: Image.Image, box, color) -> float:
    rgb = image.convert("RGB")
    left, top, right, bottom = box
    total = 0
    hit = 0
    for x in range(max(0, left), min(rgb.width, right)):
        total += 1
        if any(
            _distance(rgb.getpixel((x, y)), color) <= 75
            for y in range(max(0, top), min(rgb.height, bottom))
        ):
            hit += 1
    return hit / max(1, total)


def _kmeans_1d(values: list[float], k: int) -> list[int]:
    if k < 1 or len(values) < k:
        raise SeriesIntersectionError("SERIES_CLUSTER_COUNT_INVALID")
    ordered = sorted(values)
    centers = [ordered[min(len(ordered) - 1, int((i + 0.5) * len(ordered) / k))] for i in range(k)]
    labels = [0] * len(values)
    for _ in range(30):
        labels = [min(range(k), key=lambda j: abs(v - centers[j])) for v in values]
        new = []
        for j in range(k):
            members = [v for v, label in zip(values, labels) if label == j]
            new.append(sum(members) / len(members) if members else centers[j])
        if max(abs(a - b) for a, b in zip(new, centers)) < 1e-10:
            break
        centers = new
    rank = {old: new for new, old in enumerate(sorted(range(k), key=lambda j: centers[j]))}
    return [rank[label] for label in labels]


def _fit(points: list[tuple[float, float]]) -> tuple[float, float]:
    if len(points) < 20:
        raise SeriesIntersectionError("INSUFFICIENT_SERIES_PIXELS")
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den <= 0:
        raise SeriesIntersectionError("DEGENERATE_SERIES")
    slope = sum((x - mx) * (y - my) for x, y in points) / den
    return slope, my - slope * mx


def solve(
    image_path: str | Path,
    prompt: str,
    *,
    words: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    image = Image.open(image_path).convert("RGB")
    if words is None:
        words = extract_words(image_path, psm=11, min_confidence=0)["words"]
    calibration = infer_linear_axes(words, image_width=image.width, image_height=image.height)
    groups = line_groups(words)
    numbers = prompt_numbers(prompt, exclude_formatting=True)
    if len(numbers) < 2:
        raise SeriesIntersectionError("PROMPT_NUMBERS_INSUFFICIENT")

    candidates = []
    for group in groups:
        overlap = numeric_overlap(numbers, prompt_numbers(group["text"]))
        if overlap >= 2:
            candidates.append((overlap, len(group["text"]), group))
    if not candidates:
        raise SeriesIntersectionError("LEGEND_SELECTOR_NOT_IDENTIFIED")
    target = max(candidates, key=lambda row: (row[0], row[1]))[2]

    left, top, _, bottom = [int(round(v)) for v in target["bbox"]]
    swatch = (max(0, left - 75), max(0, top - 5), max(0, left - 3), min(image.height, bottom + 5))
    target_color = _dominant_swatch_color(image, swatch)
    target_occupancy = _swatch_occupancy(image, swatch, target_color)

    plot_right = float(calibration["plot_bbox"][2])
    same_color_entries = []
    for group in groups:
        gl, gt, _, gb = [int(round(v)) for v in group["bbox"]]
        if gl <= plot_right:
            continue
        box = (max(0, gl - 75), max(0, gt - 5), max(0, gl - 3), min(image.height, gb + 5))
        try:
            color = _dominant_swatch_color(image, box)
        except SeriesIntersectionError:
            continue
        if _distance(color, target_color) <= 75:
            same_color_entries.append((_swatch_occupancy(image, box, color), group))
    if not same_color_entries:
        same_color_entries = [(target_occupancy, target)]
    ordered_legend = sorted(range(len(same_color_entries)), key=lambda i: same_color_entries[i][0])
    target_index = min(
        range(len(same_color_entries)),
        key=lambda i: abs(same_color_entries[i][0] - target_occupancy),
    )
    target_rank = ordered_legend.index(target_index)
    cluster_count = len(same_color_entries)

    plot_left, plot_top, plot_right, plot_bottom = calibration["plot_bbox"]
    points = []
    slopes = []
    for py in range(max(0, int(plot_top)), min(image.height, int(plot_bottom) + 1)):
        for px in range(max(0, int(plot_left)), min(image.width, int(plot_right) + 1)):
            if _distance(image.getpixel((px, py)), target_color) > 75:
                continue
            x_value = pixel_to_x(calibration, px)
            y_value = pixel_to_y(calibration, py)
            if x_value <= 0:
                continue
            points.append((x_value, y_value, px))
            slopes.append(y_value / x_value)
    if len(points) < 30:
        raise SeriesIntersectionError("TARGET_COLOR_SERIES_NOT_FOUND")

    labels = _kmeans_1d(slopes, cluster_count) if cluster_count > 1 else [0] * len(points)
    clusters = []
    for index in range(cluster_count):
        data = [(x, y) for (x, y, _), label in zip(points, labels) if label == index]
        pixels = [px for (_, _, px), label in zip(points, labels) if label == index]
        if len(data) < 20:
            continue
        bins = {int(60 * (px - plot_left) / max(1.0, plot_right - plot_left)) for px in pixels}
        occupancy = len(bins) / 61.0
        slope, intercept = _fit(data)
        clusters.append({"occupancy": occupancy, "slope": slope, "intercept": intercept, "pixel_count": len(data)})
    if len(clusters) != cluster_count:
        raise SeriesIntersectionError("SERIES_CLUSTERING_AMBIGUOUS")
    clusters.sort(key=lambda row: row["occupancy"])
    chosen = clusters[min(target_rank, len(clusters) - 1)]

    selector_numbers = prompt_numbers(target["text"])
    residual = [value for value in numbers if numeric_overlap([value], selector_numbers) == 0]
    y_ticks = [row["value"] for row in calibration["y"]["ticks"]]
    target_values = [value for value in residual if min(y_ticks) <= value <= max(y_ticks)]
    if len(target_values) != 1:
        raise SeriesIntersectionError("TARGET_Y_VALUE_AMBIGUOUS")
    target_y = target_values[0]

    slope = float(chosen["slope"])
    if abs(slope) < 1e-12:
        raise SeriesIntersectionError("SERIES_SLOPE_ZERO")
    answer = (target_y - float(chosen["intercept"])) / slope
    x_ticks = [row["value"] for row in calibration["x"]["ticks"]]
    if not (min(x_ticks) <= answer <= max(x_ticks)):
        raise SeriesIntersectionError("INTERSECTION_OUTSIDE_AXIS_RANGE")

    return {
        "schema": SCHEMA,
        "status": "PASS__CALIBRATED_SERIES_INTERSECTION",
        "answer": format_requested_rounding(prompt, answer),
        "raw_value": answer,
        "target_y": target_y,
        "legend_text": target["text"],
        "axis_calibration": calibration,
        "model_dependency_count": 0,
        "external_model_runtime_dependency_count": 0,
        "producer_cognition": "BRAIN_OWNED_DETERMINISTIC_MECHANISM",
        "terminal_authority": False,
    }
