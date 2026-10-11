from __future__ import annotations

import math
import pathlib
import re
from typing import Any, Mapping

from PIL import Image

from canonical.runtime.bound_capabilities import image_ocr_tesseract_positioned as positioned_ocr
from canonical.runtime.bound_capabilities.chart_raster_scene_graph_v1 import (
    build_scene_graph,
    saturated_components,
)

CAPABILITY_ID = "chart.raster.legend_style_binding.v1"
SCHEMA = "PROJECT_BRAIN_CHART_RASTER_LEGEND_STYLE_BINDING_V1"


class LegendBindingError(ValueError):
    pass


_NUMERIC_ONLY = re.compile(r"^[\s]*[+-]?(?:\d[\d,]*)(?:\.\d+)?(?:[eE][+-]?\d+)?[%°]?[\s]*$")


def _box(raw: Mapping[str, Any]) -> tuple[float, float, float, float]:
    try:
        x0 = float(raw["x0"])
        y0 = float(raw["y0"])
        x1 = float(raw["x1_exclusive"])
        y1 = float(raw["y1_exclusive"])
    except Exception as exc:
        raise LegendBindingError("OCR_BOX_INVALID") from exc
    if not all(math.isfinite(v) for v in (x0, y0, x1, y1)) or x1 <= x0 or y1 <= y0:
        raise LegendBindingError("OCR_BOX_GEOMETRY_INVALID")
    return x0, y0, x1, y1


def _component_box(raw: Mapping[str, Any]) -> tuple[float, float, float, float]:
    try:
        x0, y0, x1, y1 = [float(x) for x in raw["bbox"]]
    except Exception as exc:
        raise LegendBindingError("COMPONENT_BOX_INVALID") from exc
    if x1 <= x0 or y1 <= y0:
        raise LegendBindingError("COMPONENT_BOX_GEOMETRY_INVALID")
    return x0, y0, x1, y1


def _confidence(item: Mapping[str, Any]) -> float:
    for key in ("confidence_min", "confidence", "confidence_mean"):
        if item.get(key) is None:
            continue
        try:
            x = float(item[key])
        except Exception:
            continue
        if math.isfinite(x):
            return x
    return -1.0


