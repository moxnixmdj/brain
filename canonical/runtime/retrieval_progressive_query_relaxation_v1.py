#!/usr/bin/env python3
"""Generic progressive semantic query relaxation for retrieval misses.

This route is answer-key blind. It expands a behavioral request through:
- phrase-level technical aliases/acronyms,
- singular/plural morphology,
- platform-anchor-preserving concept subsets,
- multilingual bridge variants already supplied by the request,
- progressively lower conjunction pressure.

It is a candidate generator only and never authorizes nonexistence.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_RETRIEVAL_PROGRESSIVE_QUERY_RELAXATION_V1"
WORD=re.compile(r"[^\W_]+(?:[.+#/-][^\W_]+)*",re.UNICODE)
GITHUB_QUALIFIER="in:name,description,readme"

PHRASE_ALIASES={
    "regular expression":("regex","regexp"),
    "command line":("CLI","terminal"),
    "text search":("search text","search files"),
    "natural language processing":("NLP","language processing"),
    "morphological analysis":("morphology","morphological analyzer"),
    "morphology":("morphological analysis","morphological analyzer"),
    "background job processing":("background jobs","job queue","asynchronous jobs"),
    "background job":("job queue","background jobs","async jobs"),
    "workers queues":("worker queue","job queue"),
    "file path pattern matching":("path matching","file patterns"),
    "serialization deserialization":("serialize deserialize","serialization"),
    "utilities":("utility","helpers"),
    "strings":("string","text"),
    "builders":("builder",),
    "object helpers":("object utilities","helpers"),
    "http client":("HTTP requests","web client"),
    "html parser":("HTML parsing","DOM parser"),
}
PLATFORM={"python","rust","ruby","java","php","javascript","node","nodejs",".net","dotnet","c#","csharp","go"}
LOW_INFO={"fast","flexible","library","toolkit","tools","tool","open","source","strongly","typed","lightweight","processing"}

def _canon(x:Any)->str:
    return " ".join(unicodedata.normalize("NFKC",str(x or "")).strip().split())

def _tokens(text:str)->list[str]:
    return [x for x in WORD.findall(_canon(text)) if len(x)>=2]

def _singular(token:str)->str:
    low=token.casefold()
    if len(low)>5 and low.endswith("ies"): return token[:-3]+"y"
    if len(low)>5 and low.endswith("ing"): return token[:-3]
    if len(low)>4 and low.endswith("s") and not low.endswith("ss"): return token[:-1]
    return token

def _dedupe(rows:Sequence[str],limit:int)->list[str]:
    out=[];seen=set()
    for raw in rows:
        q=_canon(raw)
        if not q or q.casefold() in seen: continue
        seen.add(q.casefold());out.append(q)
        if len(out)>=limit:break
    return out

def _bridge_texts(request:Mapping[str,Any])->list[str]:
    rows=[]
    for key in ("language_variants","bridge_variants"):
        for item in request.get(key) or []:
            text=_canon(item.get("text") if isinstance(item,Mapping) else item)
            if text:rows.append(text)
    return _dedupe(rows,12)

def generate(
    request:Mapping[str,Any],
    *,
    provider:str,
    max_queries:int=24,
)->dict[str,Any]:
    if "target" in request or "expected_target_answer_key" in request:
        raise ValueError("ANSWER_KEY_FIELD_FORBIDDEN")
    original=_canon(request.get("query") or request.get("text"))
    if not original:
        raise ValueError("QUERY_REQUIRED")
    provider=str(provider or "").strip().lower()

    bases=[original,*_bridge_texts(request)]
    expanded=list(bases)
    for base in bases:
        low=base.casefold()
        for phrase,aliases in PHRASE_ALIASES.items():
            if phrase in low:
                for alias in aliases:
                    expanded.append(re.sub(re.escape(phrase),alias,base,flags=re.IGNORECASE))

    raw=list(expanded)
    for base in expanded:
        toks=_tokens(base)
        platforms=[x for x in toks if x.casefold() in PLATFORM]
        content=[x for x in toks if x.casefold() not in PLATFORM|LOW_INFO]
        singular=[_singular(x) for x in content]
        content=_dedupe([*content,*singular],64)

        # Preserve one platform anchor where available while reducing conjunction.
        anchor=platforms[:1]
        for n in (4,3,2):
            if len(content)>=n:
                raw.append(" ".join([*anchor,*content[:n]]))
                raw.append(" ".join([*anchor,*content[-n:]]))
                for i in range(0,len(content)-n+1):
                    raw.append(" ".join([*anchor,*content[i:i+n]]))
        # Single high-information concepts are last-resort recall routes.
        for tok in content[:8]:
            raw.append(" ".join([*anchor,tok]))

    rows=_dedupe(raw,max_queries)
    if provider=="github":
        rows=[
            q if "in:" in q.casefold() else f"{q} {GITHUB_QUALIFIER}"
            for q in rows
        ]
    return {
        "schema":SCHEMA,
        "status":"COMPILED_PROGRESSIVE_SEMANTIC_RELAXATION",
        "provider":provider,
        "original_query":original,
        "queries":rows,
        "query_count":len(rows),
        "answer_key_identity_used":False,
        "candidate_authority":"CANDIDATE_ONLY",
        "nonexistence_claim_authorized":False,
        "incremental_spend_usd":0,
        "hard_rules":[
            "ALIASES_ARE_GENERIC_TECHNICAL_CONCEPTS_NOT_TARGET_IDENTITIES",
            "PLATFORM_ANCHORS_ARE_PRESERVED_WHEN_AVAILABLE",
            "QUERY_CONJUNCTION_PRESSURE_DECREASES_PROGRESSIVELY",
            "RESULTS_REQUIRE_DOWNSTREAM_SUFFICIENCY_VERIFICATION",
            "EMPTY_RESULTS_REMAIN_UNKNOWN"
        ]
    }
