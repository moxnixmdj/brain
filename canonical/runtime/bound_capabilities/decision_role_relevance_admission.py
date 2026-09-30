#!/usr/bin/env python3
"""Bounded deterministic decision-role admission for source relevance.

This module reuses Brain's already-qualified explicit comparison parser. It
does not infer semantic entailment, factual correctness, authority, evidence
sufficiency, or latent roles outside that bounded grammar.

For supported numeric comparison objectives it checks two things that aggregate
BM25 token coverage cannot prove:
1. a candidate preserves the shared decision property/quantity when one can be
   boundedly extracted; and
2. a candidate anchors at least one requested comparison operand identity.

Unsupported/ambiguous objective shapes are marked NOT_APPLICABLE so callers can
preserve their incumbent relevance behavior rather than pretending this module
understands them.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re

SCHEMA="PROJECT_BRAIN_DECISION_ROLE_RELEVANCE_ADMISSION_V1"
_WORD=re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")
_SIMPLE_WORD=re.compile(r"[a-z0-9]+")
_NUMERIC_START=re.compile(r"^\\s*[-+]?(?:\\d|\\.\\d)")
_GENERIC={
    "a","an","and","are","as","at","be","by","for","from","in","is","it","of",
    "on","or","that","the","this","to","was","were","whether","which","with",
    "under","comparable","conditions","condition","bulk","material","materials",
    "sample","samples","value","values","documented","measured","measure",
}

def _canon(value):
    return " ".join(str(value or "").strip().split())

def _load_claim_parser():
    path=pathlib.Path(__file__).resolve().with_name("objective_claim_operand_binding.py")
    spec=importlib.util.spec_from_file_location(
        "project_brain_decision_role_claim_parser",path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("OBJECTIVE_CLAIM_PARSER_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _words(value):
    out=[]
    for token in _SIMPLE_WORD.findall(_canon(value).lower().replace("_","-")):
        if len(token)<2 or token in _GENERIC:
            continue
        if token not in out:
            out.append(token)
    return out

def _hard_ids(tokens):
    return [x for x in tokens if any(ch.isdigit() for ch in x)]

def _right_that_of(value):
    m=re.match(r"^(?:that|those)\s+of\s+(.+)$",_canon(value),re.I)
    return _canon(m.group(1)) if m else None

def _split_that_of_roles(parsed):
    left=_canon(parsed.get("left_entity"))
    right=_canon(parsed.get("right_entity"))
    right_operand=_right_that_of(right)
    if not right_operand:
        return None
    lower=left.lower()
    pos=lower.rfind(" of ")
    if pos<=0 or pos+4>=len(left):
        return None
    property_phrase=_canon(left[:pos])
    left_operand=_canon(left[pos+4:])
    if not property_phrase or not left_operand:
        return None
    return property_phrase,left_operand,right_operand

def _roles(parsed):
    left=_canon(parsed.get("left_entity"))
    right=_canon(parsed.get("right_entity"))
    special=_split_that_of_roles(parsed)
    if special:
        prop,left_operand,right_operand=special
        property_tokens=_words(prop)
        property_core_tokens=property_tokens[-2:] if len(property_tokens)>1 else property_tokens
        left_tokens=_words(left_operand)
        right_tokens=_words(right_operand)
        mode="THAT_OF_SHARED_PROPERTY"
    else:
        left_tokens=_words(left)
        right_tokens=_words(right)
        shared=[x for x in left_tokens if x in set(right_tokens)]
        property_tokens=shared
        property_core_tokens=property_tokens[-2:] if len(property_tokens)>1 else property_tokens
        shared_set=set(shared)
        left_tokens=[x for x in left_tokens if x not in shared_set] or left_tokens
        right_tokens=[x for x in right_tokens if x not in shared_set] or right_tokens
        mode="COMMON_ROLE_TOKENS" if shared else "OPERAND_ONLY"

    return {
        "role_mode":mode,
        "property_tokens":property_tokens,
        "property_core_tokens":property_core_tokens,
        "left_operand_tokens":left_tokens,
        "right_operand_tokens":right_tokens,
        "left_hard_ids":_hard_ids(left_tokens),
        "right_hard_ids":_hard_ids(right_tokens),
    }

def _operand_match(candidate_tokens,roles):
    c=set(candidate_tokens)
    left_ids=roles["left_hard_ids"]
    right_ids=roles["right_hard_ids"]
    all_ids=list(dict.fromkeys(left_ids+right_ids))
    if all_ids:
        matched=[x for x in all_ids if x in c]
        return {
            "method":"EXACT_REQUESTED_OPERAND_DISCRIMINATOR",
            "required_match_count":1,
            "requested_discriminators":all_ids,
            "matched_discriminators":matched,
            "verified":bool(matched),
        }

    left=set(roles["left_operand_tokens"])
    right=set(roles["right_operand_tokens"])
    shared=left & right
    left_unique=[x for x in roles["left_operand_tokens"] if x not in shared]
    right_unique=[x for x in roles["right_operand_tokens"] if x not in shared]
    pool=list(dict.fromkeys(left_unique+right_unique))
    matched=[x for x in pool if x in c]
    return {
        "method":"BOUNDED_OPERAND_TOKEN_ANCHOR",
        "required_match_count":1 if pool else 0,
        "requested_operand_tokens":pool,
        "matched_operand_tokens":matched,
        "verified":bool(matched) if pool else True,
    }

def _property_match(candidate_tokens,roles):
    requested=list(dict.fromkeys(roles.get("property_core_tokens") or roles["property_tokens"]))
    if not requested:
        return {
            "method":"NO_BOUNDED_SHARED_PROPERTY",
            "required_match_count":0,
            "requested_property_tokens":[],
            "matched_property_tokens":[],
            "verified":True,
        }
    required=len(requested)
    c=set(candidate_tokens)
    matched=[x for x in requested if x in c]
    return {
        "method":"BOUNDED_SHARED_PROPERTY_TOKEN_COVERAGE",
        "required_match_count":required,
        "requested_property_tokens":requested,
        "matched_property_tokens":matched,
        "verified":len(matched)>=required,
    }

def evaluate(objective,candidate_text):
    objective=_canon(objective)
    candidate_text=_canon(candidate_text)
    base={
        "schema":SCHEMA,
        "objective":objective or None,
        "status":"NOT_APPLICABLE",
        "applicable":False,
        "verified":True,
        "claim_scope":"BOUNDED_EXPLICIT_COMPARISON_DECISION_ROLE_LEXICAL_ADMISSION_ONLY",
        "semantic_entailment_status":"UNVERIFIED",
        "factual_correctness_status":"UNVERIFIED",
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
    if not objective:
        return {**base,"verified":False,"reason":"OBJECTIVE_REQUIRED"}
    if not candidate_text:
        return {**base,"verified":False,"reason":"CANDIDATE_TEXT_REQUIRED"}

    parser=_load_claim_parser()
    parsed,reason=parser._parse_objective(objective)
    if reason or not isinstance(parsed,dict) or parsed.get("mode")!="NUMERIC_RELATION":
        return {
            **base,
            "reason":reason or "OBJECTIVE_OUTSIDE_NUMERIC_RELATION_SCOPE",
        }

    right_entity=_canon(parsed.get("right_entity"))
    if _NUMERIC_START.match(right_entity):
        return {
            **base,
            "reason":"NUMERIC_THRESHOLD_COMPARISON_PRESERVES_INCUMBENT_RELEVANCE",
            "parsed_objective":{
                "operator":parsed.get("operator"),
                "left_entity":parsed.get("left_entity"),
                "right_entity":right_entity,
            },
        }

    roles=_roles(parsed)
    candidate_tokens=_words(candidate_text)
    property_check=_property_match(candidate_tokens,roles)
    operand_check=_operand_match(candidate_tokens,roles)
    verified=bool(property_check["verified"] and operand_check["verified"])
    return {
        **base,
        "status":"DECISION_ROLE_ADMISSION_VERIFIED" if verified else "DECISION_ROLE_ADMISSION_NOT_VERIFIED",
        "applicable":True,
        "verified":verified,
        "parsed_objective":{
            "operator":parsed.get("operator"),
            "left_entity":parsed.get("left_entity"),
            "right_entity":parsed.get("right_entity"),
        },
        "roles":roles,
        "property_check":property_check,
        "operand_check":operand_check,
        "candidate_tokens":candidate_tokens,
    }

if __name__=="__main__":
    import json,sys
    objective=sys.argv[1] if len(sys.argv)>1 else ""
    candidate=" ".join(sys.argv[2:])
    print(json.dumps(evaluate(objective,candidate),indent=2,sort_keys=True))
