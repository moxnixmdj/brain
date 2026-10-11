from __future__ import annotations

import math
import pathlib
from typing import Any, Mapping, Sequence

from PIL import Image

from canonical.runtime.bound_capabilities import image_ocr_tesseract_positioned as positioned_ocr
from canonical.runtime.bound_capabilities.chart_positioned_ocr_axis_binding_v1 import bind_axes_from_positioned_ocr
from canonical.runtime.bound_capabilities.chart_raster_scene_graph_v1 import build_scene_graph
from canonical.runtime.bound_capabilities.chart_legend_style_binding_v1 import bind_legend_styles
from canonical.runtime.bound_capabilities.chart_curve_value_query_v1 import (
    CurveValueQueryError,
    _axis_pixel_from_value,
    _axis_value_from_pixel,
    _binding_for_label,
)

CAPABILITY_ID = "chart.raster.curve_x_at_y_query.v1"
SCHEMA = "PROJECT_BRAIN_CHART_RASTER_CURVE_X_AT_Y_QUERY_V1"


class CurveXAtYQueryError(ValueError):
    pass


def _crossings(
    points: Sequence[Sequence[float]],
    target_y: float,
    *,
    max_gap_px: float,
    flat_tolerance_px: float,
) -> tuple[list[dict[str, Any]], bool]:
    clean=[]
    for row in points:
        if not isinstance(row,Sequence) or isinstance(row,(str,bytes)) or len(row)!=2:
            raise CurveXAtYQueryError("POLYLINE_POINT_INVALID")
        x,y=float(row[0]),float(row[1])
        if not math.isfinite(x) or not math.isfinite(y):
            raise CurveXAtYQueryError("POLYLINE_POINT_NONFINITE")
        clean.append([x,y])
    clean.sort(key=lambda p:(p[0],p[1]))
    if len(clean)<2:
        raise CurveXAtYQueryError("POLYLINE_POINTS_INSUFFICIENT")

    out=[]
    horizontal_overlap=False
    for p0,p1 in zip(clean,clean[1:]):
        x0,y0=p0; x1,y1=p1
        gap=x1-x0
        if gap<0 or gap>max_gap_px+1e-9:
            continue
        d0=y0-target_y
        d1=y1-target_y
        if abs(y1-y0)<=1e-12:
            if abs(d0)<=flat_tolerance_px and abs(d1)<=flat_tolerance_px and x1>x0:
                horizontal_overlap=True
            continue
        if d0==0.0:
            ratio=0.0
        elif d1==0.0:
            ratio=1.0
        elif d0*d1>0:
            continue
        else:
            ratio=(target_y-y0)/(y1-y0)
        if ratio<-1e-9 or ratio>1+1e-9:
            continue
        px=x0+ratio*(x1-x0)
        out.append({
            "pixel_x":px,
            "pixel_segment":[p0,p1],
            "segment_gap_px":gap,
            "interpolation_ratio":ratio,
        })

    out.sort(key=lambda r:r["pixel_x"])
    merged=[]
    for row in out:
        if not merged or abs(row["pixel_x"]-merged[-1]["pixel_x"])>1.25:
            merged.append(row)
        else:
            # Adjacent segments meeting at one exact vertex describe one crossing.
            prev=merged[-1]
            prev["pixel_x"]=(prev["pixel_x"]+row["pixel_x"])/2.0
            prev["merged_vertex_crossing_count"]=int(prev.get("merged_vertex_crossing_count",1))+1
    return merged,horizontal_overlap


