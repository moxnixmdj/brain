from __future__ import annotations
import itertools
import math
import re
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.bound_capabilities import image_ocr_tesseract_positioned as positioned_ocr
from canonical.runtime.bound_capabilities.chart_raster_scene_graph_v1 import (
    ChartSceneGraphError,
    build_scene_graph,
    calibrate_axis,
)

CAPABILITY_ID = "chart.raster.positioned_ocr_axis_binding.v1"
SCHEMA = "PROJECT_BRAIN_CHART_POSITIONED_OCR_AXIS_BINDING_V1"

_NUMERIC = re.compile(
    r"^[\s]*([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:[eE][+-]?\d+)?)[\s]*$"
)


class ChartAxisBindingError(ValueError):
    pass


def _finite_number(text: Any) -> float | None:
    if not isinstance(text, str):
        return None
    m = _NUMERIC.match(text)
    if not m:
        return None
    try:
        value = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _box_center(box: Mapping[str, Any]) -> tuple[float, float]:
    required = ("x0", "y0", "x1_exclusive", "y1_exclusive")
    if not isinstance(box, Mapping) or any(k not in box for k in required):
        raise ChartAxisBindingError("OCR_BOX_INVALID")
    try:
        x0, y0, x1, y1 = (float(box[k]) for k in required)
    except Exception as exc:
        raise ChartAxisBindingError("OCR_BOX_NONNUMERIC") from exc
    if not all(math.isfinite(v) for v in (x0, y0, x1, y1)) or x1 <= x0 or y1 <= y0:
        raise ChartAxisBindingError("OCR_BOX_GEOMETRY_INVALID")
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


def _confidence(item: Mapping[str, Any]) -> float:
    for key in ("confidence_min", "confidence", "confidence_mean"):
        raw = item.get(key)
        if raw is None:
            continue
        try:
            value = float(raw)
        except Exception:
            continue
        if math.isfinite(value):
            return value
    return -1.0


