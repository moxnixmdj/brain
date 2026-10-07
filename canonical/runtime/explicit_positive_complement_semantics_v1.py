"""One-sided explicit positive task-complement semantics.

Recognizes only source-explicit addressee actions/constraints missed by the
existing modal + imperative parsers. It never claims whole-task completeness,
argument semantics, policy adequacy, or terminal authority.
"""
from __future__ import annotations
import re
from hashlib import sha256
from typing import Any

SCHEMA="BRAIN_EXPLICIT_POSITIVE_COMPLEMENT_V1"
WORD=r"[A-Za-z][A-Za-z-]*"
PATS=(
 ("PASSIVE_ASK",re.compile(r"\byou(?:'|’)ve\s+been\s+asked\s+to\s+(?P<v>"+WORD+r")\b",re.I)),
 ("ASKED_YOU",re.compile(r"\b(?:has\s+|have\s+)?asked\s+you\s+to\s+(?P<v>"+WORD+r")\b",re.I)),
 ("REQUESTED_THAT_YOU",re.compile(r"\b(?:has\s+|have\s+)?requested\s+that\s+you\s+(?P<v>"+WORD+r")\b",re.I)),
 ("YOU_DEONTIC",re.compile(r"\byou\s+(?:(?:will\s+(?:first\s+|then\s+|also\s+)?)?need\s+to|are\s+required\s+to|should|will(?:\s+also)?)\s+(?P<v>"+WORD+r")\b",re.I)),
 ("ROLE_TO",re.compile(r"\byour\s+(?:responsibility|job|role|goal)\s+(?:is|are)\s+to\s+(?P<v>"+WORD+r")\b",re.I)),
 ("GOAL_TO",re.compile(r"\b(?:the\s+(?:overall\s+)?goal|the\s+goal\s+of\s+this\s+project)\s+is\s+to\s+(?P<v>"+WORD+r")\b",re.I)),
 ("TASKED_TO",re.compile(r"\byou\s+(?:are|have\s+been)\s+tasked(?:\s+as\s+[^,.]+)?\s+to\s+(?P<v>"+WORD+r")\b",re.I)),
 ("TASKED_WITH",re.compile(r"\byou\s+(?:are|have\s+been)\s+tasked(?:\s+as\s+[^,.]+)?\s+with\s+(?P<v>"+WORD+r")\b",re.I)),
 ("PLEASE",re.compile(r"\bplease\s+(?:\d+\)\s*)?(?P<v>"+WORD+r")\b",re.I)),
 ("CONTEXT_IMPERATIVE",re.compile(r"^(?:Accordingly|To this end|Based on (?:the )?findings|Leveraging [^,]+),\s*(?:please\s+)?(?P<v>"+WORD+r")\b",re.I)),
 ("USING_YOU_WILL",re.compile(r"^Using\s+[^,]+,\s+you\s+will(?:\s+also)?\s+(?P<v>"+WORD+r")\b",re.I)),
 ("USING_IMPERATIVE",re.compile(r"^Using\s+[^,]+,\s*(?:please\s+)?(?P<v>"+WORD+r")\b",re.I)),
 ("DELIVERABLE_SHOULD",re.compile(r"\b(?:the|this|your)\s+(?:final\s+)?(?:product|plan|deliverable|document|content|review|memo|spreadsheet|email|guide|schedule|writing)\s+should\s+(?P<v>"+WORD+r")\b",re.I)),
 ("BE_SURE_TO",re.compile(r"^Be\s+sure\s+to\s+(?P<v>"+WORD+r")\b",re.I)),
 ("BULLET_IMPERATIVE",re.compile(r"^\s*[-*•]\s*(?P<v>"+WORD+r")\b",re.I)),
)
BOUNDARY=re.compile(r"(?<=[.!?])\s+(?=(?:[-*•]+\s*|\d+[.)]\s*|[A-Z][A-Za-z]))")

def segments(text:str)->list[str]:
    if not isinstance(text,str) or not text.strip(): return []
    out=[]
    for raw in re.split(r"\n+",text):
        line=raw.strip()
        if line: out.extend(x.strip() for x in BOUNDARY.split(line) if x.strip())
    return out

def extract(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"EMPTY_SOURCE","terminal_authority":False}
    rows=[]
    for i,seg in enumerate(segments(text)):
        for kind,rx in PATS:
            m=rx.search(seg)
            if not m: continue
            verb=m.group("v").lower()
            s,e=m.span("v")
            # Bind only the matched source construction and verb. Everything
            # after the head remains opaque, so coordination cannot be invented.
            rows.append({"segment_index":i,"construction":kind,"action_head":verb,
                         "action_head_span_in_segment":[s,e],
                         "segment_sha256":sha256(seg.encode()).hexdigest()})
            break
    return {"schema":SCHEMA,"status":"POSITIVE_UNITS_FOUND" if rows else "UNRESOLVED",
            "positive_unit_count":len(rows),"positive_units":rows,
            "absence_proves_no_positive_semantics":False,
            "whole_task_semantics_proved":False,"policy_adequacy_proved":False,
            "terminal_authority":False}
