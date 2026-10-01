"""Assign orthographic view identity under an explicitly declared projection convention."""
from __future__ import annotations
from typing import Any

SCHEMA="BRAIN_ORTHOGRAPHIC_VIEW_IDENTITY_V1"

def _center(r: dict[str, Any]) -> tuple[float,float]:
    return ((r["x0"]+r["x1_exclusive"])/2.0,(r["y0"]+r["y1_exclusive"])/2.0)

def assign_three_view_identity(regions: list[dict[str, Any]], *, convention: str) -> dict[str, Any]:
    if convention not in {"FIRST_ANGLE","THIRD_ANGLE"}:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"CONVENTION_REQUIRED"}
    if not isinstance(regions,list) or len(regions)!=3:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"EXACTLY_THREE_REGIONS_REQUIRED"}
    pts=[(_center(r),i) for i,r in enumerate(regions)]
    candidates=[]
    for (cx,cy),i in pts:
        others=[((ox,oy),j) for (ox,oy),j in pts if j!=i]
        horiz=[x for x in others if abs(x[0][1]-cy) < abs(x[0][0]-cx)]
        vert=[x for x in others if abs(x[0][0]-cx) <= abs(x[0][1]-cy)]
        if len(horiz)==1 and len(vert)==1:
            candidates.append((i,horiz[0],vert[0]))
    if len(candidates)!=1:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"AMBIGUOUS_LAYOUT"}
    front_i,horiz,vert=candidates[0]
    (hx,_),h_i=horiz
    (_,vy),v_i=vert
    fx,fy=_center(regions[front_i])
    if convention=="THIRD_ANGLE":
        if not (hx>fx and vy<fy):
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"LAYOUT_CONVENTION_MISMATCH"}
        right_i=h_i; top_i=v_i
    else:
        if not (hx<fx and vy>fy):
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"LAYOUT_CONVENTION_MISMATCH"}
        right_i=h_i; top_i=v_i
    return {"schema":SCHEMA,"status":"ASSIGNED","convention":convention,"front_region_index":front_i,"top_region_index":top_i,"right_region_index":right_i,"terminal_authority":False,"scope":"THREE_SPATIALLY_SEPARATED_AXIS_ALIGNED_VIEWS_WITH_DECLARED_PROJECTION_CONVENTION"}
