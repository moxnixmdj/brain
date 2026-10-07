"""Bridge source-aligned semantic proof v4 into monotone policy resolution.

Source entailment is not policy adequacy. Caller-supplied policy conditions are
logical queries only. COMMON_POLICY_CERTIFIED requires the exact content-addressed
Brain-owned adequacy certificate plus independent verification boundary already
enforced by V3.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v4 import verify_proof
from canonical.runtime.monotone_semantic_constraint_kernel_v1 import resolve_common_policy
import canonical.runtime.proof_carrying_semantic_refinement_v3 as adequacy_auth

SCHEMA = "BRAIN_PROOF_CARRYING_SEMANTIC_REFINEMENT_V4"


def resolve_from_source_proof(
    source_text: str,
    *,
    source_id: str,
    claims: Sequence[Mapping[str, Any]],
    decision_basis: Sequence[str],
    policy_conditions: Mapping[str, Mapping[str, Any]],
    typed_context: Mapping[str, Any] | None = None,
    expected_typed_context_sha256: str | None = None,
    policy_adequacy_bindings: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    proof = verify_proof(
        source_text,
        source_id=source_id,
        claims=claims,
        typed_context=typed_context,
        expected_typed_context_sha256=expected_typed_context_sha256,
    )
    if proof.get("status") == "FAIL_CLOSED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": "SOURCE_PROOF_FAIL_CLOSED",
            "source_proof": proof,
            "terminal_authority": False,
        }

    proved = proof.get("proved_constraints") or []
    refinement = resolve_common_policy(
        decision_basis,
        policy_conditions,
        formal_source_constraints=proved,
        proposed_refinements=proved,
    )
    if refinement.get("status") == "FAIL_CLOSED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": "SEMANTIC_REFINEMENT_FAIL_CLOSED",
            "source_proof": proof,
            "semantic_refinement": refinement,
            "terminal_authority": False,
        }

    # The monotone kernel proves only that a caller-declared policy condition is
    # entailed by the sound source constraints. It does not prove the policy is
    # adequate. Reuse the exact V3 content-addressed adequacy authentication
    # boundary so later source-proof versions cannot silently weaken it.
    entailed = list(refinement.get("certified_common_policies", []))
    bindings = (
        policy_adequacy_bindings
        if isinstance(policy_adequacy_bindings, Mapping)
        else {}
    )

    certified: list[str] = []
    auth_rows: list[dict[str, Any]] = []
    rejected_auth: list[dict[str, Any]] = []
    for pid in entailed:
        condition = policy_conditions.get(pid)
        if not isinstance(condition, Mapping):
            rejected_auth.append({
                "policy_id": pid,
                "reason": "POLICY_CONDITION_MISSING",
            })
            continue
        ok, row = adequacy_auth._authenticate_policy_adequacy(
            pid,
            condition,
            bindings.get(pid),
        )
        if ok:
            certified.append(pid)
            auth_rows.append(row)
        else:
            rejected_auth.append(row)

    if certified:
        status = "COMMON_POLICY_CERTIFIED"
    elif entailed:
        status = "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"
    else:
        status = "UNRESOLVED"

    return {
        "schema": SCHEMA,
        "status": status,
        "source_proof": proof,
        "semantic_refinement": refinement,
        "entailed_policy_conditions": entailed,
        "certified_common_policies": sorted(certified),
        "authenticated_policy_adequacy": sorted(
            auth_rows, key=lambda x: x["policy_id"]
        ),
        "rejected_policy_adequacy_bindings": sorted(
            rejected_auth, key=lambda x: x.get("policy_id", "")
        ),
        "terminal_authority": False,
        "boundary": (
            "SOURCE_FACTS_ONLY_ENTAIL_CALLER_DECLARED_POLICY_CONDITIONS;"
            "SOURCE_ENTAILMENT_IS_NOT_POLICY_ADEQUACY;"
            "COMMON_POLICY_CERTIFIED_REQUIRES_THE_V3_CONTENT_ADDRESSED_BRAIN_OWNED_"
            "ADEQUACY_CERTIFICATE_PLUS_INDEPENDENT_VERIFICATION_BOUNDARY"
        ),
    }
