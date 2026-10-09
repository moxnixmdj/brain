"""Certified explicit effect-ID inventory fragment V1.

Recognizes standalone declarations of the exact form:

    Effect IDs only for reporting.threshold: B.t, C.t.

Multiple declarations for different targets are allowed. Duplicate declarations
for the same target are rejected. The parser proves only the literal declared
set of possible effect identifiers for that target.

It does not prove the meaning/value/class of those effects.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any

SCHEMA="BRAIN_CERTIFIED_EFFECT_ID_INVENTORY_V1"
_LINE=re.compile(
    r"^\s*Effect\s+IDs\s+only\s+for\s+"
    r"(?P<target>[A-Za-z][A-Za-z0-9_.-]*)\s*:\s*"
    r"(?P<ids>[A-Za-z][A-Za-z0-9_.-]*(?:\s*,\s*[A-Za-z][A-Za-z0-9_.-]*)*)"
    r"\s*\.?\s*$",
    re.I,
)

def parse_effect_id_inventories(text:str,*,source:str="source")->dict[str,Any]:
    if not isinstance(text,str) or not text:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "reason":"SOURCE_TEXT_MISSING","terminal_authority":False,
        }
    if not isinstance(source,str) or not source.strip():
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "reason":"SOURCE_ID_MISSING","terminal_authority":False,
        }

    rows={}
    offset=0
    for line in text.splitlines(keepends=True):
        body=line.rstrip("\r\n")
        m=_LINE.fullmatch(body)
        if m:
            target=m.group("target")
            raw_ids=[x.strip() for x in m.group("ids").split(",")]
            ids=sorted(set(raw_ids))
            if len(ids)!=len(raw_ids):
                return {
                    "schema":SCHEMA,"status":"UNRESOLVED",
                    "reason":"DUPLICATE_EFFECT_ID_IN_DECLARATION",
                    "target_id":target,
                    "terminal_authority":False,
                }
            if target in rows:
                return {
                    "schema":SCHEMA,"status":"UNRESOLVED",
                    "reason":"DUPLICATE_TARGET_INVENTORY_DECLARATION",
                    "target_id":target,
                    "terminal_authority":False,
                }
            start=offset
            end=offset+len(body)
            digest=sha256(body.encode("utf-8")).hexdigest()
            inventory_id="EFFECT-INVENTORY-"+sha256(
                f"{source}\0{target}\0{start}\0{end}\0{','.join(ids)}".encode("utf-8")
            ).hexdigest()[:20]
            rows[target]={
                "inventory_id":inventory_id,
                "source_id":source,
                "target_id":target,
                "effect_ids":ids,
                "source_span":[start,end],
                "source_text_sha256":digest,
            }
        offset+=len(line)

    return {
        "schema":SCHEMA,
        "status":"PARSED",
        "inventories":[rows[k] for k in sorted(rows)],
        "terminal_authority":False,
        "scope":"EXPLICIT_DECLARED_EFFECT_ID_INVENTORY_ONLY",
    }
