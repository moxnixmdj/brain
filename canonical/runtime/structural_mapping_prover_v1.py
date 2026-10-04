"""Deterministic zero-learned structural mapping prover for unknown-domain transfer.

The prover deliberately ignores surface labels and arbitrary metadata.  It admits
only graph mappings that preserve candidate-visible node kinds and typed directed
edges exactly.  A unique mapping may be proposed for independent verification;
zero mappings fail closed; multiple mappings are explicitly ambiguous.

This module creates no independent verification receipt and no acceptance credit.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from collections import Counter
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
        nodes[nid] = {"id": nid, "kind": str(raw.get("kind") or "GENERIC").strip() or "GENERIC"}

    edges = []
    seen = set()
    for raw in raw_edges:
        if not isinstance(raw, Mapping):
            raise StructuralMappingProverError("EDGE_NOT_MAPPING")
        src = _node_id(raw.get("source"))
        dst = _node_id(raw.get("target"))
        etype = str(raw.get("type") or "EDGE").strip() or "EDGE"
        if src not in nodes or dst not in nodes:
            raise StructuralMappingProverError("EDGE_NODE_UNKNOWN")
        key = (src, dst, etype)
        if key in seen:
            raise StructuralMappingProverError("EDGE_DUPLICATE")
        seen.add(key)
        edges.append(key)

    return {"nodes": nodes, "edges": tuple(sorted(edges))}


def _signature(graph: Mapping[str, Any], node_id: str) -> tuple:
    nodes = graph["nodes"]
    edges = graph["edges"]
    kind = nodes[node_id]["kind"]
    outgoing = Counter(t for s, d, t in edges if s == node_id)
    incoming = Counter(t for s, d, t in edges if d == node_id)
    return (
        kind,
        tuple(sorted(outgoing.items())),
        tuple(sorted(incoming.items())),
        sum(outgoing.values()),
        sum(incoming.values()),
    )


def _mapping_preserves(source: Mapping[str, Any], target: Mapping[str, Any], mapping: Mapping[str, str]) -> bool:
    if set(mapping) != set(source["nodes"]):
        return False
    if len(set(mapping.values())) != len(target["nodes"]):
        return False
    for sid, tid in mapping.items():
        if target["nodes"].get(tid, {}).get("kind") != source["nodes"][sid]["kind"]:
            return False
    target_edges = set(target["edges"])
    mapped_edges = {(mapping[s], mapping[d], etype) for s, d, etype in source["edges"]}
    return mapped_edges == target_edges


def mapping_digest(mapping: Mapping[str, str]) -> str:
    body = json.dumps(dict(sorted(mapping.items())), sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(body).hexdigest()


def propose(source_graph: Mapping[str, Any], target_graph: Mapping[str, Any]) -> dict[str, Any]:
    source = _normalize(source_graph)
    target = _normalize(target_graph)
    if len(source["nodes"]) != len(target["nodes"]) or len(source["edges"]) != len(target["edges"]):
        return {
            "schema": SCHEMA,
            "status": "NO_STRUCTURAL_MAPPING",
            "mapping_count": 0,
            "mapping": None,
            "mapping_digest": None,
            "persistent_learned_bytes": 0,
            "external_learned_capability_calls": 0,
        }

    source_ids = sorted(source["nodes"])
    target_ids = sorted(target["nodes"])
    source_sigs = {n: _signature(source, n) for n in source_ids}
    target_sigs = {n: _signature(target, n) for n in target_ids}

    candidates = {}
    for sid in source_ids:
        compatible = [tid for tid in target_ids if target_sigs[tid] == source_sigs[sid]]
        if not compatible:
            return {
                "schema": SCHEMA,
                "status": "NO_STRUCTURAL_MAPPING",
                "mapping_count": 0,
                "mapping": None,
                "mapping_digest": None,
                "persistent_learned_bytes": 0,
                "external_learned_capability_calls": 0,
            }
        candidates[sid] = compatible

    order = sorted(source_ids, key=lambda sid: (len(candidates[sid]), sid))
    valid = []
    used = set()
    partial = {}

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
        status = "NO_STRUCTURAL_MAPPING"
        chosen = None
    elif len(valid) == 1:
        status = "UNIQUE_STRUCTURAL_MAPPING"
        chosen = valid[0]
    else:
        status = "AMBIGUOUS_STRUCTURAL_MAPPING"
        chosen = None

    return {
        "schema": SCHEMA,
        "status": status,
        "mapping_count": len(valid) if len(valid) <= 1 else 2,
        "mapping": chosen,
        "mapping_digest": None if chosen is None else mapping_digest(chosen),
        "proof_basis": "STRUCTURAL_EQUIVALENCE",
        "surface_labels_used": False,
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
