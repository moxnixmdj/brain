from __future__ import annotations

import math
import pathlib
import re
from typing import Any, Mapping, Sequence

from canonical.runtime.bound_capabilities import image_ocr_tesseract_positioned as positioned_ocr
from canonical.runtime.bound_capabilities.chart_positioned_ocr_axis_binding_v1 import (
    bind_axes_from_positioned_ocr,
)
from canonical.runtime.bound_capabilities.chart_raster_scene_graph_v1 import build_scene_graph

CAPABILITY_ID = "chart.raster.direct_curve_label_family_rank.v1"
SCHEMA = "PROJECT_BRAIN_CHART_DIRECT_CURVE_LABEL_FAMILY_RANK_V1"

_NUMERIC_ONLY = re.compile(
    r"^[\s]*[+-]?(?:\d[\d,]*)(?:\.\d+)?(?:[eE][+-]?\d+)?[%°]?[\s]*$"
)


class DirectCurveLabelError(ValueError):
    pass


def _norm_label(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _label_eligible(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    s = " ".join(text.split())
    return bool(s) and not _NUMERIC_ONLY.fullmatch(s) and any(ch.isalpha() for ch in s)


def _confidence(item: Mapping[str, Any]) -> float:
    for key in ("confidence_min", "confidence", "confidence_mean"):
        if item.get(key) is None:
            continue
        try:
            value = float(item[key])
        except Exception:
            continue
        if math.isfinite(value):
            return value
    return -1.0


def _ocr_box(item: Mapping[str, Any]) -> tuple[float, float, float, float]:
    raw = item.get("box")
    if not isinstance(raw, Mapping):
        raise DirectCurveLabelError("OCR_BOX_INVALID")
    try:
        x0 = float(raw["x0"])
        y0 = float(raw["y0"])
        x1 = float(raw["x1_exclusive"])
        y1 = float(raw["y1_exclusive"])
    except Exception as exc:
        raise DirectCurveLabelError("OCR_BOX_INVALID") from exc
    if not all(math.isfinite(v) for v in (x0, y0, x1, y1)) or x1 <= x0 or y1 <= y0:
        raise DirectCurveLabelError("OCR_BOX_GEOMETRY_INVALID")
    return x0, y0, x1, y1


def _point_box_distance(
    point: Sequence[float], box: tuple[float, float, float, float]
) -> float:
    if not isinstance(point, Sequence) or len(point) != 2:
        raise DirectCurveLabelError("POLYLINE_POINT_INVALID")
    x, y = float(point[0]), float(point[1])
    if not math.isfinite(x) or not math.isfinite(y):
        raise DirectCurveLabelError("POLYLINE_POINT_NONFINITE")
    x0, y0, x1, y1 = box
    dx = x0 - x if x < x0 else x - x1 if x > x1 else 0.0
    dy = y0 - y if y < y0 else y - y1 if y > y1 else 0.0
    return math.hypot(dx, dy)


def _polyline_points(row: Mapping[str, Any]) -> list[list[float]]:
    raw = row.get("points")
    if not isinstance(raw, list) or len(raw) < 2:
        raise DirectCurveLabelError("POLYLINE_POINTS_INSUFFICIENT")
    pts: list[list[float]] = []
    for point in raw:
        if not isinstance(point, Sequence) or len(point) != 2:
            raise DirectCurveLabelError("POLYLINE_POINT_INVALID")
        x, y = float(point[0]), float(point[1])
        if not math.isfinite(x) or not math.isfinite(y):
            raise DirectCurveLabelError("POLYLINE_POINT_NONFINITE")
        pts.append([x, y])
    pts.sort(key=lambda p: (p[0], p[1]))
    return pts


def bind_direct_curve_labels(
    scene: Mapping[str, Any],
    ocr: Mapping[str, Any],
    *,
    min_confidence: float = 45.0,
    max_endpoint_gap_fraction: float = 0.08,
    ambiguity_margin_px: float = 5.0,
) -> dict[str, Any]:
    if not isinstance(scene, Mapping) or not isinstance(ocr, Mapping):
        raise DirectCurveLabelError("INPUT_INVALID")
    plot_box = scene.get("plot_box")
    if not isinstance(plot_box, Sequence) or len(plot_box) != 4:
        raise DirectCurveLabelError("PLOT_BOX_INVALID")
    left, top, right, bottom = (float(v) for v in plot_box)
    if right <= left or bottom <= top:
        raise DirectCurveLabelError("PLOT_BOX_GEOMETRY_INVALID")

    polylines = scene.get("color_polylines")
    if not isinstance(polylines, list) or not polylines:
        raise DirectCurveLabelError("COLOR_POLYLINES_REQUIRED")

    diag = math.hypot(right - left, bottom - top)
    max_gap = max(2.0, float(max_endpoint_gap_fraction) * diag)
    margin = max(0.0, float(ambiguity_margin_px))

    prelim: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_labels: set[str] = set()

    for item in ocr.get("text_items") or []:
        if not isinstance(item, Mapping):
            continue
        text = " ".join(str(item.get("text") or "").split())
        label_key = _norm_label(text)
        source_id = str(item.get("source_id") or "")
        if not _label_eligible(text):
            if text:
                rejected.append({"source_id": source_id, "label": text, "reason": "LABEL_NOT_ELIGIBLE"})
            continue
        if _confidence(item) < float(min_confidence):
            rejected.append({"source_id": source_id, "label": text, "reason": "LOW_OCR_CONFIDENCE"})
            continue
        try:
            box = _ocr_box(item)
        except DirectCurveLabelError as exc:
            rejected.append({"source_id": source_id, "label": text, "reason": str(exc)})
            continue

        # Direct labels may sit just outside a plot edge, but not arbitrarily far.
        bx0, by0, bx1, by1 = box
        expanded = max_gap
        if bx1 < left - expanded or bx0 > right + expanded or by1 < top - expanded or by0 > bottom + expanded:
            rejected.append({"source_id": source_id, "label": text, "reason": "LABEL_OUTSIDE_DIRECT_BINDING_REGION"})
            continue
        if not label_key or label_key in seen_labels:
            rejected.append({"source_id": source_id, "label": text, "reason": "DUPLICATE_NORMALIZED_LABEL"})
            continue
        seen_labels.add(label_key)

        candidates: list[dict[str, Any]] = []
        for idx, row in enumerate(polylines):
            if not isinstance(row, Mapping):
                continue
            try:
                pts = _polyline_points(row)
            except DirectCurveLabelError:
                continue
            endpoints = (("START", pts[0]), ("END", pts[-1]))
            for side, point in endpoints:
                distance = _point_box_distance(point, box)
                if distance <= max_gap:
                    candidates.append({
                        "polyline_index": idx,
                        "endpoint_side": side,
                        "endpoint_pixel": point,
                        "distance_px": distance,
                        "color_bucket": list(row.get("color_bucket") or []),
                    })

        candidates.sort(key=lambda x: (float(x["distance_px"]), int(x["polyline_index"]), str(x["endpoint_side"])))
        if not candidates:
            rejected.append({"source_id": source_id, "label": text, "reason": "NO_NEARBY_CURVE_ENDPOINT"})
            continue
        best = candidates[0]
        second_distinct = next(
            (
                c for c in candidates[1:]
                if int(c["polyline_index"]) != int(best["polyline_index"])
            ),
            None,
        )
        if second_distinct is not None and float(second_distinct["distance_px"]) - float(best["distance_px"]) <= margin:
            rejected.append({
                "source_id": source_id,
                "label": text,
                "reason": "AMBIGUOUS_NEARBY_CURVE_ENDPOINTS",
                "candidate_count": len(candidates),
            })
            continue
        prelim.append({
            "source_id": source_id,
            "label": text,
            "normalized_label": label_key,
            **best,
        })

    # One direct text label per curve in this bounded v1. Multiple labels on the
    # same curve are left unresolved rather than silently choosing one.
    by_polyline: dict[int, list[dict[str, Any]]] = {}
    for row in prelim:
        by_polyline.setdefault(int(row["polyline_index"]), []).append(row)

    bindings: list[dict[str, Any]] = []
    for idx, rows in by_polyline.items():
        if len(rows) == 1:
            bindings.append(rows[0])
            continue
        for row in rows:
            rejected.append({
                "source_id": row["source_id"],
                "label": row["label"],
                "reason": "MULTIPLE_DIRECT_LABELS_FOR_ONE_CURVE",
                "polyline_index": idx,
            })

    bindings.sort(key=lambda x: (_norm_label(x["label"]), int(x["polyline_index"])))
    return {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": "PASS__BOUNDED_DIRECT_CURVE_LABEL_BINDING" if bindings else "OPEN__NO_UNAMBIGUOUS_DIRECT_CURVE_LABEL_BINDINGS",
        "pass": bool(bindings),
        "bindings": bindings,
        "rejected": rejected,
        "binding_count": len(bindings),
        "domain_semantic_authority": False,
        "benchmark_score_authority": False,
        "cognition_dependency_class": "MODEL_INDEPENDENT",
        "general_purpose_model_dependency_count": 0,
        "external_general_purpose_model_runtime_dependency_count": 0,
        "donor_general_purpose_model_runtime_dependency_count": 0,
        "incremental_spend_usd": 0,
        "hard_nonclaims": [
            "ONLY_ENDPOINT_ADJACENT_DIRECT_LABELS",
            "NO_ARBITRARY_INLINE_CONTOUR_LABEL_AUTHORITY",
            "NO_SAME_CURVE_MULTI_LABEL_RESOLUTION",
            "NO_DOMAIN_SEMANTIC_INTERPRETATION",
            "NO_CHARTOGRAPHY_SCORE_CREDIT",
        ],
    }


def _axis_pixel_from_value(axis: Mapping[str, Any], value: float) -> float:
    try:
        scale = str(axis["scale"])
        a, b = (float(x) for x in axis["transformed_value_from_pixel"])
        value = float(value)
    except Exception as exc:
        raise DirectCurveLabelError("AXIS_MODEL_INVALID") from exc
    if not math.isfinite(value) or abs(a) < 1e-15:
        raise DirectCurveLabelError("AXIS_QUERY_INVALID")
    if scale == "LINEAR":
        transformed = value
    elif scale == "LOG10":
        if value <= 0:
            raise DirectCurveLabelError("LOG_AXIS_REQUIRES_POSITIVE_QUERY")
        transformed = math.log10(value)
    else:
        raise DirectCurveLabelError("AXIS_SCALE_UNSUPPORTED")
    pixel = (transformed - b) / a
    if not math.isfinite(pixel):
        raise DirectCurveLabelError("AXIS_PIXEL_NONFINITE")
    return pixel


def _axis_value_from_pixel(axis: Mapping[str, Any], pixel: float) -> float:
    try:
        scale = str(axis["scale"])
        a, b = (float(x) for x in axis["transformed_value_from_pixel"])
    except Exception as exc:
        raise DirectCurveLabelError("AXIS_MODEL_INVALID") from exc
    transformed = a * float(pixel) + b
    if scale == "LINEAR":
        value = transformed
    elif scale == "LOG10":
        value = 10.0 ** transformed
    else:
        raise DirectCurveLabelError("AXIS_SCALE_UNSUPPORTED")
    if not math.isfinite(value):
        raise DirectCurveLabelError("AXIS_VALUE_NONFINITE")
    return value


def _interpolate_polyline_y(
    row: Mapping[str, Any],
    target_x: float,
    *,
    max_gap_px: float,
) -> float:
    pts = _polyline_points(row)
    exact = [p for p in pts if abs(p[0] - target_x) <= 1e-9]
    if exact:
        ys = [p[1] for p in exact]
        if max(ys) - min(ys) > 2.0:
            raise DirectCurveLabelError("VERTICAL_OR_OVERLAPPING_CURVE_AT_QUERY")
        return sum(ys) / len(ys)
    left = [p for p in pts if p[0] < target_x]
    right = [p for p in pts if p[0] > target_x]
    if not left or not right:
        raise DirectCurveLabelError("QUERY_NOT_BRACKETED_BY_CURVE")
    p0 = max(left, key=lambda p: p[0])
    p1 = min(right, key=lambda p: p[0])
    gap = p1[0] - p0[0]
    if gap <= 0 or gap > max_gap_px + 1e-9:
        raise DirectCurveLabelError("CURVE_INTERPOLATION_GAP_TOO_LARGE")
    ratio = (target_x - p0[0]) / gap
    return p0[1] + ratio * (p1[1] - p0[1])


def rank_direct_labeled_curve_family(
    scene: Mapping[str, Any],
    binding_result: Mapping[str, Any],
    *,
    x_value: float,
    nearest_y_value: float | None = None,
    max_interpolation_gap_fraction: float = 0.025,
    nearest_tie_tolerance: float = 1e-12,
) -> dict[str, Any]:
    if not isinstance(scene, Mapping) or not isinstance(binding_result, Mapping):
        raise DirectCurveLabelError("INPUT_INVALID")
    bindings = binding_result.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        raise DirectCurveLabelError("DIRECT_LABEL_BINDINGS_REQUIRED")
    axes = scene.get("axes")
    if not isinstance(axes, Mapping) or "x" not in axes or "y" not in axes:
        raise DirectCurveLabelError("CALIBRATED_XY_AXES_REQUIRED")
    plot_box = scene.get("plot_box")
    if not isinstance(plot_box, Sequence) or len(plot_box) != 4:
        raise DirectCurveLabelError("PLOT_BOX_INVALID")
    left, top, right, bottom = (float(v) for v in plot_box)
    target_px = _axis_pixel_from_value(axes["x"], float(x_value))
    if target_px < left or target_px > right:
        raise DirectCurveLabelError("QUERY_X_OUTSIDE_PLOT")
    max_gap_px = max(2.0, float(max_interpolation_gap_fraction) * (right - left))

    polylines = scene.get("color_polylines")
    if not isinstance(polylines, list):
        raise DirectCurveLabelError("COLOR_POLYLINES_REQUIRED")

    values: list[dict[str, Any]] = []
    used: set[int] = set()
    for binding in bindings:
        if not isinstance(binding, Mapping):
            raise DirectCurveLabelError("DIRECT_LABEL_BINDING_INVALID")
        idx = int(binding.get("polyline_index", -1))
        if idx < 0 or idx >= len(polylines) or idx in used:
            raise DirectCurveLabelError("DIRECT_LABEL_POLYLINE_BINDING_INVALID")
        used.add(idx)
        py = _interpolate_polyline_y(
            polylines[idx],
            target_px,
            max_gap_px=max_gap_px,
        )
        if py < top - 1 or py > bottom + 1:
            raise DirectCurveLabelError("CURVE_VALUE_OUTSIDE_PLOT")
        value = _axis_value_from_pixel(axes["y"], py)
        values.append({
            "label": str(binding.get("label") or ""),
            "polyline_index": idx,
            "value": value,
            "pixel_y": py,
        })

    values.sort(key=lambda row: (-float(row["value"]), _norm_label(row["label"])))
    for rank, row in enumerate(values, start=1):
        row["rank_high_to_low"] = rank

    nearest = None
    if nearest_y_value is not None:
        q = float(nearest_y_value)
        if not math.isfinite(q):
            raise DirectCurveLabelError("NEAREST_Y_QUERY_INVALID")
        nearest_rows = sorted(
            (
                {
                    **row,
                    "absolute_value_distance": abs(float(row["value"]) - q),
                }
                for row in values
            ),
            key=lambda row: (float(row["absolute_value_distance"]), _norm_label(row["label"])),
        )
        if len(nearest_rows) > 1 and abs(
            float(nearest_rows[1]["absolute_value_distance"])
            - float(nearest_rows[0]["absolute_value_distance"])
        ) <= float(nearest_tie_tolerance):
            raise DirectCurveLabelError("NEAREST_CURVE_TIE")
        nearest = nearest_rows[0]

    return {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": "PASS__BOUNDED_DIRECT_LABELED_CURVE_FAMILY_RANK",
        "pass": True,
        "x_value": float(x_value),
        "ranked_curves": values,
        "nearest_query_y_value": nearest_y_value,
        "nearest_curve": nearest,
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
    }


def run(args: dict[str, Any], root: Any) -> dict[str, Any]:
    base = pathlib.Path(root).resolve()
    src = (base / str(args.get("path") or "")).resolve()
    if src == base or base not in src.parents or not src.is_file():
        raise DirectCurveLabelError("IMAGE_PATH_INVALID")

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
        min_confidence=float(args.get("axis_min_confidence", 35.0)),
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
        raise DirectCurveLabelError("CALIBRATED_XY_AXES_REQUIRED")
    scene = build_scene_graph(src, x_ticks=x_ticks, y_ticks=y_ticks)

    bound = bind_direct_curve_labels(
        scene,
        ocr,
        min_confidence=float(args.get("label_min_confidence", 45.0)),
        max_endpoint_gap_fraction=float(args.get("max_endpoint_gap_fraction", 0.08)),
        ambiguity_margin_px=float(args.get("ambiguity_margin_px", 5.0)),
    )
    if args.get("x_value") is None:
        return {
            **bound,
            "source_path": str(src.relative_to(base)).replace("\\", "/"),
            "ocr_capability_id": ocr.get("capability_id"),
            "axis_binding_capability_id": axis_binding.get("capability_id"),
            "scene_graph_capability_id": scene.get("capability_id"),
        }

    ranked = rank_direct_labeled_curve_family(
        scene,
        bound,
        x_value=float(args["x_value"]),
        nearest_y_value=(
            None if args.get("nearest_y_value") is None
            else float(args["nearest_y_value"])
        ),
        max_interpolation_gap_fraction=float(
            args.get("max_interpolation_gap_fraction", 0.025)
        ),
    )
    return {
        **ranked,
        "direct_label_binding": bound,
        "source_path": str(src.relative_to(base)).replace("\\", "/"),
        "ocr_capability_id": ocr.get("capability_id"),
        "axis_binding_capability_id": axis_binding.get("capability_id"),
        "scene_graph_capability_id": scene.get("capability_id"),
    }
