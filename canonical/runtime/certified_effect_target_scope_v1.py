"""Certified explicit document-effect target-scope fragment V1.

This parser recognizes only an exact source declaration of the form:

    Effect targets only: target.one, target.two.

The declaration may appear as one standalone non-empty line inside a larger
document. Exactly one such declaration is allowed. Target identifiers are
restricted tokens. The parser proves only the literal declared target set and
its source span. It does not prove effect values, effect classes, reference
resolution, or that any unrecognized prose is semantically inert.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any

SCHEMA="BRAIN_CERTIFIED_EFFECT_TARGET_SCOPE_V1"
_TOKEN=r"(?:[A-Za-z]|[A-Za-z][A-Za-z0-9_.-]*[A-Za-z0-9_])"
_LINE=re.compile(
    rf"^\s*Effect\s+targets\s+only:\s*"
    rf"(?P<targets>{_TOKEN}(?:\s*,\s*{_TOKEN})*)"
    rf"\s*\.?\s*$",
    re.I,
)

def _fail(status:str,reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "reason":reason,
        "terminal_authority":False,
        **extra,
    }

def parse_effect_target_scope(text:str,*,source:str="source")->dict[str,Any]:
    if not isinstance(text,str) or not text:
        return _fail("FAIL_CLOSED","SOURCE_TEXT_MISSING")
    if not isinstance(source,str) or not source.strip():
        return _fail("FAIL_CLOSED","SOURCE_ID_MISSING")

    matches=[]
    offset=0
    for line in text.splitlines(keepends=True):
        body=line.rstrip("\r\n")
        m=_LINE.fullmatch(body)
        if m:
            start=offset
            end=offset+len(body)
            raw_targets=[x.strip() for x in m.group("targets").split(",")]
            targets=sorted(set(raw_targets))
            if len(targets)!=len(raw_targets):
                return _fail("UNRESOLVED","DUPLICATE_TARGET_IN_SCOPE_DECLARATION")
            matches.append((start,end,targets,body))
        offset+=len(line)

    if len(matches)!=1:
        return _fail(
            "UNRESOLVED",
            "EXACTLY_ONE_EFFECT_TARGET_SCOPE_DECLARATION_REQUIRED",
            declaration_count=len(matches),
        )

    start,end,targets,body=matches[0]
    digest=sha256(body.encode("utf-8")).hexdigest()
    scope_id="EFFECT-SCOPE-"+sha256(
        f"{source}\0{start}\0{end}\0{','.join(targets)}".encode("utf-8")
    ).hexdigest()[:20]
    return {
        "schema":SCHEMA,
        "status":"PARSED",
        "parse":{
            "scope_id":scope_id,
            "source_id":source,
            "source_span":[start,end],
            "source_text_sha256":digest,
            "target_ids":targets,
        },
        "terminal_authority":False,
        "scope":"EXPLICIT_DECLARED_EFFECT_TARGET_SET_ONLY",
    }
