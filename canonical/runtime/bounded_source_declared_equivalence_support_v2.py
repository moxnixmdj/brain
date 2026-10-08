"""Bounded transitive source-declared equivalence support v2.

Extends v1 only for chains of exact simple named definitions:
    A means B.
    B means C.
    Source states that <proposition using A>.

Each RHS may either be terminal simple text or exactly another defined term.
RHS expressions that merely contain another defined term plus extra material remain
outside scope. Conflicts and cycles are rejected by the existing definition graph.

Definitions are treated as source-declared equivalences only inside this evidence
unit. No external synonymy, ontology, world knowledge, or source authority is inferred.
"""
from __future__ import annotations

import re
from typing import Any

from canonical.runtime.explicit_definition_reference_graph import compile_reference_graph

SCHEMA="PROJECT_BRAIN_BOUNDED_SOURCE_DECLARED_EQUIVALENCE_SUPPORT_V2"
_SIMPLE=re.compile(r"^[A-Za-z][A-Za-z0-9 _-]{0,80}$")
_DEF=re.compile(
    r"""^\s*(?:for purposes of this [^,]+,\s*)?["']?([A-Za-z][A-Za-z0-9 _-]{0,80}?)["']?\s+"""
    r"""(?:means|refers to|is defined as)\s+(.+?)\s*$""",re.I
)
_POS=(
    re.compile(r"^(?P<source>.+?)\s+states\s+that\s+(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>.+?)\s+reports\s+that\s+(?P<body>.+)$",re.I),
)
_NEG=(
    re.compile(r"^(?P<source>.+?)\s+denies\s+that\s+(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>.+?)\s+rejects\s+that\s+(?P<body>.+)$",re.I),
)

def _sentences(text:str)->list[str]:
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+",text) if x.strip()]

def _canon(value:Any)->str:
    s=" ".join(str(value if value is not None else "").strip().split())
    if s.endswith("."):s=s[:-1].rstrip()
    return s.casefold()

def _parse_attestation(sentence:str)->tuple[str,str,str]|None:
    raw=sentence.rstrip(".").strip()
    for p in _POS:
        m=p.fullmatch(raw)
        if m:return "SUPPORTS"," ".join(m.group("source").split()),m.group("body")
    for p in _NEG:
        m=p.fullmatch(raw)
        if m:return "CONFLICTS"," ".join(m.group("source").split()),m.group("body")
    return None

def _resolve(defs:dict[str,str])->tuple[dict[str,str]|None,dict[str,list[str]]|None,str|None]:
    resolved={};paths={}
    for term in sorted(defs):
        cur=term;path=[term];seen=set()
        while cur in defs:
            if cur in seen:return None,None,"DEFINITION_CYCLE"
            seen.add(cur)
            rhs=defs[cur]
            # If the RHS mentions any defined term, it is allowed only when it
            # equals exactly one defined term after canonicalization.
            mentioned=[
                other for other in defs
                if re.search(r"(?<!\w)"+re.escape(other)+r"(?!\w)",rhs,re.I)
            ]
            exact=rhs if rhs in defs else None
            if mentioned and exact is None:
                return None,None,"NESTED_NONATOMIC_DEFINITION_OUTSIDE_V2"
            if exact is None:
                cur=rhs;path.append(rhs);break
            cur=exact;path.append(cur)
        resolved[term]=cur
        paths[term]=path
    return resolved,paths,None

def _rewrite(surface:str,resolved:dict[str,str])->str:
    out=_canon(surface)
    for term,target in sorted(resolved.items(),key=lambda x:(-len(x[0]),x[0])):
        out=re.sub(r"(?<!\w)"+re.escape(term)+r"(?!\w)",target,out,flags=re.I)
    return _canon(out)

def classify_support(claim_text:str,evidence_text:str,*,evidence_id:str|None=None)->dict[str,Any]:
    claim=_canon(claim_text)
    if not claim:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"CLAIM_TEXT_REQUIRED","terminal_authority":False}
    if not isinstance(evidence_text,str) or not evidence_text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"EVIDENCE_TEXT_REQUIRED","terminal_authority":False}

    graph=compile_reference_graph(evidence_text)
    if graph.get("status")!="COMPILED":
        return {"schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
                "reason":"EXPLICIT_DEFINITION_GRAPH_NOT_COMPILED",
                "definition_graph_status":graph.get("status"),"terminal_authority":False}
    rows=graph.get("definitions") or []
    if not rows:
        return {"schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
                "reason":"NO_EXPLICIT_SOURCE_DEFINITION","terminal_authority":False}

    defs={}
    for row in rows:
        term=_canon(row.get("term"));target=_canon(row.get("definition"))
        if not term or not target or _SIMPLE.fullmatch(row.get("term","")) is None or _SIMPLE.fullmatch(row.get("definition","")) is None:
            return {"schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
                    "reason":"DEFINITION_OUTSIDE_SIMPLE_EQUIVALENCE_GRAMMAR","terminal_authority":False}
        defs[term]=target

    resolved,paths,error=_resolve(defs)
    if error:
        return {"schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
                "reason":error,"terminal_authority":False}
    assert resolved is not None and paths is not None

    definition_sentences=set()
    for i,s in enumerate(_sentences(evidence_text)):
        if _DEF.fullmatch(s.rstrip(".")):definition_sentences.add(i)

    observations=[]
    for i,sentence in enumerate(_sentences(evidence_text)):
        if i in definition_sentences:continue
        parsed=_parse_attestation(sentence)
        if parsed is None:
            return {"schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
                    "reason":"NONDEFINITION_SENTENCE_OUTSIDE_ATTESTATION_GRAMMAR",
                    "sentence_index":i,"terminal_authority":False}
        polarity,source,body=parsed
        observations.append({
            "polarity":polarity,"source":source,
            "rewritten_body":_rewrite(body,resolved),"sentence_index":i,
        })

    if not observations:
        return {"schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
                "reason":"NO_ATTESTATION_AFTER_DEFINITION","terminal_authority":False}

    rewritten_claim=_rewrite(claim_text,resolved)
    matching=[x for x in observations if x["rewritten_body"]==rewritten_claim]
    polarities=sorted({x["polarity"] for x in matching})
    if len(polarities)>1:
        return {"schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
                "reason":"MIXED_POLARITY_FOR_CANONICAL_PROPOSITION","terminal_authority":False}
    relation=polarities[0] if polarities else "UNRELATED"
    return {
        "schema":SCHEMA,"status":"RESOLVED","relation":relation,
        "claim_normalized":claim,"canonical_proposition":rewritten_claim,
        "definitions":[{"term":t,"definition":defs[t],"terminal":resolved[t],"path":paths[t]} for t in sorted(defs)],
        "matching_attestation_count":len(matching),"evidence_id":evidence_id,
        "proof":{"rule":"EXPLICIT_DEFINITION_EQUIVALENCE_TRANSITIVE_CLOSURE","resolution_paths":paths},
        "terminal_authority":False,
        "scope":"EXPLICIT_SIMPLE_SOURCE_DECLARED_EQUIVALENCE_TRANSITIVE_CLOSURE_PLUS_EXACT_ATTESTATION_ONLY",
    }
