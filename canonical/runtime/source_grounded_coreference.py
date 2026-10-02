"""Source-grounded bounded coreference candidate compiler.

This module does not claim general coreference resolution. It converts explicit text
mentions and reference expressions into a finite provenance-preserving candidate graph.
Ambiguity is retained for downstream identifiability/adjudication.

Scope is intentionally conservative and deterministic:
- caller supplies sentence/mention spans or uses the small surface mention extractor;
- pronouns/demonstratives are linked to compatible prior mentions, never silently
  resolved;
- candidate explosion fails closed instead of truncating.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
import re
from typing import Sequence

MAX_MENTIONS=128
MAX_CANDIDATES=512

_PRONOUNS={
 "he":("PERSON","SINGULAR"),"him":("PERSON","SINGULAR"),"his":("PERSON","SINGULAR"),
 "she":("PERSON","SINGULAR"),"her":("PERSON","SINGULAR"),"hers":("PERSON","SINGULAR"),
 "they":("ANY","PLURAL"),"them":("ANY","PLURAL"),"their":("ANY","PLURAL"),"theirs":("ANY","PLURAL"),
 "it":("NONPERSON","SINGULAR"),"its":("NONPERSON","SINGULAR"),
 "this":("ANY","SINGULAR"),"that":("ANY","SINGULAR"),
 "these":("ANY","PLURAL"),"those":("ANY","PLURAL"),
}

@dataclass(frozen=True)
class Mention:
    mention_id:str
    text:str
    start:int
    end:int
    sentence_index:int
    entity_class:str="UNKNOWN"   # PERSON | NONPERSON | UNKNOWN
    number:str="UNKNOWN"         # SINGULAR | PLURAL | UNKNOWN
    is_reference:bool=False

def _compatible(ref:Mention,ant:Mention)->bool:
    key=ref.text.strip().lower()
    spec=_PRONOUNS.get(key)
    if spec is None:
        return False
    cls,num=spec
    if cls=="PERSON" and ant.entity_class=="NONPERSON":
        return False
    if cls=="NONPERSON" and ant.entity_class=="PERSON":
        return False
    if num!="UNKNOWN" and ant.number!="UNKNOWN" and ant.number!=num:
        return False
    return ant.start < ref.start and not ant.is_reference

def compile_coreference_candidates(mentions:Sequence[Mention],*,max_candidates:int=MAX_CANDIDATES)->dict:
    if not isinstance(mentions,Sequence) or isinstance(mentions,(str,bytes)) or len(mentions)>MAX_MENTIONS:
        return {"status":"FAIL_CLOSED","reason":"MENTION_UNIVERSE_INVALID_OR_TOO_LARGE","terminal_authority":False}
    ids=[m.mention_id for m in mentions if isinstance(m,Mention)]
    if len(ids)!=len(mentions) or any(not x for x in ids) or len(ids)!=len(set(ids)):
        return {"status":"FAIL_CLOSED","reason":"MENTION_IDENTITIES_INVALID_OR_DUPLICATE","terminal_authority":False}
    ordered=sorted(mentions,key=lambda m:(m.start,m.end,m.mention_id))
    if any(m.start<0 or m.end<=m.start or m.sentence_index<0 or not m.text for m in ordered):
        return {"status":"FAIL_CLOSED","reason":"MENTION_SPAN_INVALID","terminal_authority":False}
    if any(ordered[i].end>ordered[i+1].start for i in range(len(ordered)-1)):
        return {"status":"FAIL_CLOSED","reason":"MENTION_SPANS_OVERLAP","terminal_authority":False}
    edges=[]
    unresolved=[]
    for ref in ordered:
        if not ref.is_reference:
            continue
        if ref.text.strip().lower() not in _PRONOUNS:
            unresolved.append({"reference_id":ref.mention_id,"reason":"REFERENCE_FORM_UNSUPPORTED"})
            continue
        cands=[m for m in ordered if _compatible(ref,m)]
        if not cands:
            unresolved.append({"reference_id":ref.mention_id,"reason":"NO_COMPATIBLE_PRIOR_MENTION"})
            continue
        for ant in cands:
            edges.append({
                "reference_id":ref.mention_id,
                "antecedent_id":ant.mention_id,
                "reference_span":[ref.start,ref.end],
                "antecedent_span":[ant.start,ant.end],
                "sentence_distance":ref.sentence_index-ant.sentence_index,
                "status":"CANDIDATE_ONLY",
            })
            if len(edges)>max_candidates:
                return {"status":"ESCALATE","reason":"COREFERENCE_CANDIDATE_BOUND_EXCEEDED","terminal_authority":False}
    return {
        "status":"COMPILED",
        "mentions":[asdict(m) for m in ordered],
        "candidate_edges":edges,
        "unresolved_references":unresolved,
        "ambiguity_preserved":True,
        "scope":"BOUNDED_EXPLICIT_MENTION_GRAPH__NO_GENERAL_COREFERENCE_RESOLUTION",
        "terminal_authority":False,
        "semantic_authority":False,
    }

def extract_surface_mentions(text:str)->dict:
    """Tiny deterministic mention extractor for obvious capitalized NPs and pronouns."""
    if not isinstance(text,str) or not text.strip():
        return {"status":"FAIL_CLOSED","reason":"TEXT_EMPTY"}
    sentence_starts=[0]
    for m in re.finditer(r"[.!?]\s+",text):
        sentence_starts.append(m.end())
    def sent_idx(pos:int)->int:
        i=0
        for j,s in enumerate(sentence_starts):
            if s<=pos: i=j
            else: break
        return i
    spans=[]
    pattern=re.compile(
        r"\b(?:[A-Z][A-Za-z0-9'_-]*(?:\s+[A-Z][A-Za-z0-9'_-]*)*|(?i:he|him|his|she|her|hers|they|them|their|theirs|it|its|this|that|these|those))\b"
    )
    for i,m in enumerate(pattern.finditer(text)):
        raw=m.group(0)
        low=raw.lower()
        is_ref=low in _PRONOUNS
        # Capitalization is only a surface cue; class remains UNKNOWN.
        spans.append(Mention(
            mention_id=f"m{i}",text=raw,start=m.start(),end=m.end(),
            sentence_index=sent_idx(m.start()),is_reference=is_ref
        ))
        if len(spans)>MAX_MENTIONS:
            return {"status":"ESCALATE","reason":"MENTION_BOUND_EXCEEDED"}
    return {"status":"COMPILED","mentions":[asdict(x) for x in spans],"terminal_authority":False}
