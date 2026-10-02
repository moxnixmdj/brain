"""Information-safe bounded CAD orthographic solid proof.

The candidate sees only normalized binary orthographic silhouettes and isotropic
cell size. Hidden source voxels and all global geometry/topology metrics remain
oracle-only. Identifiable cases are connected one-cell-thick engineering-like
polycubes whose full three-view visual hull is unique. Nonidentifiable controls
use thicker solids admitting constructive alternative occupancies with identical
projections.

Independent oracle checks:
- projection equality and watertight polycube closure,
- global volume and exposed surface area,
- principal inertia eigenvalues,
- convex-hull volume and area,
- Euler characteristic of the cubical complex,
- connected components and global envelope,
- distribution of exposed faces per cell as a declared global curvature-equivalent
  signature for this voxelized bounded route.

Preflight only. No raw-raster/OCR, tolerance-callout, curved analytic CAD, or
whole-contract authority is claimed.
"""
from __future__ import annotations

from collections import Counter,deque
import math
import random
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_CAD_ORTHOGRAPHIC_INFORMATION_SAFE_PROOF_V1"
CLASSES=("L_SLAB_Z","RING_SLAB_Z","L_SLAB_X","L_SLAB_Y","AMBIGUOUS_BLOCK")


def _project(coords:set[tuple[int,int,int]],dims:tuple[int,int,int]):
    x_cells,y_cells,z_cells=dims
    top=[[False for _ in range(x_cells)] for _ in range(y_cells)]
    front=[[False for _ in range(x_cells)] for _ in range(z_cells)]
    right=[[False for _ in range(y_cells)] for _ in range(z_cells)]
    for x,y,z in coords:
        top[y][x]=True
        front[z][x]=True
        right[z][y]=True
    return top,front,right


def _components(coords:set[tuple[int,int,int]])->int:
    remaining=set(coords);count=0
    nbrs=((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))
    while remaining:
        count+=1
        start=remaining.pop();q=deque([start])
        while q:
            x,y,z=q.popleft()
            for dx,dy,dz in nbrs:
                n=(x+dx,y+dy,z+dz)
                if n in remaining:
                    remaining.remove(n);q.append(n)
    return count


def _cubical_euler(coords:set[tuple[int,int,int]])->int:
    vertices=set();edges=set();faces=set()
    for x,y,z in coords:
        vs=[
            (x+dx,y+dy,z+dz)
            for dx in (0,1) for dy in (0,1) for dz in (0,1)
        ]
        vertices.update(vs)
        for dy in (0,1):
            for dz in (0,1):
                edges.add(tuple(sorted(((x,y+dy,z+dz),(x+1,y+dy,z+dz)))))
        for dx in (0,1):
            for dz in (0,1):
                edges.add(tuple(sorted(((x+dx,y,z+dz),(x+dx,y+1,z+dz)))))
        for dx in (0,1):
            for dy in (0,1):
                edges.add(tuple(sorted(((x+dx,y+dy,z),(x+dx,y+dy,z+1)))))
        for fixed,axis in ((x,"x"),(x+1,"x"),(y,"y"),(y+1,"y"),(z,"z"),(z+1,"z")):
            if axis=="x":
                face=((fixed,y,z),(fixed,y+1,z),(fixed,y,z+1),(fixed,y+1,z+1))
            elif axis=="y":
                face=((x,fixed,z),(x+1,fixed,z),(x,fixed,z+1),(x+1,fixed,z+1))
            else:
                face=((x,y,fixed),(x+1,y,fixed),(x,y+1,fixed),(x+1,y+1,fixed))
            faces.add(tuple(sorted(face)))
    return len(vertices)-len(edges)+len(faces)-len(coords)


def _exposure(coords:set[tuple[int,int,int]]):
    nbrs=((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))
    counts={}
    total=0
    for p in coords:
        x,y,z=p
        n=sum((x+dx,y+dy,z+dz) not in coords for dx,dy,dz in nbrs)
        counts[p]=n;total+=n
    return total,dict(sorted(Counter(counts.values()).items()))


def _inertia_eigenvalues(coords:set[tuple[int,int,int]],cell:float):
    import numpy as np
    mass=cell**3
    centers=np.array([((x+.5)*cell,(y+.5)*cell,(z+.5)*cell) for x,y,z in sorted(coords)],dtype=float)
    center=centers.mean(axis=0)
    tensor=np.zeros((3,3),dtype=float)
    self_i=mass*cell*cell/6.0
    for c in centers:
        r=c-center
        tensor+=mass*((r@r)*np.eye(3)-np.outer(r,r))
        tensor+=np.eye(3)*self_i
    return [float(x) for x in np.linalg.eigvalsh(tensor)]


