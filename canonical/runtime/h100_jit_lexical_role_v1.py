"""Zero-learned JIT lexical-role resolution for H100.

The runtime contains no task-specific lexical cue vocabulary. Role meaning is supplied
at execution time as a raw lexical relation graph whose canonical anchors are
"input" and "output". Cue strings can therefore be novel with respect to the
runtime source. The resolver walks the graph deterministically and fails closed
when a cue is disconnected or reaches both role anchors.

This is a bounded lexical-knowledge consumption mechanism. It does not prove that
the correct graph can always be retrieved from the open world, nor does it parse
free-form compositional language.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_H100_JIT_LEXICAL_ROLE_V1"
_MAX_NODES = 10000
_MAX_EDGES = 50000
_MAX_HOPS = 16


class JITLexicalRoleError(ValueError):
    pass


def _norm(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise JITLexicalRoleError(label + "_INVALID")
    text = " ".join(value.strip().lower().split())
    if not text:
        raise JITLexicalRoleError(label + "_EMPTY")
    return text


def _graph(knowledge: Mapping[str, Any]) -> tuple[dict[str, set[str]], str, str]:
    if not isinstance(knowledge, Mapping):
        raise JITLexicalRoleError("KNOWLEDGE_INVALID")
    anchors = knowledge.get("anchors")
    edges = knowledge.get("edges")
    if not isinstance(anchors, Mapping):
        raise JITLexicalRoleError("ANCHORS_INVALID")
    input_anchor = _norm(anchors.get("input"), "INPUT_ANCHOR")
    target_anchor = _norm(anchors.get("target"), "TARGET_ANCHOR")
    if input_anchor == target_anchor:
        raise JITLexicalRoleError("ROLE_ANCHORS_COLLIDE")
    if not isinstance(edges, Sequence) or isinstance(edges, (str, bytes)):
        raise JITLexicalRoleError("EDGES_INVALID")
    if len(edges) > _MAX_EDGES:
        raise JITLexicalRoleError("EDGE_LIMIT_EXCEEDED")

    graph: dict[str, set[str]] = {}
    for i, edge in enumerate(edges):
        if (
            not isinstance(edge, Sequence)
            or isinstance(edge, (str, bytes))
            or len(edge) != 2
        ):
            raise JITLexicalRoleError(f"EDGE_INVALID:{i}")
        left = _norm(edge[0], f"EDGE_LEFT:{i}")
        right = _norm(edge[1], f"EDGE_RIGHT:{i}")
        if left == right:
            raise JITLexicalRoleError(f"EDGE_SELF_LOOP:{i}")
        graph.setdefault(left, set()).add(right)
        graph.setdefault(right, set()).add(left)
        if len(graph) > _MAX_NODES:
            raise JITLexicalRoleError("NODE_LIMIT_EXCEEDED")

    graph.setdefault(input_anchor, set())
    graph.setdefault(target_anchor, set())
    return graph, input_anchor, target_anchor


def _reachable_roles(
    cue: str,
    graph: Mapping[str, set[str]],
    input_anchor: str,
    target_anchor: str,
) -> set[str]:
    cue = _norm(cue, "CUE")
    if cue not in graph:
        return set()
    found: set[str] = set()
    queue = deque([(cue, 0)])
    seen = {cue}
    while queue:
        node, depth = queue.popleft()
        if node == input_anchor:
            found.add("INPUT")
        if node == target_anchor:
            found.add("TARGET")
        if len(found) == 2 or depth >= _MAX_HOPS:
            continue
        for nxt in sorted(graph.get(node, ())):
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, depth + 1))
    return found


def _fields(value: Any, index: int) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise JITLexicalRoleError(f"FIELDS_INVALID:{index}")
    fields = [_norm(x, f"FIELD:{index}") for x in value]
    if len(fields) != len(set(fields)):
        raise JITLexicalRoleError(f"FIELDS_DUPLICATE:{index}")
    return sorted(fields)


def induce_roles(
    clauses: Any,
    knowledge: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        not isinstance(clauses, Sequence)
        or isinstance(clauses, (str, bytes))
        or len(clauses) < 2
    ):
        raise JITLexicalRoleError("CLAUSES_INVALID")

    graph, input_anchor, target_anchor = _graph(knowledge)
    resolved: list[tuple[str, list[str]]] = []

    for i, clause in enumerate(clauses):
        if not isinstance(clause, Mapping):
            raise JITLexicalRoleError(f"CLAUSE_INVALID:{i}")
        cue = _norm(clause.get("cue"), f"CUE:{i}")
        fields = _fields(clause.get("fields"), i)
        roles = _reachable_roles(cue, graph, input_anchor, target_anchor)
        if len(roles) == 0:
            return _abstain("ABSTAIN_LEXICAL_ROLE_UNKNOWN")
        if len(roles) > 1:
            return _abstain("ABSTAIN_LEXICAL_ROLE_AMBIGUOUS")
        resolved.append((next(iter(roles)), fields))

    target_clauses = [fields for role, fields in resolved if role == "TARGET"]
    input_clauses = [fields for role, fields in resolved if role == "INPUT"]

    if len(target_clauses) != 1 or not input_clauses or len(target_clauses[0]) != 1:
        return _abstain("ABSTAIN_ROLE_CARDINALITY")

    inputs = sorted({field for group in input_clauses for field in group})
    target = target_clauses[0][0]
    if target in inputs:
        raise JITLexicalRoleError("INPUT_TARGET_OVERLAP")

    return {
        "schema": SCHEMA,
        "status": "ROLES_IDENTIFIED",
        "inputs": inputs,
        "target": target,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "raw_external_knowledge_used": True,
        "random_search": False,
        "hard_nonclaim": "JIT_GRAPH_ROLE_RESOLUTION_IS_NOT_OPEN_WORLD_LEXICAL_RETRIEVAL_OR_FREE_FORM_LANGUAGE_UNDERSTANDING",
    }


def _abstain(status: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "inputs": [],
        "target": None,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "raw_external_knowledge_used": True,
        "random_search": False,
        "hard_nonclaim": "ABSTENTION_PRESERVES_UNKNOWN_OR_AMBIGUOUS_LEXICAL_SEMANTICS",
    }
