"""Independent proof checker for normalized orthographic voxel-solid results.

This checker deliberately does not import the candidate or the visual-hull runtime.
For any finite rectangular binary top/front/right masks it recomputes the maximal
consistent voxel hull, checks whether the masks are mutually realizable, and checks
the exact uniqueness/nonidentifiability certificate returned by the candidate.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

Mask = Sequence[Sequence[bool | int]]

def _mask(value: Any) -> list[list[bool]] | None:
    if not isinstance(value, list) or not value or not isinstance(value[0], list) or not value[0]:
        return None
    width=len(value[0])
    if any(not isinstance(row,list) or len(row)!=width for row in value):
        return None
    return [[bool(v) for v in row] for row in value]

def _task(task: Any):
    if not isinstance(task, Mapping):
        return None
    top=_mask(task.get("top")); front=_mask(task.get("front")); right=_mask(task.get("right"))
    cell=task.get("cell_size")
    if top is None or front is None or right is None:
        return None
    if not isinstance(cell,(int,float)) or isinstance(cell,bool) or cell<=0:
        return None
    y,x=len(top),len(top[0]); z,fx=len(front),len(front[0]); rz,ry=len(right),len(right[0])
    if fx!=x or rz!=z or ry!=y:
        return None
    return top,front,right,float(cell),(x,y,z)

def _hull(top,front,right,dims):
    x,y,z=dims
    return {(i,j,k) for k in range(z) for j in range(y) for i in range(x)
            if top[j][i] and front[k][i] and right[k][j]}

def _project(coords,dims):
    x,y,z=dims
    top=[[False]*x for _ in range(y)]
    front=[[False]*x for _ in range(z)]
    right=[[False]*y for _ in range(z)]
    for i,j,k in coords:
        top[j][i]=True; front[k][i]=True; right[k][j]=True
    return top,front,right

def _rows(value: Any):
    if not isinstance(value,list):
        return None
    out=set()
    for row in value:
        if not isinstance(row,list) or len(row)!=3 or any(isinstance(v,bool) or not isinstance(v,int) for v in row):
            return None
        out.add(tuple(row))
    return out

def verify(public_case: Any, candidate: Any) -> dict[str,Any]:
    if not isinstance(public_case, Mapping) or not isinstance(candidate, Mapping):
        return {"pass":False,"reason":"INPUT_NOT_MAPPING"}
    parsed=_task(public_case.get("task"))
    if parsed is None:
        return {"pass":candidate.get("status")=="FAIL_CLOSED","reason":"INVALID_TASK_MUST_FAIL_CLOSED"}
    top,front,right,cell,dims=parsed
    hull=_hull(top,front,right,dims)
    if not hull:
        return {"pass":candidate.get("status")=="FAIL_CLOSED","reason":"EMPTY_HULL_MUST_FAIL_CLOSED"}
    consistent=_project(hull,dims)==(top,front,right)
    if not consistent:
        return {
            "pass":candidate.get("status")=="FAIL_CLOSED"
                   and candidate.get("reason")=="INCONSISTENT_ORTHOGRAPHIC_SILHOUETTES",
            "reason":"INCONSISTENT_MASKS_MUST_FAIL_CLOSED",
        }

    top_counts={}; front_counts={}; right_counts={}
    for i,j,k in hull:
        top_counts[(i,j)]=top_counts.get((i,j),0)+1
        front_counts[(i,k)]=front_counts.get((i,k),0)+1
        right_counts[(j,k)]=right_counts.get((j,k),0)+1
    removable={p for p in hull
               if top_counts[(p[0],p[1])]>1
               and front_counts[(p[0],p[2])]>1
               and right_counts[(p[1],p[2])]>1}

    if not removable:
        got=_rows(candidate.get("voxels"))
        ok=(candidate.get("status")=="SOLID" and got==hull
            and float(candidate.get("cell_size",-1))==cell)
        return {"pass":ok,"reason":"UNIQUE_HULL_REQUIRED","unique":True}

    alt=_rows(candidate.get("alternative_voxels"))
    witness=candidate.get("witness_removed_voxel")
    witness_tuple=tuple(witness) if isinstance(witness,list) and len(witness)==3 else None
    ok=(candidate.get("status")=="NONIDENTIFIABLE"
        and alt is not None and alt and alt!=hull
        and alt < hull
        and _project(alt,dims)==(top,front,right)
        and witness_tuple in hull-alt
        and float(candidate.get("cell_size",-1))==cell)
    return {"pass":ok,"reason":"CONSTRUCTIVE_NONIDENTIFIABILITY_REQUIRED","unique":False}

if __name__=="__main__":
    raise SystemExit("import and call verify")