def _convex_hull(coords:set[tuple[int,int,int]],cell:float):
    import numpy as np
    from scipy.spatial import ConvexHull
    pts=set()
    for x,y,z in coords:
        for dx in (0,1):
            for dy in (0,1):
                for dz in (0,1):
                    pts.add(((x+dx)*cell,(y+dy)*cell,(z+dz)*cell))
    hull=ConvexHull(np.array(sorted(pts),dtype=float))
    return float(hull.volume),float(hull.area)


def _metrics(coords:set[tuple[int,int,int]],cell:float)->dict[str,Any]:
    if not coords:
        raise ValueError("EMPTY")
    exposed,hist=_exposure(coords)
    xs=[x for x,_,_ in coords];ys=[y for _,y,_ in coords];zs=[z for _,_,z in coords]
    hv,ha=_convex_hull(coords,cell)
    return {
        "watertight":True,
        "volume":len(coords)*cell**3,
        "surface_area":exposed*cell**2,
        "principal_inertia":_inertia_eigenvalues(coords,cell),
        "convex_hull_volume":hv,
        "convex_hull_area":ha,
        "euler_number":_cubical_euler(coords),
        "connected_components":_components(coords),
        "bbox":[
            min(xs)*cell,min(ys)*cell,min(zs)*cell,
            (max(xs)+1)*cell,(max(ys)+1)*cell,(max(zs)+1)*cell,
        ],
        "curvature_equivalent_exposed_face_histogram":hist,
    }


def _shape(cls:str,r:random.Random):
    if cls=="L_SLAB_Z":
        dims=(5,5,1)
        coords={(x,y,0) for x in range(5) for y in range(5) if x<2 or y<2}
    elif cls=="RING_SLAB_Z":
        dims=(5,5,1)
        coords={(x,y,0) for x in range(5) for y in range(5) if x in (0,4) or y in (0,4)}
    elif cls=="L_SLAB_X":
        dims=(1,5,5)
        coords={(0,y,z) for y in range(5) for z in range(5) if y<2 or z<2}
    elif cls=="L_SLAB_Y":
        dims=(5,1,5)
        coords={(x,0,z) for x in range(5) for z in range(5) if x<2 or z<2}
    elif cls=="AMBIGUOUS_BLOCK":
        dims=(2+r.randrange(2),2+r.randrange(2),2+r.randrange(2))
        coords={(x,y,z) for x in range(dims[0]) for y in range(dims[1]) for z in range(dims[2])}
    else:
        raise ValueError("CLASS")
    return dims,coords


def generate_case(seed:int,ordinal:int)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool) or not isinstance(ordinal,int) or ordinal<0:
        raise ValueError("INPUT")
    r=random.Random((seed<<15)^ordinal^0xCAD5)
    cls=CLASSES[ordinal%len(CLASSES)]
    dims,coords=_shape(cls,r)
    top,front,right=_project(coords,dims)
    cell=float(r.choice((0.5,1.0,2.0,2.5)))
    identifiable=cls!="AMBIGUOUS_BLOCK"
    return {
        "schema":SCHEMA,
        "behavior_id":"CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001",
        "case_id":f"CAD-ORTHO-{seed}-{ordinal}",
        "case_class":cls,
        "task":{
            "top":top,
            "front":front,
            "right":right,
            "cell_size":cell,
            "declared_conventions":[
                "BINARY_ORTHOGRAPHIC_OCCUPANCY",
                "AXIS_ALIGNED_ISOTROPIC_VOXEL_CELLS",
                "SOLID_MUST_MATCH_ALL_THREE_VIEWS",
                "NONIDENTIFIABLE_DRAWING_MUST_RETURN_CONSTRUCTIVE_WITNESS",
            ],
        },
        "_oracle":{
            "dims":dims,
            "source_voxels":[list(x) for x in sorted(coords)],
            "identifiable":identifiable,
            "metrics":_metrics(coords,cell),
        },
    }


def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return {k:v for k,v in case.items() if k!="_oracle"}


