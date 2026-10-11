from __future__ import annotations

import math
import pathlib
from typing import Any, Mapping, Sequence

from PIL import Image

from canonical.runtime.bound_capabilities import image_ocr_tesseract_positioned as positioned_ocr
from canonical.runtime.bound_capabilities.chart_curve_value_query_v1 import (
    CurveValueQueryError,
    _axis_pixel_from_value,
    _axis_value_from_pixel,
    _binding_for_label,
)
from canonical.runtime.bound_capabilities.chart_legend_style_binding_v1 import bind_legend_styles
from canonical.runtime.bound_capabilities.chart_positioned_ocr_axis_binding_v1 import (
    bind_axes_from_positioned_ocr,
)
from canonical.runtime.bound_capabilities.chart_raster_scene_graph_v1 import build_scene_graph

CAPABILITY_ID = "chart.raster.curve_inverse_query.v1"
SCHEMA = "PROJECT_BRAIN_CHART_RASTER_CURVE_INVERSE_QUERY_V1"


class CurveInverseQueryError(ValueError):
    pass


def _clean_points(points: Sequence[Sequence[float]]) -> list[list[float]]:
    clean: list[list[float]] = []
    for row in points:
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)) or len(row) != 2:
            raise CurveInverseQueryError("POLYLINE_POINT_INVALID")
        try:
            x, y = float(row[0]), float(row[1])
        except Exception as exc:
            raise CurveInverseQueryError("POLYLINE_POINT_INVALID") from exc
        if not math.isfinite(x) or not math.isfinite(y):
            raise CurveInverseQueryError("POLYLINE_POINT_NONFINITE")
        clean.append([x, y])
    if len(clean) < 2:
        raise CurveInverseQueryError("POLYLINE_POINTS_INSUFFICIENT")
    return clean


def _segment_crossings(
    points: Sequence[Sequence[float]],
    target_y: float,
    *,
    max_gap_px: float,
) -> list[dict[str, Any]]:
    clean = _clean_points(points)
    crossings: list[dict[str, Any]] = []
    eps = 1e-9

    for i in range(len(clean) - 1):
        p0, p1 = clean[i], clean[i + 1]
        x0, y0 = p0
        x1, y1 = p1

        if abs(y1 - y0) <= eps:
            if abs(target_y - y0) <= eps and abs(x1 - x0) > eps:
                raise CurveInverseQueryError("HORIZONTAL_OR_OVERLAPPING_CURVE_AT_QUERY")
            continue

        lo, hi = sorted((y0, y1))
        if target_y < lo - eps or target_y > hi + eps:
            continue

        gap = abs(y1 - y0)
        if gap > max_gap_px + eps:
            continue

        ratio = (target_y - y0) / (y1 - y0)
        if ratio < -eps or ratio > 1.0 + eps:
            continue
        ratio = min(1.0, max(0.0, ratio))
        px = x0 + ratio * (x1 - x0)

        # A shared vertex can be found by both adjacent segments. That is one
        # crossing, not two. Deduplicate exact/near-exact pixel solutions only.
        if any(abs(px - row["pixel_x"]) <= 1e-7 for row in crossings):
            continue

        crossings.append(
            {
                "segment_index": i,
                "pixel_segment": [p0, p1],
                "vertical_interpolation_gap_px": gap,
                "interpolation_ratio": ratio,
                "pixel_x": px,
            }
        )

    return crossings


