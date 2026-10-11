from __future__ import annotations
import math
import re
from typing import Any

CAPABILITY_ID="chart.axis_ticks.from_positioned_ocr.v1"
SCHEMA="PROJECT_BRAIN_CHART_AXIS_TICKS_FROM_POSITIONED_OCR_V1"

class AxisTickObservationError(ValueError):
    pass

_NUM=re.compile(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([kKMB]?)$")

def parse_axis_number(text: str) -> dict[str,Any] | None:
    raw=str(text or "").strip().replace("−","-").replace("–","-").replace(",","")
    if not raw:
        return None
    negative_parentheses=raw.startswith("(") and raw.endswith(")")
    if negative_parentheses:
        raw=raw[1:-1].strip()
    prefix=""
    if raw[:1] in {"$","€","£","¥"}:
        prefix=raw[0]; raw=raw[1:].strip()
    suffix_unit=""
    if raw.endswith("%"):
        suffix_unit="%"; raw=raw[:-1].strip()
    elif raw.endswith("°"):
        suffix_unit="°"; raw=raw[:-1].strip()
    m=_NUM.fullmatch(raw)
    if not m:
        return None
    value=float(m.group(1))
    if not math.isfinite(value):
        return None
    scale=m.group(2)
    if scale in {"k","K"}: value*=1_000.0
    elif scale=="M": value*=1_000_000.0
    elif scale=="B": value*=1_000_000_000.0
    if negative_parentheses:
        value=-value
    return {
        "value":value,
        "raw":str(text),
        "currency_prefix":prefix or None,
        "unit_suffix":suffix_unit or None,
        "magnitude_suffix":scale or None,
    }

def _box(word: dict[str,Any]) -> tuple[float,float,float,float]:
    box=word.get("box")
    if not isinstance(box,dict):
        raise AxisTickObservationError("WORD_BOX_MISSING")
    try:
        x0=float(box["x0"]); y0=float(box["y0"])
        x1=float(box["x1_exclusive"]); y1=float(box["y1_exclusive"])
    except Exception as exc:
        raise AxisTickObservationError("WORD_BOX_INVALID") from exc
    if not all(math.isfinite(v) for v in (x0,y0,x1,y1)) or x1<=x0 or y1<=y0:
        raise AxisTickObservationError("WORD_BOX_INVALID")
    return x0,y0,x1,y1

def _dedupe(rows: list[dict[str,Any]]) -> list[dict[str,Any]]:
    out=[]
    for row in sorted(rows,key=lambda r:(r["pixel"],-r["confidence"],r["raw"])):
        if out and abs(row["pixel"]-out[-1]["pixel"])<=2.0:
            if row["confidence"]>out[-1]["confidence"]:
                out[-1]=row
        else:
            out.append(row)
    return out

def extract_axis_ticks(word_items: list[dict[str,Any]], plot_box: list[float] | tuple[float,float,float,float]) -> dict[str,Any]:
    if not isinstance(word_items,list):
        raise AxisTickObservationError("WORD_ITEMS_NOT_LIST")
    if not isinstance(plot_box,(list,tuple)) or len(plot_box)!=4:
        raise AxisTickObservationError("PLOT_BOX_INVALID")
    left,top,right,bottom=[float(v) for v in plot_box]
    if not all(math.isfinite(v) for v in (left,top,right,bottom)) or right<=left or bottom<=top:
        raise AxisTickObservationError("PLOT_BOX_INVALID")
    width=right-left; height=bottom-top
    x_rows=[]; y_rows=[]
    for word in word_items:
        if not isinstance(word,dict):
            raise AxisTickObservationError("WORD_ITEM_INVALID")
        parsed=parse_axis_number(word.get("text",""))
        if parsed is None:
            continue
        x0,y0,x1,y1=_box(word)
        cx=(x0+x1)/2.0; cy=(y0+y1)/2.0
        try:
            conf=float(word.get("confidence",0.0))
        except Exception as exc:
            raise AxisTickObservationError("WORD_CONFIDENCE_INVALID") from exc
        if not math.isfinite(conf):
            raise AxisTickObservationError("WORD_CONFIDENCE_INVALID")
        common={**parsed,"confidence":conf,"box":[x0,y0,x1,y1]}
        if (
            left-0.05*width <= cx <= right+0.05*width
            and bottom-0.03*height <= cy <= bottom+0.25*height
        ):
            x_rows.append({**common,"pixel":cx})
        if (
            left-0.30*width <= cx <= left-1.0
            and top-0.05*height <= cy <= bottom+0.05*height
        ):
            y_rows.append({**common,"pixel":cy})
    x_rows=_dedupe(x_rows); y_rows=_dedupe(y_rows)
    return {
        "schema":SCHEMA,
        "status":"PASS__AXIS_TICK_OBSERVATIONS",
        "x_ticks":x_rows,
        "y_ticks":y_rows,
        "x_calibration_points":[[r["pixel"],r["value"]] for r in x_rows],
        "y_calibration_points":[[r["pixel"],r["value"]] for r in y_rows],
        "semantic_authority":False,
        "benchmark_score_authority":False,
        "cognition_dependency_class":"MODEL_INDEPENDENT",
        "general_purpose_model_dependency_count":0,
        "external_general_purpose_model_runtime_dependency_count":0,
        "incremental_spend_usd":0,
    }

def run(args: dict[str,Any], root: Any=None) -> dict[str,Any]:
    positioned=args.get("positioned_ocr")
    if isinstance(positioned,dict):
        words=positioned.get("word_items")
    else:
        words=args.get("word_items")
    out=extract_axis_ticks(words,args.get("plot_box"))
    return {**out,"pass":True}
