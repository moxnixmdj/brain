from __future__ import annotations

import math
import re
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_LINEAR_AXIS_CALIBRATION_V1"
_NUM = re.compile(r"^[+\\-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)$")


class AxisCalibrationError(ValueError):
    pass


def parse_numeric_token(text: str) -> float | None:
    s = str(text).strip().replace(",", "").replace("−", "-").replace("°", "")
    if s.endswith("C") or s.endswith("%"):
        s = s[:-1]
    if not _NUM.fullmatch(s):
        return None
    try:
        value = float(s)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _cluster(rows: list[dict[str, Any]], key: str, tolerance: float):
    ordered = sorted(rows, key=lambda row: float(row[key]))
    groups: list[list[dict[str, Any]]] = []
    for row in ordered:
        if not groups:
            groups.append([row])
            continue
        mean = sum(float(x[key]) for x in groups[-1]) / len(groups[-1])
        if abs(float(row[key]) - mean) <= tolerance:
            groups[-1].append(row)
        else:
            groups.append([row])
    return groups


def _linear_fit(points: list[tuple[float, float]], *, positive: bool):
    if len(points) < 3:
        raise AxisCalibrationError("AT_LEAST_THREE_TICKS_REQUIRED")
    px = [x for x, _ in points]
    values = [y for _, y in points]
    mx, my = sum(px) / len(px), sum(values) / len(values)
    den = sum((x - mx) ** 2 for x in px)
    if den <= 0:
        raise AxisCalibrationError("DEGENERATE_TICK_COORDINATES")
    scale = sum((x - mx) * (y - my) for x, y in points) / den
    offset = my - scale * mx
    if positive and scale <= 0:
        raise AxisCalibrationError("X_AXIS_DIRECTION_INVALID")
    if not positive and scale >= 0:
        raise AxisCalibrationError("Y_AXIS_DIRECTION_INVALID")
    span = max(values) - min(values)
    if span <= 0:
        raise AxisCalibrationError("TICK_VALUE_SPAN_INVALID")
    residual = max(abs(scale * x + offset - y) for x, y in points)
    if residual / span > 0.025:
        raise AxisCalibrationError("NONLINEAR_OR_INCONSISTENT_TICKS")
    return {"scale": scale, "offset": offset, "max_residual": residual}


def infer_linear_axes(
    words: Iterable[Mapping[str, Any]],
    *,
    image_width: int,
    image_height: int,
) -> dict[str, Any]:
    numeric = []
    for raw in words:
        value = parse_numeric_token(str(raw.get("text") or ""))
        if value is None:
            continue
        try:
            numeric.append({
                "value": value,
                "cx": float(raw["cx"]),
                "cy": float(raw["cy"]),
            })
        except Exception:
            continue
    if len(numeric) < 6:
        raise AxisCalibrationError("INSUFFICIENT_NUMERIC_OCR")

    x_candidates = []
    for group in _cluster(numeric, "cy", max(5.0, image_height * 0.025)):
        if len(group) < 3:
            continue
        points = sorted((row["cx"], row["value"]) for row in group)
        if len({v for _, v in points}) < 3:
            continue
        try:
            fit = _linear_fit(points, positive=True)
        except AxisCalibrationError:
            continue
        score = (len(points), max(x for x, _ in points) - min(x for x, _ in points), -fit["max_residual"])
        x_candidates.append((score, points, fit))

    y_candidates = []
    for group in _cluster(numeric, "cx", max(5.0, image_width * 0.025)):
        if len(group) < 3:
            continue
        points = sorted((row["cy"], row["value"]) for row in group)
        if len({v for _, v in points}) < 3:
            continue
        try:
            fit = _linear_fit(points, positive=False)
        except AxisCalibrationError:
            continue
        score = (len(points), max(x for x, _ in points) - min(x for x, _ in points), -fit["max_residual"])
        y_candidates.append((score, points, fit))

    if not x_candidates or not y_candidates:
        raise AxisCalibrationError("LINEAR_AXIS_TICK_SET_NOT_IDENTIFIED")
    _, xpoints, xfit = max(x_candidates, key=lambda row: row[0])
    _, ypoints, yfit = max(y_candidates, key=lambda row: row[0])

    left, right = min(x for x, _ in xpoints), max(x for x, _ in xpoints)
    top, bottom = min(x for x, _ in ypoints), max(x for x, _ in ypoints)
    if right - left < image_width * 0.25 or bottom - top < image_height * 0.25:
        raise AxisCalibrationError("PLOT_SPAN_TOO_SMALL")

    return {
        "schema": SCHEMA,
        "status": "PASS__AFFINE_AXES_IDENTIFIED",
        "x": {"pixel_to_value": xfit, "ticks": [{"pixel": p, "value": v} for p, v in xpoints]},
        "y": {"pixel_to_value": yfit, "ticks": [{"pixel": p, "value": v} for p, v in ypoints]},
        "plot_bbox": [left, top, right, bottom],
        "producer_cognition": False,
        "terminal_authority": False,
    }


def pixel_to_x(cal: Mapping[str, Any], pixel: float) -> float:
    row = cal["x"]["pixel_to_value"]
    return float(row["scale"]) * pixel + float(row["offset"])


def pixel_to_y(cal: Mapping[str, Any], pixel: float) -> float:
    row = cal["y"]["pixel_to_value"]
    return float(row["scale"]) * pixel + float(row["offset"])


def x_to_pixel(cal: Mapping[str, Any], value: float) -> float:
    row = cal["x"]["pixel_to_value"]
    return (value - float(row["offset"])) / float(row["scale"])


def y_to_pixel(cal: Mapping[str, Any], value: float) -> float:
    row = cal["y"]["pixel_to_value"]
    return (value - float(row["offset"])) / float(row["scale"])
