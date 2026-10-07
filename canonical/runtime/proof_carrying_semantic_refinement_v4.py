"""Bridge source-aligned semantic proof v4 into monotone policy resolution.

V4 extends the source proof language with controlled typed conditions. It does not
weaken the policy-adequacy authentication boundary established by V3.

Source entailment is not policy adequacy. Caller-supplied policy conditions remain
logical queries only. COMMON_POLICY_CERTIFIED requires a content-addressed Brain-owned
adequacy certificate plus an independent verification receipt bound to the exact
policy/condition pair.
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

    # The monotone kernel reports which caller-declared policy conditions are
    # entailed by the sound source constraints. That is a logical fact only.
    # Adequacy is authenticated separately using the exact V3 boundary so V4
    # cannot regress to caller self-certification.
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
            "V4_BINDS_CONTROLLED_SOURCE_EXCEPTION_CONDITION_TRUTH_INTO_MONOTONE_POLICY_RESOLUTION;"
            "SOURCE_FACTS_ONLY_ENTAIL_CALLER_DECLARED_POLICY_CONDITIONS;"
            "COMMON_POLICY_CERTIFIED_REQUIRES_THE_V3_CONTENT_ADDRESSED_BRAIN_OWNED_ADEQUACY"
            "_CERTIFICATE_PLUS_INDEPENDENT_VERIFICATION_BOUNDARY"
        ),
    }
