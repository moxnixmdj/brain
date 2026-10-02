"""Deterministic post-freeze CAD geometry population for T0 direct instrumentation.

This is not a synthetic whole-domain proof. It supplies hidden-reference geometry
cases inside the frozen T0 terminal portfolio after candidate/oracle bytes are
committed and an unpredictable beacon is known.

The candidate receives only the visible drawing and declared output schema.
Typed reference geometry, identifiability truth, and case-family labels remain
evaluator-side.
"""
from __future__ import annotations
import hashlib, html, json, math
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_CAD_T0_GEOMETRY_POPULATION_V1"
FAMILIES=(
    "BOX_EXTRUDE",
    "CIRCLE_EXTRUDE",
    "BOX_THROUGH_HOLE",
    "REVOLVED_STEPS",
    "SPLINE_REVOLVE",
    "CIRCLE_LOFT",
    "POLYGON_LOFT",
    "NONIDENTIFIABLE_DEPTH",
)
SLOT_COUNT=128

def derive_seed(commitment:str, beacon:str, case_id:str)->int:
    if not all(isinstance(x,str) and x for x in (commitment,beacon,case_id)):
        raise ValueError("commitment beacon and case_id must be nonempty strings")
    raw=("PROJECT_BRAIN_CAD_T0_GEOMETRY_V1\0"+commitment+"\0"+beacon+"\0"+case_id).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8],"big")

def _u(seed:int,key:str)->float:
    raw=(str(int(seed))+"\0"+key).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8],"big")/(2**64-1)

def _f(seed:int,key:str,lo:float,hi:float,places:int=3)->float:
    return round(lo+(hi-lo)*_u(seed,key),places)

def _svg(title:str, lines:list[str])->str:
    safe=html.escape(title)
    rows=[f'<text x="10" y="{25+i*20}" font-size="12">{html.escape(x)}</text>' for i,x in enumerate(lines)]
    h=max(100,45+20*len(rows))
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="{h}" viewBox="0 0 640 {h}"><rect width="100%" height="100%" fill="white"/><text x="10" y="15" font-size="13">{safe}</text>'+''.join(rows)+'</svg>'

def _tol_metrics()->dict[str,dict[str,float]]:
    return {
        "volume":{"abs":0.05,"rel":1e-7},
        "surface_area":{"abs":0.05,"rel":1e-7},
        "bbox":{"abs":0.01,"rel":1e-7},
        "topology_counts":{"abs":0,"rel":0},
    }

def _rect_profile(w:float,h:float)->dict[str,Any]:
    return {
        "kind":"profile_extrude","start":[0.0,0.0],
        "segments":[
            {"kind":"line","end":[w,0.0]},
            {"kind":"line","end":[w,h]},
            {"kind":"line","end":[0.0,h]},
            {"kind":"line","end":[0.0,0.0]},
        ],
    }

def _graph(family:str, dims:Mapping[str,float], features:list[dict[str,Any]]|None=None)->dict[str,Any]:
    return {
        "geometry_family":family,
        "dimensions":{k:float(v) for k,v in sorted(dims.items())},
        "features":features or [],
    }

