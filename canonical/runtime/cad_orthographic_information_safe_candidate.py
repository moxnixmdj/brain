"""Bounded Brain candidate for orthographic voxel-solid reconstruction.

The candidate receives only normalized top/front/right binary silhouettes and an
isotropic cell size. It reconstructs the maximal visual hull and decides exact
identifiability. A hull voxel is indispensable when it is the sole occupied voxel
on at least one required projection ray. The full hull is unique iff every hull
voxel is indispensable; otherwise removing any nonessential voxel is a constructive
nonidentifiability witness with identical projections.

This owns a bounded normalized orthographic voxel subset only. It does not claim
raw drawing interpretation, curved/analytic CAD, or whole terminal CAD scope.
"""
from __future__ import annotations

from typing import Any,Mapping

from canonical.runtime.orthographic_visual_hull import reconstruct_visual_hull,project_visual_hull


def _coords(grid)->list[tuple[int,int,int]]:
    out=[]
    for z,slab in enumerate(grid):
        for y,row in enumerate(slab):
            for x,value in enumerate(row):
                if value:
                    out.append((x,y,z))
    return out


def _ray_counts(coords:list[tuple[int,int,int]]):
    top={};front={};right={}
    for x,y,z in coords:
        top[(x,y)]=top.get((x,y),0)+1
        front[(x,z)]=front.get((x,z),0)+1
        right[(y,z)]=right.get((y,z),0)+1
    return top,front,right


def _grid_from_coords(coords:set[tuple[int,int,int]],dims:tuple[int,int,int]):
    x_cells,y_cells,z_cells=dims
    return [
        [
            [(x,y,z) in coords for x in range(x_cells)]
            for y in range(y_cells)
        ]
        for z in range(z_cells)
    ]


def solve(public_case:Mapping[str,Any])->dict[str,Any]:
    task=public_case.get("task")
    if not isinstance(task,Mapping):
        return {"status":"FAIL_CLOSED","reason":"TASK_INVALID"}
    top=task.get("top")
    front=task.get("front")
    right=task.get("right")
    cell=task.get("cell_size")
    if not isinstance(cell,(int,float)) or isinstance(cell,bool) or cell<=0:
        return {"status":"FAIL_CLOSED","reason":"CELL_SIZE_INVALID"}
    try:
        hull=reconstruct_visual_hull(top,front,right)
        coords=_coords(hull)
        if not coords:
            return {"status":"FAIL_CLOSED","reason":"EMPTY_HULL"}
        x_cells=len(hull[0][0]);y_cells=len(hull[0]);z_cells=len(hull)
        counts=_ray_counts(coords)
        removable=[]
        for voxel in coords:
            x,y,z=voxel
            if counts[0][(x,y)]>1 and counts[1][(x,z)]>1 and counts[2][(y,z)]>1:
                removable.append(voxel)

        if not removable:
            return {
                "status":"SOLID",
                "voxels":[list(x) for x in sorted(coords)],
                "cell_size":float(cell),
                "reason":"EVERY_VISUAL_HULL_VOXEL_PROJECTION_INDISPENSABLE",
                "terminal_authority":False,
            }

        witness=sorted(removable)[0]
        alt=set(coords);alt.remove(witness)
        alt_grid=_grid_from_coords(alt,(x_cells,y_cells,z_cells))
        at,af,ar=project_visual_hull(alt_grid)
        if at!=[[bool(v) for v in row] for row in top] or af!=[[bool(v) for v in row] for row in front] or ar!=[[bool(v) for v in row] for row in right]:
            return {"status":"FAIL_CLOSED","reason":"INTERNAL_WITNESS_PROJECTION_MISMATCH"}
        return {
            "status":"NONIDENTIFIABLE",
            "reason":"REMOVABLE_VOXEL_PRESERVES_ALL_DECLARED_PROJECTIONS",
            "witness_removed_voxel":list(witness),
            "alternative_voxels":[list(x) for x in sorted(alt)],
            "cell_size":float(cell),
            "terminal_authority":False,
        }
    except Exception as exc:
        return {"status":"FAIL_CLOSED","reason":"RECONSTRUCTION_ERROR","error":type(exc).__name__+":"+str(exc)}
