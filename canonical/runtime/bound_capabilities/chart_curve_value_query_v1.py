from __future__ import annotations

import math
import pathlib
from typing import Any, Mapping, Sequence

from PIL import Image

from canonical.runtime.bound_capabilities import image_ocr_tesseract_positioned as positioned_ocr
from canonical.runtime.bound_capabilities.chart_positioned_ocr_axis_binding_v1 import (
    bind_axes_from_positioned_ocr,
)
from canonical.runtime.bound_capabilities.chart_raster_scene_graph_v1 import build_scene_graph
from canonical.runtime.bound_capabilities.chart_legend_style_binding_v1 import bind_legend_styles

CAPABILITY_ID = "chart.raster.curve_value_query.v1"
SCHEMA = "PROJECT_BRAIN_CHART_RASTER_CURVE_VALUE_QUERY_V1"


class CurveValueQueryError(ValueError):
    pass


def _norm_label(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _axis_value_from_pixel(axis: Mapping[str, Any], pixel: float) -> float:
    try:
        scale = str(axis["scale"])
        a, b = (float(x) for x in axis["transformed_value_from_pixel"])
    except Exception as exc:
        raise CurveValueQueryError("AXIS_MODEL_INVALID") from exc
    transformed = a * float(pixel) + b
    if scale == "LINEAR":
        value = transformed
    elif scale == "LOG10":
        try:
            value = 10.0 ** transformed
        except OverflowError as exc:
            raise CurveValueQueryError("AXIS_VALUE_OVERFLOW") from exc
    else:
        raise CurveValueQueryError("AXIS_SCALE_UNSUPPORTED")
    if not math.isfinite(value):
        raise CurveValueQueryError("AXIS_VALUE_NONFINITE")
    return value


def _axis_pixel_from_value(axis: Mapping[str, Any], value: float) -> float:
    try:
        scale = str(axis["scale"])
        a, b = (float(x) for x in axis["transformed_value_from_pixel"])
        value = float(value)
    except Exception as exc:
        raise CurveValueQueryError("AXIS_MODEL_INVALID") from exc
    if not math.isfinite(value) or abs(a) < 1e-15:
        raise CurveValueQueryError("AXIS_QUERY_INVALID")
    if scale == "LINEAR":
        transformed = value
    elif scale == "LOG10":
        if value <= 0:
            raise CurveValueQueryError("LOG_AXIS_REQUIRES_POSITIVE_QUERY")
        transformed = math.log10(value)
    else:
        raise CurveValueQueryError("AXIS_SCALE_UNSUPPORTED")
    pixel = (transformed - b) / a
    if not math.isfinite(pixel):
        raise CurveValueQueryError("AXIS_PIXEL_NONFINITE")
    return pixel


def _binding_for_label(legend: Mapping[str, Any], label: str) -> Mapping[str, Any]:
    target = _norm_label(label)
    if not target:
        raise CurveValueQueryError("LABEL_REQUIRED")
    rows = [
        row for row in (legend.get("bindings") or [])
        if isinstance(row, Mapping) and _norm_label(row.get("label")) == target
    ]
    if len(rows) != 1:
        raise CurveValueQueryError(
            "LEGEND_LABEL_NOT_UNIQUELY_BOUND:" + str(len(rows))
        )
    color = rows[0].get("color_bucket")
    if not isinstance(color, Sequence) or isinstance(color, (str, bytes)) or len(color) != 3:
        raise CurveValueQueryError("LEGEND_COLOR_BUCKET_INVALID")
    return rows[0]


def _bracket(points: Sequence[Sequence[float]], target_x: float) -> tuple[list[float], list[float]]:
    clean = []
    for row in points:
        if not isinstance(row, Sequence) or len(row) != 2:
            raise CurveValueQueryError("POLYLINE_POINT_INVALID")
        x, y = float(row[0]), float(row[1])
        if not math.isfinite(x) or not math.isfinite(y):
            raise CurveValueQueryError("POLYLINE_POINT_NONFINITE")
        clean.append([x, y])
    clean.sort(key=lambda p: (p[0], p[1]))
    if len(clean) < 2:
        raise CurveValueQueryError("POLYLINE_POINTS_INSUFFICIENT")

    exact = [p for p in clean if abs(p[0] - target_x) <= 1e-9]
    if exact:
        ys = [p[1] for p in exact]
        if max(ys) - min(ys) > 2.0:
            raise CurveValueQueryError("VERTICAL_OR_OVERLAPPING_CURVE_AT_QUERY")
        p = [target_x, sum(ys) / len(ys)]
        return p, p

    left = [p for p in clean if p[0] < target_x]
    right = [p for p in clean if p[0] > target_x]
    if not left or not right:
        raise CurveValueQueryError("QUERY_NOT_BRACKETED_BY_CURVE")
    return max(left, key=lambda p: p[0]), min(right, key=lambda p: p[0])


def query_curve_value(
    scene: Mapping[str, Any],
    legend: Mapping[str, Any],
    *,
    label: str,
    x_value: float,
    max_interpolation_gap_fraction: float = 0.025,
) -> dict[str, Any]:
    if not isinstance(scene, Mapping):
        raise CurveValueQueryError("SCENE_INVALID")
    axes = scene.get("axes")
    if not isinstance(axes, Mapping) or "x" not in axes or "y" not in axes:
        raise CurveValueQueryError("CALIBRATED_XY_AXES_REQUIRED")
    plot_box = scene.get("plot_box")
    if not isinstance(plot_box, Sequence) or len(plot_box) != 4:
        raise CurveValueQueryError("PLOT_BOX_INVALID")
    left, top, right, bottom = (float(x) for x in plot_box)
    if right <= left or bottom <= top:
        raise CurveValueQueryError("PLOT_BOX_GEOMETRY_INVALID")

    binding = _binding_for_label(legend, label)
    color = tuple(int(x) for x in binding["color_bucket"])
    target_px = _axis_pixel_from_value(axes["x"], float(x_value))
    if target_px < left or target_px > right:
        raise CurveValueQueryError("QUERY_X_OUTSIDE_PLOT")

    max_gap_px = max(2.0, float(max_interpolation_gap_fraction) * (right - left))
    candidates = []
    for index, row in enumerate(scene.get("color_polylines") or []):
        if not isinstance(row, Mapping):
            continue
        if tuple(int(x) for x in (row.get("color_bucket") or [])) != color:
            continue
        try:
            p0, p1 = _bracket(row.get("points") or [], target_px)
        except CurveValueQueryError:
            continue
        gap = float(p1[0]) - float(p0[0])
        if gap > max_gap_px + 1e-9:
            continue
        if abs(gap) <= 1e-12:
            py = float(p0[1])
            ratio = 0.0
        else:
            ratio = (target_px - float(p0[0])) / gap
            py = float(p0[1]) + ratio * (float(p1[1]) - float(p0[1]))
        if py < top - 1 or py > bottom + 1:
            continue
        candidates.append({
            "polyline_index": index,
            "pixel_bracket": [p0, p1],
            "interpolation_gap_px": gap,
            "interpolation_ratio": ratio,
            "pixel_y": py,
            "column_count": int(row.get("column_count") or 0),
            "x_range": row.get("x_range"),
        })

    if len(candidates) != 1:
        raise CurveValueQueryError(
            "CURVE_NOT_UNIQUELY_QUERYABLE:" + str(len(candidates))
        )
    chosen = candidates[0]
    py = float(chosen["pixel_y"])
    y_value = _axis_value_from_pixel(axes["y"], py)
    y_minus = _axis_value_from_pixel(axes["y"], max(top, py - 1.0))
    y_plus = _axis_value_from_pixel(axes["y"], min(bottom, py + 1.0))
    one_pixel_resolution = abs(y_plus - y_minus) / 2.0

    return {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": "PASS__BOUNDED_CALIBRATED_CURVE_VALUE_QUERY",
        "pass": True,
        "label": str(binding["label"]),
        "color_bucket": list(color),
        "x_value": float(x_value),
        "value": y_value,
        "target_pixel_x": target_px,
        "interpolated_pixel_y": py,
        "estimated_one_pixel_value_resolution": one_pixel_resolution,
        "query_receipt": chosen,
        "axis_scales": {
            "x": str(axes["x"]["scale"]),
            "y": str(axes["y"]["scale"]),
        },
        "domain_semantic_authority": False,
        "benchmark_score_authority": False,
        "cognition_dependency_class": "MODEL_INDEPENDENT",
        "general_purpose_model_dependency_count": 0,
        "external_general_purpose_model_runtime_dependency_count": 0,
        "donor_general_purpose_model_runtime_dependency_count": 0,
        "incremental_spend_usd": 0,
        "hard_nonclaims": [
            "NO_DOMAIN_SEMANTIC_INTERPRETATION",
            "NO_OVERLAPPING_SAME_COLOR_MULTI_SERIES_AUTHORITY",
            "NO_UNBRACKETED_OR_LARGE_GAP_INTERPOLATION",
            "NO_CHARTOGRAPHY_SCORE_CREDIT",
        ],
    }


def run(args: dict[str, Any], root: Any) -> dict[str, Any]:
    base = pathlib.Path(root).resolve()
    src = (base / str(args.get("path") or "")).resolve()
    if src == base or base not in src.parents or not src.is_file():
        raise CurveValueQueryError("IMAGE_PATH_INVALID")

    ocr = positioned_ocr.run(
        {
            "path": str(src.relative_to(base)),
            "language": "eng",
            "psm_values": args.get("psm_values") or ["3", "6", "11"],
        },
        base,
    )
    scene0 = build_scene_graph(src)
    axis_binding = bind_axes_from_positioned_ocr(
        ocr,
        scene0["plot_box"],
        min_confidence=float(args.get("min_confidence", 35.0)),
    )
    x_ticks = [
        (float(r["pixel"]), float(r["value"]))
        for r in axis_binding["axes"].get("x", {}).get("selected_ticks", [])
    ]
    y_ticks = [
        (float(r["pixel"]), float(r["value"]))
        for r in axis_binding["axes"].get("y", {}).get("selected_ticks", [])
    ]
    if not x_ticks or not y_ticks:
        raise CurveValueQueryError("CALIBRATED_XY_AXES_REQUIRED")
    scene = build_scene_graph(src, x_ticks=x_ticks, y_ticks=y_ticks)

    with Image.open(src) as raw:
        legend = bind_legend_styles(
            raw,
            ocr,
            scene["plot_box"],
            min_confidence=float(args.get("legend_min_confidence", 45.0)),
        )

    out = query_curve_value(
        scene,
        legend,
        label=str(args.get("label") or ""),
        x_value=float(args["x_value"]),
        max_interpolation_gap_fraction=float(args.get("max_interpolation_gap_fraction", 0.025)),
    )
    return {
        **out,
        "source_path": str(src.relative_to(base)).replace("\\", "/"),
        "ocr_capability_id": ocr.get("capability_id"),
        "axis_binding_capability_id": axis_binding.get("capability_id"),
        "legend_binding_capability_id": legend.get("capability_id"),
        "scene_graph_capability_id": scene.get("capability_id"),
    }
