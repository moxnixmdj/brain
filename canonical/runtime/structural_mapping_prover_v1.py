"""Deterministic zero-learned topology mapping prover for unknown-domain transfer.

Surface node labels, node-kind names, edge-type names, and arbitrary metadata are
non-load-bearing.  The prover uses only directed adjacency topology.  A unique
isomorphism may be proposed for independent verification; zero mappings fail
closed; multiple mappings are explicitly ambiguous.

This module creates no independent verification receipt and no acceptance credit.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ZERO_LEARNED_STRUCTURAL_MAPPING_PROVER_V1"
MAX_NODES = 8


class StructuralMappingProverError(ValueError):
    pass


def _node_id(value: Any) -> str:
    out = str(value or "").strip()
    if not out:
        raise StructuralMappingProverError("NODE_ID_REQUIRED")
    return out


def _normalize(graph: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(graph, Mapping):
        raise StructuralMappingProverError("GRAPH_NOT_MAPPING")
    raw_nodes = graph.get("nodes")
    raw_edges = graph.get("edges")
    if not isinstance(raw_nodes, Sequence) or isinstance(raw_nodes, (str, bytes)):
        raise StructuralMappingProverError("NODES_INVALID")
    if not isinstance(raw_edges, Sequence) or isinstance(raw_edges, (str, bytes)):
        raise StructuralMappingProverError("EDGES_INVALID")
    if not raw_nodes or len(raw_nodes) > MAX_NODES:
        raise StructuralMappingProverError("NODE_COUNT_OUT_OF_RANGE")

    nodes = {}
    for raw in raw_nodes:
        if not isinstance(raw, Mapping):
            raise StructuralMappingProverError("NODE_NOT_MAPPING")
        nid = _node_id(raw.get("id"))
        if nid in nodes:
            raise StructuralMappingProverError("NODE_ID_DUPLICATE:" + nid)
        nodes[nid] = {"id": nid}

    edges = []
    seen = set()
    for raw in raw_edges:
        if not isinstance(raw, Mapping):
            raise StructuralMappingProverError("EDGE_NOT_MAPPING")
        src = _node_id(raw.get("source"))
        dst = _node_id(raw.get("target"))
        if src not in nodes or dst not in nodes:
            raise StructuralMappingProverError("EDGE_NODE_UNKNOWN")
        key = (src, dst)
        if key in seen:
            raise StructuralMappingProverError("EDGE_DUPLICATE")
        seen.add(key)
        edges.append(key)

    return {"nodes": nodes, "edges": tuple(sorted(edges))}


def _signature(graph: Mapping[str, Any], node_id: str) -> tuple[int, int, tuple[int, ...], tuple[int, ...]]:
    edges = graph["edges"]
    incoming = sorted(s for s, d in edges if d == node_id)
    outgoing = sorted(d for s, d in edges if s == node_id)
    indeg = len(incoming)
    outdeg = len(outgoing)
    # One-hop degree profiles strengthen pruning without using any names/types.
    pred_degrees = sorted(
        sum(1 for s, d in edges if d == pred) + sum(1 for s, d in edges if s == pred)
        for pred in incoming
    )
    succ_degrees = sorted(
        sum(1 for s, d in edges if d == succ) + sum(1 for s, d in edges if s == succ)
        for succ in outgoing
    )
    return indeg, outdeg, tuple(pred_degrees), tuple(succ_degrees)


def _mapping_preserves(source: Mapping[str, Any], target: Mapping[str, Any], mapping: Mapping[str, str]) -> bool:
    if set(mapping) != set(source["nodes"]):
        return False
    if len(set(mapping.values())) != len(target["nodes"]):
        return False
    target_edges = set(target["edges"])
    mapped_edges = {(mapping[s], mapping[d]) for s, d in source["edges"]}
    return mapped_edges == target_edges


def mapping_digest(mapping: Mapping[str, str]) -> str:
    body = json.dumps(dict(sorted(mapping.items())), sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(body).hexdigest()


def propose(source_graph: Mapping[str, Any], target_graph: Mapping[str, Any]) -> dict[str, Any]:
    source = _normalize(source_graph)
    target = _normalize(target_graph)
    if len(source["nodes"]) != len(target["nodes"]) or len(source["edges"]) != len(target["edges"]):
        return _result("NO_STRUCTURAL_MAPPING", None, 0)

    source_ids = sorted(source["nodes"])
    target_ids = sorted(target["nodes"])
    source_sigs = {n: _signature(source, n) for n in source_ids}
    target_sigs = {n: _signature(target, n) for n in target_ids}

    candidates = {}
    for sid in source_ids:
        compatible = [tid for tid in target_ids if target_sigs[tid] == source_sigs[sid]]
        if not compatible:
            return _result("NO_STRUCTURAL_MAPPING", None, 0)
        candidates[sid] = compatible

    order = sorted(source_ids, key=lambda sid: (len(candidates[sid]), sid))
    valid: list[dict[str, str]] = []
    used: set[str] = set()
    partial: dict[str, str] = {}

    def search(index: int) -> None:
        if len(valid) > 1:
            return
        if index == len(order):
            if _mapping_preserves(source, target, partial):
                valid.append(dict(partial))
            return
        sid = order[index]
        for tid in candidates[sid]:
            if tid in used:
                continue
            partial[sid] = tid
            used.add(tid)
            search(index + 1)
            used.remove(tid)
            partial.pop(sid, None)
            if len(valid) > 1:
                return

    search(0)

    if not valid:
        return _result("NO_STRUCTURAL_MAPPING", None, 0)
    if len(valid) > 1:
        return _result("AMBIGUOUS_STRUCTURAL_MAPPING", None, 2)
    return _result("UNIQUE_STRUCTURAL_MAPPING", valid[0], 1)


def _result(status: str, mapping: Mapping[str, str] | None, count: int) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "mapping_count": count,
        "mapping": None if mapping is None else dict(mapping),
        "mapping_digest": None if mapping is None else mapping_digest(mapping),
        "proof_basis": "DIRECTED_TOPOLOGY_ISOMORPHISM",
        "surface_labels_used": False,
        "node_kind_names_used": False,
        "edge_type_names_used": False,
        "metadata_used": False,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "random_search": False,
        "dynamic_code_execution": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
