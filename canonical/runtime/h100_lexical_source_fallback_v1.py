"""Zero-learned bridge from explicit source relations to canonical roles.

The runtime does not know lexical term identities. It consumes source-asserted
relation phrases and maps them through a fixed role ontology. Conflicting or
unsupported relation sets fail closed.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_H100_LEXICAL_SOURCE_FALLBACK_V1"

_INPUT_RELATIONS={
    "independent variable",
    "predictor",
    "predictor variable",
    "explanatory variable",
    "feature",
    "feature variable",
    "input variable",
}
_TARGET_RELATIONS={
    "dependent variable",
    "response variable",
    "outcome variable",
    "target variable",
    "label",
    "regressand",
}

class LexicalSourceFallbackError(ValueError):
    pass

def _norm(value:Any,label:str)->str:
    if not isinstance(value,str):
        raise LexicalSourceFallbackError(label+"_INVALID")
    text=" ".join(value.strip().lower().split())
    if not text:
        raise LexicalSourceFallbackError(label+"_EMPTY")
    return text

def resolve_source_relations(term:Any, records:Any)->dict[str,Any]:
    term_n=_norm(term,"TERM")
    if not isinstance(records,Sequence) or isinstance(records,(str,bytes)) or not records:
        raise LexicalSourceFallbackError("RECORDS_INVALID")

    seen_sources=set()
    mapped_roles=set()
    mapped_phrases=[]
    unsupported=[]

    for i,row in enumerate(records):
        if not isinstance(row,Mapping):
            raise LexicalSourceFallbackError(f"RECORD_INVALID:{i}")
        row_term=_norm(row.get("term"),f"RECORD_TERM:{i}")
        if row_term!=term_n:
            raise LexicalSourceFallbackError(f"RECORD_TERM_MISMATCH:{i}")
        source_value = row.get("source_id") if row.get("source_id") is not None else row.get("source")
        source=_norm(source_value,f"SOURCE:{i}")
        if source in seen_sources:
            raise LexicalSourceFallbackError("SOURCE_DUPLICATE:"+source)
        seen_sources.add(source)
        phrases=row.get("relation_phrases")
        if not isinstance(phrases,Sequence) or isinstance(phrases,(str,bytes)) or not phrases:
            raise LexicalSourceFallbackError(f"RELATION_PHRASES_INVALID:{i}")
        for raw in phrases:
            phrase=_norm(raw,f"RELATION:{i}")
            if phrase in _INPUT_RELATIONS:
                mapped_roles.add("INPUT")
                mapped_phrases.append(phrase)
            elif phrase in _TARGET_RELATIONS:
                mapped_roles.add("TARGET")
                mapped_phrases.append(phrase)
            else:
                unsupported.append(phrase)

    if len(mapped_roles)>1:
        return _abstain(term_n,"ABSTAIN_SOURCE_ROLE_CONFLICT",mapped_phrases,unsupported,len(seen_sources))
    if len(mapped_roles)==0:
        return _abstain(term_n,"ABSTAIN_SOURCE_RELATION_UNSUPPORTED",mapped_phrases,unsupported,len(seen_sources))
    role=next(iter(mapped_roles))
    return {
        "schema":SCHEMA,
        "status":"ROLE_IDENTIFIED",
        "term":term_n,
        "role":role,
        "mapped_relation_phrases":sorted(set(mapped_phrases)),
        "unsupported_relation_phrases":sorted(set(unsupported)),
        "source_count":len(seen_sources),
        "persistent_learned_bytes":0,
        "external_frontier_model_calls":0,
        "external_learned_capability_calls":0,
        "hard_nonclaim":"FINITE_SOURCE_RELATION_BRIDGE_IS_NOT_OPEN_WORLD_LEXICAL_COVERAGE",
    }

def _abstain(term:str,status:str,mapped:list[str],unsupported:list[str],source_count:int)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "term":term,
        "role":None,
        "mapped_relation_phrases":sorted(set(mapped)),
        "unsupported_relation_phrases":sorted(set(unsupported)),
        "source_count":source_count,
        "persistent_learned_bytes":0,
        "external_frontier_model_calls":0,
        "external_learned_capability_calls":0,
        "hard_nonclaim":"FAIL_CLOSED_SOURCE_RELATION_MAPPING",
    }
