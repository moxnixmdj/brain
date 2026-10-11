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


def discovery_queries(goal: str, *, max_queries: int = 8) -> list[str]:
    """Return deterministic generic schema-discovery queries for the goal."""
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

    for intent in intents:
        action = str(intent.get("action_class") or "")
        resources = [str(x) for x in (intent.get("resource_terms") or [])]
        action_terms = list(_ACTION_QUERY_TERMS.get(action, (action,)))
        add([*action_terms, *resources[:6]])
        if resources:
            add([*resources[:6], *action_terms[:2]])
        if len(queries) >= max_queries:
            return queries[:max_queries]

    if not queries:
        terms = _fallback_terms(goal)
        if terms:
            add(terms[:8])

    return queries[:max_queries]


def discovery_summary(goal: str, *, max_queries: int = 8) -> dict[str, Any]:
    contract = compile_goal_contract(goal)
    queries = discovery_queries(goal, max_queries=max_queries)
    return {
        "schema": SCHEMA,
        "goal_status": contract.get("status"),
        "query_count": len(queries),
        "queries": queries,
    }