def generate_case(seed:int, slot:int)->dict[str,Any]:
    if not isinstance(slot,int) or isinstance(slot,bool) or not 0<=slot<SLOT_COUNT:
        raise ValueError("slot out of range")
    family=FAMILIES[slot%len(FAMILIES)]
    cid=f"CAD_T0_GEOMETRY_V1::slot::{slot}"
    oracle:dict[str,Any]={"family":family,"identifiable":True}
    lines:list[str]=[]
    if family=="BOX_EXTRUDE":
        w=_f(seed,"w",16,120); h=_f(seed,"h",12,90); d=_f(seed,"d",4,45)
        contract={"units":"mm","geometry":{**_rect_profile(w,h),"depth":d},
                  "dimensions":[{"name":"overall_width","nominal":w},{"name":"overall_height","nominal":h},{"name":"overall_depth","nominal":d}]}
        graph=_graph(family,{"width":w,"height":h,"depth":d})
        lines=[f"FRONT: rectangle {w} mm x {h} mm",f"DEPTH: {d} mm","Three orthographic views; all dimensions nominal."]
    elif family=="CIRCLE_EXTRUDE":
        dia=_f(seed,"dia",12,80); d=_f(seed,"d",5,60)
        contract={"units":"mm","geometry":{"kind":"circle_extrude","diameter":dia,"depth":d},
                  "dimensions":[{"name":"overall_diameter","nominal":dia},{"name":"overall_depth","nominal":d}]}
        graph=_graph(family,{"diameter":dia,"depth":d})
        lines=[f"FRONT: circle diameter {dia} mm",f"DEPTH: {d} mm","Axis normal to front view."]
    elif family=="BOX_THROUGH_HOLE":
        w=_f(seed,"w",35,120); h=_f(seed,"h",30,100); d=_f(seed,"d",5,30)
        dia=min(_f(seed,"dia",4,20),round(min(w,h)*0.35,3)); x=round(w/2,3); y=round(h/2,3)
        contract={"units":"mm","geometry":{**_rect_profile(w,h),"depth":d},
                  "holes":[{"x":x,"y":y,"diameter":dia,"hole_type":"through"}],
                  "dimensions":[{"name":"overall_width","nominal":w},{"name":"overall_height","nominal":h},{"name":"overall_depth","nominal":d}]}
        graph=_graph(family,{"width":w,"height":h,"depth":d,"hole_diameter":dia},
                     [{"kind":"through_hole","x":x,"y":y,"diameter":dia}])
        lines=[f"PLATE: {w} x {h} x {d} mm",f"CENTER THROUGH HOLE: diameter {dia} mm","Hole centered in width and height."]
    elif family=="REVOLVED_STEPS":
        z1=_f(seed,"z1",8,30); z2=round(z1+_f(seed,"z2",8,35),3)
        od1=_f(seed,"od1",20,70); od2=_f(seed,"od2",12,max(13,od1-2))
        contract={"units":"mm","geometry":{"kind":"revolved_steps","segments":[
            {"z_start":0.0,"z_end":z1,"outer_diameter":od1,"inner_diameter":0.0},
            {"z_start":z1,"z_end":z2,"outer_diameter":od2,"inner_diameter":0.0},
        ]}}
        graph=_graph(family,{"length_1":z1,"length_total":z2,"diameter_1":od1,"diameter_2":od2})
        lines=[f"REVOLVE PROFILE: segment 1 L={z1} mm OD={od1} mm",f"segment 2 ends at Z={z2} mm OD={od2} mm","Revolve 360 degrees about center axis."]
    elif family=="SPLINE_REVOLVE":
        z0=0.0; z1=_f(seed,"z1",8,20); z2=round(z1+_f(seed,"z2",8,22),3); z3=round(z2+_f(seed,"z3",8,25),3)
        r0=_f(seed,"r0",6,18); r1=_f(seed,"r1",8,22); r2=_f(seed,"r2",6,20); r3=_f(seed,"r3",5,16)
        pts=[[r0,z0],[r1,z1],[r2,z2],[r3,z3]]
        contract={"kind":"spline_revolve","radial_axial_points":pts}
        graph=_graph(family,{"z_end":z3},[{"kind":"spline_revolve_profile","points":pts}])
        lines=["SMOOTH REVOLVED PROFILE control points (radius,z), mm: "+json.dumps(pts),"Smooth interpolation; revolve 360 degrees about z axis."]
    elif family=="CIRCLE_LOFT":
        z0=0.0; z1=_f(seed,"z1",10,30); z2=round(z1+_f(seed,"z2",10,35),3)
        r0=_f(seed,"r0",5,16); r1=_f(seed,"r1",8,22); r2=_f(seed,"r2",5,18)
        sections=[{"z":z0,"radius":r0},{"z":z1,"radius":r1},{"z":z2,"radius":r2}]
        contract={"kind":"circle_loft","sections":sections}
        graph=_graph(family,{"z_end":z2},[{"kind":"circle_sections","sections":sections}])
        lines=["SMOOTH CIRCULAR LOFT sections (z,radius), mm: "+json.dumps(sections),"Smooth non-ruled loft."]
    elif family=="POLYGON_LOFT":
        z0=0.0; z1=_f(seed,"z1",12,35)
        a=_f(seed,"a",8,20); b=_f(seed,"b",5,15); scale=_f(seed,"scale",0.65,1.35)
        p0=[[-a,-b],[a,-b],[a,b],[-a,b]]
        p1=[[round(x*scale,3),round(y*scale,3)] for x,y in p0]
        sections=[{"z":z0,"points":p0},{"z":z1,"points":p1}]
        contract={"kind":"polygon_loft","sections":sections}
        graph=_graph(family,{"z_end":z1},[{"kind":"polygon_sections","sections":sections}])
        lines=["POLYGON LOFT section Z=0: "+json.dumps(p0),f"section Z={z1}: "+json.dumps(p1),"Smooth loft between closed sections."]
    else:
        w=_f(seed,"w",20,100); h=_f(seed,"h",15,80)
        d1=_f(seed,"d1",5,25); d2=round(d1+_f(seed,"delta",4,20),3)
        oracle.update({"identifiable":False,"ambiguity_parameter":"depth_mm","consistent_alternatives":[d1,d2]})
        contract=None
        graph=_graph(family,{"width":w,"height":h})
        lines=[f"FRONT: rectangle {w} mm x {h} mm","DEPTH DIMENSION AND SIDE VIEW INTENTIONALLY ABSENT.","Return nonidentifiability with a constructive depth ambiguity witness."]
    oracle["reference_constraint_graph"]=graph
    if contract is not None:
        oracle["reference_geometry_contract"]=contract
        oracle["required_geometry_metrics"]=["volume","surface_area","bbox","topology_counts"]
        oracle["metric_tolerances"]=_tol_metrics()
    return {
        "schema":SCHEMA,
        "case_id":cid,
        "drawing_svg":_svg("Engineering drawing — hidden-reference T0 geometry case",lines),
        "declared_output_schema":{"status":"SOLID|NONIDENTIFIABLE","constraint_graph":"object","solid_artifact":"native CAD when status=SOLID"},
        "_oracle":oracle,
    }

def public_case(case:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(case,Mapping) or case.get("schema")!=SCHEMA:
        raise ValueError("invalid case")
    return {k:v for k,v in case.items() if k!="_oracle"}

def generate_post_freeze(commitment:str,beacon:str)->list[dict[str,Any]]:
    return [generate_case(derive_seed(commitment,beacon,f"CAD_T0_GEOMETRY_V1::slot::{i}"),i) for i in range(SLOT_COUNT)]
