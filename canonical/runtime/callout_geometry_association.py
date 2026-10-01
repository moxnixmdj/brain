"""Deterministic association of a callout box to a uniquely nearest drawing primitive."""
from __future__ import annotations
import math
from typing import Any

SCHEMA="BRAIN_CALLOUT_GEOMETRY_ASSOCIATION_V1"

def _box_center(b):
    return ((b["x0"]+b["x1_exclusive"])/2.0,(b["y0"]+b["y1_exclusive"])/2.0)

def _point_segment_distance(px,py,x1,y1,x2,y2):
    dx=x2-x1; dy=y2-y1
    if dx==0 and dy==0:
        return math.hypot(px-x1,py-y1)
    t=((px-x1)*dx+(py-y1)*dy)/(dx*dx+dy*dy)
    t=max(0.0,min(1.0,t))
    qx=x1+t*dx; qy=y1+t*dy
    return math.hypot(px-qx,py-qy)

def associate_callout(callout_box: dict[str,Any], primitives: dict[str,Any], *, max_distance: float=80.0, min_margin: float=1.5) -> dict[str,Any]:
    if max_distance<=0 or min_margin<=1:
        raise ValueError("invalid association thresholds")
    cx,cy=_box_center(callout_box)
    rows=[]
    for i,line in enumerate(primitives.get("lines",[])):
        d=_point_segment_distance(cx,cy,line["x1"],line["y1"],line["x2"],line["y2"])
        rows.append((d,"line",i))
    for i,c in enumerate(primitives.get("circles",[])):
        d=abs(math.hypot(cx-c["cx"],cy-c["cy"])-c["radius"])
        rows.append((d,"circle",i))
    rows.sort()
    if not rows or rows[0][0]>max_distance:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"NO_NEARBY_PRIMITIVE"}
    if len(rows)>1 and rows[1][0] <= rows[0][0]*min_margin + 1e-9:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"AMBIGUOUS_ASSOCIATION","best_distance":rows[0][0],"second_distance":rows[1][0]}
    d,kind,index=rows[0]
    return {"schema":SCHEMA,"status":"ASSOCIATED","primitive_kind":kind,"primitive_index":index,"distance":d,"terminal_authority":False}
