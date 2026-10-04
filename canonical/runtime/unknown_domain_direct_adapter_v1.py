"""Direct zero-learned adapter for the two frozen unknown-domain leaves.

Stage 1 proposes a structural mapping without using labels/metadata.
Stage 2 requires an evaluator-issued independent receipt bound to the exact
proposed mapping digest before V3 structural transfer is allowed.
Calibrated decision behavior is delegated to the already independently verified
Universal Learning Decision Router V3.

No hidden case generator or answer key is present in this candidate runtime.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import structural_mapping_prover_v1 as prover
from canonical.runtime import universal_learning_decision_router_v3 as router

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_ADAPTER_V1"


class UnknownDomainDirectAdapterError(ValueError):
    pass


def propose_cross_domain_mapping(*, source_graph: Mapping[str, Any], target_graph: Mapping[str, Any]) -> dict[str, Any]:
    proposal = prover.propose(source_graph, target_graph)
    if proposal["status"] == "UNIQUE_STRUCTURAL_MAPPING":
        route = "AWAIT_INDEPENDENT_MAPPING_VERIFICATION"
    elif proposal["status"] == "AMBIGUOUS_STRUCTURAL_MAPPING":
        route = "ABSTAIN_OR_REQUEST_DISCRIMINATOR"
    else:
        route = "REJECT_TRANSFER"
    return {
        "schema": SCHEMA,
        "route": route,
        "proposal": proposal,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def _verified_mapping_receipt(
    *,
    source_primitive: str,
    target_primitive: str,
    proposal: Mapping[str, Any],
    evaluator_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    if proposal.get("status") != "UNIQUE_STRUCTURAL_MAPPING":
        raise UnknownDomainDirectAdapterError("UNIQUE_MAPPING_REQUIRED")
    expected_digest = str(proposal.get("mapping_digest") or "")
    if not expected_digest:
        raise UnknownDomainDirectAdapterError("MAPPING_DIGEST_REQUIRED")
    if evaluator_receipt.get("independent_verified") is not True:
        raise UnknownDomainDirectAdapterError("EVALUATOR_RECEIPT_NOT_INDEPENDENT")
    if evaluator_receipt.get("exact_byte_bound") is not True:
        raise UnknownDomainDirectAdapterError("EVALUATOR_RECEIPT_NOT_EXACT_BYTE_BOUND")
    if evaluator_receipt.get("conclusion") != "success":
        raise UnknownDomainDirectAdapterError("EVALUATOR_RECEIPT_NOT_SUCCESS")
    if str(evaluator_receipt.get("mapping_digest") or "") != expected_digest:
        raise UnknownDomainDirectAdapterError("EVALUATOR_MAPPING_DIGEST_MISMATCH")
    if str(evaluator_receipt.get("source_primitive") or "") != source_primitive:
        raise UnknownDomainDirectAdapterError("EVALUATOR_SOURCE_PRIMITIVE_MISMATCH")
    if str(evaluator_receipt.get("target_primitive") or "") != target_primitive:
        raise UnknownDomainDirectAdapterError("EVALUATOR_TARGET_PRIMITIVE_MISMATCH")
    rid = str(evaluator_receipt.get("receipt_id") or "").strip()
    if not rid:
        raise UnknownDomainDirectAdapterError("EVALUATOR_RECEIPT_ID_REQUIRED")
    return {
        "receipt_id": rid,
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "source_primitive": source_primitive,
        "target_primitive": target_primitive,
        "relation": "EXACT",
        "mapping_basis": "STRUCTURAL_EQUIVALENCE",
        "mapping_digest": expected_digest,
    }


def apply_verified_cross_domain_transfer(
    *,
    goal: str,
    verified_coverage: Any,
    source_primitive: str,
    target_primitive: str,
    source_graph: Mapping[str, Any],
    target_graph: Mapping[str, Any],
    evaluator_receipt: Mapping[str, Any],
    hypotheses: Sequence[Mapping[str, Any]] = (),
    actions: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    proposal = prover.propose(source_graph, target_graph)
    receipt = _verified_mapping_receipt(
        source_primitive=source_primitive,
        target_primitive=target_primitive,
        proposal=proposal,
        evaluator_receipt=evaluator_receipt,
    )
    mapping = {
        "source_primitive": source_primitive,
        "target_primitive": target_primitive,
        "relation": "EXACT",
        "mapping_basis": "STRUCTURAL_EQUIVALENCE",
        "verification_receipt": receipt,
        "provenance_chain": [
            "SOURCE_PRIMITIVE_VERIFIED",
            "CANDIDATE_MAPPING_PROPOSED_WITHOUT_SURFACE_LABELS",
            "INDEPENDENT_HIDDEN_EVALUATOR_MAPPING_VERIFICATION",
        ],
    }
    out = router.route(
        goal=goal,
        verified_coverage=verified_coverage,
        required_facts=[target_primitive],
        verified_facts=[source_primitive],
        transfer_mappings=[mapping],
        hypotheses=hypotheses,
        actions=actions,
    )
    return {
        "schema": SCHEMA,
        "route": out["route"],
        "target_primitive_reused": target_primitive in out["transfer_coverage"]["verified_facts"],
        "full_target_rediscovery_invoked": False,
        "mapping_proposal": proposal,
        "router": out,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def calibrated_decision(
    *,
    goal: str,
    hypotheses: Sequence[Mapping[str, Any]],
    actions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    out = router.route(
        goal=goal,
        verified_coverage=False,
        required_facts=["UNRESOLVED_DECISION"],
        verified_facts=[],
        transfer_mappings=[],
        hypotheses=hypotheses,
        actions=actions,
    )
    return {
        "schema": SCHEMA,
        "route": out["route"],
        "recommended_action": out.get("recommended_action"),
        "next_action": out.get("next_action"),
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
