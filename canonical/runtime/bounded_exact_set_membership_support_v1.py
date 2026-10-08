"""Bounded exact set-membership support v1.

Controlled claim surfaces:
- "<item> is in <set>."
- "<item> belongs to <set>."

Controlled evidence surface:
- "<source> states <set> are exactly {A, B, C}."
- "<source> reports that <set> are exactly {A, B, C}."
- "<source>: <set> are exactly {A, B, C}."

The word "exactly" is load-bearing: only a complete explicit enumeration permits
both positive and negative membership conclusions. No open-world absence,
taxonomy, ontology, fuzzy matching, source authority, or world knowledge.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA="PROJECT_BRAIN_BOUNDED_EXACT_SET_MEMBERSHIP_SUPPORT_V1"
_SIMPLE=r"[A-Za-z0-9][A-Za-z0-9 _-]{0,80}"
_CLAIMS=(
    re.compile(rf"^(?P<item>{_SIMPLE})\s+is\s+in\s+(?P<set>{_SIMPLE})\.?$",re.I),
    re.compile(rf"^(?P<item>{_SIMPLE})\s+belongs\s+to\s+(?P<set>{_SIMPLE})\.?$",re.I),
)
_PREFIXES=(
    re.compile(r"^(?P<source>.+?)\s+reports\s+that\s+(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>.+?)\s+states\s+(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>[^:]+):\s*(?P<body>.+)$",re.I),
)
_SET=re.compile(rf"^(?P<set>{_SIMPLE})\s+are\s+exactly\s+\{{(?P<members>[^{{}}]+)\}}\.?$",re.I)

def _canon(x:Any)->str:
    return " ".join(str(x if x is not None else "").strip().split()).casefold()

def parse_membership_claim(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"CLAIM_TEXT_REQUIRED","claim_in_scope":False}
    raw=" ".join(text.strip().split())
    for pat in _CLAIMS:
        m=pat.fullmatch(raw)
        if m:
            return {"schema":SCHEMA,"status":"RESOLVED","claim_in_scope":True,
                    "item":_canon(m.group("item")),"set":_canon(m.group("set")),
                    "terminal_authority":False}
    return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"CLAIM_OUTSIDE_EXACT_MEMBERSHIP_GRAMMAR","claim_in_scope":False}

def _parse_exact_set(text:str,*,default_source:str|None=None)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"status":"FAIL_CLOSED","reason":"EVIDENCE_TEXT_REQUIRED"}
    raw=" ".join(text.strip().split())
    source=default_source;body=raw
    for pat in _PREFIXES:
        m=pat.fullmatch(raw)
        if m:
            source=" ".join(m.group("source").split());body=m.group("body");break
    m=_SET.fullmatch(body)
    if not m:
        return {"status":"UNRESOLVED","reason":"EVIDENCE_OUTSIDE_EXACT_SET_ENUMERATION_GRAMMAR"}
    pieces=[_canon(x) for x in m.group("members").split(",")]
    if not pieces or any(not x for x in pieces):
        return {"status":"FAIL_CLOSED","reason":"SET_MEMBER_EMPTY"}
    if len(pieces)!=len(set(pieces)):
        return {"status":"FAIL_CLOSED","reason":"SET_MEMBER_DUPLICATE"}
    return {"status":"RESOLVED","set":_canon(m.group("set")),"members":sorted(pieces),"source":source}

def classify_support(claim_text:str,evidence_text:str,*,evidence_id:str|None=None)->dict[str,Any]:
    claim=parse_membership_claim(claim_text)
    if claim.get("status")!="RESOLVED":
        return {"schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
                "claim_in_scope":bool(claim.get("claim_in_scope")),"reason":claim.get("reason"),
                "terminal_authority":False}
    ev=_parse_exact_set(evidence_text,default_source=evidence_id or "EVIDENCE")
    if ev.get("status")!="RESOLVED":
        return {"schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN","claim_in_scope":True,
                "reason":ev.get("reason"),"terminal_authority":False}
    if ev["set"]!=claim["set"]:
        relation="UNRELATED"
    else:
        relation="SUPPORTS" if claim["item"] in set(ev["members"]) else "CONFLICTS"
    return {"schema":SCHEMA,"status":"RESOLVED","relation":relation,"claim_in_scope":True,
            "claim":{"item":claim["item"],"set":claim["set"]},
            "evidence":{"set":ev["set"],"members":ev["members"],"source":ev["source"]},
            "terminal_authority":False,
            "scope":"EXACT_COMPLETE_SET_ENUMERATION_MEMBERSHIP_ONLY"}
