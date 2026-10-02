"""Deterministic grounding for normalized DOM/accessibility-state actions.

This owns only the exact-match subset: the desired action and target constraints are
already normalized, and visible/enabled elements expose structured role/name/text/attrs
plus supported actions. Ambiguous or fuzzy cases fail closed.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence

@dataclass(frozen=True)
class Element:
    element_id:str
    role:str|None
    name:str|None
    text:str|None
    attrs:Mapping[str,str]
    actions:frozenset[str]
    visible:bool=True
    enabled:bool=True

@dataclass(frozen=True)
class GroundRequest:
    action:str
    role:str|None=None
    name:str|None=None
    text:str|None=None
    attrs:Mapping[str,str]|None=None

def ground_exact_action(req:GroundRequest,elements:Sequence[Element])->dict:
    if not req.action or not isinstance(req.action,str):
        return {"status":"ESCALATE","reason":"ACTION_INVALID"}
    ids=[e.element_id for e in elements]
    if any(not isinstance(x,str) or not x for x in ids) or len(ids)!=len(set(ids)):
        return {"status":"ESCALATE","reason":"ELEMENT_IDENTITIES_INVALID_OR_DUPLICATE"}
    wanted=dict(req.attrs or {})
    cands=[]
    for e in elements:
        if not e.visible or not e.enabled or req.action not in e.actions:
            continue
        if req.role is not None and e.role!=req.role: continue
        if req.name is not None and e.name!=req.name: continue
        if req.text is not None and e.text!=req.text: continue
        if any(e.attrs.get(k)!=v for k,v in wanted.items()): continue
        cands.append(e)
    if len(cands)==1:
        return {
            "status":"SELECT",
            "element_id":cands[0].element_id,
            "action":req.action,
            "reason":"UNIQUE_EXACT_STRUCTURED_MATCH",
            "terminal_authority":False,
        }
    return {
        "status":"ESCALATE",
        "reason":"NO_EXACT_MATCH" if not cands else "AMBIGUOUS_EXACT_MATCH",
        "candidate_ids":sorted(e.element_id for e in cands),
        "terminal_authority":False,
    }
