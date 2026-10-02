"""Declarative engineering-notation resolver.

Knowledge (symbol catalogs, aliases, semantic labels) is supplied at runtime/JIT.
Capability stays local: catalog validation, alias matching, ambiguity rejection, and
typed token emission. No standard-specific truth is hard-coded here.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence
import re

SCHEMA="BRAIN_DECLARATIVE_ENGINEERING_NOTATION_V1"

def compile_catalog(rows: Sequence[Mapping[str,Any]]) -> dict[str,Any]:
    errors=[]; aliases={}; symbols={}
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["CATALOG_NOT_SEQUENCE"]}
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            errors.append(f"ROW_NOT_OBJECT:{i}"); continue
        sid=row.get("symbol_id"); kind=row.get("kind"); als=row.get("aliases")
        if not isinstance(sid,str) or not sid.strip(): errors.append(f"SYMBOL_ID_INVALID:{i}"); continue
        if sid in symbols: errors.append(f"SYMBOL_ID_DUPLICATE:{sid}"); continue
        if not isinstance(kind,str) or not kind.strip(): errors.append(f"KIND_INVALID:{sid}")
        if not isinstance(als,list) or not als or any(not isinstance(a,str) or not a.strip() for a in als):
            errors.append(f"ALIASES_INVALID:{sid}"); als=[]
        norm=[]
        for a in als:
            key=" ".join(a.upper().split())
            prior=aliases.get(key)
            if prior is not None and prior!=sid:
                errors.append(f"ALIAS_AMBIGUOUS:{key}:{prior}:{sid}")
            aliases[key]=sid; norm.append(key)
        symbols[sid]={"symbol_id":sid,"kind":kind,"aliases":sorted(set(norm)),
                      "semantics":row.get("semantics"),"source":row.get("source")}
    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors))}
    return {"schema":SCHEMA,"status":"COMPILED","symbols":symbols,"aliases":aliases,"terminal_authority":False}

def resolve_tokens(text:str,catalog:Mapping[str,Any]) -> dict[str,Any]:
    if catalog.get("status")!="COMPILED":
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["CATALOG_NOT_COMPILED"]}
    if not isinstance(text,str) or not text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["EMPTY_TEXT"]}
    hay=" ".join(text.upper().split())
    matches=[]
    # Longest aliases first so "TOTAL RUNOUT" dominates "RUNOUT".
    for alias,sid in sorted(catalog["aliases"].items(),key=lambda x:(-len(x[0]),x[0])):
        for m in re.finditer(r"(?<!\w)"+re.escape(alias)+r"(?!\w)",hay):
            matches.append((m.start(),m.end(),alias,sid))
    matches.sort()
    accepted=[]; occupied=set()
    for start,end,alias,sid in matches:
        span=set(range(start,end))
        if span & occupied: continue
        occupied |= span
        row=catalog["symbols"][sid]
        accepted.append({"start":start,"end":end,"alias":alias,"symbol_id":sid,"kind":row["kind"],
                         "semantics":row.get("semantics"),"source":row.get("source")})
    return {"schema":SCHEMA,"status":"RESOLVED","tokens":accepted,"terminal_authority":False,
            "scope":"DECLARATIVE_ALIAS_TO_TYPED_SYMBOL_RESOLUTION_ONLY"}
