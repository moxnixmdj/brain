from __future__ import annotations

import math
import pathlib
from typing import Any, Mapping, Sequence

from canonical.runtime.bound_capabilities import image_ocr_tesseract_positioned as positioned_ocr
from canonical.runtime.bound_capabilities.chart_positioned_ocr_axis_binding_v1 import bind_axes_from_positioned_ocr
from canonical.runtime.bound_capabilities.chart_raster_scene_graph_v1 import build_scene_graph
from canonical.runtime.bound_capabilities.chart_curve_value_query_v1 import (
    CurveValueQueryError,
    _axis_pixel_from_value,
    _axis_value_from_pixel,
    _bracket,
)

CAPABILITY_ID = "chart.raster.direct_curve_family_query.v1"
SCHEMA = "PROJECT_BRAIN_CHART_RASTER_DIRECT_CURVE_FAMILY_QUERY_V1"


class DirectCurveFamilyError(ValueError):
    pass


def _confidence(item: Mapping[str, Any]) -> float:
    for key in ("confidence_min", "confidence", "confidence_mean"):
        raw=item.get(key)
        if raw is None:
            continue
        try:
            v=float(raw)
        except Exception:
            continue
        if math.isfinite(v):
            return v
    return -1.0


def _box(item: Mapping[str, Any]) -> tuple[float,float,float,float]:
    raw=item.get("box")
    if not isinstance(raw,Mapping):
        raise DirectCurveFamilyError("OCR_BOX_INVALID")
    try:
        x0=float(raw["x0"]); y0=float(raw["y0"])
        x1=float(raw["x1_exclusive"]); y1=float(raw["y1_exclusive"])
    except Exception as exc:
        raise DirectCurveFamilyError("OCR_BOX_INVALID") from exc
    if not all(math.isfinite(v) for v in (x0,y0,x1,y1)) or x1<=x0 or y1<=y0:
        raise DirectCurveFamilyError("OCR_BOX_GEOMETRY_INVALID")
    return x0,y0,x1,y1


def _text_ok(raw: Any) -> bool:
    if not isinstance(raw,str):
        return False
    s=" ".join(raw.split())
    if not s or len(s)>80:
        return False
    return any(ch.isalnum() for ch in s)


def _point_box_distance(px: float, py: float, box: tuple[float,float,float,float]) -> float:
    x0,y0,x1,y1=box
    dx=0.0 if x0<=px<=x1 else min(abs(px-x0),abs(px-x1))
    dy=0.0 if y0<=py<=y1 else min(abs(py-y0),abs(py-y1))
    return math.hypot(dx,dy)


