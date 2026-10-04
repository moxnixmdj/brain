#!/usr/bin/env python3
"""Fail-closed compiler for stronger-proof replacement races.

This module NEVER grants acceptance credit. It only:
1. compiles nondominated replacement-proof route candidates; and
2. mechanically checks whether a proposed replacement certificate contains
   the minimum fields needed for a later predicate-specific verifier.

A new benchmark score alone is never a replacement proof.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_TERMINAL_STRONGER_PROOF_REPLACEMENT_COMPILER_V1"

ROUTE_ORDER = (
    "FORMAL_ENTAILMENT",
    "OBJECTIVE_CEILING_OR_FLOOR",
    "EXHAUSTIVE_FINITE_UNIVERSE",
    "SCOPE_SAFE_STRONGER_PROOF",
    "EXISTING_CONTENT_ADDRESSED_COMPARATOR_EVIDENCE",
    "MATCHED_EMPIRICAL_COMPARISON",
)

ALLOWED_SCOPE_RELATIONS = {"EXACT", "SUPERSET"}


def _norm(x: Any) -> str:
    return " ".join(str(x or "").strip().split())


def compile_replacement_races(
    predicate_ids: Sequence[str],
    *,
    deleted_routes: Mapping[str, Iterable[str]] | None = None,
) -> dict[str, Any]:
    deleted_routes = deleted_routes or {}
    races = []
    seen = set()
    for raw in predicate_ids:
        pid = _norm(raw)
        if not pid or pid in seen:
            continue
        seen.add(pid)
        blocked = {_norm(x) for x in deleted_routes.get(pid, ())}
        routes = [
            {
                "route": route,
                "candidate_only": True,
                "acceptance_credit_authorized": False,
                "requires_predicate_specific_implication_certificate": route
                != "MATCHED_EMPIRICAL_COMPARISON",
            }
            for route in ROUTE_ORDER
            if route not in blocked
        ]
        races.append({"predicate_id": pid, "routes": routes})
    return {
        "schema": SCHEMA,
        "status": "COMPILED_CANDIDATE_RACES__ZERO_CREDIT",
        "predicate_count": len(races),
        "races": races,
        "probability_policy": "UNKNOWN_REMAINS_UNKNOWN__NO_INVENTED_POINT_PROBABILITIES",
        "acceptance_credit_authorized": False,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def check_replacement_certificate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Mechanical minimum gate, not a semantic theorem prover."""
    reasons: list[str] = []
    pid = _norm(candidate.get("target_predicate"))
    target_hash = _norm(candidate.get("target_contract_sha256"))
    proof_kind = _norm(candidate.get("proof_kind"))
    scope = _norm(candidate.get("scope_relation")).upper()

    if not pid:
        reasons.append("MISSING_TARGET_PREDICATE")
    if len(target_hash) != 64 or any(
        c not in "0123456789abcdefABCDEF" for c in target_hash
    ):
        reasons.append("INVALID_OR_MISSING_TARGET_CONTRACT_SHA256")
    if proof_kind not in ROUTE_ORDER[:4]:
        reasons.append("PROOF_KIND_NOT_A_STRONGER_PROOF_ROUTE")
    if scope not in ALLOWED_SCOPE_RELATIONS:
        reasons.append("SCOPE_RELATION_MUST_BE_EXACT_OR_SUPERSET")
    if candidate.get("semantic_implication_proved") is not True:
        reasons.append("SEMANTIC_IMPLICATION_NOT_PROVED")
    if candidate.get("metric_threshold_implication_proved") is not True:
        reasons.append("METRIC_THRESHOLD_IMPLICATION_NOT_PROVED")
    if candidate.get("independent_verification_pass") is not True:
        reasons.append("INDEPENDENT_VERIFICATION_NOT_BOUND")
    if candidate.get("source_content_addressed") is not True:
        reasons.append("SOURCE_NOT_CONTENT_ADDRESSED")

    complete = not reasons
    return {
        "schema": SCHEMA,
        "replacement_certificate_mechanically_complete": complete,
        "reasons": reasons,
        "acceptance_credit_authorized": False,
        "requires_separate_predicate_specific_activation": True,
    }
