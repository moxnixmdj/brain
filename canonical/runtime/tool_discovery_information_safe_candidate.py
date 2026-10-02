"""Brain policy for hidden-capability tool discovery and selection.

The policy consumes only candidate-visible tool metadata, current requirements,
public safe-probe receipts, and public version-change events. It never imports the
proof evaluator or a hidden capability table.
"""
from __future__ import annotations

from typing import Any, Mapping


def _epoch_map(public: Mapping[str, Any]) -> dict[str, int]:
    out = {str(t["tool_id"]): 0 for t in public.get("tools", [])}
    for ev in public.get("version_events", []):
        if ev.get("kind") == "TOOL_VERSION_CHANGED":
            tid = str(ev.get("tool_id") or "")
            if tid in out:
                out[tid] = int(ev.get("new_epoch", 1))
    return out


def _evidence(public: Mapping[str, Any]) -> dict[tuple[str, str], bool]:
    epochs = _epoch_map(public)
    out: dict[tuple[str, str], bool] = {}
    for rec in public.get("prior_probe_receipts", []):
        if rec.get("kind") != "SAFE_CAPABILITY_PROBE":
            continue
        tid = str(rec.get("tool_id") or "")
        cap = str(rec.get("capability") or "")
        if tid not in epochs or rec.get("epoch") != epochs[tid]:
            continue
        out[(tid, cap)] = rec.get("supported") is True
    return out


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    required = sorted({str(x) for x in public.get("required_capabilities", []) if str(x)})
    evidence = _evidence(public)
    tools = [
        t for t in public.get("tools", [])
        if t.get("available") is True and t.get("authorized") is True
    ]
    tools.sort(key=lambda t: (float(t.get("cost", 0.0)), str(t.get("tool_id") or "")))

    for tool in tools:
        tid = str(tool.get("tool_id") or "")
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
