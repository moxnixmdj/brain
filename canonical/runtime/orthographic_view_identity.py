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
        if len(others)!=2:
            continue

        # For a valid three-view L layout, the front view is the unique
        # "elbow": one other region is horizontally aligned and one is
        # vertically aligned. Relative closeness alone is insufficient because
        # each endpoint can also look axis-like. Rank candidates by the actual
        # axis-alignment residual and require a unique best elbow.
        a,b=others
        pairings=[
            (a,b,abs(a[0][1]-cy)+abs(b[0][0]-cx)),
            (b,a,abs(b[0][1]-cy)+abs(a[0][0]-cx)),
        ]
        horiz,vert,score=min(pairings,key=lambda x:x[2])
        candidates.append((score,i,horiz,vert))

    candidates.sort(key=lambda x:(x[0],x[1]))
    if not candidates:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"AMBIGUOUS_LAYOUT"}
    if len(candidates)>1 and candidates[0][0]==candidates[1][0]:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"AMBIGUOUS_LAYOUT"}

    _,front_i,horiz,vert=candidates[0]
    (hx,hy),h_i=horiz
    (vx,vy),v_i=vert
    fx,fy=_center(regions[front_i])

    # Fail closed unless the selected elbow is genuinely axis-aligned.
    # Tolerance scales with view size so small raster jitter does not invent
    # semantic identity, while clearly diagonal layouts remain rejected.
    fw=max(1.0,float(regions[front_i]["x1_exclusive"]-regions[front_i]["x0"]))
    fh=max(1.0,float(regions[front_i]["y1_exclusive"]-regions[front_i]["y0"]))
    tol=max(1.0,0.10*min(fw,fh))
    if abs(hy-fy)>tol or abs(vx-fx)>tol:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"AMBIGUOUS_LAYOUT"}

    if convention=="THIRD_ANGLE":
        if not (hx>fx and vy<fy):
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"LAYOUT_CONVENTION_MISMATCH"}
        right_i=h_i; top_i=v_i
    else:
        if not (hx<fx and vy>fy):
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"LAYOUT_CONVENTION_MISMATCH"}
        right_i=h_i; top_i=v_i
    return {"schema":SCHEMA,"status":"ASSIGNED","convention":convention,"front_region_index":front_i,"top_region_index":top_i,"right_region_index":right_i,"terminal_authority":False,"scope":"THREE_SPATIALLY_SEPARATED_AXIS_ALIGNED_VIEWS_WITH_DECLARED_PROJECTION_CONVENTION"}
