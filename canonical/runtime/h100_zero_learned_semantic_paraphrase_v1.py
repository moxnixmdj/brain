"""Zero-learned bounded semantic-role paraphrase normalizer for H100.

This module maps a finite, explicit ontology of role phrases into input/target
roles. It is intentionally not an open-world language model. If both role sides
are not identified from declared ontology cues, it abstains.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_H100_ZERO_LEARNED_SEMANTIC_PARAPHRASE_V1"
_IDENT = r"[A-Za-z_][A-Za-z0-9_]*"

_INPUT_PATTERNS = (
    re.compile(r"^\s*We\s+vary\s+(.+?)\s*;", re.IGNORECASE),
    re.compile(r"^\s*Knobs\s+are\s+(.+?)\s*;", re.IGNORECASE),
    re.compile(r"^\s*Predictors\s*:\s*(.+?)\s*;", re.IGNORECASE),
    re.compile(r"^\s*Features\s*:\s*(.+?)\s*;", re.IGNORECASE),
    re.compile(r"^\s*Controlled\s+factors\s*:\s*(.+?)\s*;", re.IGNORECASE),
    re.compile(r"^\s*Manipulated\s+variables\s*:\s*(.+?)\s*;", re.IGNORECASE),
    re.compile(r"^\s*Parameters\s*:\s*(.+?)\s*;", re.IGNORECASE),
    re.compile(r"^\s*Inputs\s*:\s*(.+?)\s*;", re.IGNORECASE),
)

_OUTPUT_PATTERNS = (
    re.compile(r"\bthe\s+response\s+is\s+("+_IDENT+r")\b", re.IGNORECASE),
    re.compile(r"\breadout\s+is\s+("+_IDENT+r")\b", re.IGNORECASE),
    re.compile(r"\bdependent\s+variable\s*:\s*("+_IDENT+r")\b", re.IGNORECASE),
    re.compile(r"\blabel\s*:\s*("+_IDENT+r")\b", re.IGNORECASE),
    re.compile(r"\bendpoint\s*:\s*("+_IDENT+r")\b", re.IGNORECASE),
    re.compile(r"\boutcome\s*:\s*("+_IDENT+r")\b", re.IGNORECASE),
    re.compile(r"\bresult\s*:\s*("+_IDENT+r")\b", re.IGNORECASE),
    re.compile(r"\bsensor\s+reports\s+("+_IDENT+r")\b", re.IGNORECASE),
)

class SemanticRoleError(ValueError):
    pass

def _parse_names(text: str) -> list[str]:
    normalized = re.sub(r"\s+and\s+", ",", text.strip(), flags=re.IGNORECASE)
    parts = [x.strip() for x in normalized.split(",") if x.strip()]
    if not parts:
        raise SemanticRoleError("INPUT_NAMES_EMPTY")
    if any(re.fullmatch(_IDENT, x) is None for x in parts):
        raise SemanticRoleError("INPUT_NAME_INVALID")
    if len(parts) != len(set(parts)):
        raise SemanticRoleError("INPUT_NAME_DUPLICATE")
    return sorted(parts)

def _match_unique(patterns, text: str, label: str):
    matches=[]
    for p in patterns:
        m=p.search(text)
        if m:
            matches.append(m.group(1))
    unique=sorted(set(matches))
    if len(unique)>1:
        raise SemanticRoleError(label+"_CONFLICT")
    return unique[0] if unique else None

def induce_semantic_roles(text: Any) -> dict[str, Any]:
    if not isinstance(text,str) or not text.strip():
        raise SemanticRoleError("TEXT_INVALID")
    input_segment=_match_unique(_INPUT_PATTERNS,text,"INPUT_CUE")
    target=_match_unique(_OUTPUT_PATTERNS,text,"OUTPUT_CUE")

    if input_segment is None or target is None:
        return {
            "schema":SCHEMA,
            "status":"ABSTAIN_DIRECTION_NOT_IDENTIFIED",
            "inputs":[],
            "target":None,
            "persistent_learned_bytes":0,
            "external_frontier_model_calls":0,
            "external_learned_capability_calls":0,
            "random_search":False,
            "hard_nonclaim":"FINITE_ONTOLOGY_ABSTENTION_IS_NOT_OPEN_WORLD_SEMANTICS",
        }

    inputs=_parse_names(input_segment)
    if target in inputs:
        raise SemanticRoleError("INPUT_TARGET_OVERLAP")
    return {
        "schema":SCHEMA,
        "status":"ROLES_IDENTIFIED",
        "inputs":inputs,
        "target":target,
        "persistent_learned_bytes":0,
        "external_frontier_model_calls":0,
        "external_learned_capability_calls":0,
        "random_search":False,
        "hard_nonclaim":"FINITE_ONTOLOGY_ROLE_MAPPING_IS_NOT_OPEN_WORLD_SEMANTICS",
    }
