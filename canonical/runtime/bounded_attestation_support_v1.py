"""Bounded exact-proposition attestation support v1.

Supports arbitrary proposition text only when an evidence unit explicitly states
or denies that exact normalized proposition. This is lexical attestation, not
paraphrase entailment, factual truth, or source authority.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA="PROJECT_BRAIN_BOUNDED_ATTESTATION_SUPPORT_V1"

_POS=(
    re.compile(r"^(?P<source>.+?)\s+states\s+that\s+(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>.+?)\s+reports\s+that\s+(?P<body>.+)$",re.I),
)
_NEG=(
    re.compile(r"^(?P<source>.+?)\s+denies\s+that\s+(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>.+?)\s+rejects\s+that\s+(?P<body>.+)$",re.I),
)

def _canon(value:Any)->str:
    s=" ".join(str(value if value is not None else "").strip().split())
    if s.endswith("."): s=s[:-1].rstrip()
    return s.casefold()

def classify_support(claim_text:str,evidence_text:str,*,evidence_id:str|None=None)->dict[str,Any]:
    claim=_canon(claim_text)
    if not claim:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"CLAIM_TEXT_REQUIRED","terminal_authority":False}
    raw=" ".join(str(evidence_text if evidence_text is not None else "").strip().split())
    if not raw:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"EVIDENCE_TEXT_REQUIRED","terminal_authority":False}
    polarity=None; source=None; body=None
    for p in _POS:
        m=p.fullmatch(raw)
        if m:
            polarity="SUPPORTS";source=m.group("source");body=m.group("body");break
    if polarity is None:
        for p in _NEG:
            m=p.fullmatch(raw)
            if m:
                polarity="CONFLICTS";source=m.group("source");body=m.group("body");break
    if polarity is None:
        return {
            "schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
            "reason":"OUTSIDE_EXACT_ATTESTATION_GRAMMAR",
            "terminal_authority":False,
        }
    proposition=_canon(body)
    relation=polarity if proposition==claim else "UNRELATED"
    return {
        "schema":SCHEMA,"status":"RESOLVED","relation":relation,
        "claim_normalized":claim,"evidence_proposition_normalized":proposition,
        "evidence_source":" ".join(source.split()),"evidence_id":evidence_id,
        "terminal_authority":False,
        "scope":"EXACT_NORMALIZED_PROPOSITION_ATTESTATION_OR_DENIAL_ONLY",
    }
