"""Bounded event-nominalization support v1.

This checker recognizes one deliberately narrow entailment pattern:

    "The <TIME> launch of the <ENTITY> succeeded."
        entails
    "The <ENTITY> launched in <TIME>."

It does not perform general nominalization, paraphrase, synonymy, world knowledge,
or source authorization. Anything outside the exact grammar remains UNKNOWN.
"""
from __future__ import annotations
import re
from typing import Any

SCHEMA="PROJECT_BRAIN_BOUNDED_EVENT_NOMINALIZATION_SUPPORT_V1"

_CLAIM=re.compile(
    r"^The (?P<entity>[A-Za-z0-9][A-Za-z0-9 _-]*) launched in "
    r"(?P<time>[A-Za-z0-9][A-Za-z0-9 _-]*)\.?$",
    re.I,
)
_EVIDENCE=re.compile(
    r"^The (?P<time>[A-Za-z0-9][A-Za-z0-9 _-]*) launch of the "
    r"(?P<entity>[A-Za-z0-9][A-Za-z0-9 _-]*) succeeded\.?$",
    re.I,
)

def _canon(s:Any)->str:
    return " ".join(str(s if s is not None else "").strip().split()).casefold()

def classify_support(claim_text:str,evidence_text:str,*,evidence_id:str|None=None)->dict[str,Any]:
    cm=_CLAIM.fullmatch(" ".join(str(claim_text).strip().split()))
    em=_EVIDENCE.fullmatch(" ".join(str(evidence_text).strip().split()))
    if cm is None or em is None:
        return {
            "schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
            "reason":"OUTSIDE_EVENT_NOMINALIZATION_GRAMMAR",
            "terminal_authority":False,
        }
    same_entity=_canon(cm.group("entity"))==_canon(em.group("entity"))
    same_time=_canon(cm.group("time"))==_canon(em.group("time"))
    relation="SUPPORTS" if same_entity and same_time else "UNRELATED"
    return {
        "schema":SCHEMA,"status":"RESOLVED","relation":relation,
        "evidence_id":evidence_id,
        "claim_entity":_canon(cm.group("entity")),
        "claim_time":_canon(cm.group("time")),
        "evidence_entity":_canon(em.group("entity")),
        "evidence_time":_canon(em.group("time")),
        "proof_rule":"SUCCESSFUL_LAUNCH_EVENT_NOMINALIZATION_IMPLIES_LAUNCH_EVENT_OCCURRED",
        "scope":"EXACT_LAUNCH_NOMINALIZATION_WITH_ENTITY_AND_TIME_BINDING_ONLY",
        "terminal_authority":False,
    }
