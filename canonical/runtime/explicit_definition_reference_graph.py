"""Deterministic explicit-definition and cross-sentence reference propagation.

Owns only explicit named definitions such as "X means Y", "X refers to Y", or
"X is defined as Y", then binds later exact named references to those definitions.
Conflicting definitions, cycles, pronouns, implicit requirements, and context-dependent
ellipsis fail closed or remain unresolved.
"""
from __future__ import annotations
import re
from typing import Any

SCHEMA="BRAIN_EXPLICIT_DEFINITION_REFERENCE_GRAPH_V1"

_DEF_PATTERNS=[
    re.compile(r"^\s*(?:for purposes of this [^,]+,\s*)?["']?([A-Za-z][A-Za-z0-9 _-]{0,80}?)["']?\s+(?:means|refers to|is defined as)\s+(.+?)\s*$",re.I),
]

def _sentences(text:str)->list[str]:
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+",text) if x.strip()]

def compile_reference_graph(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["EMPTY_SOURCE"]}
    sents=_sentences(text)
    defs={}
    definition_sentence_ids=set()
    errors=[]
    for i,s in enumerate(sents):
        bare=s.rstrip(".")
        matched=None
        for p in _DEF_PATTERNS:
            m=p.match(bare)
            if m: matched=m; break
        if not matched: continue
        term=" ".join(matched.group(1).split()).strip()
        value=" ".join(matched.group(2).split()).strip()
        key=term.casefold()
        prior=defs.get(key)
        if prior and prior["definition"].casefold()!=value.casefold():
            errors.append(f"CONFLICTING_DEFINITION:{term}")
            continue
        defs[key]={"term":term,"definition":value,"sentence_index":i}
        definition_sentence_ids.add(i)

    # Exact named-term dependency graph among definitions.
    deps={k:set() for k in defs}
    for k,row in defs.items():
        v=row["definition"].casefold()
        for other,orow in defs.items():
            if other==k: continue
            if re.search(r"(?<!\w)"+re.escape(orow["term"].casefold())+r"(?!\w)",v):
                deps[k].add(other)

    # Cycle detection.
    temp=set(); perm=set()
    def visit(k):
        if k in perm: return
        if k in temp:
            errors.append("DEFINITION_CYCLE:"+k); return
        temp.add(k)
        for d in deps[k]: visit(d)
        temp.remove(k); perm.add(k)
    for k in sorted(deps): visit(k)

    refs=[]
    for i,s in enumerate(sents):
        if i in definition_sentence_ids: continue
        low=s.casefold()
        matched=[]
        for k,row in defs.items():
            if re.search(r"(?<!\w)"+re.escape(row["term"].casefold())+r"(?!\w)",low):
                matched.append({"term":row["term"],"definition":row["definition"],"definition_sentence_index":row["sentence_index"]})
        if matched:
            refs.append({"sentence_index":i,"sentence":s,"resolved_named_definitions":matched})

    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors)),
                "definition_count":len(defs),"terminal_authority":False}
    return {"schema":SCHEMA,"status":"COMPILED","definitions":list(defs.values()),
            "references":refs,"unresolved_semantics":[
                "PRONOUN_RESOLUTION","IMPLICIT_REQUIREMENTS","ELLIPSIS",
                "CONTEXT_DEPENDENT_WORD_SENSE","UNSTATED_WORLD_KNOWLEDGE"
            ],
            "terminal_authority":False,
            "scope":"EXPLICIT_NAMED_DEFINITION_PROPAGATION_ACROSS_SENTENCES_ONLY"}
