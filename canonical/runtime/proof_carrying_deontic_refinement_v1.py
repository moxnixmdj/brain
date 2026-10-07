from __future__ import annotations
from canonical.runtime.source_aligned_deontic_extension_v1 import verify_proof
from canonical.runtime.monotone_semantic_constraint_kernel_v1 import resolve_common_policy

def resolve_from_source_proof(
    source_text, *, source_id, claims, decision_basis, policy_conditions,
    typed_context=None, expected_typed_context_sha256=None,
    fact_source=None, fact_source_id=None,
):
    proof = verify_proof(
        source_text, source_id=source_id, claims=claims,
        typed_context=typed_context,
        expected_typed_context_sha256=expected_typed_context_sha256,
        fact_source=fact_source, fact_source_id=fact_source_id,
    )
    if proof.get("status") == "FAIL_CLOSED":
        return {"status": "FAIL_CLOSED", "source_proof": proof, "terminal_authority": False}
    proved = proof.get("proved_constraints") or []
    refinement = resolve_common_policy(
        decision_basis, policy_conditions,
        formal_source_constraints=proved, proposed_refinements=proved,
    )
    return {
        "status": refinement.get("status"), "source_proof": proof,
        "semantic_refinement": refinement,
        "certified_common_policies": refinement.get("certified_common_policies", []),
        "terminal_authority": False,
    }
