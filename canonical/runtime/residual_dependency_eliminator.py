"""Fail-closed residual dependency eliminator for the Project Brain terminal frontier.

This module does not solve arbitrary cognition. It classifies a claimed residual
into the cheapest causally valid disposition before implementation is allowed.

Order:
1. already owned exact route
2. exact derivation
3. source-grounded JIT retrieval
4. finite identifiability / principled abstention
5. verifier-complete proposal-substrate bypass
6. bounded owned synthesis
7. irreducible implementation residual

Any missing evidence required for a disposition fails closed rather than silently
demoting the residual.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ResidualClaim:
    residual_id: str
    required_behavior: str
    exact_owned_route: bool = False
    exactly_derivable: bool = False
    retrievable_source_grounded: bool = False
    finite_hypothesis_space: bool = False
    discriminator_available: bool = False
    observationally_nonidentifiable: bool = False
    verifier_complete_for_scope: bool = False
    proposal_source_has_zero_authority: bool = False
    bounded_owned_synthesis_applies: bool = False
    terminal_success_requires_unverifiable_ranking: bool = False
    evidence: Mapping[str, Any] | None = None


_ALLOWED_PREFIXES = (
    "canonical/",
    "github:",
    "workflow:",
    "artifact:",
    "source:",
)


def _valid_evidence(evidence: Mapping[str, Any] | None) -> bool:
    if not isinstance(evidence, Mapping) or not evidence:
        return False
    for key, value in evidence.items():
        if not isinstance(key, str) or not key:
            return False
        if isinstance(value, str) and value.startswith(_ALLOWED_PREFIXES):
            return True
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
    return False


def eliminate_residual(claim: ResidualClaim) -> dict[str, Any]:
    if not isinstance(claim, ResidualClaim):
        return {"status": "FAIL_CLOSED", "reason": "INVALID_CLAIM_TYPE"}
    if not claim.residual_id or not claim.required_behavior:
        return {"status": "FAIL_CLOSED", "reason": "MISSING_ID_OR_BEHAVIOR"}
    if not _valid_evidence(claim.evidence):
        return {
            "status": "FAIL_CLOSED",
            "reason": "NO_TRACEABLE_EVIDENCE",
            "residual_id": claim.residual_id,
        }

    base = {
        "residual_id": claim.residual_id,
        "required_behavior": claim.required_behavior,
        "implementation_authorized": False,
        "terminal_authority": False,
    }

    if claim.exact_owned_route:
        return {
            **base,
            "status": "ELIMINATED",
            "disposition": "REUSE_OWNED_EXACT_ROUTE",
        }

    if claim.exactly_derivable:
        return {
            **base,
            "status": "ELIMINATED",
            "disposition": "EXACT_DEDUCTIVE_CLOSURE",
        }

    if claim.retrievable_source_grounded:
        return {
            **base,
            "status": "ELIMINATED",
            "disposition": "JIT_SOURCE_GROUNDED_KNOWLEDGE",
        }

    if claim.finite_hypothesis_space:
        if claim.discriminator_available:
            return {
                **base,
                "status": "ELIMINATED",
                "disposition": "FINITE_IDENTIFIABILITY_WITH_MINIMUM_DISCRIMINATOR",
            }
        if claim.observationally_nonidentifiable:
            return {
                **base,
                "status": "ELIMINATED",
                "disposition": "PRINCIPLED_NONIDENTIFIABILITY_ABSTENTION",
            }

    if claim.verifier_complete_for_scope:
        if not claim.proposal_source_has_zero_authority:
            return {
                **base,
                "status": "FAIL_CLOSED",
                "reason": "VERIFIER_BYPASS_REQUIRES_ZERO_PROPOSER_AUTHORITY",
            }
        if claim.terminal_success_requires_unverifiable_ranking:
            return {
                **base,
                "status": "SURVIVES",
                "disposition": "IRREDUCIBLE_UNVERIFIABLE_RANKING",
                "implementation_authorized": True,
            }
        return {
            **base,
            "status": "ELIMINATED",
            "disposition": "VERIFIER_COMPLETE_PROPOSAL_SUBSTRATE_BYPASS",
        }

    if claim.bounded_owned_synthesis_applies:
        return {
            **base,
            "status": "ELIMINATED",
            "disposition": "BOUNDED_BRAIN_OWNED_SYNTHESIS",
        }

    return {
        **base,
        "status": "SURVIVES",
        "disposition": "IRREDUCIBLE_IMPLEMENTATION_RESIDUAL",
        "implementation_authorized": True,
    }


def eliminate_batch(claims: Sequence[ResidualClaim]) -> dict[str, Any]:
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        return {"status": "FAIL_CLOSED", "reason": "CLAIMS_NOT_SEQUENCE"}
    results = [eliminate_residual(c) for c in claims]
    if any(r.get("status") == "FAIL_CLOSED" for r in results):
        return {
            "status": "FAIL_CLOSED",
            "results": results,
            "surviving_residual_ids": [],
        }
    survivors = [
        r["residual_id"]
        for r in results
        if r.get("status") == "SURVIVES"
    ]
    return {
        "status": "PASS",
        "results": results,
        "surviving_residual_ids": survivors,
        "implementation_count": len(survivors),
        "terminal_authority": False,
    }
