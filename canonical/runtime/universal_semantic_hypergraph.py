"""Universal source-traceable semantic hypergraph representation.

This module separates *representation capacity* from *semantic inference*.

Any finite labeled directed hypergraph with finite-arity relations can be encoded
without adding executable primitive types: previously unseen entity/relation/type
names are opaque data labels. Higher-order relations are represented by allowing
relation arguments to target either nodes or other relations.

This does NOT infer which graph is correct from raw text, images, UI state, or
documents. That inference remains S0. The module only proves that novel finite
semantic structure does not require a new runtime primitive merely to represent it.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

Scalar = str | int | float | bool | None

MAX_NODES = 2048
MAX_RELATIONS = 4096
MAX_ARGUMENTS_PER_RELATION = 128
MAX_SOURCE_REFS = 128
MAX_TEXT = 4096

STATUSES = frozenset({"SUPPORTED", "CANDIDATE", "UNKNOWN", "CONFLICT"})


@dataclass(frozen=True)
class SemanticNode:
    node_id: str
    type_label: str
    source_refs: tuple[str, ...]
    value: Scalar = None


@dataclass(frozen=True)
class RoleBinding:
    role_label: str
    target_id: str


@dataclass(frozen=True)
class SemanticRelation:
    relation_id: str
    relation_label: str
    arguments: tuple[RoleBinding, ...]
    source_refs: tuple[str, ...]
    status: str = "CANDIDATE"


@dataclass(frozen=True)
class SemanticHypergraph:
    nodes: tuple[SemanticNode, ...]
    relations: tuple[SemanticRelation, ...]


def _text(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value.strip()) <= MAX_TEXT


def _scalar(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return not isinstance(value, str) or len(value) <= MAX_TEXT
    return isinstance(value, float) and math.isfinite(value)


def _refs(refs: Any) -> bool:
    return (
        isinstance(refs, tuple)
        and 1 <= len(refs) <= MAX_SOURCE_REFS
        and all(_text(x) for x in refs)
        and len(refs) == len(set(refs))
    )


def validate_graph(graph: SemanticHypergraph) -> dict[str, Any]:
    if not isinstance(graph, SemanticHypergraph):
        return {"status": "FAIL_CLOSED", "reason": "GRAPH_TYPE_INVALID"}

    if not (0 <= len(graph.nodes) <= MAX_NODES):
        return {"status": "FAIL_CLOSED", "reason": "NODE_COUNT_OUT_OF_BOUND"}
    if not (0 <= len(graph.relations) <= MAX_RELATIONS):
        return {"status": "FAIL_CLOSED", "reason": "RELATION_COUNT_OUT_OF_BOUND"}

    node_ids: list[str] = []
    relation_ids: list[str] = []

    for i, node in enumerate(graph.nodes):
        if not isinstance(node, SemanticNode):
            return {"status": "FAIL_CLOSED", "reason": f"NODE_TYPE_INVALID:{i}"}
        if not _text(node.node_id) or not _text(node.type_label):
            return {"status": "FAIL_CLOSED", "reason": f"NODE_ID_OR_TYPE_INVALID:{i}"}
        if not _refs(node.source_refs):
            return {"status": "FAIL_CLOSED", "reason": f"NODE_PROVENANCE_INVALID:{node.node_id}"}
        if not _scalar(node.value):
            return {"status": "FAIL_CLOSED", "reason": f"NODE_VALUE_INVALID:{node.node_id}"}
        node_ids.append(node.node_id)

    for i, rel in enumerate(graph.relations):
        if not isinstance(rel, SemanticRelation):
            return {"status": "FAIL_CLOSED", "reason": f"RELATION_TYPE_INVALID:{i}"}
        if not _text(rel.relation_id) or not _text(rel.relation_label):
            return {"status": "FAIL_CLOSED", "reason": f"RELATION_ID_OR_LABEL_INVALID:{i}"}
        if rel.status not in STATUSES:
            return {"status": "FAIL_CLOSED", "reason": f"RELATION_STATUS_INVALID:{rel.relation_id}"}
        if not _refs(rel.source_refs):
            return {"status": "FAIL_CLOSED", "reason": f"RELATION_PROVENANCE_INVALID:{rel.relation_id}"}
        if not (
            isinstance(rel.arguments, tuple)
            and 1 <= len(rel.arguments) <= MAX_ARGUMENTS_PER_RELATION
        ):
            return {"status": "FAIL_CLOSED", "reason": f"RELATION_ARGUMENTS_INVALID:{rel.relation_id}"}
        for j, arg in enumerate(rel.arguments):
            if not isinstance(arg, RoleBinding):
                return {"status": "FAIL_CLOSED", "reason": f"ARGUMENT_TYPE_INVALID:{rel.relation_id}:{j}"}
            if not _text(arg.role_label) or not _text(arg.target_id):
                return {"status": "FAIL_CLOSED", "reason": f"ARGUMENT_INVALID:{rel.relation_id}:{j}"}
        relation_ids.append(rel.relation_id)

    all_ids = node_ids + relation_ids
    if len(all_ids) != len(set(all_ids)):
        return {"status": "FAIL_CLOSED", "reason": "GLOBAL_IDENTIFIER_COLLISION_OR_DUPLICATE"}

    universe = set(all_ids)
    for rel in graph.relations:
        for arg in rel.arguments:
            if arg.target_id not in universe:
                return {
                    "status": "FAIL_CLOSED",
                    "reason": f"DANGLING_ARGUMENT_TARGET:{rel.relation_id}:{arg.target_id}",
                }

    return {
        "status": "PASS",
        "node_count": len(graph.nodes),
        "relation_count": len(graph.relations),
        "novel_labels_are_data": True,
        "higher_order_relation_targets_supported": True,
        "semantic_truth_authority": False,
        "terminal_authority": False,
    }


def canonical_dict(graph: SemanticHypergraph) -> dict[str, Any]:
    verdict = validate_graph(graph)
    if verdict["status"] != "PASS":
        return verdict

    nodes = [
        {
            "node_id": n.node_id,
            "type_label": n.type_label,
            "source_refs": list(sorted(n.source_refs)),
            "value": n.value,
        }
        for n in sorted(graph.nodes, key=lambda n: n.node_id)
    ]
    relations = [
        {
            "relation_id": r.relation_id,
            "relation_label": r.relation_label,
            "arguments": [
                {"role_label": a.role_label, "target_id": a.target_id}
                for a in r.arguments
            ],
            "source_refs": list(sorted(r.source_refs)),
            "status": r.status,
        }
        for r in sorted(graph.relations, key=lambda r: r.relation_id)
    ]
    return {
        "status": "PASS",
        "schema": "BRAIN_UNIVERSAL_SEMANTIC_HYPERGRAPH_V1",
        "nodes": nodes,
        "relations": relations,
        "representation_scope": (
            "ANY_FINITE_LABELED_DIRECTED_HYPERGRAPH_WITH_FINITE_STRING_LABELS_"
            "FINITE_ARITY_ORDERED_ROLE_BINDINGS_AND_SOURCE_PROVENANCE"
        ),
        "novel_labels_are_data": True,
        "semantic_truth_authority": False,
        "inference_boundary": (
            "CHOOSING_THE_CORRECT_GRAPH_FROM_RAW_CONTEXT_REMAINS_S0_"
            "REPRESENTATION_DOES_NOT_SUPPLY_SEMANTIC_TRUTH"
        ),
        "terminal_authority": False,
    }


def graph_from_canonical_dict(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or payload.get("schema") != "BRAIN_UNIVERSAL_SEMANTIC_HYPERGRAPH_V1":
        return {"status": "FAIL_CLOSED", "reason": "SCHEMA_INVALID"}

    raw_nodes = payload.get("nodes")
    raw_relations = payload.get("relations")
    if not isinstance(raw_nodes, list) or not isinstance(raw_relations, list):
        return {"status": "FAIL_CLOSED", "reason": "NODE_OR_RELATION_LIST_INVALID"}

    try:
        nodes = tuple(
            SemanticNode(
                node_id=row["node_id"],
                type_label=row["type_label"],
                source_refs=tuple(row["source_refs"]),
                value=row.get("value"),
            )
            for row in raw_nodes
        )
        relations = tuple(
            SemanticRelation(
                relation_id=row["relation_id"],
                relation_label=row["relation_label"],
                arguments=tuple(
                    RoleBinding(role_label=a["role_label"], target_id=a["target_id"])
                    for a in row["arguments"]
                ),
                source_refs=tuple(row["source_refs"]),
                status=row["status"],
            )
            for row in raw_relations
        )
    except Exception as exc:
        return {"status": "FAIL_CLOSED", "reason": "PAYLOAD_DECODE_FAILED", "error": type(exc).__name__}

    graph = SemanticHypergraph(nodes=nodes, relations=relations)
    verdict = validate_graph(graph)
    if verdict["status"] != "PASS":
        return verdict
    return {"status": "PASS", "graph": graph, "terminal_authority": False}


def roundtrip_is_lossless(graph: SemanticHypergraph) -> dict[str, Any]:
    encoded = canonical_dict(graph)
    if encoded.get("status") != "PASS":
        return encoded

    decoded = graph_from_canonical_dict(encoded)
    if decoded.get("status") != "PASS":
        return decoded

    reencoded = canonical_dict(decoded["graph"])
    if reencoded != encoded:
        return {"status": "FAIL_CLOSED", "reason": "CANONICAL_ROUNDTRIP_MISMATCH"}

    return {
        "status": "PASS",
        "lossless": True,
        "canonical": encoded,
        "semantic_truth_authority": False,
        "terminal_authority": False,
    }