def numeric_tick_candidates(
    ocr: Mapping[str, Any],
    plot_box: list[int] | tuple[int, int, int, int],
    *,
    min_confidence: float = 35.0,
    axis_margin_fraction: float = 0.12,
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(ocr, Mapping):
        raise ChartAxisBindingError("OCR_RESULT_INVALID")
    items = ocr.get("text_items")
    if not isinstance(items, list):
        raise ChartAxisBindingError("OCR_TEXT_ITEMS_INVALID")
    if not isinstance(plot_box, (list, tuple)) or len(plot_box) != 4:
        raise ChartAxisBindingError("PLOT_BOX_INVALID")
    left, top, right, bottom = (float(x) for x in plot_box)
    if right <= left or bottom <= top:
        raise ChartAxisBindingError("PLOT_BOX_GEOMETRY_INVALID")
    w, h = right - left, bottom - top
    mx = max(8.0, axis_margin_fraction * w)
    my = max(8.0, axis_margin_fraction * h)

    out = {"x": [], "y": []}
    for item in items:
        if not isinstance(item, Mapping):
            continue
        value = _finite_number(item.get("text"))
        conf = _confidence(item)
        if value is None or conf < min_confidence:
            continue
        cx, cy = _box_center(item.get("box") or {})
        base = {
            "source_id": str(item.get("source_id") or ""),
            "text": str(item.get("text")),
            "value": value,
            "confidence": conf,
            "center": [cx, cy],
        }

        if left - mx <= cx <= right + mx and bottom + 1.0 <= cy <= bottom + my:
            out["x"].append({**base, "pixel": cx})

        if left - mx <= cx <= left - 1.0 and top - my <= cy <= bottom + my:
            out["y"].append({**base, "pixel": cy})

    for axis in ("x", "y"):
        out[axis].sort(key=lambda r: (float(r["pixel"]), -float(r["confidence"]), r["source_id"]))
    return out


def _dedupe_pixels(rows: list[dict[str, Any]], tolerance_px: float = 2.0) -> tuple[list[dict[str, Any]], list[str]]:
    kept: list[dict[str, Any]] = []
    rejected: list[str] = []
    for row in rows:
        if not kept or abs(float(row["pixel"]) - float(kept[-1]["pixel"])) > tolerance_px:
            kept.append(row)
            continue
        prior = kept[-1]
        if math.isclose(float(prior["value"]), float(row["value"]), rel_tol=1e-9, abs_tol=1e-12):
            better = row if float(row["confidence"]) > float(prior["confidence"]) else prior
            worse = prior if better is row else row
            kept[-1] = better
            rejected.append(str(worse["source_id"]))
        else:
            rejected.extend([str(prior["source_id"]), str(row["source_id"])])
            kept.pop()
    return kept, rejected


def _residuals(rows: list[dict[str, Any]], model: Mapping[str, Any]) -> list[float]:
    a, b = (float(x) for x in model["transformed_value_from_pixel"])
    transformed = []
    for row in rows:
        value = float(row["value"])
        if model["scale"] == "LOG10":
            if value <= 0:
                transformed.append(float("inf"))
                continue
            obs = math.log10(value)
        else:
            obs = value
        transformed.append(abs((a * float(row["pixel"]) + b) - obs))
    vals = [
        math.log10(float(r["value"])) if model["scale"] == "LOG10" else float(r["value"])
        for r in rows if model["scale"] != "LOG10" or float(r["value"]) > 0
    ]
    span = max(vals) - min(vals) if len(vals) >= 2 else 0.0
    denom = max(abs(span), 1e-12)
    return [x / denom for x in transformed]


def robust_axis_calibration(
    rows: list[dict[str, Any]],
    expected_direction: str,
    *,
    max_ticks: int = 20,
    inlier_normalized_residual: float = 0.035,
    min_inlier_fraction: float = 0.60,
) -> dict[str, Any]:
    rows, duplicate_rejections = _dedupe_pixels(rows)
    if len(rows) < 3:
        raise ChartAxisBindingError("AXIS_TICKS_INSUFFICIENT")

    if len(rows) > max_ticks:
        rows = sorted(rows, key=lambda r: (-float(r["confidence"]), float(r["pixel"]), r["source_id"]))[:max_ticks]
        rows.sort(key=lambda r: float(r["pixel"]))

    best = None
    n = len(rows)
    for idxs in itertools.combinations(range(n), 3):
        subset = [rows[i] for i in idxs]
        try:
            model = calibrate_axis(
                [(float(r["pixel"]), float(r["value"])) for r in subset],
                expected_direction,
            )
        except ChartSceneGraphError:
            continue
        residuals = _residuals(rows, model)
        inliers = [i for i, err in enumerate(residuals) if err <= inlier_normalized_residual]
        need = max(3, math.ceil(min_inlier_fraction * n))
        if len(inliers) < need:
            continue
        try:
            refit = calibrate_axis(
                [(float(rows[i]["pixel"]), float(rows[i]["value"])) for i in inliers],
                expected_direction,
            )
        except ChartSceneGraphError:
            continue
        refit_residuals = _residuals(rows, refit)
        refit_inliers = [i for i, err in enumerate(refit_residuals) if err <= inlier_normalized_residual]
        score = (
            -len(refit_inliers),
            float(refit["normalized_rmse"]),
            tuple(str(rows[i]["source_id"]) for i in refit_inliers),
        )
        if best is None or score < best[0]:
            best = (score, refit, refit_inliers, refit_residuals)

    if best is None:
        raise ChartAxisBindingError("AXIS_CALIBRATION_NO_ROBUST_CONSENSUS")

    _, model, inliers, residuals = best
    selected = [rows[i] for i in inliers]
    rejected = duplicate_rejections + [
        str(rows[i]["source_id"]) for i in range(len(rows)) if i not in set(inliers)
    ]
    return {
        **model,
        "selected_tick_count": len(selected),
        "candidate_tick_count": len(rows),
        "selected_ticks": selected,
        "rejected_source_ids": sorted(set(rejected)),
        "max_selected_normalized_residual": max(residuals[i] for i in inliers),
        "robust_consensus": True,
    }


def bind_axes_from_positioned_ocr(
    ocr: Mapping[str, Any],
    plot_box: list[int] | tuple[int, int, int, int],
    *,
    min_confidence: float = 35.0,
) -> dict[str, Any]:
    candidates = numeric_tick_candidates(ocr, plot_box, min_confidence=min_confidence)
    axes: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for axis, direction in (("x", "INCREASING"), ("y", "DECREASING")):
        try:
            axes[axis] = robust_axis_calibration(candidates[axis], direction)
        except (ChartAxisBindingError, ChartSceneGraphError) as exc:
            errors[axis] = str(exc)
    return {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": "PASS__POSITIONED_OCR_AXIS_BINDING" if axes else "OPEN__NO_ROBUST_AXIS_BINDING",
        "axes": axes,
        "axis_errors": errors,
        "candidate_counts": {k: len(v) for k, v in candidates.items()},
        "semantic_authority": False,
        "domain_semantic_authority": False,
        "benchmark_score_authority": False,
        "cognition_dependency_class": "MODEL_INDEPENDENT",
        "general_purpose_model_dependency_count": 0,
        "external_general_purpose_model_runtime_dependency_count": 0,
        "donor_general_purpose_model_runtime_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


def run(args: dict[str, Any], root: Any) -> dict[str, Any]:
    base = Path(root).resolve()
    src = (base / str(args.get("path") or "")).resolve()
    if src == base or base not in src.parents or not src.is_file():
        raise ChartAxisBindingError("IMAGE_PATH_INVALID")

    ocr = positioned_ocr.run(
        {
            "path": str(src.relative_to(base)),
            "language": "eng",
            "psm_values": args.get("psm_values") or ["3", "6", "11"],
        },
        base,
    )
    scene0 = build_scene_graph(src)
    binding = bind_axes_from_positioned_ocr(
        ocr,
        scene0["plot_box"],
        min_confidence=float(args.get("min_confidence", 35.0)),
    )
    x_ticks = [
        (float(r["pixel"]), float(r["value"]))
        for r in binding["axes"].get("x", {}).get("selected_ticks", [])
    ]
    y_ticks = [
        (float(r["pixel"]), float(r["value"]))
        for r in binding["axes"].get("y", {}).get("selected_ticks", [])
    ]
    scene = build_scene_graph(src, x_ticks=x_ticks or None, y_ticks=y_ticks or None)
    return {
        **binding,
        "pass": bool(binding["axes"]),
        "source_path": str(src.relative_to(base)).replace("\\", "/"),
        "ocr_capability_id": ocr.get("capability_id"),
        "scene_graph_capability_id": scene.get("capability_id"),
        "plot_box": scene["plot_box"],
        "scene_graph": scene,
        "hard_nonclaims": [
            "NO_CHART_DOMAIN_SEMANTIC_AUTHORITY",
            "NO_LEGEND_BINDING_AUTHORITY",
            "NO_GENERAL_CHARTOGRAPHY_SCORE_CREDIT",
            "NO_HELDOUT_COVERAGE_CLAIM",
        ],
    }