def query_curve_x_at_y(
    scene: Mapping[str, Any],
    legend: Mapping[str, Any],
    *,
    label: str,
    y_value: float,
    max_segment_gap_fraction: float = 0.025,
    flat_tolerance_px: float = 0.75,
) -> dict[str, Any]:
    if not isinstance(scene,Mapping):
        raise CurveXAtYQueryError("SCENE_INVALID")
    axes=scene.get("axes")
    if not isinstance(axes,Mapping) or "x" not in axes or "y" not in axes:
        raise CurveXAtYQueryError("CALIBRATED_XY_AXES_REQUIRED")
    plot_box=scene.get("plot_box")
    if not isinstance(plot_box,Sequence) or isinstance(plot_box,(str,bytes)) or len(plot_box)!=4:
        raise CurveXAtYQueryError("PLOT_BOX_INVALID")
    left,top,right,bottom=(float(v) for v in plot_box)
    if right<=left or bottom<=top:
        raise CurveXAtYQueryError("PLOT_BOX_GEOMETRY_INVALID")

    try:
        binding=_binding_for_label(legend,label)
        target_py=_axis_pixel_from_value(axes["y"],float(y_value))
    except CurveValueQueryError as exc:
        raise CurveXAtYQueryError(str(exc)) from exc
    if target_py<top or target_py>bottom:
        raise CurveXAtYQueryError("QUERY_Y_OUTSIDE_PLOT")
    color=tuple(int(v) for v in binding["color_bucket"])
    max_gap_px=max(2.0,float(max_segment_gap_fraction)*(right-left))

    candidates=[]
    horizontal_overlap=False
    for index,row in enumerate(scene.get("color_polylines") or []):
        if not isinstance(row,Mapping):
            continue
        if tuple(int(v) for v in (row.get("color_bucket") or []))!=color:
            continue
        try:
            crossings,flat=_crossings(
                row.get("points") or [],
                target_py,
                max_gap_px=max_gap_px,
                flat_tolerance_px=float(flat_tolerance_px),
            )
        except CurveXAtYQueryError:
            continue
        horizontal_overlap=horizontal_overlap or flat
        for cross in crossings:
            px=float(cross["pixel_x"])
            if left-1<=px<=right+1:
                candidates.append({"polyline_index":index,**cross})

    candidates.sort(key=lambda r:(r["pixel_x"],r["polyline_index"]))

    if horizontal_overlap:
        raise CurveXAtYQueryError("CURVE_OVERLAPS_TARGET_Y_OVER_INTERVAL")
    # _crossings() already coalesces the two adjacent segments that meet at one
    # exact vertex within a single polyline. Never coalesce across polyline rows:
    # two rendered series remain semantically ambiguous even if they cross the
    # requested y at the same pixel.
    if len(candidates)!=1:
        raise CurveXAtYQueryError("CURVE_X_AT_Y_NOT_UNIQUE:"+str(len(candidates)))

    chosen=candidates[0]
    px=float(chosen["pixel_x"])
    try:
        x_value=_axis_value_from_pixel(axes["x"],px)
        x_minus=_axis_value_from_pixel(axes["x"],max(left,px-1.0))
        x_plus=_axis_value_from_pixel(axes["x"],min(right,px+1.0))
    except CurveValueQueryError as exc:
        raise CurveXAtYQueryError(str(exc)) from exc
    one_pixel_resolution=abs(x_plus-x_minus)/2.0

    return {
        "schema":SCHEMA,
        "capability_id":CAPABILITY_ID,
        "status":"PASS__BOUNDED_CALIBRATED_CURVE_X_AT_Y_QUERY",
        "pass":True,
        "label":str(binding["label"]),
        "color_bucket":list(color),
        "y_value":float(y_value),
        "value":x_value,
        "target_pixel_y":target_py,
        "interpolated_pixel_x":px,
        "estimated_one_pixel_value_resolution":one_pixel_resolution,
        "query_receipt":chosen,
        "axis_scales":{"x":str(axes["x"]["scale"]),"y":str(axes["y"]["scale"])},
        "domain_semantic_authority":False,
        "benchmark_score_authority":False,
        "cognition_dependency_class":"MODEL_INDEPENDENT",
        "general_purpose_model_dependency_count":0,
        "external_general_purpose_model_runtime_dependency_count":0,
        "donor_general_purpose_model_runtime_dependency_count":0,
        "incremental_spend_usd":0,
        "hard_nonclaims":[
            "NO_DOMAIN_SEMANTIC_INTERPRETATION",
            "NO_MULTIPLE_CROSSING_SELECTION_AUTHORITY",
            "NO_HORIZONTAL_TARGET_OVERLAP_SELECTION_AUTHORITY",
            "NO_SAME_COLOR_MULTI_SERIES_DISAMBIGUATION_AUTHORITY",
            "NO_CHARTOGRAPHY_SCORE_CREDIT",
        ],
    }


def run(args: dict[str,Any], root: Any) -> dict[str,Any]:
    base=pathlib.Path(root).resolve()
    src=(base/str(args.get("path") or "")).resolve()
    if src==base or base not in src.parents or not src.is_file():
        raise CurveXAtYQueryError("IMAGE_PATH_INVALID")

    ocr=positioned_ocr.run({
        "path":str(src.relative_to(base)),
        "language":"eng",
        "psm_values":args.get("psm_values") or ["3","6","11"],
    },base)
    scene0=build_scene_graph(src)
    axis_binding=bind_axes_from_positioned_ocr(
        ocr,scene0["plot_box"],
        min_confidence=float(args.get("min_confidence",35.0)),
    )
    x_ticks=[(float(r["pixel"]),float(r["value"])) for r in axis_binding["axes"].get("x",{}).get("selected_ticks",[])]
    y_ticks=[(float(r["pixel"]),float(r["value"])) for r in axis_binding["axes"].get("y",{}).get("selected_ticks",[])]
    if not x_ticks or not y_ticks:
        raise CurveXAtYQueryError("CALIBRATED_XY_AXES_REQUIRED")
    scene=build_scene_graph(src,x_ticks=x_ticks,y_ticks=y_ticks)
    with Image.open(src) as raw:
        legend=bind_legend_styles(
            raw,ocr,scene["plot_box"],
            min_confidence=float(args.get("legend_min_confidence",45.0)),
        )
    out=query_curve_x_at_y(
        scene,legend,
        label=str(args.get("label") or ""),
        y_value=float(args["y_value"]),
        max_segment_gap_fraction=float(args.get("max_segment_gap_fraction",0.025)),
        flat_tolerance_px=float(args.get("flat_tolerance_px",0.75)),
    )
    return {
        **out,
        "source_path":str(src.relative_to(base)).replace("\\","/"),
        "ocr_capability_id":ocr.get("capability_id"),
        "axis_binding_capability_id":axis_binding.get("capability_id"),
        "legend_binding_capability_id":legend.get("capability_id"),
        "scene_graph_capability_id":scene.get("capability_id"),
    }
