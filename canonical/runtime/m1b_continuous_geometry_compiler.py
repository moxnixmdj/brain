"""Executable M1B compiler from a typed continuous-geometry contract to Brain PartSpec.

This is deliberately downstream of M1A. It consumes geometry that is already identified
and semantically typed. It does not infer hidden geometry from a drawing.

Supported current grammar:
- closed line/three-point-circular-arc profiles extruded to an exact depth;
- circular extrusions;
- stepped axisymmetric revolved solids with optional bores;
- multibody CSG from boxes, cylinders, spheres, and line/arc prisms;
- holes, rectangular cuts, fillets, chamfers;
- named dimensional tolerances with no integer/pixel quantization.

The compiler preserves floats exactly as Python binary floats and exposes the accepted
interval for every dimension. Unknown geometry kinds fail closed.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence
import math

from cad_partspec import (
    Body,
    Dimension,
    ExtrudedGeometry,
    Hole,
    MultiBodyGeometry,
    PartSpec,
    Point,
    ProfileSegment,
    RectCut,
    RevolvedGeometry,
    RevolvedSegment,
)

SCHEMA="BRAIN_M1B_CONTINUOUS_GEOMETRY_COMPILER_V1"


def _finite_positive(v:Any,name:str)->float:
    if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(float(v)) or float(v)<=0:
        raise ValueError(f"{name} must be a finite positive number")
    return float(v)


def _finite(v:Any,name:str)->float:
    if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(float(v)):
        raise ValueError(f"{name} must be finite")
    return float(v)


def _point(raw:Any,name:str)->Point:
    if not isinstance(raw,(list,tuple)) or len(raw)!=2:
        raise ValueError(f"{name} must be [x,y]")
    return Point(x=_finite(raw[0],name+".x"),y=_finite(raw[1],name+".y"))


def _segments(rows:Any)->list[ProfileSegment]:
    if not isinstance(rows,list) or len(rows)<2:
        raise ValueError("profile segments must contain at least two segments")
    out=[]
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            raise ValueError(f"segment {i} must be an object")
        kind=str(row.get("kind",""))
        end=_point(row.get("end"),f"segment[{i}].end")
        if kind=="line":
            out.append(ProfileSegment(kind="line",end=end))
        elif kind=="arc":
            mid=_point(row.get("mid"),f"segment[{i}].mid")
            out.append(ProfileSegment(kind="arc",mid=mid,end=end))
        else:
            raise ValueError(f"unsupported profile segment kind: {kind}")
    return out


def _dimensions(rows:Any)->list[Dimension]:
    if rows is None:
        return []
    if not isinstance(rows,list):
        raise ValueError("dimensions must be a list")
    out=[]
    seen=set()
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            raise ValueError(f"dimension {i} must be an object")
        name=row.get("name")
        if not isinstance(name,str) or not name or name in seen:
            raise ValueError(f"dimension {i} has invalid/duplicate name")
        seen.add(name)
        nominal=_finite_positive(row.get("nominal"),f"dimension[{i}].nominal")
        plus=_finite(row.get("tol_plus",0.0),f"dimension[{i}].tol_plus")
        minus=_finite(row.get("tol_minus",0.0),f"dimension[{i}].tol_minus")
        if plus<0 or minus<0:
            raise ValueError("dimension tolerances must be nonnegative")
        out.append(Dimension(name=name,nominal=nominal,tol_plus=plus,tol_minus=minus))
    return out


def dimension_intervals(spec:PartSpec)->dict[str,dict[str,float]]:
    return {
        d.name:{
            "nominal":float(d.nominal),
            "lower":float(d.nominal-d.tol_minus),
            "upper":float(d.nominal+d.tol_plus),
            "tol_minus":float(d.tol_minus),
            "tol_plus":float(d.tol_plus),
        }
        for d in spec.dimensions
    }


def _holes(rows:Any)->list[Hole]:
    if rows is None:
        return []
    if not isinstance(rows,list):
        raise ValueError("holes must be a list")
    return [Hole.model_validate(dict(x)) for x in rows]


def _cuts(rows:Any)->list[RectCut]:
    if rows is None:
        return []
    if not isinstance(rows,list):
        raise ValueError("cuts must be a list")
    return [RectCut.model_validate(dict(x)) for x in rows]


def _body(row:Mapping[str,Any],i:int)->Body:
    d=dict(row)
    if d.get("shape")=="prism" and d.get("profile_start") is not None:
        p=d["profile_start"]; d["profile_start"]={"x":_finite(p[0],f"body{i}.profile_start.x"),"y":_finite(p[1],f"body{i}.profile_start.y")}
        segs=[]
        for s in d.get("profile_segments",[]):
            s=dict(s)
            ep=s.get("end"); s["end"]={"x":_finite(ep[0],"end.x"),"y":_finite(ep[1],"end.y")}
            if s.get("mid") is not None:
                mp=s["mid"]; s["mid"]={"x":_finite(mp[0],"mid.x"),"y":_finite(mp[1],"mid.y")}
            segs.append(s)
        d["profile_segments"]=segs
    return Body.model_validate(d)


def compile_contract(contract:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(contract,Mapping):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["CONTRACT_NOT_OBJECT"]}
    errors=[]
    try:
        units=contract.get("units","mm")
        if units not in {"mm","in"}:
            raise ValueError("units must be mm or in")
        g=contract.get("geometry")
        if not isinstance(g,Mapping):
            raise ValueError("geometry must be an object")
        kind=g.get("kind")
        if kind=="profile_extrude":
            start=_point(g.get("start"),"geometry.start")
            geometry=MultiBodyGeometry(bodies=[Body(
                shape="prism",operation="add",axis="z",
                x=0.0,y=0.0,z=_finite(g.get("z",0.0),"geometry.z"),
                length=_finite_positive(g.get("depth"),"geometry.depth"),
                profile_start=start,profile_segments=_segments(g.get("segments")),
            )])
        elif kind=="circle_extrude":
            diameter=_finite_positive(g.get("diameter"),"geometry.diameter")
            depth=_finite_positive(g.get("depth"),"geometry.depth")
            geometry=ExtrudedGeometry(
                profile_kind="circle",diameter=diameter,thickness=depth
            )
        elif kind=="revolved_steps":
            rows=g.get("segments")
            if not isinstance(rows,list) or not rows:
                raise ValueError("revolved_steps requires segments")
            geometry=RevolvedGeometry(segments=[
                RevolvedSegment(
                    z_start=_finite(x.get("z_start"),"z_start"),
                    z_end=_finite(x.get("z_end"),"z_end"),
                    outer_diameter=_finite_positive(x.get("outer_diameter"),"outer_diameter"),
                    inner_diameter=_finite(x.get("inner_diameter",0.0),"inner_diameter"),
                ) for x in rows
            ])
        elif kind=="multibody":
            rows=g.get("bodies")
            if not isinstance(rows,list) or not rows:
                raise ValueError("multibody requires bodies")
            geometry=MultiBodyGeometry(bodies=[_body(x,i) for i,x in enumerate(rows)])
        else:
            raise ValueError(f"unsupported geometry kind: {kind}")

        spec=PartSpec(
            units=units,
            geometry=geometry,
            holes=_holes(contract.get("holes")),
            cuts=_cuts(contract.get("cuts")),
            fillets=[_finite_positive(x,"fillet") for x in contract.get("fillets",[])],
            chamfers=[_finite_positive(x,"chamfer") for x in contract.get("chamfers",[])],
            dimensions=_dimensions(contract.get("dimensions")),
            notes=contract.get("notes"),
        )
        sanity=spec.sanity_check()
        if sanity:
            errors.extend("PARTSPEC_SANITY:"+x for x in sanity)
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))
        spec=None

    if errors or spec is None:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors))}

    return {
        "schema":SCHEMA,
        "status":"COMPILED",
        "partspec":spec,
        "dimension_intervals":dimension_intervals(spec),
        "terminal_authority":False,
        "scope":"IDENTIFIED_TYPED_GEOMETRY_TO_CONTINUOUS_PARTSPEC_WITH_LINE_ARC_ANALYTIC_SOLIDS_AND_FLOAT_TOLERANCES",
    }
