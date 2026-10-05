"""Formal lexical-coverage bounds for H100.

A fixed finite persistent lexicon cannot cover an unbounded token universe.
Open-world lexical operation must therefore be conditional on runtime source
availability, with fail-closed abstention when sources are missing, incomplete,
or conflicting.

No learned model is used.
"""
from __future__ import annotations
from typing import Iterable

SCHEMA="PROJECT_BRAIN_H100_LEXICAL_COVERAGE_BOUND_V1"

class LexicalCoverageBoundError(ValueError):
    pass

def normalize_terms(terms:Iterable[str])->tuple[str,...]:
    out=[]
    for raw in terms:
        if not isinstance(raw,str):
            raise LexicalCoverageBoundError("TERM_INVALID")
        term=raw.strip()
        if not term:
            raise LexicalCoverageBoundError("TERM_EMPTY")
        out.append(term)
    return tuple(sorted(set(out)))

def constructive_outside_term(terms:Iterable[str], symbol:str="z")->str:
    """Construct a token guaranteed absent from any finite lexicon.

    It is one character longer than the longest lexicon entry, so it cannot be
    equal to any member regardless of their content.
    """
    lex=normalize_terms(terms)
    if not isinstance(symbol,str) or len(symbol)!=1:
        raise LexicalCoverageBoundError("SYMBOL_INVALID")
    max_len=max((len(x) for x in lex),default=0)
    witness=symbol*(max_len+1)
    assert witness not in set(lex)
    return witness

def finite_lexicon_open_world_complete(terms:Iterable[str])->bool:
    lex=normalize_terms(terms)
    witness=constructive_outside_term(lex)
    return witness in set(lex)

def source_union_coverage(source_term_sets:Iterable[Iterable[str]])->dict:
    sets=[set(normalize_terms(x)) for x in source_term_sets]
    covered=set().union(*sets) if sets else set()
    return {
        "source_count":len(sets),
        "covered_unique_terms":len(covered),
        "coverage_union":tuple(sorted(covered)),
    }

def monotonic_source_addition(before:Iterable[Iterable[str]], new_source:Iterable[str])->dict:
    b=source_union_coverage(before)
    a=source_union_coverage([*list(before),new_source])
    return {
        "before_unique_terms":b["covered_unique_terms"],
        "after_unique_terms":a["covered_unique_terms"],
        "nondecreasing":a["covered_unique_terms"]>=b["covered_unique_terms"],
        "new_terms":tuple(sorted(set(a["coverage_union"])-set(b["coverage_union"]))),
    }

def conditional_jit_certificate(
    *,
    term:str,
    source_records_present:bool,
    source_query_complete:bool,
    source_relations_conflict:bool,
)->dict:
    if not isinstance(term,str) or not term.strip():
        raise LexicalCoverageBoundError("TERM_INVALID")
    if not source_records_present:
        status="ABSTAIN_SOURCE_NOT_AVAILABLE"
    elif not source_query_complete:
        status="ABSTAIN_SOURCE_QUERY_INCOMPLETE"
    elif source_relations_conflict:
        status="ABSTAIN_SOURCE_ROLE_CONFLICT"
    else:
        status="SOURCE_EVIDENCE_ADMISSIBLE_FOR_DETERMINISTIC_ROLE_BRIDGE"
    return {
        "schema":SCHEMA,
        "term":term.strip(),
        "status":status,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "SOURCE_AVAILABILITY_IS_NOT_GUARANTEED_FOR_ARBITRARY_TERMS",
            "ADMISSIBLE_SOURCE_EVIDENCE_DOES_NOT_BY_ITSELF_PROVE_A_ROLE_WITHOUT_THE_VERIFIED_BRIDGE",
            "NO_FULL_H100_TERMINAL_CREDIT",
        ],
        "h100_terminal_credit_delta":0,
    }
