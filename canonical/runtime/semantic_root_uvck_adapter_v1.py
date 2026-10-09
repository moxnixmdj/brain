from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import assurance_closure_compiler_v1 as uvck

SEMANTIC_ROOTS = (
    "SR1_REALITY_CONTAINMENT",
    "SR2_MISSION_SOUNDNESS",
    "SR3_TERMINAL_CLOSURE",
    "SR4_ASSURANCE_AUTHORITY",
)


def compile_graph(root_support: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    for root_id in SEMANTIC_ROOTS:
        support = root_support.get(root_id)
        if not isinstance(support, Mapping):
            nodes.append({
                "id": root_id,
                "type": "CLAIM",
                "status": "OPEN",
                "depends_on": [],
                "defeated_by": [],
            })
            continue

        status = support.get("status")
        if status == "SUPPORTED":
            evidence_id = "evidence:" + root_id
            nodes.append({
                "id": root_id,
                "type": "CLAIM",
                "status": "SUPPORTED",
                "depends_on": [evidence_id],
                "defeated_by": [],
            })
            nodes.append({
                "id": evidence_id,
                "type": "EVIDENCE",
                "status": "SUPPORTED",
                "authoritative_leaf": support.get("authoritative") is True,
                "certificate_id": support.get("certificate_id"),
            })
        else:
            normalized = status if status in {"OPEN", "STALE", "REJECTED"} else "OPEN"
            nodes.append({
                "id": root_id,
                "type": "CLAIM",
                "status": normalized,
                "depends_on": [],
                "defeated_by": [],
            })

    nodes.append({
        "id": "SEMANTIC_TERMINAL_THEOREM",
        "type": "CLAIM",
        "status": "SUPPORTED",
        "depends_on": list(SEMANTIC_ROOTS),
        "defeated_by": [],
    })
    return {
        "schema": uvck.GRAPH_SCHEMA,
        "root_ids": ["SEMANTIC_TERMINAL_THEOREM"],
        "nodes": nodes,
        "execution_closure_proved": False,
        "adversarial_closure_proved": False,
    }


def evaluate(root_support: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    graph = compile_graph(root_support)
    out = uvck.evaluate(graph)
    return {
        **out,
        "semantic_root_ids": list(SEMANTIC_ROOTS),
        "semantic_theorem_conclusion": "B_REAL_SUBSET_G_REAL",
        "semantic_terminal_authority": False,
        "semantic_terminal_credit_delta": 0,
    }


def classify_novelty(
    uvck_result: Mapping[str, Any],
    *,
    semantic_countermodel: bool = False,
    proof_search_failure_only: bool = False,
    material_proof_cost_reduction: bool = False,
) -> dict[str, Any]:
    if semantic_countermodel:
        return {
            "classification": "SEMANTIC_ROOT_THEOREM_REVIEW_REQUIRED",
            "new_semantic_root_required": True,
            "terminal_credit_delta": 0,
        }

    if uvck_result.get("new_primitive_required") is True:
        return {
            "classification": "UVCK_REPRESENTATION_EXTENSION_REQUIRED",
            "new_semantic_root_required": False,
            "terminal_credit_delta": 0,
        }

    if proof_search_failure_only:
        return {
            "classification": "CAPABILITY_CLOSURE_PROOF_ROUTE_GAP",
            "new_semantic_root_required": False,
            "terminal_credit_delta": 0,
        }

    if material_proof_cost_reduction:
        return {
            "classification": "EXISTING_ROOT_OPTIMIZATION_CANDIDATE",
            "new_semantic_root_required": False,
            "terminal_credit_delta": 0,
        }

    if uvck_result.get("status") in {
        "OPEN__ASSURANCE_RESIDUAL",
        "OPEN__EXECUTION_CLOSURE_REQUIRED",
        "OPEN__ADVERSARIAL_CLOSURE_REQUIRED",
        "COUNTERPROVED",
        "FAIL_CLOSED",
    }:
        return {
            "classification": "EXISTING_SEMANTIC_ROOT_OR_SR4_ASSURANCE_RESIDUAL",
            "new_semantic_root_required": False,
            "terminal_credit_delta": 0,
        }

    return {
        "classification": "NO_CANONICAL_ARCHITECTURE_DELTA",
        "new_semantic_root_required": False,
        "terminal_credit_delta": 0,
    }
