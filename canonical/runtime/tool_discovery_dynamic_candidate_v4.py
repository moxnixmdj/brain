"""Information-safe dynamic tool discovery/selection policy V4.

V4 repairs a global-optimality flaw in V3: V3 could SELECT a currently visible
sufficient tool before querying still-unqueried discovery sources, so a cheaper
sufficient unknown-identity tool could be missed by both policy and evaluator.

V4 saturates the finite authoritative discovery interface before any PROBE or
SELECT. After saturation it evaluates admissible tools in declared-cost order,
uses only current-epoch probe evidence, selects only with positive evidence for
all required capabilities, and escalates only after every admissible route has
been ruled out.

The policy remains backward compatible with the legacy pre-enumerated terminal
shape: if `visible_tools` is absent, `tools` is treated as the already-complete
visible catalog and no discovery step is introduced unless discovery_sources are
actually present.
"""
from __future__ import annotations

from typing import Any, Mapping

CMP = {"eq", "neq", "in", "not_in", "lt", "le", "gt", "ge", "contains", "exists"}


def _get(obj: Mapping[str, Any], path: str):
    cur: Any = obj
    for part in str(path).split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _pred(expr: Any, tool: Mapping[str, Any]) -> bool:
    if expr in (None, {}, []):
        return True
    if not isinstance(expr, Mapping):
        return False
    op = str(expr.get("op") or "")
    if op == "and":
        xs = expr.get("args")
        return isinstance(xs, list) and all(_pred(x, tool) for x in xs)
    if op == "or":
        xs = expr.get("args")
        return isinstance(xs, list) and bool(xs) and any(_pred(x, tool) for x in xs)
    if op == "not":
        return not _pred(expr.get("arg"), tool)
    if op not in CMP:
        return False
    value = _get(tool, str(expr.get("path") or ""))
    target = expr.get("value")
    if op == "exists":
        return (value is not None) is bool(target)
    if op == "eq":
        return value == target
    if op == "neq":
        return value != target
    if op == "in":
        return isinstance(target, list) and value in target
    if op == "not_in":
        return isinstance(target, list) and value not in target
    if op == "contains":
        return isinstance(value, (str, list, tuple, set)) and target in value
    if isinstance(value, bool) or isinstance(target, bool):
        return False
    if not isinstance(value, (int, float)) or not isinstance(target, (int, float)):
        return False
    if op == "lt":
        return value < target
    if op == "le":
        return value <= target
    if op == "gt":
        return value > target
    if op == "ge":
        return value >= target
    return False


def _queried_sources(public: Mapping[str, Any]) -> set[str]:
    return {
        str(x.get("source_id"))
        for x in public.get("discovery_receipts", [])
        if isinstance(x, Mapping) and x.get("kind") == "DISCOVERY_RESULT"
    }


def _catalog(public: Mapping[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    raw_visible = public.get("visible_tools")
    if raw_visible is None:
        raw_visible = public.get("tools", [])

    by_id: dict[str, dict[str, Any]] = {}
    conflict = False

    def add_tool(row: Any) -> None:
        nonlocal conflict
        if not isinstance(row, Mapping):
            return
        tid = str(row.get("tool_id") or "")
        if not tid:
            return
        normalized = dict(row)
        prior = by_id.get(tid)
        if prior is not None and prior != normalized:
            conflict = True
            return
        by_id[tid] = normalized

    for tool in raw_visible or []:
        add_tool(tool)

    for rec in public.get("discovery_receipts", []):
        if not isinstance(rec, Mapping) or rec.get("kind") != "DISCOVERY_RESULT":
            continue
        for tool in rec.get("tools", []) or []:
            add_tool(tool)

    return list(by_id.values()), conflict


def _epochs(public: Mapping[str, Any], tools: list[dict[str, Any]]) -> dict[str, int]:
    out = {
        str(t.get("tool_id")): int(t.get("epoch", 0))
        for t in tools
        if isinstance(t, Mapping) and str(t.get("tool_id") or "")
    }
    for ev in public.get("version_events", []):
        if isinstance(ev, Mapping) and ev.get("kind") == "TOOL_VERSION_CHANGED":
            tid = str(ev.get("tool_id") or "")
            if tid in out:
                out[tid] = int(ev.get("new_epoch", out[tid] + 1))
    return out


def _evidence(
    public: Mapping[str, Any],
    tools: list[dict[str, Any]],
) -> dict[tuple[str, str], bool]:
    epochs = _epochs(public, tools)
    out: dict[tuple[str, str], bool] = {}
    for rec in public.get("prior_probe_receipts", []):
        if not isinstance(rec, Mapping) or rec.get("kind") != "SAFE_CAPABILITY_PROBE":
            continue
        tid = str(rec.get("tool_id") or "")
        cap = str(rec.get("capability") or "")
        if tid in epochs and int(rec.get("epoch", -1)) == epochs[tid]:
            out[(tid, cap)] = rec.get("supported") is True
    return out


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    required = sorted(
        {str(x) for x in public.get("required_capabilities", []) if str(x)}
    )
    if not required:
        return {"action": "ESCALATE", "reason": "NO_REQUIRED_CAPABILITIES"}

    # Global-optimality repair: exhaust the finite authoritative identity
    # discovery interface before probing or selecting any route.
    queried = _queried_sources(public)
    sources = [
        s
        for s in public.get("discovery_sources", [])
        if isinstance(s, Mapping)
        and s.get("available") is True
        and str(s.get("source_id") or "") not in queried
    ]
    sources.sort(
        key=lambda s: (float(s.get("cost", 0.0)), str(s.get("source_id") or ""))
    )
    if sources:
        return {
            "action": "DISCOVER",
            "source_id": str(sources[0].get("source_id")),
            "query": " ".join(required),
        }

    tools, conflict = _catalog(public)
    if conflict:
        return {"action": "ESCALATE", "reason": "DISCOVERY_METADATA_CONFLICT"}

    constraint = public.get("constraint")
    evidence = _evidence(public, tools)

    admissible = [
        t
        for t in tools
        if isinstance(t, Mapping)
        and t.get("available") is True
        and t.get("authorized") is True
        and _pred(constraint, t)
    ]
    admissible.sort(
        key=lambda t: (float(t.get("cost", 0.0)), str(t.get("tool_id") or ""))
    )

    for tool in admissible:
        tid = str(tool.get("tool_id") or "")
        unknown: list[str] = []
        falsified = False
        for cap in required:
            value = evidence.get((tid, cap))
            if value is False:
                falsified = True
                break
            if value is None:
                unknown.append(cap)
        if falsified:
            continue
        if unknown:
            return {"action": "PROBE", "tool_id": tid, "capability": unknown[0]}
        return {"action": "SELECT", "tool_id": tid}

    return {
        "action": "ESCALATE",
        "reason": "NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY",
    }
