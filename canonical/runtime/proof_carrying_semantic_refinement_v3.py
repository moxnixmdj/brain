"""Bridge source-aligned semantic proof v3 into monotone policy resolution.

Only constraints independently accepted by the v3 proof checker enter the semantic
state. Exact typed-field atoms are therefore usable alongside source-aligned scope
atoms, but neither the typed-context authority nor policy adequacy self-authenticates.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v3 import verify_proof
from canonical.runtime.monotone_semantic_constraint_kernel_v1 import resolve_common_policy

SCHEMA = "BRAIN_PROOF_CARRYING_SEMANTIC_REFINEMENT_V3"


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
            "V3_ADDS_CONTENT_ADDRESSED_EXACT_TYPED_VALUES_TO_THE_NARROW_SOURCE_ALIGNED_FRAGMENT;"
            "EXPECTED_DIGEST_AUTHORITY_FIELD_DENOTATION_AND_POLICY_ADEQUACY_REQUIRE_SEPARATE_SOUND_CERTIFICATES"
        ),
    }
