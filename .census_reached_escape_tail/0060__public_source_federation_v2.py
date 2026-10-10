#!/usr/bin/env python3
"""Diversity-preserving federation selector for Retrieval V4."""
from __future__ import annotations
import hashlib, json, re, unicodedata
from collections import defaultdict
from typing import Any, Mapping, Sequence

from canonical.runtime.public_source_federation_v1 import SOURCE_GROUPS

SCHEMA="PROJECT_BRAIN_PUBLIC_SOURCE_FEDERATION_V2"
WORD=re.compile(r"[^\W_]+",re.UNICODE)

def canon(x:Any)->str:
    return " ".join(unicodedata.normalize("NFKC",str(x or "")).strip().split())

def script(text:str)->str:
    c=defaultdict(int)
    for ch in canon(text):
        if ch.isspace() or ch.isdigit() or unicodedata.category(ch).startswith("P"): continue
        n=unicodedata.name(ch,""); cp=ord(ch)
        if 0x3400<=cp<=0x9FFF or "HIRAGANA" in n or "KATAKANA" in n or "HANGUL" in n: c["CJK"]+=1
        elif "ARABIC" in n: c["ARABIC"]+=1
        elif "CYRILLIC" in n: c["CYRILLIC"]+=1
        elif "DEVANAGARI" in n: c["DEVANAGARI"]+=1
        elif "LATIN" in n: c["LATIN"]+=1
        else: c["OTHER"]+=1
    for preferred in ("CJK","ARABIC","CYRILLIC","DEVANAGARI","OTHER"):
        if c.get(preferred,0)>0: return preferred
    return "LATIN" if c.get("LATIN",0)>0 else "UNKNOWN"

def rows(queries:Sequence[str]|Sequence[Mapping[str,Any]])->list[dict[str,str]]:
    out=[]; seen=set()
    for raw in queries:
        if isinstance(raw,Mapping):
            text=canon(raw.get("text")); basis=canon(raw.get("basis")) or "UNSPECIFIED"
        else:
            text=canon(raw); basis="UNSPECIFIED"
        if not text or text.casefold() in seen: continue
        seen.add(text.casefold())
        out.append({"text":text,"basis":basis,"script":script(text)})
    if not out: raise ValueError("AT_LEAST_ONE_QUERY_REQUIRED")
    return out

def technical(row:Mapping[str,str])->bool:
    text=row["text"]; basis=row["basis"].upper()
    return basis.startswith("OBSERVABLE_") or "TECHNICAL_ANCHOR" in basis or any(ch.isdigit() for ch in text) or any(x in text for x in ("_","/","@"))

def select_queries(queries:Sequence[str]|Sequence[Mapping[str,Any]],max_queries:int=8)->list[dict[str,str]]:
    pool=rows(queries); max_queries=max(1,min(int(max_queries),32))
    selected=[]; seen=set()
    def add(r,kind):
        if len(selected)>=max_queries or r["text"].casefold() in seen: return
        seen.add(r["text"].casefold()); selected.append({**r,"selection_class":kind})
    strong=[r for r in pool if r["basis"].upper().startswith("OBSERVABLE_") or "TECHNICAL_ANCHOR" in r["basis"].upper()]
    for r in strong[:2]:
        add(r,"EXACT_TECHNICAL_ANCHOR")
    for wanted in ("CJK","ARABIC","CYRILLIC","DEVANAGARI","OTHER"):
        for r in pool:
            if r["script"]==wanted:
                add(r,"SCRIPT_DIVERSITY"); break
    for r in pool:
        if r["script"]=="LATIN" and ("MULTILINGUAL" in r["basis"].upper() or "LANGUAGE" in r["basis"].upper()):
            add(r,"LATIN_LANGUAGE_VARIANT"); break
    for r in pool:
        if technical(r):
            add(r,"TECHNICAL_FILL")
    for r in pool: add(r,"FILL")
    return selected

def compile_federation(queries:Sequence[str]|Sequence[Mapping[str,Any]],max_queries_per_source:int=8)->dict[str,Any]:
    selected=select_queries(queries,max_queries_per_source)
    requests=[]
    for source_class,domain in SOURCE_GROUPS:
        for rank,row in enumerate(selected):
            query=f"site:{domain} {row['text']}"
            rid=hashlib.sha256(f"{domain}\0{query}".encode()).hexdigest()[:24]
            requests.append({"request_id":rid,"source_class":source_class,"domain":domain,"query":query,"base_query":row["text"],"script":row["script"],"selection_class":row["selection_class"],"selected_rank":rank,"authority":"CANDIDATE_ONLY","complete":False})
    available={r["script"] for r in rows(queries)}
    chosen={r["script"] for r in selected}
    program_sha=hashlib.sha256(json.dumps(requests,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
    return {"schema":SCHEMA,"status":"COMPILED_DIVERSITY_PRESERVING","selected_queries":selected,"source_group_count":len(SOURCE_GROUPS),"request_count":len(requests),"requests":requests,"available_scripts":sorted(available),"selected_scripts":sorted(chosen),"nonlatin_available":any(x not in {"LATIN","UNKNOWN"} for x in available),"nonlatin_selected":any(x not in {"LATIN","UNKNOWN"} for x in chosen),"federation_program_sha256":program_sha,"complete":False,"incremental_spend_usd":0,"hard_rules":["CROSS_SCRIPT_DIVERSITY_PRECEDES_REDUNDANT_BASE_QUERIES","EMPTY_RESULT_IS_UNKNOWN_NOT_NONEXISTENCE","CANDIDATES_REQUIRE_INDEPENDENT_VERIFICATION"]}
