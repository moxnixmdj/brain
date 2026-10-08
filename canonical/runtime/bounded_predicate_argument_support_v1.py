"""Bounded predicate-argument support relation v1.

Deterministically proves SUPPORTS / CONFLICTS only for source texts and claims
that both fit Brain's existing bounded explicit modal predicate-argument grammar.

Active/passive equivalence is admitted only for a small explicit regular English
inflection relation checked against the active predicate itself. Irregular or
otherwise unproved morphology is not normalized. Unsupported coordination,
co-reference, ellipsis, open lexical inference, and world knowledge remain
UNRESOLVED or unrelated.

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
        "voice": str(g["voice"]).strip().upper(),
        "condition": (
            {
                "relation": str(condition["relation"]).strip().upper(),
                "text": str(condition["text"]).strip().lower(),
            }
            if isinstance(condition, dict)
            else None
        ),
    }


def _regular_passive_form(active: str) -> str:
    if active.endswith("e"):
        return active + "d"
    if (
        len(active) >= 2
        and active.endswith("y")
        and active[-2] not in "aeiou"
    ):
        return active[:-1] + "ied"
    return active + "ed"


def _predicate_equivalent(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if a["predicate"] == b["predicate"]:
        return True
    if a["voice"] == "ACTIVE" and b["voice"] == "PASSIVE":
        return b["predicate"] == _regular_passive_form(a["predicate"])
    if a["voice"] == "PASSIVE" and b["voice"] == "ACTIVE":
        return a["predicate"] == _regular_passive_form(b["predicate"])
    return False


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

    same_nonpredicate = all(
        claim[k] == evidence[k]
        for k in ("subject", "object", "modality", "condition")
    )
    same_predicate = _predicate_equivalent(claim, evidence)
    if not (same_nonpredicate and same_predicate):
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

    relation = "SUPPORTS" if claim["polarity"] == evidence["polarity"] else "CONFLICTS"
    return {
        "schema": SCHEMA,
        "status": "RESOLVED",
        "relation": relation,
        "reason": "BOUNDED_NORMALIZED_PREDICATE_ARGUMENT_MATCH",
        "claim_graph": claim,
        "evidence_graph": evidence,
        "regular_active_passive_inflection_checked": True,
        "evidence_id": evidence_id,
        "terminal_authority": False,
        "boundary": (
            "SIMPLE_EXPLICIT_MODAL_PREDICATE_ARGUMENT_CLAUSES__"
            "REGULAR_ACTIVE_PASSIVE_INFLECTION_ONLY__NO_IRREGULAR_MORPHOLOGY__"
            "NO_GENERAL_PARAPHRASE_COREFERENCE_WORLD_KNOWLEDGE_OR_NLI"
        ),
    }
