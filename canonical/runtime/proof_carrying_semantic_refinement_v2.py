"""Bridge source-aligned semantic proof v2 into monotone policy resolution.

Checked primitive and certified scope constraints are the only facts admitted into
the monotone semantic state. Missing or rejected claims leave the state broader.
The bridge has no terminal authority.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v2 import verify_proof
from canonical.runtime.monotone_semantic_constraint_kernel_v1 import resolve_common_policy

SCHEMA = "BRAIN_PROOF_CARRYING_SEMANTIC_REFINEMENT_V2"


def resolve_from_source_proof(
    source_text: str,
    *,
    source_id: str,
    claims: Sequence[Mapping[str, Any]],
    decision_basis: Sequence[str],
    policy_conditions: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    proof = verify_proof(source_text, source_id=source_id, claims=claims)
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
            "SOURCE_ALIGNED_V2_PROVES_ONLY_NARROW_PRIMITIVES_AND_CERTIFIED_SCOPE;"
            "POLICY_ADEQUACY_CONDITIONS_AND_DOMAIN_DENOTATIONS_REQUIRE_SEPARATE_SOUND_CERTIFICATES"
        ),
    }
