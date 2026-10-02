"""Brain policy for hidden-capability tool discovery and selection.

V3 remains information-safe and backward compatible with V1/V2. It consumes only
candidate-visible metadata, safe probe receipts, public version events, public catalog
discovery events, and declarative active constraints. Hidden capabilities remain hidden.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence


def _norm_id(v: Any) -> str:
    return str(v or "").strip()


def _visible_tools(public: Mapping[str, Any]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    conflict = False
    for raw in public.get("tools", []):
        if not isinstance(raw, Mapping):
            continue
        tid = _norm_id(raw.get("tool_id"))
        if not tid:
            continue
        row = dict(raw)
        if tid in by_id and by_id[tid] != row:
            conflict = True
        by_id[tid] = row
    for ev in public.get("catalog_events", []):
        if not isinstance(ev, Mapping) or ev.get("kind") != "TOOL_DISCOVERED":
            continue
        raw = ev.get("tool")
        if not isinstance(raw, Mapping):
            continue
        tid = _norm_id(raw.get("tool_id"))
        if not tid:
            continue
        row = dict(raw)
        if tid in by_id and by_id[tid] != row:
            conflict = True
        by_id[tid] = row
    if conflict:
        return []
    return [by_id[k] for k in sorted(by_id)]


def _constraint_ok(tool: Mapping[str, Any], active_constraints: Sequence[Mapping[str, Any]]) -> bool:
    attrs = tool.get("constraint_values", {})
    if not isinstance(attrs, Mapping):
        attrs = {}
    for raw in active_constraints:
        if not isinstance(raw, Mapping):
            return False
        key = _norm_id(raw.get("key"))
        op = _norm_id(raw.get("op")).upper()
        if not key or key not in attrs:
            return False
        actual = attrs[key]
        expected = raw.get("value")
        try:
            if op == "EQ":
                ok = actual == expected
            elif op == "NE":
                ok = actual != expected
            elif op == "LE":
                ok = float(actual) <= float(expected)
            elif op == "LT":
                ok = float(actual) < float(expected)
            elif op == "GE":
                ok = float(actual) >= float(expected)
            elif op == "GT":
                ok = float(actual) > float(expected)
            elif op == "IN":
                ok = actual in expected if isinstance(expected, (list, tuple, set)) else False
            elif op == "NOT_IN":
                ok = actual not in expected if isinstance(expected, (list, tuple, set)) else False
            else:
                return False
        except Exception:
            return False
        if not ok:
            return False
    return True


def _epoch_map(public: Mapping[str, Any]) -> dict[str, int]:
    out = {_norm_id(t.get("tool_id")): 0 for t in _visible_tools(public)}
    for ev in public.get("version_events", []):
        if ev.get("kind") == "TOOL_VERSION_CHANGED":
            tid = _norm_id(ev.get("tool_id"))
            if tid in out:
                out[tid] = int(ev.get("new_epoch", 1))
    return out


def _evidence(public: Mapping[str, Any]) -> dict[tuple[str, str], bool]:
    epochs = _epoch_map(public)
    out: dict[tuple[str, str], bool] = {}
    for rec in public.get("prior_probe_receipts", []):
        if rec.get("kind") != "SAFE_CAPABILITY_PROBE":
            continue
        tid = _norm_id(rec.get("tool_id"))
        cap = _norm_id(rec.get("capability"))
        if tid not in epochs or rec.get("epoch") != epochs[tid]:
            continue
        out[(tid, cap)] = rec.get("supported") is True
    return out


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    required = sorted({_norm_id(x) for x in public.get("required_capabilities", []) if _norm_id(x)})
    tools = _visible_tools(public)
    if not tools and (public.get("tools") or public.get("catalog_events")):
        return {"action": "ESCALATE", "reason": "CATALOG_CONFLICT_OR_NO_VISIBLE_TOOLS"}

    constraints = public.get("active_constraints", [])
    if not isinstance(constraints, Sequence) or isinstance(constraints, (str, bytes)):
        return {"action": "ESCALATE", "reason": "ACTIVE_CONSTRAINT_SCHEMA_INVALID"}

    evidence = _evidence(public)
    eligible = [
        t for t in tools
        if t.get("available") is True
        and t.get("authorized") is True
        and _constraint_ok(t, constraints)
    ]
    eligible.sort(key=lambda t: (float(t.get("cost", 0.0)), _norm_id(t.get("tool_id"))))

    for tool in eligible:
        tid = _norm_id(tool.get("tool_id"))
        known_false = False
        unknown = []
        for cap in required:
            value = evidence.get((tid, cap))
            if value is False:
                known_false = True
                break
            if value is None:
                unknown.append(cap)
        if known_false:
            continue
        if unknown:
            return {"action": "PROBE", "tool_id": tid, "capability": unknown[0]}
        return {"action": "SELECT", "tool_id": tid}

    return {"action": "ESCALATE", "reason": "NO_EVIDENCE_SUPPORTED_SUFFICIENT_TOOL"}