def _label_eligible(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    s = " ".join(text.split())
    if not s or _NUMERIC_ONLY.fullmatch(s):
        return False
    return any(ch.isalpha() for ch in s)


def _overlap_fraction(a0: float, a1: float, b0: float, b1: float) -> float:
    inter = max(0.0, min(a1, b1) - max(a0, b0))
    den = max(1e-9, min(a1 - a0, b1 - b0))
    return inter / den


def _iou(a: tuple[float,float,float,float], b: tuple[float,float,float,float]) -> float:
    x0=max(a[0],b[0]);y0=max(a[1],b[1]);x1=min(a[2],b[2]);y1=min(a[3],b[3])
    inter=max(0.0,x1-x0)*max(0.0,y1-y0)
    aa=max(0.0,a[2]-a[0])*max(0.0,a[3]-a[1])
    bb=max(0.0,b[2]-b[0])*max(0.0,b[3]-b[1])
    den=aa+bb-inter
    return inter/den if den>0 else 0.0


def _candidate_geometry(
    label_box: tuple[float,float,float,float],
    comp_box: tuple[float,float,float,float],
    image_size: tuple[int,int],
    *,
    max_gap_fraction: float,
    min_vertical_overlap: float,
) -> dict[str, Any] | None:
    lx0,ly0,lx1,ly1=label_box
    cx0,cy0,cx1,cy1=comp_box
    w,h=image_size
    cw,ch=cx1-cx0,cy1-cy0
    if cw > max(12.0,0.28*w) or ch > max(12.0,0.15*h):
        return None
    vo=_overlap_fraction(ly0,ly1,cy0,cy1)
    if vo < min_vertical_overlap:
        return None
    if cx1 <= lx0:
        gap=lx0-cx1;side="LEFT"
    elif cx0 >= lx1:
        gap=cx0-lx1;side="RIGHT"
    else:
        return None
    if gap > max(12.0,max_gap_fraction*w):
        return None
    lcy=(ly0+ly1)/2.0
    ccy=(cy0+cy1)/2.0
    score=gap+0.75*abs(lcy-ccy)
    return {"side":side,"gap_px":gap,"vertical_overlap":vo,"score":score}


def _data_evidence(
    color: tuple[int,int,int],
    candidate_box: tuple[float,float,float,float],
    plot_components: list[Mapping[str,Any]],
    polylines: list[Mapping[str,Any]],
    plot_box: tuple[int,int,int,int],
) -> list[dict[str, Any]]:
    out=[]
    pw=max(1,plot_box[2]-plot_box[0])
    for row in polylines:
        if tuple(row.get("color_bucket") or ()) != color:
            continue
        cols=int(row.get("column_count") or 0)
        if cols >= max(8,math.ceil(0.08*pw)):
            out.append({"kind":"PLOT_POLYLINE","column_count":cols,"x_range":row.get("x_range")})
    for row in plot_components:
        if tuple(row.get("color_bucket") or ()) != color:
            continue
        rb=_component_box(row)
        if _iou(candidate_box,rb) >= 0.70:
            continue
        out.append({"kind":"PLOT_COMPONENT","area":int(row.get("area") or 0),"bbox":list(row.get("bbox") or [])})
    return out


def bind_legend_styles(
    image: Image.Image,
    ocr: Mapping[str, Any],
    plot_box: list[int] | tuple[int,int,int,int],
    *,
    min_confidence: float = 45.0,
    max_gap_fraction: float = 0.12,
    min_vertical_overlap: float = 0.30,
    ambiguity_margin_px: float = 5.0,
) -> dict[str, Any]:
    im=image.convert("RGB")
    if not isinstance(ocr,Mapping) or not isinstance(ocr.get("text_items"),list):
        raise LegendBindingError("OCR_RESULT_INVALID")
    if not isinstance(plot_box,(list,tuple)) or len(plot_box)!=4:
        raise LegendBindingError("PLOT_BOX_INVALID")
    pb=tuple(int(x) for x in plot_box)
    if pb[2]<=pb[0] or pb[3]<=pb[1]:
        raise LegendBindingError("PLOT_BOX_GEOMETRY_INVALID")

    full=saturated_components(im,(0,0,im.width-1,im.height-1),min_area=4)
    plot=saturated_components(im,pb,min_area=4)
    from canonical.runtime.bound_capabilities.chart_raster_scene_graph_v1 import color_polylines
    lines=color_polylines(im,pb,min_columns=8)

    bindings=[]
    rejected=[]
    for item in ocr["text_items"]:
        if not isinstance(item,Mapping):
            continue
        text=" ".join(str(item.get("text") or "").split())
        conf=_confidence(item)
        sid=str(item.get("source_id") or "")
        if conf < min_confidence:
            rejected.append({"source_id":sid,"text":text,"reason":"LOW_OCR_CONFIDENCE"})
            continue
        if not _label_eligible(text):
            rejected.append({"source_id":sid,"text":text,"reason":"LABEL_NOT_ELIGIBLE"})
            continue
        lb=_box(item.get("box") or {})
        candidates=[]
        for comp in full:
            cb=_component_box(comp)
            geom=_candidate_geometry(lb,cb,(im.width,im.height),
                                     max_gap_fraction=max_gap_fraction,
                                     min_vertical_overlap=min_vertical_overlap)
            if geom is None:
                continue
            color=tuple(int(x) for x in comp["color_bucket"])
            evidence=_data_evidence(color,cb,plot,lines,pb)
            if not evidence:
                continue
            candidates.append({
                "color_bucket":list(color),
                "sample_bbox":[int(x) for x in comp["bbox"]],
                "sample_area":int(comp["area"]),
                "data_evidence":evidence,
                **geom,
            })
        candidates.sort(key=lambda x:(float(x["score"]),x["sample_bbox"],x["color_bucket"]))
        if not candidates:
            rejected.append({"source_id":sid,"text":text,"reason":"NO_STYLE_SAMPLE_WITH_PLOT_EVIDENCE"})
            continue
        if len(candidates)>=2 and abs(float(candidates[1]["score"])-float(candidates[0]["score"])) <= ambiguity_margin_px:
            rejected.append({
                "source_id":sid,"text":text,"reason":"AMBIGUOUS_STYLE_SAMPLE",
                "candidate_count":len(candidates),
                "best_score":candidates[0]["score"],
                "second_score":candidates[1]["score"],
            })
            continue
        best=candidates[0]
        bindings.append({
            "source_id":sid,
            "label":text,
            "label_box":[float(x) for x in lb],
            "ocr_confidence":conf,
            **best,
        })

    color_to_labels={}
    for b in bindings:
        key=tuple(b["color_bucket"])
        color_to_labels.setdefault(key,[]).append(b["label"])
    conflicts=[
        {"color_bucket":list(k),"labels":sorted(v)}
        for k,v in color_to_labels.items() if len(set(v))>1
    ]
    if conflicts:
        conflict_colors={tuple(x["color_bucket"]) for x in conflicts}
        kept=[]
        for b in bindings:
            if tuple(b["color_bucket"]) in conflict_colors:
                rejected.append({"source_id":b["source_id"],"text":b["label"],"reason":"COLOR_BOUND_TO_MULTIPLE_LABELS"})
            else:
                kept.append(b)
        bindings=kept

    return {
        "schema":SCHEMA,
        "capability_id":CAPABILITY_ID,
        "status":"PASS__BOUNDED_LEGEND_STYLE_BINDING" if bindings else "OPEN__NO_UNAMBIGUOUS_LEGEND_STYLE_BINDING",
        "pass":bool(bindings),
        "bindings":bindings,
        "binding_count":len(bindings),
        "rejected":rejected,
        "conflicts":conflicts,
        "plot_box":list(pb),
        "full_color_component_count":len(full),
        "plot_color_component_count":len(plot),
        "plot_polyline_count":len(lines),
        "semantic_authority":"LABEL_TO_COLOR_STYLE_ONLY",
        "domain_semantic_authority":False,
        "benchmark_score_authority":False,
        "cognition_dependency_class":"MODEL_INDEPENDENT",
        "general_purpose_model_dependency_count":0,
        "external_general_purpose_model_runtime_dependency_count":0,
        "donor_general_purpose_model_runtime_dependency_count":0,
        "incremental_spend_usd":0,
        "hard_nonclaims":[
            "NO_SERIES_VALUE_OR_DOMAIN_SEMANTIC_AUTHORITY",
            "NO_NUMERIC_ONLY_LEGEND_LABEL_SUPPORT",
            "NO_PATTERN_OR_DASH_STYLE_BINDING",
            "NO_ROTATED_LABEL_AUTHORITY",
            "NO_CHARTOGRAPHY_SCORE_CREDIT",
        ],
    }


def run(args: dict[str,Any], root: Any) -> dict[str,Any]:
    base=pathlib.Path(root).resolve()
    src=(base/str(args.get("path") or "")).resolve()
    if src==base or base not in src.parents or not src.is_file():
        raise LegendBindingError("IMAGE_PATH_INVALID")
    ocr=positioned_ocr.run({
        "path":str(src.relative_to(base)),
        "language":"eng",
        "psm_values":args.get("psm_values") or ["3","6","11"],
    },base)
    scene=build_scene_graph(src)
    with Image.open(src) as raw:
        out=bind_legend_styles(
            raw,ocr,scene["plot_box"],
            min_confidence=float(args.get("min_confidence",45.0)),
            max_gap_fraction=float(args.get("max_gap_fraction",0.12)),
            min_vertical_overlap=float(args.get("min_vertical_overlap",0.30)),
            ambiguity_margin_px=float(args.get("ambiguity_margin_px",5.0)),
        )
    return {
        **out,
        "source_path":str(src.relative_to(base)).replace("\\","/"),
        "ocr_capability_id":ocr.get("capability_id"),
        "scene_graph_capability_id":scene.get("capability_id"),
    }
