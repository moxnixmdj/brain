"""Shared authenticated positive-policy resolution.

A sound semantic proof may entail a caller-declared policy-condition formula. That
logical entailment is not a proof that the policy itself is adequate. This helper
centralizes the content-addressed adequacy authentication boundary already enforced
by proof_carrying_semantic_refinement_v3 so later semantic-proof versions cannot
silently regress to caller self-certification.

This helper has no terminal authority.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.monotone_semantic_constraint_kernel_v1 import resolve_common_policy
import canonical.runtime.proof_carrying_semantic_refinement_v3 as adequacy_auth

SCHEMA = "BRAIN_AUTHENTICATED_POLICY_RESOLUTION_V1"


def resolve_authenticated_policy(
    decision_basis: Sequence[str],
    policy_conditions: Mapping[str, Mapping[str, Any]],
    *,
    proved_constraints: Sequence[Mapping[str, Any]],
    policy_adequacy_bindings: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    refinement = resolve_common_policy(
        decision_basis,
        policy_conditions,
        formal_source_constraints=proved_constraints,
        proposed_refinements=proved_constraints,
    )
    if refinement.get("status") == "FAIL_CLOSED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": "SEMANTIC_REFINEMENT_FAIL_CLOSED",
            "semantic_refinement": refinement,
            "entailed_policy_conditions": [],
            "certified_common_policies": [],
            "authenticated_policy_adequacy": [],
            "rejected_policy_adequacy_bindings": [],
            "terminal_authority": False,
        }

    entailed = list(refinement.get("certified_common_policies", []))
    bindings = (
        policy_adequacy_bindings
        if isinstance(policy_adequacy_bindings, Mapping)
        else {}
    )

    certified: list[str] = []
    authenticated: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for policy_id in entailed:
        condition = policy_conditions.get(policy_id)
        if not isinstance(condition, Mapping):
            rejected.append({
                "policy_id": policy_id,
                "reason": "POLICY_CONDITION_MISSING",
            })
            continue

        ok, row = adequacy_auth._authenticate_policy_adequacy(
            policy_id,
            condition,
            bindings.get(policy_id),
        )
        if ok:
            certified.append(policy_id)
            authenticated.append(row)
        else:
            rejected.append(row)

    if certified:
        status = "COMMON_POLICY_CERTIFIED"
    elif entailed:
        status = "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"
    else:
        status = "UNRESOLVED"

    return {
        "schema": SCHEMA,
        "status": status,
        "semantic_refinement": refinement,
        "entailed_policy_conditions": sorted(entailed),
        "certified_common_policies": sorted(certified),
        "authenticated_policy_adequacy": sorted(
            authenticated, key=lambda x: x["policy_id"]
        ),
        "rejected_policy_adequacy_bindings": sorted(
            rejected, key=lambda x: x.get("policy_id", "")
        ),
        "terminal_authority": False,
        "boundary": (
            "SOURCE_OR_SEMANTIC_ENTAILMENT_ONLY_PROVES_POLICY_CONDITION_FORMULAS;"
            "COMMON_POLICY_CERTIFIED_REQUIRES_SEPARATE_CONTENT_ADDRESSED_BRAIN_OWNED_"
            "ADEQUACY_CERTIFICATE_PLUS_INDEPENDENT_VERIFICATION"
        ),
    }
