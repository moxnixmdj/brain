"""Certified controlled-natural semantic subsumption source V1.

Recognized standalone sentence:
  In scope <scope_id>, every <source_id> is a <target_id>.

Semantics inside the declared scope:
  extension(source_id) ⊆ extension(target_id)

Only exact ASCII token ids are accepted. The parser extracts source-aligned
positive subsumption edges; it grants no open-world completeness and no negative
entailment.
"""
from __future__ import annotations
from hashlib import sha256
import re
from typing import Any

SCHEMA="BRAIN_CERTIFIED_NATURAL_SEMANTIC_SUBSUMPTION_SOURCE_V1"
TOK=r"[A-Za-z0-9_.:-]+"
PAT=re.compile(
    rf"^In scope (?P<scope>{TOK}), every (?P<src>{TOK}) is a (?P<dst>{TOK})\.$"
)

def parse(text:str,*,source_id:str="source")->dict[str,Any]:
    if not isinstance(text,str) or not text:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "reason":"SOURCE_TEXT_MISSING","terminal_authority":False,
        }
    if not isinstance(source_id,str) or not source_id.strip():
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "reason":"SOURCE_ID_MISSING","terminal_authority":False,
        }

    edges=[]; seen=set(); char=0; byte=0
    for line in text.splitlines(keepends=True):
        body=line.rstrip("\r\n")
        raw=body.encode("utf-8")
        m=PAT.match(body)
        if m:
            scope=m.group("scope")
            src=m.group("src")
            dst=m.group("dst")
            if src==dst:
                return {
                    "schema":SCHEMA,"status":"FAIL_CLOSED",
                    "reason":"SELF_SUBSUMPTION_DECLARATION_FORBIDDEN",
                    "terminal_authority":False,
                }
            key=(scope,src,dst)
            if key in seen:
                return {
                    "schema":SCHEMA,"status":"FAIL_CLOSED",
                    "reason":"DUPLICATE_SUBSUMPTION_DECLARATION",
                    "terminal_authority":False,
                }
            seen.add(key)
            edges.append({
                "scope_id":scope,
                "source_id":src,
                "target_id":dst,
                "declaration_source_id":source_id,
                "source_span_chars":[char,char+len(body)],
                "source_span_bytes":[byte,byte+len(raw)],
                "source_text_sha256":sha256(raw).hexdigest(),
                "semantic_relation":"SUBSET_ENTAILS",
            })
        char+=len(line)
        byte+=len(line.encode("utf-8"))

    return {
        "schema":SCHEMA,
        "status":"PARSED",
        "edges":edges,
        "terminal_authority":False,
        "scope":"CONTROLLED_NATURAL_EVERY_IS_A_DIRECTIONAL_SUBSUMPTION_ONLY",
    }
