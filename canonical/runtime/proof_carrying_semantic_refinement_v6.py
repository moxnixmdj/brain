"""Proof-carrying semantic refinement v6 with authenticated policy adequacy."""
from __future__ import annotations
from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v6 import verify_proof
from canonical.runtime.monotone_semantic_constraint_kernel_v1 import resolve_common_policy
from canonical.runtime.proof_carrying_semantic_refinement_v3 import _authenticate_policy_adequacy

SCHEMA="BRAIN_PROOF_CARRYING_SEMANTIC_REFINEMENT_V6"

def resolve_from_source_proof(
    source_text: str,
    *,
    source_id: str,
    claims: Sequence[Mapping[str,Any]],
    decision_basis: Sequence[str],
    policy_conditions: Mapping[str,Mapping[str,Any]],
    typed_context: Mapping[str,Any] | None=None,
    expected_typed_context_sha256: str | None=None,
    fact_source: str | bytes | None=None,
    fact_source_id: str | None=None,
    policy_adequacy_bindings: Mapping[str,Mapping[str,Any]] | None=None,
)->dict[str,Any]:
    proof=verify_proof(
        source_text,source_id=source_id,claims=claims,typed_context=typed_context,
        expected_typed_context_sha256=expected_typed_context_sha256,
        fact_source=fact_source,fact_source_id=fact_source_id,
    )
    if proof.get("status")=="FAIL_CLOSED":
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"SOURCE_PROOF_FAIL_CLOSED",
                "source_proof":proof,"terminal_authority":False}
    proved=proof.get("proved_constraints") or []
    refinement=resolve_common_policy(
        decision_basis,policy_conditions,
        formal_source_constraints=proved,proposed_refinements=proved,
    )
    if refinement.get("status")=="FAIL_CLOSED":
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"SEMANTIC_REFINEMENT_FAIL_CLOSED",
                "source_proof":proof,"semantic_refinement":refinement,"terminal_authority":False}
    entailed=list(refinement.get("certified_common_policies",[]))
    bindings=policy_adequacy_bindings if isinstance(policy_adequacy_bindings,Mapping) else {}
    certified=[]; accepted=[]; rejected=[]
    for pid in entailed:
        condition=policy_conditions.get(pid)
        if not isinstance(condition,Mapping):
            rejected.append({"policy_id":pid,"reason":"POLICY_CONDITION_MISSING"})
            continue
        ok,row=_authenticate_policy_adequacy(pid,condition,bindings.get(pid))
        if ok:
            certified.append(pid); accepted.append(row)
        else:
            rejected.append(row)
    status=("COMMON_POLICY_CERTIFIED" if certified else
            "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED" if entailed else
            "UNRESOLVED")
    return {
        "schema":SCHEMA,"status":status,"source_proof":proof,
        "semantic_refinement":refinement,
        "entailed_policy_conditions":entailed,
        "certified_common_policies":sorted(certified),
        "authenticated_policy_adequacy":sorted(accepted,key=lambda x:x["policy_id"]),
        "rejected_policy_adequacy_bindings":sorted(rejected,key=lambda x:x.get("policy_id","")),
        "terminal_authority":False,
        "boundary":(
            "V6_BINDS_RAW_FACT_SOURCE_SEMANTICS_BUT_SOURCE_ENTAILMENT_IS_NOT_POLICY_ADEQUACY;"
            "COMMON_POLICY_CERTIFIED_REQUIRES_V3_CONTENT_ADDRESSED_BRAIN_OWNED_ADEQUACY_AUTHENTICATION;"
            "UPSTREAM_FACT_SOURCE_AUTHORIZATION_REMAINS_SEPARATE"
        ),
    }
