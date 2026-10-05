"""Fail-closed finite channel-graph dominator verifier.

This proves only a graph property: for every declared load-bearing edge, every
reachable path from any runtime entrypoint to the edge's source traverses the
required mediator. It does not prove graph completeness, guard soundness, or
semantic correctness. Unknown/dynamic edges must be explicitly declared
complete by an upstream scope proof or verification fails closed.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


class ChannelGraphError(ValueError):
    pass


@dataclass(frozen=True)
class Edge:
    edge_id: str
    source: str
    target: str


def _as_nonempty_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ChannelGraphError(f"INVALID_{label}")
    return value


def _normalize(spec: Mapping[str, Any]) -> tuple[set[str], tuple[Edge, ...], set[str], dict[str, str]]:
    if spec.get("dynamic_edge_registry_complete") is not True:
        raise ChannelGraphError("DYNAMIC_EDGE_REGISTRY_NOT_PROVED_COMPLETE")

    raw_nodes = spec.get("nodes")
    raw_edges = spec.get("edges")
    raw_entries = spec.get("entrypoints")
    raw_bindings = spec.get("mediator_bindings")

    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ChannelGraphError("NODES_MISSING")
    nodes = {_as_nonempty_str(x, "NODE") for x in raw_nodes}
    if len(nodes) != len(raw_nodes):
        raise ChannelGraphError("DUPLICATE_NODE")

    if not isinstance(raw_entries, list) or not raw_entries:
        raise ChannelGraphError("ENTRYPOINTS_MISSING")
    entries = {_as_nonempty_str(x, "ENTRYPOINT") for x in raw_entries}
    if not entries <= nodes:
        raise ChannelGraphError("ENTRYPOINT_NOT_IN_NODES")

    if not isinstance(raw_edges, list):
        raise ChannelGraphError("EDGES_MISSING")
    edges: list[Edge] = []
    ids: set[str] = set()
    for row in raw_edges:
        if not isinstance(row, Mapping):
            raise ChannelGraphError("INVALID_EDGE")
        edge_id = _as_nonempty_str(row.get("id"), "EDGE_ID")
        source = _as_nonempty_str(row.get("source"), "EDGE_SOURCE")
        target = _as_nonempty_str(row.get("target"), "EDGE_TARGET")
        if edge_id in ids:
            raise ChannelGraphError("DUPLICATE_EDGE_ID")
        if source not in nodes or target not in nodes:
            raise ChannelGraphError("EDGE_ENDPOINT_NOT_IN_NODES")
        ids.add(edge_id)
        edges.append(Edge(edge_id, source, target))

    if not isinstance(raw_bindings, Mapping) or not raw_bindings:
        raise ChannelGraphError("MEDIATOR_BINDINGS_MISSING")
    bindings: dict[str, str] = {}
    for raw_edge_id, raw_mediator in raw_bindings.items():
        edge_id = _as_nonempty_str(raw_edge_id, "BOUND_EDGE_ID")
        mediator = _as_nonempty_str(raw_mediator, "MEDIATOR")
        if edge_id not in ids:
            raise ChannelGraphError("BOUND_EDGE_NOT_DECLARED")
        if mediator not in nodes:
            raise ChannelGraphError("MEDIATOR_NOT_IN_NODES")
        bindings[edge_id] = mediator

    return nodes, tuple(edges), entries, bindings


def _reachable_without(
    *,
    entries: Iterable[str],
    adjacency: Mapping[str, tuple[str, ...]],
    blocked: str,
) -> set[str]:
    q: deque[str] = deque(e for e in entries if e != blocked)
    seen = set(q)
    while q:
        node = q.popleft()
        for nxt in adjacency.get(node, ()):
            if nxt == blocked or nxt in seen:
                continue
            seen.add(nxt)
            q.append(nxt)
    return seen


def verify(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Verify declared mediator dominance for all bound load-bearing edges.

    For a bound edge u->v with required mediator m, m dominates the commit edge
    iff either u == m or u is unreachable from every entrypoint after removing m.
    The proof is finite over the exact declared graph. Graph-totality and guard
    semantics remain separate proof obligations.
    """
    try:
        nodes, edges, entries, bindings = _normalize(spec)
    except ChannelGraphError as exc:
        return {
            "schema": "PROJECT_BRAIN_SHARED_CHANNEL_DOMINATOR_VERIFICATION_V1",
            "pass": False,
            "status": "FAIL_CLOSED__INVALID_OR_INCOMPLETE_CHANNEL_GRAPH",
            "reason": str(exc),
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }

    adjacency_mut: dict[str, list[str]] = defaultdict(list)
    by_id = {e.edge_id: e for e in edges}
    for edge in edges:
        adjacency_mut[edge.source].append(edge.target)
    adjacency = {k: tuple(v) for k, v in adjacency_mut.items()}

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for edge_id, mediator in sorted(bindings.items()):
        edge = by_id[edge_id]
        if edge.source == mediator:
            dominated = True
            reachable_without = False
        else:
            reachable = _reachable_without(entries=entries, adjacency=adjacency, blocked=mediator)
            reachable_without = edge.source in reachable
            dominated = not reachable_without
        row = {
            "edge_id": edge_id,
            "source": edge.source,
            "target": edge.target,
            "required_mediator": mediator,
            "source_reachable_from_entry_without_mediator": reachable_without,
            "dominated": dominated,
        }
        rows.append(row)
        if not dominated:
            failures.append(edge_id)

    ok = not failures
    return {
        "schema": "PROJECT_BRAIN_SHARED_CHANNEL_DOMINATOR_VERIFICATION_V1",
        "pass": ok,
        "status": (
            "PASS__ALL_BOUND_LOAD_BEARING_EDGES_MEDIATOR_DOMINATED"
            if ok
            else "FAIL_CLOSED__MEDIATOR_BYPASS_PATH_EXISTS"
        ),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "entrypoint_count": len(entries),
        "bound_load_bearing_edge_count": len(bindings),
        "results": rows,
        "bypass_edge_ids": failures,
        "hard_nonclaims": [
            "DOES_NOT_PROVE_CHANNEL_GRAPH_SCOPE_COMPLETENESS",
            "DOES_NOT_PROVE_DYNAMIC_EDGE_REGISTRY_COMPLETENESS",
            "DOES_NOT_PROVE_GUARD_SEMANTIC_SOUNDNESS",
            "DOES_NOT_GRANT_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
