"""Benchmark-agnostic tool-schema discovery query generator.

Transforms a natural-language goal into compact search queries for arbitrary
tool/schema registries. It contains no benchmark, vendor, app, endpoint, task,
or seeded-entity literals.

The output is intentionally shallow: discovery only. Planning and action
selection remain in the generic goal/tool-effect planner.
"""
from __future__ import annotations

import re
from typing import Any

from canonical.runtime.generic_goal_tool_effect_planner_v1 import compile_goal_contract

SCHEMA = "PROJECT_BRAIN_GENERIC_TOOL_SCHEMA_DISCOVERY_V1"

_ACTION_QUERY_TERMS = {
    "observe": ("search", "list", "get"),
    "create": ("create", "add"),
    "update": ("update", "patch"),
    "delete": ("delete", "remove"),
    "associate": ("attach", "assign", "link"),
    "notify": ("send", "message"),
}

_FALLBACK_STOP = {
    "a","an","the","to","of","for","from","with","in","on","at","by","as",
    "it","its","this","that","these","those","and","or","then","please","our",
    "my","your","their","all","any","each","into","onto","using","use","before",
    "after","once","when","where","which","who","what","is","are","be","been",
    "do","not","dont","must","never",
}


def _fallback_terms(goal: str) -> list[str]:
    out: list[str] = []
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", str(goal or "")):
        token = raw.lower()
        if len(token) < 2 or token in _FALLBACK_STOP:
            continue
        if token not in out:
            out.append(token)
    return out


def _priority_resources(intent: dict[str, Any]) -> list[str]:
    resources = [str(x) for x in (intent.get("resource_terms") or []) if str(x)]
    clause = str(intent.get("clause") or "")
    priority: list[str] = []

    def add(token: str) -> None:
        token = token.lower()
        if token in resources and token not in priority:
            priority.append(token)

    # Explicit transport semantics are highly discriminative.
    for token in ("email", "channel"):
        add(token)

    # Proper/camel-case surface forms often identify a service or named object.
    raw_words = re.findall(r"[A-Za-z][A-Za-z0-9]*", clause)
    for raw in raw_words:
        compact = raw.lower()
        has_internal_cap = any(ch.isupper() for ch in raw[1:])
        if has_internal_cap or (raw[:1].isupper() and raw.lower() not in _FALLBACK_STOP):
            add(compact)

    # Prefer longer lexical identities before generic short nouns, while
    # preserving original order as deterministic tiebreaker.
    indexed = {value: i for i, value in enumerate(resources)}
    for token in sorted(
        resources,
        key=lambda x: (0 if len(x) >= 6 else 1, indexed[x]),
    ):
        if token not in priority:
            priority.append(token)
    return priority


def discovery_queries(goal: str, *, max_queries: int = 12) -> list[str]:
    """Return deterministic, intent-balanced schema-discovery queries."""
    if not isinstance(goal, str) or not goal.strip():
        raise ValueError("GOAL_REQUIRED")
    if not isinstance(max_queries, int) or max_queries < 1:
        raise ValueError("MAX_QUERIES_POSITIVE_INT_REQUIRED")

    contract = compile_goal_contract(goal)
    intents = list(contract.get("intents") or [])
    queries: list[str] = []

    def add(parts: list[str]) -> None:
        tokens: list[str] = []
        for part in parts:
            for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", str(part or "").lower()):
                if token not in tokens:
                    tokens.append(token)
        q = " ".join(tokens).strip()
        if q and q not in queries:
            queries.append(q)

    specs: list[tuple[list[str], list[str]]] = []
    for intent in intents:
        action = str(intent.get("action_class") or "")
        action_terms = list(_ACTION_QUERY_TERMS.get(action, (action,)))
        resources = _priority_resources(intent)
        specs.append((action_terms, resources))

    # Round 1: every intent gets one compact broad query before any intent gets
    # extra search budget.
    for action_terms, resources in specs:
        add([*action_terms, *resources[:4]])
        if len(queries) >= max_queries:
            return queries[:max_queries]

    # Rounds 2+: focused BM25 queries, balanced across intents by resource rank.
    max_resources = max((len(resources) for _, resources in specs), default=0)
    for resource_index in range(max_resources):
        for action_terms, resources in specs:
            if resource_index >= len(resources):
                continue
            add([action_terms[0] if action_terms else "", resources[resource_index]])
            if len(queries) >= max_queries:
                return queries[:max_queries]

    # Action-only fallbacks recover generic operation surfaces when no
    # endpoint-native object vocabulary is present in the goal.
    for action_terms, _ in specs:
        add(action_terms)
        if len(queries) >= max_queries:
            return queries[:max_queries]

    if not queries:
        terms = _fallback_terms(goal)
        if terms:
            add(terms[:8])

    return queries[:max_queries]

def discovery_summary(goal: str, *, max_queries: int = 12) -> dict[str, Any]:
    contract = compile_goal_contract(goal)
    queries = discovery_queries(goal, max_queries=max_queries)
    return {
        "schema": SCHEMA,
        "goal_status": contract.get("status"),
        "query_count": len(queries),
        "queries": queries,
    }
