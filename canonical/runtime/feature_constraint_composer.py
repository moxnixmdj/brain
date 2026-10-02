"""Compose parsed engineering annotations into a conflict-checked feature constraint graph.

This module starts after OCR/symbol parsing and callout-to-geometry association.
It owns deterministic composition: multiple annotations on one feature become a
conjunctive constraint set; incompatible claims fail closed instead of relying on
last-write-wins behavior.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

SCHEMA="BRAIN_FEATURE_CONSTRAINT_COMPOSER_V1"

def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _claims_from_annotation(a:Mapping[str,Any])->list[tuple[str,Any]]:
    kind=a.get("kind")
    if kind=="hole_or_cylindrical_feature":
        out=[("diameter",{"value":a.get("diameter"),"units":a.get("units")})]
        if a.get("through") is True:
            out.append(("extent",{"through":True}))
        if a.get("depth") is not None:
            out.append(("extent",{"depth":a.get("depth"),"units":a.get("depth_units")}))
        if a.get("counterbore") is not None:
            out.append(("counterbore",a.get("counterbore")))
        if a.get("countersink") is not None:
            out.append(("countersink",a.get("countersink")))
        if a.get("quantity") not in (None,1):
            out.append(("quantity",int(a.get("quantity"))))
        return out
    if kind=="thread":
        return [("thread",{
            "standard":a.get("standard"),
            "major_diameter":a.get("major_diameter"),
            "pitch":a.get("pitch"),
            "depth":a.get("depth"),
            "units":a.get("units"),
            "quantity":a.get("quantity",1),
        })]
    if kind=="radius_feature":
        return [("radius",{
            "value":a.get("radius"),"units":a.get("units"),"quantity":a.get("quantity",1)
        })]
    if kind=="diameter":
        return [("diameter",{"value":a.get("value"),"units":a.get("units")})]
    if kind=="radius":
        return [("radius",{"value":a.get("value"),"units":a.get("units")})]
    if kind=="linear":
        return [("linear_dimension",{"value":a.get("value"),"units":a.get("units")})]
    if kind in {"symmetric_tolerance","asymmetric_tolerance"}:
        return [("size_tolerance",{
            "nominal":a.get("value"),
            "upper_deviation":a.get("upper_deviation"),
            "lower_deviation":a.get("lower_deviation"),
            "units":a.get("units"),
        })]
    if kind=="gdt":
        char=a.get("characteristic")
        if not isinstance(char,str) or not char:
            raise ValueError("gdt characteristic missing")
        return [(f"gdt:{char}",{
            "tolerance":a.get("tolerance"),
            "diametrical_zone":a.get("diametrical_zone",False),
            "units":a.get("units"),
            "datums":a.get("datums",[]),
        })]
    if kind=="datum":
        return [("datum_label",a.get("datum"))]
    raise ValueError(f"unsupported annotation kind: {kind}")

def compose_feature_constraints(rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)):
        raise ValueError("rows must be a sequence")
    features:dict[str,dict[str,Any]]={}
    provenance:dict[str,dict[str,list[str]]]={}
    errors=[]
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            errors.append(f"ROW_NOT_OBJECT:{i}"); continue
        target=row.get("target_id")
        ann=row.get("annotation")
        source_id=str(row.get("source_id",f"row:{i}"))
        if not isinstance(target,str) or not target:
            errors.append(f"TARGET_ID_INVALID:{i}"); continue
        if not isinstance(ann,Mapping) or ann.get("status")!="PARSED":
            errors.append(f"ANNOTATION_NOT_PARSED:{i}"); continue
        try:
            claims=_claims_from_annotation(ann)
        except Exception as exc:
            errors.append(f"ANNOTATION_UNSUPPORTED:{i}:{type(exc).__name__}:{exc}"); continue
        target_map=features.setdefault(target,{})
        prov_map=provenance.setdefault(target,{})
        for prop,val in claims:
            if prop in target_map and _canon(target_map[prop])!=_canon(val):
                errors.append(f"CONFLICT:{target}:{prop}")
                continue
            target_map[prop]=val
            prov_map.setdefault(prop,[]).append(source_id)
    if errors:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":sorted(set(errors)),
            "partial_features":features,
            "terminal_authority":False,
        }
    return {
        "schema":SCHEMA,"status":"COMPOSED",
        "feature_count":len(features),
        "features":features,
        "provenance":provenance,
        "terminal_authority":False,
        "scope":"CONJUNCTIVE_COMPOSITION_OF_SUPPORTED_PARSED_AND_ASSOCIATED_ENGINEERING_ANNOTATIONS",
    }
