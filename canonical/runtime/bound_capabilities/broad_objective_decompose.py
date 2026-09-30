#!/usr/bin/env python3
"""Fail-closed model-independent decomposition of broad research objectives.

This module does not answer the objective, choose sources, invent facts, or
execute capabilities. It exposes a bounded research-role graph so existing
grounding/composition can reason about the next real causal gap.
"""
from __future__ import annotations

import hashlib
import re

SCHEMA="PROJECT_BRAIN_BROAD_OBJECTIVE_DECOMPOSITION_V1"

_BROAD_PREFIX=re.compile(
    r"^(?:determine|assess|evaluate|investigate|estimate|quantify|compare|analy[sz]e)\b",
    re.IGNORECASE,
)
_GENERIC_METHOD_RUN=re.compile(
    r"\b(?:run|execute)\s+(?:(?:an?|the)\s+)?"
    r"(?:(?:zero[- ]cost|no[- ]cost|free)\s+)?"
    r"(?:(?:independently|autonomously)\s+(?:chosen|selected)\s+)?"
    r"(?:verification|validation|evaluation|analysis|research|checking)\s+"
    r"(?:method|approach|procedure|strategy|check)\b"
    r"(?=\s*(?:[.,;:]|$|\band\b))",
    re.IGNORECASE,
)
_EXPLICIT_ACTION=re.compile(
    r"(?:\busing\s+https?://|\bhttps?://|"
    r"\bsave\s+.+?\.(?:json|csv|md|txt)|"
    r"\bextract\s+json\s+path|"
    r"\bcreate\s+.+?\.(?:json|csv|md|txt)|"
    r"\b(?:run|execute)\s+\S+|"
    r"\bopen\s+https?://)",
    re.IGNORECASE,
)

ROLE_SPECS=(
    (
        "SOURCE_DISCOVERY",
        "Identify authoritative source candidates that can supply evidence needed to resolve the objective.",
        "authoritative source discovery",
    ),
    (
        "EVIDENCE_ACQUISITION",
        "Acquire provenance-bearing evidence for every decision-relevant operand or claim in the objective.",
        "provenance-bearing evidence acquisition",
    ),
    (
        "EVIDENCE_EXTRACTION",
        "Extract typed decision-relevant facts or quantities from the acquired evidence without inventing missing values.",
        "typed evidence extraction",
    ),
    (
        "RELATION_EVALUATION",
        "Evaluate the relation or comparison requested by the objective using verified deterministic capabilities where applicable.",
        "verified deterministic relation evaluation",
    ),
    (
        "DECISION_SYNTHESIS_AND_VERIFICATION",
        "Synthesize the answer from verified evidence while preserving provenance, uncertainty, conflicts, and independent verification requirements.",
        "verified evidence synthesis",
    ),
)


def _canonical(text):
    return " ".join(str(text or "").strip().split())


def _question_shape(text):
    low=text.lower()
    if re.search(r"\bwhether\b",low):
        return "BOOLEAN_ASSESSMENT"
    if re.search(r"\b(?:faster|slower|higher|lower|greater|less|more|fewer)\b",low):
        return "COMPARATIVE"
    if re.match(r"^compare\b",low):
        return "COMPARATIVE"
    if re.match(r"^(?:estimate|quantify)\b",low):
        return "QUANTITATIVE_ESTIMATION"
    return "OPEN_RESEARCH_ASSESSMENT"


def decompose(objective):
    text=_canonical(objective)
    if not text:
        return {
            "schema":SCHEMA,
            "status":"UNSUPPORTED",
            "reason":"OBJECTIVE_REQUIRED",
            "objective":"",
            "roles":[],
            "model_dependency_count":0,
        }
    if len(text)>4000:
        return {
            "schema":SCHEMA,
            "status":"UNSUPPORTED",
            "reason":"OBJECTIVE_TOO_LONG",
            "objective_sha256":hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "roles":[],
            "model_dependency_count":0,
        }
    if not _BROAD_PREFIX.search(text):
        return {
            "schema":SCHEMA,
            "status":"UNSUPPORTED",
            "reason":"BROAD_OBJECTIVE_PREFIX_NOT_RECOGNIZED",
            "objective":text,
            "roles":[],
            "model_dependency_count":0,
        }
    recipe_text=_GENERIC_METHOD_RUN.sub("",text)
    if _EXPLICIT_ACTION.search(recipe_text):
        return {
            "schema":SCHEMA,
            "status":"UNSUPPORTED",
            "reason":"OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE",
            "objective":text,
            "roles":[],
            "model_dependency_count":0,
        }

    roles=[]
    for index,(role,description,required_capability_class) in enumerate(ROLE_SPECS):
        roles.append({
            "index":index,
            "role":role,
            "description":description,
            "required_capability_class":required_capability_class,
            "status":"REQUIRES_GROUNDING",
        })
    return {
        "schema":SCHEMA,
        "status":"DECOMPOSED",
        "objective":text,
        "objective_sha256":hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "question_shape":_question_shape(text),
        "roles":roles,
        "role_count":len(roles),
        "invented_source_urls":[],
        "invented_facts":[],
        "task_specific_literals_added":[],
        "model_dependency_count":0,
    }
