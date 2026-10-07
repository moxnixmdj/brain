"""Bridge source-aligned semantic proof v6 into authenticated policy resolution."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v6 import verify_proof
from canonical.runtime.authenticated_policy_resolution_v1 import resolve_authenticated_policy

SCHEMA = "BRAIN_PROOF_CARRYING_SEMANTIC_REFINEMENT_V6"


def resolve_from_source_proof(
    source_text: str,
    *,
    source_id: str,
    claims: Sequence[Mapping[str, Any]],
    decision_basis: Sequence[str],
    policy_conditions: Mapping[str, Mapping[str, Any]],
    typed_context: Mapping[str, Any] | None = None,
    expected_typed_context_sha256: str | None = None,
    fact_source: str | bytes | None = None,
    fact_source_id: str | None = None,
    policy_adequacy_bindings: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    proof = verify_proof(
        source_text,
        source_id=source_id,
        claims=claims,
        typed_context=typed_context,
        expected_typed_context_sha256=expected_typed_context_sha256,
        fact_source=fact_source,
        fact_source_id=fact_source_id,
    )
    if proof.get("status") == "FAIL_CLOSED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": "SOURCE_PROOF_FAIL_CLOSED",
            "source_proof": proof,
            "terminal_authority": False,
        }

    resolved = resolve_authenticated_policy(
        decision_basis,
        policy_conditions,
        proved_constraints=proof.get("proved_constraints") or [],
        policy_adequacy_bindings=policy_adequacy_bindings,
    )
    return {
        "schema": SCHEMA,
        "status": resolved.get("status"),
        "source_proof": proof,
        "semantic_refinement": resolved.get("semantic_refinement"),
        "entailed_policy_conditions": resolved.get("entailed_policy_conditions", []),
        "certified_common_policies": resolved.get("certified_common_policies", []),
        "authenticated_policy_adequacy": resolved.get("authenticated_policy_adequacy", []),
        "rejected_policy_adequacy_bindings": resolved.get("rejected_policy_adequacy_bindings", []),
        "terminal_authority": False,
        "boundary": (
            "SOURCE_PROOF_VERSION_6_MAY_ENTAIL_POLICY_CONDITIONS;"
            "POLICY_ADEQUACY_IS_AUTHENTICATED_ONLY_BY_THE_SHARED_CONTENT_ADDRESSED_BOUNDARY"
        ),
    }