def query_curve_x_at_y(
    scene: Mapping[str, Any],
    legend: Mapping[str, Any],
    *,
    label: str,
    y_value: float,
    max_interpolation_gap_fraction: float = 0.025,
) -> dict[str, Any]:
    if not isinstance(scene, Mapping):
        raise CurveInverseQueryError("SCENE_INVALID")
    axes = scene.get("axes")
    if not isinstance(axes, Mapping) or "x" not in axes or "y" not in axes:
        raise CurveInverseQueryError("CALIBRATED_XY_AXES_REQUIRED")
    plot_box = scene.get("plot_box")
    if not isinstance(plot_box, Sequence) or isinstance(plot_box, (str, bytes)) or len(plot_box) != 4:
        raise CurveInverseQueryError("PLOT_BOX_INVALID")
    left, top, right, bottom = (float(x) for x in plot_box)
    if right <= left or bottom <= top:
        raise CurveInverseQueryError("PLOT_BOX_GEOMETRY_INVALID")

    try:
        binding = _binding_for_label(legend, label)
        target_py = _axis_pixel_from_value(axes["y"], float(y_value))
    except CurveValueQueryError as exc:
        raise CurveInverseQueryError(str(exc)) from exc

    color = tuple(int(x) for x in binding["color_bucket"])
    if target_py < top or target_py > bottom:
        raise CurveInverseQueryError("QUERY_Y_OUTSIDE_PLOT")

    max_gap_px = max(2.0, float(max_interpolation_gap_fraction) * (bottom - top))
    candidates: list[dict[str, Any]] = []
    for polyline_index, row in enumerate(scene.get("color_polylines") or []):
        if not isinstance(row, Mapping):
            continue
        if tuple(int(x) for x in (row.get("color_bucket") or [])) != color:
            continue
        try:
            crossings = _segment_crossings(
                row.get("points") or [],
                target_py,
                max_gap_px=max_gap_px,
            )
        except CurveInverseQueryError as exc:
            if str(exc) == "HORIZONTAL_OR_OVERLAPPING_CURVE_AT_QUERY":
                raise
            continue
        for crossing in crossings:
            px = float(crossing["pixel_x"])
            if px < left - 1.0 or px > right + 1.0:
                continue
            candidates.append(
                {
                    "polyline_index": polyline_index,
                    "pixel_x": px,
                    "pixel_y": target_py,
                    "segment_index": crossing["segment_index"],
                    "pixel_segment": crossing["pixel_segment"],
                    "vertical_interpolation_gap_px": crossing["vertical_interpolation_gap_px"],
                    "interpolation_ratio": crossing["interpolation_ratio"],
                    "column_count": int(row.get("column_count") or 0),
                    "x_range": row.get("x_range"),
                }
            )

    if len(candidates) != 1:
        raise CurveInverseQueryError(
            "CURVE_NOT_UNIQUELY_INVERTIBLE_AT_QUERY:" + str(len(candidates))
        )

    chosen = candidates[0]
    px = float(chosen["pixel_x"])
    try:
        x_value = _axis_value_from_pixel(axes["x"], px)
        x_minus = _axis_value_from_pixel(axes["x"], max(left, px - 1.0))
        x_plus = _axis_value_from_pixel(axes["x"], min(right, px + 1.0))
    except CurveValueQueryError as exc:
        raise CurveInverseQueryError(str(exc)) from exc
    one_pixel_resolution = abs(x_plus - x_minus) / 2.0

    return {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": "PASS__BOUNDED_CALIBRATED_CURVE_INVERSE_QUERY",
        "pass": True,
        "label": str(binding["label"]),
        "color_bucket": list(color),
        "y_value": float(y_value),
        "value": x_value,
        "target_pixel_y": target_py,
        "interpolated_pixel_x": px,
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
            "NO_MULTIPLE_CROSSING_CURVE_AUTHORITY",
            "NO_HORIZONTAL_PLATEAU_INVERSION",
            "NO_UNBRACKETED_OR_LARGE_GAP_INTERPOLATION",
            "NO_CHARTOGRAPHY_SCORE_CREDIT",
        ],
    }


def run(args: dict[str, Any], root: Any) -> dict[str, Any]:
    base = pathlib.Path(root).resolve()
    src = (base / str(args.get("path") or "")).resolve()
    if src == base or base not in src.parents or not src.is_file():
        raise CurveInverseQueryError("IMAGE_PATH_INVALID")

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
        raise CurveInverseQueryError("CALIBRATED_XY_AXES_REQUIRED")
    scene = build_scene_graph(src, x_ticks=x_ticks, y_ticks=y_ticks)

    with Image.open(src) as raw:
        legend = bind_legend_styles(
            raw,
            ocr,
            scene["plot_box"],
            min_confidence=float(args.get("legend_min_confidence", 45.0)),
        )

    out = query_curve_x_at_y(
        scene,
        legend,
        label=str(args.get("label") or ""),
        y_value=float(args["y_value"]),
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
