"""Brain-owned deterministic trajectory invariant checker.

Mechanism scope: normalize event/message trajectories and evaluate explicit,
machine-checkable invariants. This intentionally does NOT synthesize invariants
or make ambiguous semantic judgments.

Mechanism informed by the deterministic IR/checking decomposition in
microsoft/AgentRx (MIT); implementation here is a minimal independent capsule.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import Any, Iterable


@dataclass(frozen=True)
class Event:
    index: int
    role: str
    content: str


@dataclass(frozen=True)
class Violation:
    invariant_id: str
    kind: str
    step_index: int
    reason: str
    evidence: dict[str, Any]


def normalize_trajectory(obj: Any) -> list[Event]:
    """Normalize common list/wrapper/message shapes to flat ordered events."""
    if isinstance(obj, str):
        obj = json.loads(obj)
    if isinstance(obj, dict):
        for key in ("events", "messages", "trajectory", "traj"):
            if isinstance(obj.get(key), list):
                obj = obj[key]
                break
        else:
            obj = [obj]
    if not isinstance(obj, list):
        raise ValueError("trajectory must be list/dict/JSON")
    out: list[Event] = []
    for i, item in enumerate(obj, 1):
        if not isinstance(item, dict):
            raise ValueError(f"event {i} must be dict")
        role = str(item.get("role") or item.get("source") or item.get("actor") or "unknown")
        content = item.get("content")
        if content is None:
            content = item.get("message")
        if content is None:
            content = json.dumps(item, sort_keys=True, ensure_ascii=False)
        elif not isinstance(content, str):
            content = json.dumps(content, sort_keys=True, ensure_ascii=False)
        out.append(Event(i, role, content))
    return out


def _rx(pattern: str, text: str) -> re.Match[str] | None:
    return re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)


def _find(events: list[Event], pattern: str, start: int = 0) -> list[Event]:
    return [e for e in events[start:] if _rx(pattern, e.content)]


def evaluate(events: Iterable[Event] | Any, invariants: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(events, list) or (events and not isinstance(events[0], Event)):
        events = normalize_trajectory(events)
    events = list(events)
    violations: list[Violation] = []

    def fail(inv: dict[str, Any], step: int, reason: str, evidence: dict[str, Any]):
        violations.append(Violation(str(inv["id"]), str(inv["kind"]), step, reason, evidence))

    for inv in invariants:
        iid = str(inv["id"])
        kind = str(inv["kind"])

        if kind == "required_sequence":
            cursor = 0
            for pat in inv["patterns"]:
                hit = next((e for e in events[cursor:] if _rx(str(pat), e.content)), None)
                if hit is None:
                    fail(inv, events[-1].index if events else 0, "required sequence element missing",
                         {"missing_pattern": pat, "matched_prefix_count": cursor})
                    break
                cursor = hit.index

        elif kind == "forbidden_after":
            trigger = next((e for e in events if _rx(str(inv["trigger"]), e.content)), None)
            if trigger:
                bad = next((e for e in events if e.index > trigger.index and _rx(str(inv["forbidden"]), e.content)), None)
                if bad:
                    fail(inv, bad.index, "forbidden event occurred after trigger",
                         {"trigger_step": trigger.index, "forbidden_excerpt": bad.content[:500]})

        elif kind == "required_after":
            trigger = next((e for e in events if _rx(str(inv["trigger"]), e.content)), None)
            if trigger:
                hit = next((e for e in events if e.index > trigger.index and _rx(str(inv["required"]), e.content)), None)
                if hit is None:
                    fail(inv, trigger.index, "required follow-up missing after trigger",
                         {"trigger_step": trigger.index, "required_pattern": inv["required"]})

        elif kind == "must_not_contain":
            bad = next((e for e in events if _rx(str(inv["pattern"]), e.content)), None)
            if bad:
                fail(inv, bad.index, "forbidden pattern present", {"excerpt": bad.content[:500]})

        elif kind == "must_contain":
            if not any(_rx(str(inv["pattern"]), e.content) for e in events):
                fail(inv, events[-1].index if events else 0, "required pattern absent",
                     {"required_pattern": inv["pattern"]})

        elif kind == "field_provenance":
            source_values: set[str] = set()
            src = re.compile(str(inv["source_pattern"]), flags=re.IGNORECASE | re.DOTALL)
            use = re.compile(str(inv["use_pattern"]), flags=re.IGNORECASE | re.DOTALL)
            for e in events:
                for m in src.finditer(e.content):
                    source_values.add(m.group(str(inv.get("source_group", "value"))))
            for e in events:
                for m in use.finditer(e.content):
                    value = m.group(str(inv.get("use_group", "value")))
                    if value not in source_values:
                        fail(inv, e.index, "used value has no prior/source provenance",
                             {"value": value, "known_values": sorted(source_values)[:100]})

        elif kind == "json_keys":
            pat = re.compile(str(inv["selector"]), flags=re.IGNORECASE | re.DOTALL)
            required = [str(x) for x in inv.get("required_keys", [])]
            for e in events:
                m = pat.search(e.content)
                if not m:
                    continue
                raw = m.group(str(inv.get("json_group", "json")))
                try:
                    data = json.loads(raw)
                except Exception as exc:
                    fail(inv, e.index, "selected payload is not valid JSON", {"error": str(exc), "raw": raw[:500]})
                    continue
                missing = [k for k in required if k not in data]
                if missing:
                    fail(inv, e.index, "required JSON keys missing", {"missing": missing})

        else:
            raise ValueError(f"unsupported invariant kind: {kind} ({iid})")

    return {
        "schema": "BRAIN_TRAJECTORY_INVARIANT_RESULT_V1",
        "event_count": len(events),
        "invariant_count": len(invariants),
        "pass": not violations,
        "violations": [asdict(v) for v in violations],
        "first_violation": asdict(violations[0]) if violations else None,
    }
