"""UVCK V2 domain challenge catalog for V1.52-V1.67 killer classes.

Each historical challenge is represented only with the fixed V2 primitive
vocabulary. The catalog is not a proof that the domain-specific obligation is
already solved. It proves the challenge is representable as ordinary residual
work rather than requiring a new meta-architecture primitive.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from canonical.runtime import assurance_closure_compiler_v1 as closure

SCHEMA = "PROJECT_BRAIN_ASSURANCE_DOMAIN_CHALLENGE_CATALOG_V1"

CHALLENGES = {
    "V1_52_CAUSALLY_CONSISTENT_EPISTEMIC_SNAPSHOT": ["CLAIM","EVIDENCE","DEPENDENCY","EPOCH"],
    "V1_53_ADVERSARIAL_OBSERVATION_RECONSTRUCTION": ["CLAIM","EVIDENCE","DEFEATER","MONITOR"],
    "V1_54_ACTIVE_PHYSICAL_CHALLENGE_RESPONSE": ["OBLIGATION","EFFECT","EVIDENCE","MONITOR"],
    "V1_55_TARGET_BOUND_CAUSAL_ATTESTATION": ["CLAIM","AUTHORITY","EVIDENCE","DEPENDENCY"],
    "V1_56_ATTESTATION_TO_EFFECT_TEMPORAL_CLOSURE": ["ASSUMPTION","EPOCH","MONITOR","TRANSITION"],
    "V1_57_END_TO_END_TEMPORAL_CAPACITY": ["RESOURCE","OBLIGATION","ASSUMPTION","MONITOR"],
    "V1_58_TRUSTED_TEMPORAL_REFERENCE": ["EVIDENCE","ASSUMPTION","EPOCH","MONITOR"],
    "V1_59_RESOURCE_SUPPLY_AND_DEPLETION": ["RESOURCE","ASSUMPTION","MONITOR","TRANSITION"],
    "V1_60_GLOBAL_PROGRESS_AND_DEADLOCK": ["RESOURCE","DEPENDENCY","OBLIGATION","TRANSITION"],
    "V1_61_PARTITION_AWARE_DISTRIBUTED_LIVENESS": ["ASSUMPTION","DEPENDENCY","EPOCH","TRANSITION"],
    "V1_62_SEMANTIC_EFFECT_COMMIT": ["EFFECT","EVIDENCE","EPOCH","TRANSITION"],
    "V1_63_SEMANTIC_ISOLATION_AND_COMPENSATION": ["EFFECT","DEPENDENCY","DEFEATER","TRANSITION"],
    "V1_64_EXTERNAL_OBSERVATION_FINALITY": ["CLAIM","EFFECT","DEPENDENCY","EPOCH"],
    "V1_65_COMMUNICATION_UPTAKE": ["EFFECT","EVIDENCE","OBLIGATION","MONITOR"],
    "V1_66_OBLIGATION_OWNERSHIP_HANDOFF": ["OBLIGATION","AUTHORITY","RESOURCE","TRANSITION"],
    "V1_67_RESPONSIBILITY_CONTINUITY": ["OBLIGATION","AUTHORITY","RESOURCE","EPOCH"],
}


def graph_for(challenge_id: str) -> dict[str, Any]:
    kinds = CHALLENGES[challenge_id]
    nodes: list[dict[str, Any]] = []
    prior = "e:ground"
    nodes.append({
        "id": prior,
        "type": "EVIDENCE",
        "status": "SUPPORTED",
        "authoritative_leaf": True,
    })
    for index, kind in enumerate(kinds):
        node_id = f"n:{index}:{kind.lower()}"
        if index == len(kinds) - 1:
            status = "OPEN"
            deps = [prior] if prior else []
        else:
            status = "SUPPORTED"
            deps = [prior] if prior else []
        nodes.append({
            "id": node_id,
            "type": kind,
            "status": status,
            "depends_on": deps,
            "defeated_by": [],
        })
        prior = node_id
    nodes.append({
        "id": "root",
        "type": "CLAIM",
        "status": "SUPPORTED",
        "depends_on": [prior],
        "defeated_by": [],
    })
    return {
        "schema": closure.GRAPH_SCHEMA,
        "root_ids": ["root"],
        "nodes": nodes,
        "challenge_id": challenge_id,
    }


def evaluate_all() -> dict[str, Any]:
    rows = []
    for challenge_id in sorted(CHALLENGES):
        graph = graph_for(challenge_id)
        result = closure.evaluate(graph)
        rows.append({
            "challenge_id": challenge_id,
            "status": result["status"],
            "existing_kernel_expressive": result["existing_kernel_expressive"],
            "new_primitive_required": result["new_primitive_required"],
            "open_residual_ids": result["open_residual_ids"],
        })
    return {
        "schema": SCHEMA,
        "pass": all(
            row["existing_kernel_expressive"]
            and not row["new_primitive_required"]
            and row["status"] == "OPEN__ASSURANCE_RESIDUAL"
            for row in rows
        ),
        "challenge_count": len(rows),
        "rows": rows,
        "scope": "REPRESENTABILITY_ONLY_NOT_DOMAIN_CLOSURE",
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
