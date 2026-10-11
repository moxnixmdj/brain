"""Deterministic comparative visual disambiguation over V13 region candidates."""
from __future__ import annotations

import re
from typing import Any, Mapping

from canonical.runtime.osworld_v21_visual_policy_overlay_v1 import _target
from canonical.runtime.osworld_v21_visual_region_grounding_v1 import ground_visual_region

SCHEMA="PROJECT_BRAIN_OSWORLD_V21_VISUAL_RELATIONAL_GROUNDING_V1"

_RELATIONS=(
    ("largest", "area", -1),
    ("smallest", "area", 1),
    ("leftmost", "x", 1),
    ("rightmost", "x", -1),
    ("topmost", "y", 1),
    ("bottommost", "y", -1),
)

def _relation(instruction:str)->tuple[str,str,int]|None:
    low=instruction.casefold()
    found=[row for row in _RELATIONS if re.search(r"\b"+row[0]+r"\b",low)]
    return found[0] if len(found)==1 else None

def _metric(candidate:Mapping[str,Any], key:str)->float:
    if key=="area":
        return float(candidate.get("grid_area") or 0)
    center=candidate.get("center")
    if not isinstance(center,Mapping):
        raise ValueError("CENTER_REQUIRED")
    return float(center["x" if key=="x" else "y"])

def route_relational_visual(state:Mapping[str,Any])->dict[str,Any]|None:
    instruction=state.get("instruction")
    screenshot=state.get("screenshot_bytes")
    if not isinstance(instruction,str) or not isinstance(screenshot,(bytes,bytearray)):
        return None
    rel=_relation(instruction)
    if rel is None:
        return None
    target=_target(instruction)
    if target is None:
        return None

    out=ground_visual_region(
        bytes(screenshot),
        color=target["color"],
        shape=target["shape"],
        spatial=target["spatial"],
    )
    candidates=out.get("candidates")
    if not isinstance(candidates,list) or not candidates:
        return {
            "response":"comparative visual target has no candidates",
            "actions":[{"type":"WAIT"}],
            "_policy_receipt":{
                "schema":SCHEMA,"route":"VISUAL_RELATION_UNRESOLVED",
                "relation":rel[0],"reason":"NO_CANDIDATES",
            },
        }

    name,key,direction=rel
    scored=[(_metric(c,key),i,c) for i,c in enumerate(candidates)]
    scored.sort(key=lambda row:row[0],reverse=direction<0)
    best=scored[0]
    if len(scored)>1 and best[0]==scored[1][0]:
        return {
            "response":"comparative visual relation is tied",
            "actions":[{"type":"WAIT"}],
            "_policy_receipt":{
                "schema":SCHEMA,"route":"VISUAL_RELATION_UNRESOLVED",
                "relation":name,"reason":"TIED_EXTREME",
                "candidate_count":len(candidates),
            },
        }

    point=best[2].get("center")
    if not isinstance(point,Mapping):
        return None
    return {
        "response":"click uniquely ranked visual target",
        "actions":[{"type":"CLICK","x":int(point["x"]),"y":int(point["y"])}],
        "_policy_receipt":{
            "schema":SCHEMA,
            "route":"COMPARATIVE_VISUAL_REGION_CLICK",
            "relation":name,
            "target":dict(target),
            "candidate_count":len(candidates),
            "selected_rank":1,
        },
    }
