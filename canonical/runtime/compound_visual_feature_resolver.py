"""Deterministic bounded compound visual-feature resolver.

Input is already-detected primitive geometry plus a parsed engineering annotation.
The resolver:
1) identifies the leader target only when boundary distance has a unique minimum;
2) defines a feature-equivalence class from visible geometric invariants;
3) resolves a quantity-bearing callout only when cardinality + target identify one set;
4) returns an ambiguity witness rather than selecting among equally valid sets.

This is a bounded geometry-semantic bridge, not general vision.
"""
from __future__ import annotations
import itertools, math
from typing import Any, Mapping, Sequence

SCHEMA="BRAIN_COMPOUND_VISUAL_FEATURE_RESOLVER_V1"
_EPS=1e-6

def _num(v:Any,name:str)->float:
    if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(float(v)):
        raise ValueError(name+" must be finite")
    return float(v)

def _center(f:Mapping[str,Any])->tuple[float,float]:
    c=f.get("center")
    if not isinstance(c,(list,tuple)) or len(c)!=2:
        raise ValueError("feature center missing")
    return _num(c[0],"center.x"),_num(c[1],"center.y")

def _boundary_distance(point:Sequence[float],f:Mapping[str,Any])->float:
    if not isinstance(point,(list,tuple)) or len(point)!=2:
        raise ValueError("leader endpoint invalid")
    px,py=_num(point[0],"leader.x"),_num(point[1],"leader.y")
    cx,cy=_center(f)
    kind=str(f.get("kind","")).lower()
    if kind=="circle":
        r=_num(f.get("radius"),"radius")
        if r<=0: raise ValueError("radius must be positive")
        return abs(math.hypot(px-cx,py-cy)-r)
    if kind=="slot":
        length=_num(f.get("length"),"length")
        width=_num(f.get("width"),"width")
        if length<=0 or width<=0 or length<width:
            raise ValueError("slot dimensions invalid")
        # Current bounded scene grammar: axis-aligned horizontal capsule.
        half_axis=(length-width)/2.0
        qx=min(max(px,cx-half_axis),cx+half_axis)
        axis_distance=math.hypot(px-qx,py-cy)
        return abs(axis_distance-width/2.0)
    raise ValueError("unsupported feature kind: "+kind)

def _signature(f:Mapping[str,Any])->tuple[Any,...]:
    kind=str(f.get("kind","")).lower()
    if kind=="circle":
        return ("circle",round(_num(f.get("radius"),"radius"),9))
    if kind=="slot":
        return ("slot",round(_num(f.get("length"),"length"),9),round(_num(f.get("width"),"width"),9))
    raise ValueError("unsupported feature kind: "+kind)

def _expected_kind(annotation:Mapping[str,Any])->str|None:
    explicit=annotation.get("feature_kind")
    if isinstance(explicit,str) and explicit:
        return explicit.lower()
    kind=str(annotation.get("kind","")).lower()
    if kind in {"hole_or_cylindrical_feature","diameter","thread"}:
        return "circle"
    if kind in {"slot","slot_feature"}:
        return "slot"
    return None

def resolve(
    features:Sequence[Mapping[str,Any]],
    annotation:Mapping[str,Any],
    leader_endpoint:Sequence[float],
    *,
    distance_tolerance:float=1e-6,
)->dict[str,Any]:
    if not isinstance(features,Sequence) or isinstance(features,(str,bytes)) or not features:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"FEATURES_INVALID"}
    if not isinstance(annotation,Mapping) or annotation.get("status")!="PARSED":
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"ANNOTATION_NOT_PARSED"}
    if distance_tolerance<0:
        raise ValueError("distance_tolerance must be nonnegative")

    expected=_expected_kind(annotation)
    quantity=annotation.get("quantity",1)
    if not isinstance(quantity,int) or isinstance(quantity,bool) or quantity<=0:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"QUANTITY_INVALID"}

    rows=[]
    ids=set()
    try:
        for i,f in enumerate(features):
            if not isinstance(f,Mapping):
                raise ValueError(f"feature {i} not object")
            fid=str(f.get("id","")).strip()
            if not fid or fid in ids:
                raise ValueError(f"bad or duplicate feature id:{fid}")
            ids.add(fid)
            if expected is not None and str(f.get("kind","")).lower()!=expected:
                continue
            rows.append((_boundary_distance(leader_endpoint,f),fid,f))
    except Exception as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":type(exc).__name__+":"+str(exc)}

    if not rows:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"NO_COMPATIBLE_FEATURE"}
    rows.sort(key=lambda x:(x[0],x[1]))
    best=rows[0][0]
    tied=[r for r in rows if abs(r[0]-best)<=distance_tolerance]
    if len(tied)!=1:
        return {
            "schema":SCHEMA,"status":"AMBIGUOUS","reason":"LEADER_TARGET_NONUNIQUE",
            "candidate_targets":[{"id":r[1],"distance":r[0]} for r in tied],
            "terminal_authority":False,
        }

    target_id=tied[0][1]
    target=tied[0][2]
    try:
        sig=_signature(target)
        equivalent=sorted(
            str(f["id"]) for f in features
            if isinstance(f,Mapping) and _signature(f)==sig
        )
    except Exception as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":type(exc).__name__+":"+str(exc)}

    if quantity==1:
        return {
            "schema":SCHEMA,"status":"RESOLVED",
            "feature_id":target_id,"feature_kind":str(target.get("kind","")).lower(),
            "quantity":1,"terminal_authority":False,
        }

    if len(equivalent)<quantity:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","reason":"INSUFFICIENT_EQUIVALENT_FEATURES",
            "target_id":target_id,"equivalent_feature_ids":equivalent,
            "requested_quantity":quantity,"terminal_authority":False,
        }
    if len(equivalent)==quantity:
        return {
            "schema":SCHEMA,"status":"RESOLVED",
            "feature_ids":equivalent,"quantity":quantity,
            "leader_target_id":target_id,"terminal_authority":False,
        }

    # Every admissible subset must contain the observed leader target.
    others=[x for x in equivalent if x!=target_id]
    alternatives=[
        [target_id,*list(combo)]
        for combo in itertools.combinations(others,quantity-1)
    ]
    alternatives=[sorted(x) for x in alternatives]
    if len(alternatives)==1:
        return {
            "schema":SCHEMA,"status":"RESOLVED",
            "feature_ids":alternatives[0],"quantity":quantity,
            "leader_target_id":target_id,"terminal_authority":False,
        }
    return {
        "schema":SCHEMA,"status":"AMBIGUOUS",
        "reason":"QUANTITY_SUBSET_NONUNIQUE",
        "leader_target_id":target_id,
        "alternatives":alternatives[:16],
        "alternative_count":len(alternatives),
        "terminal_authority":False,
    }
