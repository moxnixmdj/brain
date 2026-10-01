"""Deterministic requirement-to-output calculation graph validator.

This validates *structural completeness*, not domain truth. A requirement must
either reach at least one declared output through explicit graph edges or carry
an explicit justified exclusion. The validator fails closed on dangling nodes,
cycles, orphan requirements, and missing output reachability.
"""
from __future__ import annotations
from collections import defaultdict, deque
from typing import Any

def validate(model: dict[str, Any]) -> dict[str, Any]:
    reqs = model.get("requirements")
    nodes = model.get("nodes")
    edges = model.get("edges")
    outputs = model.get("outputs")
    exclusions = model.get("exclusions", [])
    if not all(isinstance(x, list) for x in (reqs, nodes, edges, outputs, exclusions)):
        raise ValueError("requirements/nodes/edges/outputs/exclusions must be lists")

    req_ids = {str(r["id"]) for r in reqs}
    node_ids = {str(n["id"]) for n in nodes}
    output_ids = {str(x) for x in outputs}
    exclusion_map = {
        str(x["requirement_id"]): str(x.get("justification", "")).strip()
        for x in exclusions
    }

    errors: list[str] = []
    if len(req_ids) != len(reqs):
        errors.append("DUPLICATE_REQUIREMENT_ID")
    if len(node_ids) != len(nodes):
        errors.append("DUPLICATE_NODE_ID")
    unknown_outputs = sorted(output_ids - node_ids)
    if unknown_outputs:
        errors.append("UNKNOWN_OUTPUT:" + ",".join(unknown_outputs))

    adj: dict[str, list[str]] = defaultdict(list)
    indeg: dict[str, int] = {n: 0 for n in node_ids}
    for e in edges:
        s, t = str(e["from"]), str(e["to"])
        if s not in node_ids or t not in node_ids:
            errors.append(f"DANGLING_EDGE:{s}->{t}")
            continue
        adj[s].append(t)
        indeg[t] += 1

    q = deque(sorted([n for n, d in indeg.items() if d == 0]))
    seen = 0
    indeg2 = dict(indeg)
    while q:
        n = q.popleft()
        seen += 1
        for t in adj[n]:
            indeg2[t] -= 1
            if indeg2[t] == 0:
                q.append(t)
    if seen != len(node_ids):
        errors.append("CYCLE_DETECTED")

    req_node = {str(n.get("requirement_id")): str(n["id"])
                for n in nodes if n.get("requirement_id") is not None}

    def reaches_output(start: str) -> bool:
        stack, visited = [start], set()
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            if n in output_ids:
                return True
            stack.extend(adj.get(n, ()))
        return False

    uncovered: list[str] = []
    excluded: list[str] = []
    for rid in sorted(req_ids):
        just = exclusion_map.get(rid, "")
        if just:
            excluded.append(rid)
            continue
        n = req_node.get(rid)
        if not n:
            uncovered.append(rid + ":NO_REQUIREMENT_NODE")
        elif not reaches_output(n):
            uncovered.append(rid + ":NO_OUTPUT_PATH")

    for rid, just in sorted(exclusion_map.items()):
        if rid not in req_ids:
            errors.append("EXCLUSION_FOR_UNKNOWN_REQUIREMENT:" + rid)
        elif not just:
            errors.append("EMPTY_EXCLUSION_JUSTIFICATION:" + rid)

    ok = not errors and not uncovered
    return {
        "schema": "BRAIN_COMPLETE_CALCULATION_GRAPH_RESULT_V1",
        "pass": ok,
        "requirements_total": len(req_ids),
        "requirements_reaching_output": len(req_ids) - len(uncovered) - len(excluded),
        "explicitly_excluded": excluded,
        "uncovered": uncovered,
        "errors": errors,
    }
