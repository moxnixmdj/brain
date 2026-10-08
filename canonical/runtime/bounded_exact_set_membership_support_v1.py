"""Bounded exact set-membership support v1.

Controlled claim grammar:
    "<ITEM> is a member of <SET>."

Controlled evidence grammars:
    "<SET> contains <ITEM>."
    "The complete members of <SET> are {<ITEM1>, <ITEM2>, ...}."

Optional evidence source prefixes:
    "<SOURCE> states that ..."
    "<SOURCE> reports that ..."

A positive contains statement can prove membership of the named item but cannot
prove non-membership of anything else. A complete-members enumeration can prove
both membership and non-membership. No taxonomy, subclass, synonymy, fuzzy
category, or world-knowledge membership is inferred.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA="PROJECT_BRAIN_BOUNDED_EXACT_SET_MEMBERSHIP_SUPPORT_V1"

_CLAIM=re.compile(
    r"^(?P<item>[A-Za-z0-9][A-Za-z0-9 _.-]*?)\s+is\s+a\s+member\s+of\s+"
    r"(?P<set>[A-Za-z0-9][A-Za-z0-9 _.-]*?)\s*\.?$",
    re.I,
)
_CONTAINS=re.compile(
    r"^(?P<set>[A-Za-z0-9][A-Za-z0-9 _.-]*?)\s+contains\s+"
    r"(?P<item>[A-Za-z0-9][A-Za-z0-9 _.-]*?)\s*\.?$",
    re.I,
)
_COMPLETE=re.compile(
    r"^The\s+complete\s+members\s+of\s+"
    r"(?P<set>[A-Za-z0-9][A-Za-z0-9 _.-]*?)\s+are\s+\{(?P<members>[^{}]*)\}\s*\.?$",
    re.I,
)
_PREFIXES=(
    re.compile(r"^(?P<source>.+?)\s+states\s+that\s+(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>.+?)\s+reports\s+that\s+(?P<body>.+)$",re.I),
)

def _norm(x:Any)->str:
    return " ".join(str(x if x is not None else "").strip().casefold().split())

def _strip_source(text:str)->tuple[str|None,str]:
    raw=" ".join(text.strip().split())
    for pat in _PREFIXES:
        m=pat.fullmatch(raw)
        if m:
            return " ".join(m.group("source").split()),m.group("body")
    return None,raw

def _parse_claim(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"status":"FAIL_CLOSED","reason":"CLAIM_TEXT_REQUIRED"}
    m=_CLAIM.fullmatch(" ".join(text.strip().split()))
    if not m:
        return {"status":"UNRESOLVED","reason":"CLAIM_OUTSIDE_EXACT_SET_MEMBERSHIP_GRAMMAR"}
    return {"status":"RESOLVED","item":_norm(m.group("item")),"set":_norm(m.group("set"))}

def _parse_members(raw:str)->tuple[list[str]|None,str|None]:
    if not raw.strip():
        return [],None
    parts=[_norm(x) for x in raw.split(",")]
    if any(not x for x in parts):
        return None,"EMPTY_MEMBER_TOKEN"
    if len(parts)!=len(set(parts)):
        return None,"DUPLICATE_MEMBER_TOKEN"
    return parts,None

def _parse_evidence(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"status":"FAIL_CLOSED","reason":"EVIDENCE_TEXT_REQUIRED"}
    source,body=_strip_source(text)
    m=_COMPLETE.fullmatch(body)
    if m:
        members,error=_parse_members(m.group("members"))
        if error:
            return {"status":"FAIL_CLOSED","reason":error}
        return {
            "status":"RESOLVED","kind":"COMPLETE_SET",
            "set":_norm(m.group("set")),"members":members,"source":source,
        }
    m=_CONTAINS.fullmatch(body)
    if m:
        return {
            "status":"RESOLVED","kind":"POSITIVE_MEMBER",
            "set":_norm(m.group("set")),"item":_norm(m.group("item")),"source":source,
        }
    return {"status":"UNRESOLVED","reason":"EVIDENCE_OUTSIDE_EXACT_SET_MEMBERSHIP_GRAMMAR"}

def classify_support(claim_text:str,evidence_text:str,*,evidence_id:str|None=None)->dict[str,Any]:
    claim=_parse_claim(claim_text)
    evidence=_parse_evidence(evidence_text)
    if claim.get("status")=="FAIL_CLOSED" or evidence.get("status")=="FAIL_CLOSED":
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","relation":"UNKNOWN",
            "reason":claim.get("reason") if claim.get("status")=="FAIL_CLOSED" else evidence.get("reason"),
            "terminal_authority":False,
        }
    if claim.get("status")!="RESOLVED" or evidence.get("status")!="RESOLVED":
        return {
            "schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
            "reason":claim.get("reason") if claim.get("status")!="RESOLVED" else evidence.get("reason"),
            "terminal_authority":False,
        }
    if claim["set"]!=evidence["set"]:
        return {
            "schema":SCHEMA,"status":"RESOLVED","relation":"UNRELATED",
            "claim":claim,"evidence_kind":evidence["kind"],"terminal_authority":False,
        }

    if evidence["kind"]=="POSITIVE_MEMBER":
        if claim["item"]==evidence["item"]:
            relation="SUPPORTS"
            proof={"rule":"EXPLICIT_POSITIVE_SET_MEMBERSHIP","member":claim["item"],"set":claim["set"]}
        else:
            relation="UNRELATED"
            proof={"rule":"OPEN_WORLD_POSITIVE_MEMBERSHIP_DOES_NOT_PROVE_ABSENCE"}
    else:
        members=set(evidence["members"])
        relation="SUPPORTS" if claim["item"] in members else "CONFLICTS"
        proof={
            "rule":"COMPLETE_FINITE_SET_MEMBERSHIP_DECISION",
            "member":claim["item"],"set":claim["set"],
            "complete_members":sorted(members),
            "membership":claim["item"] in members,
        }

    return {
        "schema":SCHEMA,"status":"RESOLVED","relation":relation,
        "claim":{"item":claim["item"],"set":claim["set"]},
        "evidence":{
            "kind":evidence["kind"],"source":evidence.get("source"),
            "evidence_id":evidence_id,
            **({"item":evidence["item"]} if evidence["kind"]=="POSITIVE_MEMBER" else {"members":evidence["members"]}),
        },
        "proof":proof,
        "terminal_authority":False,
        "scope":"EXACT_CONTROLLED_SET_MEMBERSHIP_ONLY",
    }
