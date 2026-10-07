"""Bridge source-aligned semantic proof v4 into monotone policy resolution."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v4 import verify_proof
from canonical.runtime.monotone_semantic_constraint_kernel_v1 import resolve_common_policy

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
    return {
        "schema": SCHEMA,
        "status": refinement.get("status"),
        "source_proof": proof,
        "semantic_refinement": refinement,
        "certified_common_policies": refinement.get("certified_common_policies", []),
        "terminal_authority": False,
        "boundary": (
            "V4_BINDS_CONTROLLED_SOURCE_EXCEPTION_CONDITION_TRUTH_INTO_MONOTONE_POLICY_RESOLUTION;"
            "POLICY_ADEQUACY_AND_TYPED_CONTEXT_AUTHORITY_REMAIN_SEPARATE_CERTIFICATE_OBLIGATIONS"
        ),
    }