def bind_right_endpoint_curve_labels(
    scene: Mapping[str, Any],
    ocr: Mapping[str, Any],
    *,
    min_confidence: float = 45.0,
    max_endpoint_distance_fraction: float = 0.06,
    ambiguity_margin_px: float = 3.0,
    min_curve_columns: int = 8,
) -> dict[str, Any]:
    if not isinstance(scene,Mapping):
        raise DirectCurveFamilyError("SCENE_INVALID")
    pb=scene.get("plot_box")
    if not isinstance(pb,Sequence) or isinstance(pb,(str,bytes)) or len(pb)!=4:
        raise DirectCurveFamilyError("PLOT_BOX_INVALID")
    left,top,right,bottom=(float(v) for v in pb)
    if right<=left or bottom<=top:
        raise DirectCurveFamilyError("PLOT_BOX_GEOMETRY_INVALID")
    items=ocr.get("text_items") if isinstance(ocr,Mapping) else None
    if not isinstance(items,list):
        raise DirectCurveFamilyError("OCR_TEXT_ITEMS_INVALID")
    rows=scene.get("color_polylines")
    if not isinstance(rows,list):
        raise DirectCurveFamilyError("POLYLINES_INVALID")

    pw=right-left; ph=bottom-top
    max_dist=max(4.0,float(max_endpoint_distance_fraction)*math.hypot(pw,ph))
    # Direct right-end labels may sit just inside or just outside the plot.
    label_x_min=left+0.10*pw
    label_x_max=right+0.18*pw
    label_y_min=top-0.04*ph
    label_y_max=bottom+0.04*ph

    bindings=[]
    rejected=[]
    for item in items:
        if not isinstance(item,Mapping):
            continue
        text=" ".join(str(item.get("text") or "").split())
        sid=str(item.get("source_id") or "")
        conf=_confidence(item)
        if conf<min_confidence:
            rejected.append({"source_id":sid,"text":text,"reason":"LOW_OCR_CONFIDENCE"})
            continue
        if not _text_ok(text):
            rejected.append({"source_id":sid,"text":text,"reason":"LABEL_NOT_ELIGIBLE"})
            continue
        try:
            bx=_box(item)
        except DirectCurveFamilyError:
            rejected.append({"source_id":sid,"text":text,"reason":"OCR_BOX_INVALID"})
            continue
        cx=(bx[0]+bx[2])/2.0; cy=(bx[1]+bx[3])/2.0
        if not (label_x_min<=cx<=label_x_max and label_y_min<=cy<=label_y_max):
            continue

        candidates=[]
        for index,row in enumerate(rows):
            if not isinstance(row,Mapping):
                continue
            if int(row.get("column_count") or 0)<int(min_curve_columns):
                continue
            pts=row.get("points")
            if not isinstance(pts,list) or not pts:
                continue
            try:
                clean=[(float(p[0]),float(p[1])) for p in pts if isinstance(p,Sequence) and len(p)==2]
            except Exception:
                continue
            if not clean or any(not math.isfinite(x) or not math.isfinite(y) for x,y in clean):
                continue
            endpoint=max(clean,key=lambda p:(p[0],-abs(p[1]-cy)))
            ex,ey=endpoint
            # Right-end direct label evidence: text must be at/after the curve's
            # right endpoint up to a tiny overlap tolerance caused by raster/text antialiasing.
            if bx[2] < ex-2.0:
                continue
            dist=_point_box_distance(ex,ey,bx)
            if dist>max_dist:
                continue
            vertical_miss=0.0 if bx[1]<=ey<=bx[3] else min(abs(ey-bx[1]),abs(ey-bx[3]))
            if vertical_miss>max(3.0,0.025*ph):
                continue
            candidates.append({
                "polyline_index":index,
                "color_bucket":list(row.get("color_bucket") or []),
                "endpoint_pixel":[ex,ey],
                "endpoint_distance_px":dist,
                "vertical_miss_px":vertical_miss,
                "column_count":int(row.get("column_count") or 0),
                "x_range":row.get("x_range"),
            })

        candidates.sort(key=lambda r:(float(r["endpoint_distance_px"]),-int(r["column_count"]),r["polyline_index"]))
        if not candidates:
            rejected.append({"source_id":sid,"text":text,"reason":"NO_NEARBY_RIGHT_CURVE_ENDPOINT"})
            continue
        if len(candidates)>=2 and abs(float(candidates[1]["endpoint_distance_px"])-float(candidates[0]["endpoint_distance_px"]))<=float(ambiguity_margin_px):
            rejected.append({
                "source_id":sid,"text":text,"reason":"AMBIGUOUS_NEARBY_CURVE_ENDPOINT",
                "candidate_count":len(candidates)
            })
            continue
        bindings.append({
            "source_id":sid,
            "label":text,
            "label_box":[float(v) for v in bx],
            "ocr_confidence":conf,
            **candidates[0],
        })

    by_poly={}
    for b in bindings:
        by_poly.setdefault(int(b["polyline_index"]),[]).append(b)
    conflict_polys={k for k,v in by_poly.items() if len(v)>1}
    if conflict_polys:
        kept=[]
        for b in bindings:
            if int(b["polyline_index"]) in conflict_polys:
                rejected.append({"source_id":b["source_id"],"text":b["label"],"reason":"POLYLINE_BOUND_TO_MULTIPLE_LABELS"})
            else:
                kept.append(b)
        bindings=kept

    return {
        "schema":"PROJECT_BRAIN_CHART_RASTER_DIRECT_CURVE_LABEL_BINDING_V1",
        "status":"PASS__BOUNDED_RIGHT_ENDPOINT_CURVE_LABEL_BINDING" if bindings else "OPEN__NO_UNAMBIGUOUS_DIRECT_CURVE_LABELS",
        "pass":bool(bindings),
        "bindings":bindings,
        "binding_count":len(bindings),
        "rejected":rejected,
        "semantic_authority":"RIGHT_ENDPOINT_LABEL_TO_COLOR_POLYLINE_ONLY",
        "domain_semantic_authority":False,
        "benchmark_score_authority":False,
        "cognition_dependency_class":"MODEL_INDEPENDENT",
        "external_general_purpose_model_runtime_dependency_count":0,
        "donor_general_purpose_model_runtime_dependency_count":0,
        "incremental_spend_usd":0,
    }