def _as_set(rows:Any)->set[tuple[int,int,int]]|None:
    if not isinstance(rows,list):
        return None
    out=set()
    try:
        for row in rows:
            if not isinstance(row,list) or len(row)!=3:
                return None
            p=tuple(int(v) for v in row)
            if any(isinstance(v,bool) for v in row):
                return None
            out.add(p)
    except Exception:
        return None
    return out


def _metrics_close(a:Mapping[str,Any],b:Mapping[str,Any])->bool:
    exact=("watertight","euler_number","connected_components","curvature_equivalent_exposed_face_histogram")
    if any(a.get(k)!=b.get(k) for k in exact):
        return False
    for k in ("volume","surface_area","convex_hull_volume","convex_hull_area"):
        if not math.isclose(float(a[k]),float(b[k]),rel_tol=1e-10,abs_tol=1e-10):
            return False
    for k in ("principal_inertia","bbox"):
        av=list(a[k]);bv=list(b[k])
        if len(av)!=len(bv) or any(not math.isclose(float(x),float(y),rel_tol=1e-9,abs_tol=1e-9) for x,y in zip(av,bv)):
            return False
    return True


def score_case(case:Mapping[str,Any],candidate:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(candidate,Mapping):
        return {"pass":False,"reason":"CANDIDATE_NOT_MAPPING"}
    oracle=case["_oracle"]
    top=case["task"]["top"];front=case["task"]["front"];right=case["task"]["right"]
    dims=tuple(oracle["dims"])
    cell=float(case["task"]["cell_size"])
    source=_as_set(oracle["source_voxels"])
    if source is None:
        raise AssertionError("oracle source invalid")

    if oracle["identifiable"]:
        if candidate.get("status")!="SOLID":
            return {"pass":False,"reason":"IDENTIFIABLE_CASE_NOT_SOLID"}
        got=_as_set(candidate.get("voxels"))
        if got is None or got!=source:
            return {"pass":False,"reason":"GLOBAL_SOLID_VOXELS_WRONG"}
        if _project(got,dims)!=(top,front,right):
            return {"pass":False,"reason":"PROJECTION_MISMATCH"}
        metrics=_metrics(got,cell)
        if not _metrics_close(metrics,oracle["metrics"]):
            return {"pass":False,"reason":"GLOBAL_GEOMETRY_TOPOLOGY_METRICS_WRONG","metrics":metrics}
        return {"pass":True,"reason":"PASS_IDENTIFIABLE"}

    if candidate.get("status")!="NONIDENTIFIABLE":
        return {"pass":False,"reason":"AMBIGUOUS_CASE_FORCED_TO_SINGLE_SOLID"}
    alt=_as_set(candidate.get("alternative_voxels"))
    witness=candidate.get("witness_removed_voxel")
    if alt is None or not isinstance(witness,list) or len(witness)!=3:
        return {"pass":False,"reason":"AMBIGUITY_WITNESS_INVALID"}
    if alt==source or not alt:
        return {"pass":False,"reason":"ALTERNATIVE_NOT_DISTINCT"}
    if any(not (0<=x<dims[0] and 0<=y<dims[1] and 0<=z<dims[2]) for x,y,z in alt):
        return {"pass":False,"reason":"ALTERNATIVE_OUT_OF_BOUNDS"}
    if _project(alt,dims)!=(top,front,right):
        return {"pass":False,"reason":"ALTERNATIVE_DOES_NOT_PRESERVE_DRAWING"}
    return {"pass":True,"reason":"PASS_NONIDENTIFIABLE"}


def run_batch(seed:int,count:int,candidate_fn)->dict[str,Any]:
    rows=[]
    for ordinal in range(count):
        case=generate_case(seed,ordinal)
        try:
            verdict=score_case(case,candidate_fn(public_task(case)))
        except Exception as exc:
            verdict={"pass":False,"reason":"EXCEPTION:"+type(exc).__name__+":"+str(exc)}
        rows.append({"case_id":case["case_id"],"class":case["case_class"],**verdict})
    passed=sum(int(bool(x["pass"])) for x in rows)
    return {
        "schema":"PROJECT_BRAIN_CAD_ORTHOGRAPHIC_INFORMATION_SAFE_PREFLIGHT_RESULT_V1",
        "case_count":count,
        "passed":passed,
        "failed":count-passed,
        "all_pass":passed==count,
        "failures":[x for x in rows if not x["pass"]],
        "terminal_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "incremental_spend_usd":0,
    }
