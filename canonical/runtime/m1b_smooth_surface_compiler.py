"""Kernel-backed smooth-surface compiler for identified M1B geometry.

This extends the analytic PartSpec prefix with smooth continuous constructions whose
defining data is already identified:
- spline_revolve: a smooth radial/axial interpolation curve revolved about its axis;
- circle_loft: smooth loft through circular cross-sections;
- polygon_loft: loft through explicit polygon cross-sections.

No drawing inference occurs here. Section/control data is the contract.
"""
from __future__ import annotations

from typing import Any, Mapping
import math

SCHEMA="BRAIN_M1B_SMOOTH_SURFACE_COMPILER_V1"


def _f(v:Any,name:str)->float:
    if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(float(v)):
        raise ValueError(f"{name} must be finite")
    return float(v)


def _pos(v:Any,name:str)->float:
    x=_f(v,name)
    if x<=0: raise ValueError(f"{name} must be positive")
    return x


def _points2(rows:Any,name:str,min_count:int)->list[tuple[float,float]]:
    if not isinstance(rows,list) or len(rows)<min_count:
        raise ValueError(f"{name} needs at least {min_count} points")
    out=[]
    for i,p in enumerate(rows):
        if not isinstance(p,(list,tuple)) or len(p)!=2:
            raise ValueError(f"{name}[{i}] must be [x,y]")
        out.append((_f(p[0],f"{name}[{i}].x"),_f(p[1],f"{name}[{i}].y")))
    return out


def compile_source(contract:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(contract,Mapping):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["CONTRACT_NOT_OBJECT"]}
    try:
        kind=contract.get("kind")
        if kind=="spline_revolve":
            pts=_points2(contract.get("radial_axial_points"),"radial_axial_points",3)
            if any(r<=0 for r,_ in pts):
                raise ValueError("spline_revolve radii must be positive")
            zs=[z for _,z in pts]
            if any(b<=a for a,b in zip(zs,zs[1:])):
                raise ValueError("spline_revolve axial coordinates must strictly increase")
            start_axis=(0.0,zs[0]); end_axis=(0.0,zs[-1])
            first=pts[0]
            rest=pts[1:]
            rows=[
                "import cadquery as cq",
                f"surface_points = {repr(rest)}",
                f"result = (cq.Workplane('XY').moveTo({start_axis[0]}, {start_axis[1]})",
                f"          .lineTo({first[0]}, {first[1]})",
                "          .spline(surface_points, includeCurrent=True)",
                f"          .lineTo({end_axis[0]}, {end_axis[1]})",
                "          .close()",
                f"          .revolve(360.0, ({start_axis[0]}, {start_axis[1]}), ({end_axis[0]}, {end_axis[1]})))",
            ]
            source="\n".join(rows)+"\n"
        elif kind=="circle_loft":
            sections=contract.get("sections")
            if not isinstance(sections,list) or len(sections)<2:
                raise ValueError("circle_loft needs at least two sections")
            clean=[]
            for i,s in enumerate(sections):
                if not isinstance(s,Mapping): raise ValueError(f"section {i} not object")
                clean.append((_f(s.get("z"),f"section[{i}].z"),_pos(s.get("radius"),f"section[{i}].radius")))
            clean.sort()
            if len({z for z,_ in clean})!=len(clean):
                raise ValueError("circle_loft z values must be unique")
            z0,r0=clean[0]
            rows=["import cadquery as cq",f"result = cq.Workplane('XY', origin=(0,0,{z0})).circle({r0})"]
            prev=z0
            for z,r in clean[1:]:
                rows.append(f"result = result.workplane(offset={z-prev}).circle({r})")
                prev=z
            rows.append("result = result.loft(combine=True, ruled=False)")
            source="\n".join(rows)+"\n"
        elif kind=="polygon_loft":
            sections=contract.get("sections")
            if not isinstance(sections,list) or len(sections)<2:
                raise ValueError("polygon_loft needs at least two sections")
            clean=[]
            for i,s in enumerate(sections):
                if not isinstance(s,Mapping): raise ValueError(f"section {i} not object")
                z=_f(s.get("z"),f"section[{i}].z")
                pts=_points2(s.get("points"),f"section[{i}].points",3)
                clean.append((z,pts))
            clean.sort(key=lambda x:x[0])
            if len({z for z,_ in clean})!=len(clean):
                raise ValueError("polygon_loft z values must be unique")
            z0,p0=clean[0]
            rows=[
                "import cadquery as cq",
                f"result = cq.Workplane('XY', origin=(0,0,{z0})).polyline({repr(p0)}).close()"
            ]
            prev=z0
            for z,pts in clean[1:]:
                rows.append(f"result = result.workplane(offset={z-prev}).polyline({repr(pts)}).close()")
                prev=z
            rows.append("result = result.loft(combine=True, ruled=False)")
            source="\n".join(rows)+"\n"
        else:
            raise ValueError(f"unsupported smooth surface kind: {kind}")
        compile(source,"<m1b-smooth-surface>","exec")
        return {
            "schema":SCHEMA,"status":"COMPILED","kind":kind,"source":source,
            "terminal_authority":False,
            "scope":"IDENTIFIED_CONTROL_OR_SECTION_GEOMETRY_TO_KERNEL_BACKED_SMOOTH_CONTINUOUS_SOLID",
        }
    except Exception as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":[type(exc).__name__+":"+str(exc)]}
