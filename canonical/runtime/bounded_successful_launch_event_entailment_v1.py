"""Bounded successful-launch event entailment v1.

This is deliberately one tiny event-nominalization rule extracted from the
current P3 paraphrase counterexample.

Evidence grammar:
    "The <TIME> launch of the <ENTITY> succeeded."

Claim grammar:
    "The <ENTITY> launched in <TIME>."

For an exact entity/time match the evidence is compiled to:
    exists e: launch(e, ENTITY) & time(e, TIME) & succeeded(e)
and the claim to:
    exists e: launch(e, ENTITY) & time(e, TIME)

The entailment is checked by conjunction weakening. No other nominalization,
tense, causality, planned/attempted/failed event, synonym, or world knowledge
is inferred.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA="PROJECT_BRAIN_BOUNDED_SUCCESSFUL_LAUNCH_EVENT_ENTAILMENT_V1"

_CLAIM=re.compile(
    r"^The\s+(?P<entity>[A-Za-z][A-Za-z0-9 _-]*?)\s+launched\s+in\s+"
    r"(?P<time>[A-Za-z][A-Za-z0-9 _-]*?)\s*\.?$",
    re.I,
)
_EVIDENCE=re.compile(
    r"^The\s+(?P<time>[A-Za-z][A-Za-z0-9 _-]*?)\s+launch\s+of\s+the\s+"
    r"(?P<entity>[A-Za-z][A-Za-z0-9 _-]*?)\s+succeeded\s*\.?$",
    re.I,
)

def _norm(x:Any)->str:
    return " ".join(str(x if x is not None else "").strip().casefold().split())

def _parse_claim(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"status":"FAIL_CLOSED","reason":"CLAIM_TEXT_REQUIRED"}
    m=_CLAIM.fullmatch(" ".join(text.strip().split()))
    if not m:
        return {"status":"UNRESOLVED","reason":"CLAIM_OUTSIDE_SUCCESSFUL_LAUNCH_EVENT_GRAMMAR"}
    return {"status":"RESOLVED","entity":_norm(m.group("entity")),"time":_norm(m.group("time"))}

def _parse_evidence(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"status":"FAIL_CLOSED","reason":"EVIDENCE_TEXT_REQUIRED"}
    m=_EVIDENCE.fullmatch(" ".join(text.strip().split()))
    if not m:
        return {"status":"UNRESOLVED","reason":"EVIDENCE_OUTSIDE_SUCCESSFUL_LAUNCH_EVENT_GRAMMAR"}
    return {"status":"RESOLVED","entity":_norm(m.group("entity")),"time":_norm(m.group("time"))}

def classify_support(claim_text:str,evidence_text:str,*,evidence_id:str|None=None)->dict[str,Any]:
    claim=_parse_claim(claim_text)
    evidence=_parse_evidence(evidence_text)
    if claim.get("status")!="RESOLVED" or evidence.get("status")!="RESOLVED":
        return {
            "schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
            "claim_parse":claim.get("status"),"evidence_parse":evidence.get("status"),
            "reason":claim.get("reason") if claim.get("status")!="RESOLVED" else evidence.get("reason"),
            "terminal_authority":False,
        }

    same_entity=claim["entity"]==evidence["entity"]
    same_time=claim["time"]==evidence["time"]
    if not (same_entity and same_time):
        return {
            "schema":SCHEMA,"status":"RESOLVED","relation":"UNRELATED",
            "claim":{"entity":claim["entity"],"time":claim["time"]},
            "evidence":{"entity":evidence["entity"],"time":evidence["time"],"evidence_id":evidence_id},
            "terminal_authority":False,
        }

    atoms=[
        f"launch(e,{evidence['entity']})",
        f"time(e,{evidence['time']})",
        "succeeded(e)",
    ]
    claim_atoms=atoms[:2]
    assert set(claim_atoms).issubset(set(atoms))
    return {
        "schema":SCHEMA,
        "status":"RESOLVED",
        "relation":"SUPPORTS",
        "claim":{"entity":claim["entity"],"time":claim["time"]},
        "evidence":{"entity":evidence["entity"],"time":evidence["time"],"evidence_id":evidence_id},
        "compiled_evidence_formula":{
            "quantifier":"EXISTS","variable":"e","conjunction":atoms,
        },
        "compiled_claim_formula":{
            "quantifier":"EXISTS","variable":"e","conjunction":claim_atoms,
        },
        "proof":{
            "rule":"EXISTENTIAL_CONJUNCTION_WEAKENING",
            "dropped_atoms":["succeeded(e)"],
            "checked_subset":True,
        },
        "linguistic_rule":{
            "id":"SUCCESSFUL_LAUNCH_NOMINALIZATION_V1",
            "surface_lock":"THE_<TIME>_LAUNCH_OF_THE_<ENTITY>_SUCCEEDED",
            "claim_lock":"THE_<ENTITY>_LAUNCHED_IN_<TIME>",
        },
        "terminal_authority":False,
        "scope":"EXACT_SUCCESSFUL_LAUNCH_EVENT_NOMINALIZATION_ONLY",
    }
