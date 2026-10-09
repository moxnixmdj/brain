"""Bounded cross-document glossary Finance UNLESS producer V1.

Owned scope:
- one content-addressed rule document with exactly one UNLESS rule;
- one separate content-addressed glossary document with exactly one matching term;
- the glossary maps that term to one already-certified Boolean/decimal condition;
- one content-addressed typed context proves the condition;
- branch selection is deterministic.

The glossary is explicit knowledge. This module does not infer synonymy, ontology,
world facts, source authority, or general cross-document semantics.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping

from canonical.runtime.certified_scope_fragment_v1 import parse_scope
from canonical.runtime.certified_typed_unless_condition_v1 import evaluate_unless_condition
from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256

SCHEMA="PROJECT_BRAIN_FINANCE_CROSS_DOCUMENT_GLOSSARY_UNLESS_BRANCH_V1"
CASE_SCHEMA="PROJECT_BRAIN_FINANCE_CROSS_DOCUMENT_GLOSSARY_UNLESS_CASE_V1"
RULE_SCHEMA="PROJECT_BRAIN_FINANCE_RULE_DOCUMENT_V1"
GLOSSARY_SCHEMA="PROJECT_BRAIN_FINANCE_GLOSSARY_DOCUMENT_V1"
RESULT_SCHEMA="PROJECT_BRAIN_FINANCE_CROSS_DOCUMENT_GLOSSARY_UNLESS_RESULT_V1"

def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _sha_text(v:str)->str:
    return sha256(v.encode("utf-8")).hexdigest()

def _sha_obj(v:Any)->str:
    return sha256(_canon(v).encode("utf-8")).hexdigest()

def _norm(v:Any,label:str)->str:
    if not isinstance(v,str):
        raise ValueError(label+"_INVALID")
    out=" ".join(v.strip().split())
    if not out:
        raise ValueError(label+"_EMPTY")
    return out

def compute(
    case:Mapping[str,Any],
    rule_document:Mapping[str,Any],
    glossary_document:Mapping[str,Any],
)->dict[str,Any]:
    if not isinstance(case,Mapping) or case.get("schema")!=CASE_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")
    if not isinstance(rule_document,Mapping) or rule_document.get("schema")!=RULE_SCHEMA:
        raise ValueError("RULE_DOCUMENT_SCHEMA_INVALID")
    if not isinstance(glossary_document,Mapping) or glossary_document.get("schema")!=GLOSSARY_SCHEMA:
        raise ValueError("GLOSSARY_DOCUMENT_SCHEMA_INVALID")

    source_id=_norm(case.get("source_id"),"SOURCE_ID")
    rule_id=_norm(rule_document.get("document_id"),"RULE_DOCUMENT_ID")
    glossary_id=_norm(glossary_document.get("document_id"),"GLOSSARY_DOCUMENT_ID")
    if rule_id==glossary_id:
        raise ValueError("DOCUMENT_ID_COLLISION")

    expected_rule_id=_norm(case.get("rule_document_id"),"CASE_RULE_DOCUMENT_ID")
    expected_glossary_id=_norm(case.get("glossary_document_id"),"CASE_GLOSSARY_DOCUMENT_ID")
    if rule_id!=expected_rule_id:
        raise ValueError("RULE_DOCUMENT_ID_MISMATCH")
    if glossary_id!=expected_glossary_id:
        raise ValueError("GLOSSARY_DOCUMENT_ID_MISMATCH")

    rule_text=_norm(rule_document.get("rule_text"),"RULE_TEXT")
    entries=glossary_document.get("entries")
    if not isinstance(entries,list) or len(entries)!=1 or not isinstance(entries[0],Mapping):
        raise ValueError("EXACTLY_ONE_GLOSSARY_ENTRY_REQUIRED")
    term=_norm(entries[0].get("term"),"GLOSSARY_TERM")
    definition=_norm(entries[0].get("definition"),"GLOSSARY_DEFINITION")

    typed_context=case.get("typed_context")
    expected_ctx=case.get("typed_context_sha256")
    if not isinstance(typed_context,Mapping):
        raise ValueError("TYPED_CONTEXT_REQUIRED")
    actual_ctx=typed_context_sha256(typed_context)
    if not isinstance(expected_ctx,str) or actual_ctx!=expected_ctx:
        raise ValueError("TYPED_CONTEXT_CONTENT_ADDRESS_MISMATCH")

    scoped=parse_scope(rule_text,source=source_id+"#rule")
    parsed=scoped.get("parse") if scoped.get("status")=="PARSED" else None
    if not isinstance(parsed,Mapping) or parsed.get("relation")!="UNLESS":
        raise ValueError("EXACT_SINGLE_UNLESS_RULE_REQUIRED")
    left=parsed.get("left_span"); right=parsed.get("right_span")
    if not isinstance(left,list) or len(left)!=2 or not isinstance(right,list) or len(right)!=2:
        raise ValueError("UNLESS_SPAN_INVALID")
    ordinary=rule_text[left[0]:left[1]]
    reference=rule_text[right[0]:right[1]]
    if reference.casefold()!=term.casefold():
        raise ValueError("GLOSSARY_TERM_REFERENCE_MISMATCH")

    expanded=ordinary+" unless "+definition+"."
    condition=evaluate_unless_condition(
        expanded,
        source_id=source_id+"#glossary-expanded",
        typed_context=typed_context,
        expected_typed_context_sha256=actual_ctx,
    )
    if condition.get("status") not in {"PROVED_TRUE","PROVED_FALSE"}:
        raise ValueError(
            "GLOSSARY_CONDITION_NOT_PROVED:"
            +str(condition.get("reason") or condition.get("errors"))
        )
    holds=condition.get("condition_holds") is True
    selected_span=right if holds else left
    selected_text=rule_text[selected_span[0]:selected_span[1]]

    return {
        "schema":RESULT_SCHEMA,
        "status":"PASS__CROSS_DOCUMENT_GLOSSARY_TYPED_UNLESS_BRANCH_SELECTED",
        "pass":True,
        "source_id":source_id,
        "rule_document_id":rule_id,
        "glossary_document_id":glossary_id,
        "rule_document_semantic_sha256":_sha_obj(rule_document),
        "glossary_document_semantic_sha256":_sha_obj(glossary_document),
        "typed_context_sha256":actual_ctx,
        "rule_text_sha256":_sha_text(rule_text),
        "glossary_term":term,
        "glossary_term_sha256":_sha_text(term),
        "glossary_definition_sha256":_sha_text(definition),
        "expanded_rule_sha256":_sha_text(expanded),
        "rule_scope_id":parsed.get("scope_id"),
        "condition_holds":holds,
        "condition_atom_id":condition.get("condition_atom_id"),
        "proved_constraint":condition.get("proved_constraint"),
        "field_name":condition.get("field_name"),
        "field_type":condition.get("field_type"),
        "operator":condition.get("operator"),
        "literal":condition.get("literal"),
        "selected_branch":"EXCEPTION_BRANCH" if holds else "ORDINARY_BRANCH",
        "selected_span":list(selected_span),
        "selected_text":selected_text,
        "selected_text_sha256":_sha_text(selected_text),
        "model_dependency_count":0,
        "reference_resolution_authority":"EXACT_CONTENT_ADDRESSED_CROSS_DOCUMENT_GLOSSARY_TERM_TO_TYPED_CONDITION_ONLY",
        "external_world_truth_claimed":False,
        "inferred_synonymy_claimed":False,
        "general_ontology_mapping_claimed":False,
        "general_cross_document_semantics_claimed":False,
        "terminal_authority":False,
    }
