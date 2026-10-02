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
    mechanical_suffix_owned: bool = False
    decomposes_to_existing_residuals: bool = False
    dependency_residual_ids: tuple[str, ...] = ()
    terminal_success_requires_unverifiable_ranking: bool = False
    terminal_failure_required_before_implementation: bool = False
    repeatable_solvable_terminal_failure_observed: bool = False
    current_composed_route_exists: bool = False
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

    if claim.terminal_failure_required_before_implementation:
        if not claim.current_composed_route_exists:
            return {
                **base,
                "status": "FAIL_CLOSED",
                "reason": "PROOF_ONLY_DEFERRAL_REQUIRES_CURRENT_COMPOSED_ROUTE",
            }
        if not claim.repeatable_solvable_terminal_failure_observed:
            return {
                **base,
                "status": "ELIMINATED",
                "disposition": "PROOF_ONLY_DEFERRED__MEASURE_CURRENT_COMPOSED_ROUTE_FIRST",
                "reopen_condition": "REPEATABLE_SOLVABLE_CAUSALLY_LOCALIZED_TERMINAL_FAILURE",
            }

    if claim.mechanical_suffix_owned or claim.decomposes_to_existing_residuals or claim.dependency_residual_ids:
        if not (claim.mechanical_suffix_owned and claim.decomposes_to_existing_residuals and claim.dependency_residual_ids):
            return {
                **base,
                "status": "FAIL_CLOSED",
                "reason": "DEPENDENCY_RELOCATION_REQUIRES_OWNED_SUFFIX_DECOMPOSITION_AND_NONEMPTY_DEPENDENCIES",
            }
        deps = tuple(claim.dependency_residual_ids)
        if claim.residual_id in set(deps):
            return {
                **base,
                "status": "FAIL_CLOSED",
                "reason": "DEPENDENCY_RELOCATION_SELF_CYCLE",
            }
        if any(not isinstance(x, str) or not x for x in deps):
            return {
                **base,
                "status": "FAIL_CLOSED",
                "reason": "DEPENDENCY_RELOCATION_INVALID_DEPENDENCY_ID",
            }
        return {
            **base,
            "status": "ELIMINATED",
            "disposition": "DEPENDENCY_RELOCATION__OWNED_MECHANICAL_SUFFIX_PLUS_EXISTING_RESIDUALS",
            "dependency_residual_ids": list(deps),
        }

    return {
        **base,
        "status": "SURVIVES",
        "disposition": "IRREDUCIBLE_IMPLEMENTATION_RESIDUAL",
        "implementation_authorized": True,
    }


def eliminate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Classify a frozen JSON-style residual batch without silently accepting fields."""
    if not isinstance(payload, Mapping):
        return {"status": "FAIL_CLOSED", "reason": "PAYLOAD_NOT_MAPPING"}
    rows = payload.get("claims")
    if not isinstance(rows, list):
        return {"status": "FAIL_CLOSED", "reason": "CLAIMS_NOT_LIST"}
    allowed = set(ResidualClaim.__dataclass_fields__)
    claims: list[ResidualClaim] = []
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            return {"status": "FAIL_CLOSED", "reason": f"CLAIM_NOT_MAPPING:{i}"}
        unknown = sorted(set(row) - allowed)
        if unknown:
            return {"status": "FAIL_CLOSED", "reason": f"UNKNOWN_CLAIM_FIELDS:{i}:" + ",".join(unknown)}
        data = dict(row)
        deps = data.get("dependency_residual_ids", ())
        if isinstance(deps, list):
            data["dependency_residual_ids"] = tuple(deps)
        try:
            claims.append(ResidualClaim(**data))
        except Exception as exc:
            return {"status": "FAIL_CLOSED", "reason": f"CLAIM_CONSTRUCTION_FAILED:{i}:{type(exc).__name__}"}
    out = eliminate_batch(claims)
    out["schema"] = "PROJECT_BRAIN_RESIDUAL_DEPENDENCY_ELIMINATION_VERDICT_V1"
    return out


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