def query_direct_curve_family(
    scene: Mapping[str, Any],
    direct_binding: Mapping[str, Any],
    *,
    x_value: float,
    target_y: float | None = None,
    max_interpolation_gap_fraction: float = 0.025,
    tie_tolerance_px: float = 1.5,
) -> dict[str, Any]:
    axes=scene.get("axes") if isinstance(scene,Mapping) else None
    if not isinstance(axes,Mapping) or "x" not in axes or "y" not in axes:
        raise DirectCurveFamilyError("CALIBRATED_XY_AXES_REQUIRED")
    pb=scene.get("plot_box")
    if not isinstance(pb,Sequence) or isinstance(pb,(str,bytes)) or len(pb)!=4:
        raise DirectCurveFamilyError("PLOT_BOX_INVALID")
    left,top,right,bottom=(float(v) for v in pb)
    rows=scene.get("color_polylines")
    if not isinstance(rows,list):
        raise DirectCurveFamilyError("POLYLINES_INVALID")
    bindings=direct_binding.get("bindings") if isinstance(direct_binding,Mapping) else None
    if not isinstance(bindings,list) or len(bindings)<2:
        raise DirectCurveFamilyError("AT_LEAST_TWO_DIRECTLY_LABELED_CURVES_REQUIRED")

    try:
        target_px=_axis_pixel_from_value(axes["x"],float(x_value))
    except CurveValueQueryError as exc:
        raise DirectCurveFamilyError(str(exc)) from exc
    if target_px<left or target_px>right:
        raise DirectCurveFamilyError("QUERY_X_OUTSIDE_PLOT")
    max_gap=max(2.0,float(max_interpolation_gap_fraction)*(right-left))

    values=[]
    seen_labels=set()
    seen_poly=set()
    for b in bindings:
        label=" ".join(str(b.get("label") or "").split())
        pi=int(b.get("polyline_index",-1))
        norm=label.casefold()
        if not label or norm in seen_labels or pi in seen_poly or pi<0 or pi>=len(rows):
            raise DirectCurveFamilyError("DIRECT_BINDING_NOT_ONE_TO_ONE")
        seen_labels.add(norm); seen_poly.add(pi)
        row=rows[pi]
        try:
            p0,p1=_bracket(row.get("points") or [],target_px)
        except CurveValueQueryError as exc:
            raise DirectCurveFamilyError("FAMILY_MEMBER_NOT_QUERYABLE:"+label+":"+str(exc)) from exc
        gap=float(p1[0])-float(p0[0])
        if gap>max_gap+1e-9:
            raise DirectCurveFamilyError("FAMILY_MEMBER_INTERPOLATION_GAP_TOO_LARGE:"+label)
        if abs(gap)<=1e-12:
            py=float(p0[1]); ratio=0.0
        else:
            ratio=(target_px-float(p0[0]))/gap
            py=float(p0[1])+ratio*(float(p1[1])-float(p0[1]))
        if py<top-1 or py>bottom+1:
            raise DirectCurveFamilyError("FAMILY_MEMBER_VALUE_OUTSIDE_PLOT:"+label)
        try:
            yv=_axis_value_from_pixel(axes["y"],py)
        except CurveValueQueryError as exc:
            raise DirectCurveFamilyError(str(exc)) from exc
        values.append({
            "label":label,"polyline_index":pi,"pixel_y":py,"value":yv,
            "pixel_bracket":[p0,p1],"interpolation_gap_px":gap,"interpolation_ratio":ratio
        })

    # Higher semantic y is smaller raster y for both verified linear/log y transforms.
    by_pixel=sorted(values,key=lambda r:(float(r["pixel_y"]),r["label"].casefold()))
    for a,b in zip(by_pixel,by_pixel[1:]):
        if abs(float(a["pixel_y"])-float(b["pixel_y"]))<=float(tie_tolerance_px):
            raise DirectCurveFamilyError("CURVE_FAMILY_RANK_TIE_OR_UNREADABLE")
    for rank,row in enumerate(by_pixel,1):
        row["rank_high_to_low"]=rank

    nearest=None
    if target_y is not None:
        try:
            target_py=_axis_pixel_from_value(axes["y"],float(target_y))
        except CurveValueQueryError as exc:
            raise DirectCurveFamilyError(str(exc)) from exc
        d=sorted(
            [{"label":r["label"],"pixel_distance":abs(float(r["pixel_y"])-target_py),"value":r["value"]} for r in values],
            key=lambda r:(r["pixel_distance"],r["label"].casefold())
        )
        if len(d)>=2 and abs(float(d[1]["pixel_distance"])-float(d[0]["pixel_distance"]))<=float(tie_tolerance_px):
            raise DirectCurveFamilyError("NEAREST_CURVE_TIE_OR_UNREADABLE")
        nearest=d[0]

    return {
        "schema":SCHEMA,
        "capability_id":CAPABILITY_ID,
        "status":"PASS__BOUNDED_DIRECT_CURVE_FAMILY_QUERY",
        "pass":True,
        "x_value":float(x_value),
        "target_y":None if target_y is None else float(target_y),
        "ranked_high_to_low":by_pixel,
        "nearest_to_target_y":nearest,
        "family_size":len(values),
        "domain_semantic_authority":False,
        "benchmark_score_authority":False,
        "cognition_dependency_class":"MODEL_INDEPENDENT",
        "external_general_purpose_model_runtime_dependency_count":0,
        "donor_general_purpose_model_runtime_dependency_count":0,
        "incremental_spend_usd":0,
        "hard_nonclaims":[
            "NO_PERCENTILE_OR_SURVIVAL_DOMAIN_SEMANTICS",
            "NO_LEFT_ENDPOINT_OR_ROTATED_LABEL_BINDING_AUTHORITY",
            "NO_BLACK_OR_GRAYSCALE_CURVE_FAMILY_AUTHORITY",
            "NO_TIED_OR_UNREADABLE_RANK_SELECTION",
            "NO_CHARTOGRAPHY_SCORE_CREDIT"
        ]
    }


