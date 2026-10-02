"""Deterministic resolver for externally supplied engineering reference tables.

Knowledge stays external/JIT. Brain owns the mechanism that validates a supplied
machine-readable table and resolves symbols/modifiers/roughness rows without
inventing facts absent from that table.
"""
from __future__ import annotations
import csv, io, unicodedata
from typing import Any

SCHEMA="BRAIN_ENGINEERING_REFERENCE_RESOLVER_V1"

def _rows(csv_text:str)->list[dict[str,str]]:
    if not isinstance(csv_text,str) or not csv_text.strip():
        raise ValueError("empty CSV")
    rows=list(csv.DictReader(io.StringIO(csv_text)))
    if not rows:
        raise ValueError("CSV has no data rows")
    return rows

def _unique(rows:list[dict[str,str]], key:str)->dict[str,dict[str,str]]:
    out={}
    for i,row in enumerate(rows):
        v=str(row.get(key,"")).strip()
        if not v:
            raise ValueError(f"missing {key} at row {i}")
        k=v.casefold()
        if k in out:
            raise ValueError(f"duplicate {key}: {v}")
        out[k]=row
    return out

def validate_gdt_symbols(csv_text:str)->dict[str,Any]:
    rows=_rows(csv_text)
    required={"characteristic","category","datum_required","symbol","codepoint","unicode_name"}
    if not required <= set(rows[0]):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"GDT_SCHEMA_MISSING_COLUMNS"}
    try:
        index=_unique(rows,"characteristic")
        for row in rows:
            cp=row["codepoint"].strip()
            if not cp.startswith("U+"): raise ValueError("bad codepoint")
            ch=chr(int(cp[2:],16))
            if ch != row["symbol"]: raise ValueError("symbol/codepoint mismatch")
            if unicodedata.name(ch) != row["unicode_name"]: raise ValueError("unicode name mismatch")
    except Exception as e:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":type(e).__name__+":"+str(e)}
    return {"schema":SCHEMA,"status":"VALIDATED","kind":"gdt_symbols","row_count":len(rows),"index":index,"terminal_authority":False}

def validate_gdt_modifiers(csv_text:str)->dict[str,Any]:
    rows=_rows(csv_text)
    required={"modifier","meaning","symbol","codepoint","unicode_name"}
    if not required <= set(rows[0]):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"MODIFIER_SCHEMA_MISSING_COLUMNS"}
    try:
        index=_unique(rows,"modifier")
        for row in rows:
            cp=row["codepoint"].strip()
            ch=chr(int(cp[2:],16))
            if ch != row["symbol"]: raise ValueError("symbol/codepoint mismatch")
            if unicodedata.name(ch) != row["unicode_name"]: raise ValueError("unicode name mismatch")
    except Exception as e:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":type(e).__name__+":"+str(e)}
    return {"schema":SCHEMA,"status":"VALIDATED","kind":"gdt_modifiers","row_count":len(rows),"index":index,"terminal_authority":False}

def validate_roughness_grades(csv_text:str)->dict[str,Any]:
    rows=_rows(csv_text)
    required={"grade","ra_um","ra_uin_conventional"}
    if not required <= set(rows[0]):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"ROUGHNESS_SCHEMA_MISSING_COLUMNS"}
    try:
        index=_unique(rows,"grade")
        for row in rows:
            float(row["ra_um"]); int(row["ra_uin_conventional"])
    except Exception as e:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":type(e).__name__+":"+str(e)}
    return {"schema":SCHEMA,"status":"VALIDATED","kind":"roughness","row_count":len(rows),"index":index,"terminal_authority":False}

def resolve(validated:dict[str,Any], query:str)->dict[str,Any]:
    if validated.get("status")!="VALIDATED" or not isinstance(validated.get("index"),dict):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"UNVALIDATED_REFERENCE_TABLE"}
    q=" ".join(str(query or "").split()).casefold()
    if not q:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"EMPTY_QUERY"}
    row=validated["index"].get(q)
    if row is None:
        # Exact symbol/codepoint lookup is allowed, fuzzy semantic guessing is not.
        matches=[]
        for r in validated["index"].values():
            if q in {str(r.get("symbol","")).casefold(),str(r.get("codepoint","")).casefold()}:
                matches.append(r)
        if len(matches)!=1:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"NO_UNIQUE_REFERENCE_MATCH","match_count":len(matches)}
        row=matches[0]
    return {"schema":SCHEMA,"status":"RESOLVED","kind":validated.get("kind"),"row":row,"terminal_authority":False}
