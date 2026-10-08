"""Bounded predicate-argument support relation v1.

Deterministically proves SUPPORTS / CONFLICTS only for source texts and claims
that both fit Brain's existing bounded explicit modal predicate-argument grammar.

Active and passive voice are normalized to the same semantic role tuple. Exact
surface wording is not required. Unsupported coordination, co-reference,
ellipsis, open lexical inference, and world knowledge remain UNRESOLVED.

This module has no policy, DB, U-empty, acceptance, or terminal authority.
"""
from __future__ import annotations

from typing import Any

from canonical.runtime.bounded_predicate_argument_semantics import parse_clause

SCHEMA = "PROJECT_BRAIN_BOUNDED_PREDICATE_ARGUMENT_SUPPORT_V1"


def _normalized(text: str) -> dict[str, Any] | None:
    parsed = parse_clause(text)
    if parsed.get("status") != "RESOLVED":
        return None
    g = parsed["semantic_graph"]
    condition = parsed.get("condition")
    return {
        "subject": str(g["subject"]).strip().lower(),
        "predicate": str(g["predicate"]).strip().lower(),
        "object": str(g["object"]).strip().lower(),
        "modality": str(g["modality"]).strip().lower(),
        "polarity": str(g["polarity"]).strip().upper(),
        "condition": (
            {
                "relation": str(condition["relation"]).strip().upper(),
                "text": str(condition["text"]).strip().lower(),
            }
            if isinstance(condition, dict)
            else None
        ),
    }


def classify_support(claim_text: str, evidence_text: str, *, evidence_id: str) -> dict[str, Any]:
    if not isinstance(claim_text, str) or not claim_text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "CLAIM_TEXT_REQUIRED"}
    if not isinstance(evidence_text, str) or not evidence_text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "EVIDENCE_TEXT_REQUIRED"}
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "EVIDENCE_ID_REQUIRED"}

    claim = _normalized(claim_text)
    evidence = _normalized(evidence_text)
    if claim is None or evidence is None:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "relation": None,
            "reason": "OUTSIDE_BOUNDED_PREDICATE_ARGUMENT_GRAMMAR",
            "evidence_id": evidence_id,
            "terminal_authority": False,
        }

    claim_core = {k: claim[k] for k in ("subject", "predicate", "object", "modality", "condition")}
    evidence_core = {k: evidence[k] for k in ("subject", "predicate", "object", "modality", "condition")}

    if claim_core != evidence_core:
        return {
            "schema": SCHEMA,
            "status": "RESOLVED",
            "relation": "UNRELATED",
            "reason": "NORMALIZED_PREDICATE_ARGUMENT_CORE_DIFFERS",
            "claim_graph": claim,
            "evidence_graph": evidence,
            "evidence_id": evidence_id,
            "terminal_authority": False,
        }

    if claim["polarity"] == evidence["polarity"]:
        relation = "SUPPORTS"
    else:
        relation = "CONFLICTS"

    return {
        "schema": SCHEMA,
        "status": "RESOLVED",
        "relation": relation,
        "reason": "BOUNDED_NORMALIZED_PREDICATE_ARGUMENT_MATCH",
        "claim_graph": claim,
        "evidence_graph": evidence,
        "active_passive_voice_normalized": True,
        "evidence_id": evidence_id,
        "terminal_authority": False,
        "boundary": (
            "SIMPLE_EXPLICIT_MODAL_PREDICATE_ARGUMENT_CLAUSES_ONLY__"
            "NO_GENERAL_PARAPHRASE_COREFERENCE_WORLD_KNOWLEDGE_OR_NLI"
        ),
    }