def run(args: dict[str,Any], root: Any) -> dict[str,Any]:
    base=pathlib.Path(root).resolve()
    src=(base/str(args.get("path") or "")).resolve()
    if src==base or base not in src.parents or not src.is_file():
        raise DirectCurveFamilyError("IMAGE_PATH_INVALID")
    ocr=positioned_ocr.run({
        "path":str(src.relative_to(base)),
        "language":"eng",
        "psm_values":args.get("psm_values") or ["3","6","11"],
    },base)
    scene0=build_scene_graph(src)
    axis_binding=bind_axes_from_positioned_ocr(
        ocr,scene0["plot_box"],
        min_confidence=float(args.get("min_confidence",35.0))
    )
    x_ticks=[(float(r["pixel"]),float(r["value"])) for r in axis_binding["axes"].get("x",{}).get("selected_ticks",[])]
    y_ticks=[(float(r["pixel"]),float(r["value"])) for r in axis_binding["axes"].get("y",{}).get("selected_ticks",[])]
    if not x_ticks or not y_ticks:
        raise DirectCurveFamilyError("CALIBRATED_XY_AXES_REQUIRED")
    scene=build_scene_graph(src,x_ticks=x_ticks,y_ticks=y_ticks)
    binding=bind_right_endpoint_curve_labels(
        scene,ocr,
        min_confidence=float(args.get("direct_label_min_confidence",45.0)),
        max_endpoint_distance_fraction=float(args.get("max_endpoint_distance_fraction",0.06)),
        ambiguity_margin_px=float(args.get("ambiguity_margin_px",3.0))
    )
    out=query_direct_curve_family(
        scene,binding,
        x_value=float(args["x_value"]),
        target_y=None if args.get("target_y") is None else float(args["target_y"]),
        max_interpolation_gap_fraction=float(args.get("max_interpolation_gap_fraction",0.025)),
        tie_tolerance_px=float(args.get("tie_tolerance_px",1.5))
    )
    return {
        **out,
        "source_path":str(src.relative_to(base)).replace("\\","/"),
        "direct_binding":binding,
        "ocr_capability_id":ocr.get("capability_id"),
        "axis_binding_capability_id":axis_binding.get("capability_id"),
        "scene_graph_capability_id":scene.get("capability_id")
    }
