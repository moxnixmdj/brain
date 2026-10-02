"""V3 preflight for TOOL_ROUTE_DISCOVERY_AND_SELECTION_001.

V3 is a strict superset of the independently verified V2 route. It keeps all V2
cases and adds exactly the three missing dimensions:
- dynamic discovery of a tool absent from the initial catalog,
- generic declarative active constraints beyond cost/availability/authorization,
- strict advantage over a matched-schema/popularity baseline.

No post-freeze terminal population is consumed.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from canonical.runtime import tool_discovery_information_safe_proof_v2 as v2

SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_INFORMATION_SAFE_PROOF_V3"
NEW_CLASSES = ("DYNAMIC_DISCOVERY", "ACTIVE_CONSTRAINT_SCHEMA", "BASELINE_ADVANTAGE")
CLASSES = tuple(v2.CLASSES) + NEW_CLASSES


def _mk_tool(tid: str, cost: float, *, popularity: float, schema_match: float, region: str, latency: int, tier: str):
    return {
        "tool_id": tid,
        "cost": cost,
        "available": True,
        "authorized": True,
        "popularity": popularity,
        "schema_match": schema_match,
        "constraint_values": {"region": region, "latency_ms": latency, "tier": tier},
    }


def generate_case(seed: int, ordinal: int) -> dict[str, Any]:
    cls = CLASSES[ordinal % len(CLASSES)]
    if cls in v2.CLASSES:
        i = v2.CLASSES.index(cls)
        case = v2.generate_case(seed, i)
        case["schema"] = SCHEMA
        case["case_id"] = f"TOOL-DISCOVERY-V3-{seed}-{ordinal}"
        case["case_class"] = cls
        return case

    suffix = f"{seed % 10000:04d}-{ordinal}"
    req = [f"CAP_A_{suffix}", f"CAP_B_{suffix}"]
    t1 = _mk_tool(f"T1_{suffix}", 1.0, popularity=0.20, schema_match=0.60, region="EU", latency=30, tier="standard")
    t2 = _mk_tool(f"T2_{suffix}", 2.0, popularity=0.95, schema_match=0.99, region="US", latency=80, tier="premium")
    t3 = _mk_tool(f"T3_{suffix}", 3.0, popularity=0.70, schema_match=0.90, region="EU", latency=40, tier="premium")

    if cls == "DYNAMIC_DISCOVERY":
        initial = [t2, t3]
        discovered = dict(t1)
        hidden = {
            t1["tool_id"]: set(req),
            t2["tool_id"]: set(req),
            t3["tool_id"]: {req[0]},
        }
        constraints = []
        catalog_events = [{"kind": "TOOL_DISCOVERED", "event_id": f"D-{suffix}", "tool": discovered}]
    elif cls == "ACTIVE_CONSTRAINT_SCHEMA":
        initial = [t1, t2, t3]
        hidden = {x["tool_id"]: set(req) for x in initial}
        constraints = [
            {"key": "region", "op": "EQ", "value": "EU"},
            {"key": "latency_ms", "op": "LE", "value": 50},
            {"key": "tier", "op": "IN", "value": ["premium"]},
        ]
        catalog_events = []
    else:
        initial = [t1, t2, t3]
        hidden = {
            t1["tool_id"]: set(req),
            t2["tool_id"]: set(req),
            t3["tool_id"]: {req[0]},
        }
        constraints = []
        catalog_events = []

    return {
        "schema": SCHEMA,
        "case_id": f"TOOL-DISCOVERY-V3-{seed}-{ordinal}",
        "case_class": cls,
        "tools": initial,
        "stage1": {
            "task_id": f"S1-{suffix}",
            "required_capabilities": req,
            "catalog_events": catalog_events,
            "active_constraints": constraints,
        },
        "_oracle": {"epoch0": hidden},
    }


def _visible_tools(case: Mapping[str, Any]) -> list[dict[str, Any]]:
    out = [dict(x) for x in case["tools"]]
    for ev in case["stage1"].get("catalog_events", []):
        if ev.get("kind") == "TOOL_DISCOVERED":
            out.append(dict(ev["tool"]))
    return out


def _constraint_ok(tool: Mapping[str, Any], constraints) -> bool:
    attrs = tool.get("constraint_values", {})
    for c in constraints:
        key, op, expected = c["key"], c["op"], c.get("value")
        if key not in attrs:
            return False
        actual = attrs[key]
        if op == "EQ":
            ok = actual == expected
        elif op == "LE":
            ok = float(actual) <= float(expected)
        elif op == "IN":
            ok = actual in expected
        else:
            raise ValueError("UNSUPPORTED_ORACLE_CONSTRAINT_OP")
        if not ok:
            return False
    return True


def public_stage(case: Mapping[str, Any], receipts=()):
    row = case["stage1"]
    return {
        "schema": case["schema"],
        "case_id": case["case_id"],
        "stage": 1,
        "task_id": row["task_id"],
        "required_capabilities": list(row["required_capabilities"]),
        "tools": [dict(x) for x in case["tools"]],
        "catalog_events": [dict(x) for x in row.get("catalog_events", [])],
        "active_constraints": [dict(x) for x in row.get("active_constraints", [])],
        "prior_probe_receipts": [dict(x) for x in receipts],
        "version_events": [],
    }


def _oracle_best(case: Mapping[str, Any]) -> str:
    req = set(case["stage1"]["required_capabilities"])
    constraints = case["stage1"].get("active_constraints", [])
    eligible = []
    for t in _visible_tools(case):
        tid = t["tool_id"]
        if t.get("available") is not True or t.get("authorized") is not True:
            continue
        if not _constraint_ok(t, constraints):
            continue
        if req.issubset(set(case["_oracle"]["epoch0"][tid])):
            eligible.append((float(t["cost"]), tid))
    if not eligible:
        raise ValueError("NO_SUFFICIENT_TOOL")
    return sorted(eligible)[0][1]


def _probe(case: Mapping[str, Any], action: Mapping[str, Any], seq: int) -> dict[str, Any]:
    tid = str(action.get("tool_id") or "")
    cap = str(action.get("capability") or "")
    visible = {x["tool_id"] for x in _visible_tools(case)}
    req = set(case["stage1"]["required_capabilities"])
    if tid not in visible:
        raise ValueError("PROBE_UNKNOWN_OR_UNDISCOVERED_TOOL")
    if cap not in req:
        raise ValueError("PROBE_IRRELEVANT_CAPABILITY")
    return {
        "receipt_id": f"P-{case['case_id']}-{seq}",
        "kind": "SAFE_CAPABILITY_PROBE",
        "stage": 1,
        "tool_id": tid,
        "capability": cap,
        "epoch": 0,
        "supported": cap in case["_oracle"]["epoch0"][tid],
    }


def _supported(receipts, tid: str, req: set[str]) -> bool:
    m = {(r["tool_id"], r["capability"]): bool(r["supported"]) for r in receipts}
    return all(m.get((tid, c)) is True for c in req)


def _run_policy(case: Mapping[str, Any], policy, max_actions=24):
    receipts = []
    actions = []
    for i in range(max_actions):
        action = policy(public_stage(case, receipts))
        if not isinstance(action, Mapping):
            return {"pass": False, "reason": "ACTION_NOT_MAPPING", "actions": actions}
        kind = action.get("action")
        if kind == "PROBE":
            try:
                rec = _probe(case, action, i)
            except Exception as exc:
                return {"pass": False, "reason": type(exc).__name__ + ":" + str(exc), "actions": actions}
            key = (rec["tool_id"], rec["capability"])
            if any((r["tool_id"], r["capability"]) == key for r in receipts):
                return {"pass": False, "reason": "DUPLICATE_PROBE", "actions": actions}
            receipts.append(rec)
            actions.append({"action": "PROBE", "tool_id": rec["tool_id"], "capability": rec["capability"]})
            continue
        if kind == "SELECT":
            tid = str(action.get("tool_id") or "")
            expected = _oracle_best(case)
            if tid != expected:
                return {"pass": False, "reason": "NONOPTIMAL_OR_INSUFFICIENT_SELECTION", "selected": tid, "expected": expected, "actions": actions}
            if not _supported(receipts, tid, set(case["stage1"]["required_capabilities"])):
                return {"pass": False, "reason": "SELECTION_WITHOUT_CURRENT_POSITIVE_EVIDENCE", "actions": actions}
            tools = {x["tool_id"]: x for x in _visible_tools(case)}
            return {
                "pass": True,
                "reason": "PASS",
                "selected": tid,
                "selected_cost": float(tools[tid]["cost"]),
                "probe_count": len([x for x in actions if x["action"] == "PROBE"]),
                "actions": actions + [{"action": "SELECT", "tool_id": tid}],
            }
        if kind == "ESCALATE":
            return {"pass": False, "reason": "PREMATURE_ESCALATION", "actions": actions}
        return {"pass": False, "reason": "UNKNOWN_ACTION", "actions": actions}
    return {"pass": False, "reason": "ACTION_BUDGET_EXHAUSTED", "actions": actions}


def popularity_schema_baseline(public: Mapping[str, Any]) -> dict[str, Any]:
    from canonical.runtime.tool_discovery_information_safe_candidate import _visible_tools, _constraint_ok, _evidence
    required = sorted(set(public.get("required_capabilities", [])))
    evidence = _evidence(public)
    tools = [
        t for t in _visible_tools(public)
        if t.get("available") is True and t.get("authorized") is True
        and _constraint_ok(t, public.get("active_constraints", []))
    ]
    tools.sort(key=lambda t: (-float(t.get("schema_match", 0.0)), -float(t.get("popularity", 0.0)), str(t.get("tool_id"))))
    for t in tools:
        tid = str(t["tool_id"])
        unknown = [c for c in required if evidence.get((tid, c)) is None]
        false = any(evidence.get((tid, c)) is False for c in required)
        if false:
            continue
        if unknown:
            return {"action": "PROBE", "tool_id": tid, "capability": unknown[0]}
        return {"action": "SELECT", "tool_id": tid}
    return {"action": "ESCALATE", "reason": "NO_ROUTE"}


def score_episode(case: Mapping[str, Any], policy):
    if case["case_class"] in v2.CLASSES:
        return v2.score_episode(case, policy)
    verdict = _run_policy(case, policy)
    if not verdict["pass"]:
        return {"schema": SCHEMA, **verdict}
    if case["case_class"] == "DYNAMIC_DISCOVERY":
        discovered_ids = {ev["tool"]["tool_id"] for ev in case["stage1"]["catalog_events"]}
        if verdict["selected"] not in discovered_ids:
            return {"schema": SCHEMA, "pass": False, "reason": "DYNAMIC_DISCOVERY_NOT_USED"}
    if case["case_class"] == "ACTIVE_CONSTRAINT_SCHEMA":
        expected = _oracle_best(case)
        if verdict["selected"] != expected:
            return {"schema": SCHEMA, "pass": False, "reason": "ACTIVE_CONSTRAINT_SELECTION_WRONG"}
    if case["case_class"] == "BASELINE_ADVANTAGE":
        baseline = _run_policy(case, popularity_schema_baseline)
        if not baseline["pass"]:
            return {"schema": SCHEMA, "pass": False, "reason": "BASELINE_INVALID_FOR_COMPARISON", "baseline": baseline}
        candidate_tuple = (verdict["selected_cost"], verdict["probe_count"])
        baseline_tuple = (baseline["selected_cost"], baseline["probe_count"])
        if not (candidate_tuple < baseline_tuple):
            return {"schema": SCHEMA, "pass": False, "reason": "NO_STRICT_ADVANTAGE_OVER_BASELINE", "candidate": verdict, "baseline": baseline}
        verdict["baseline"] = baseline
    return {"schema": SCHEMA, **verdict}


def run_batch(seed: int, case_count: int, policy):
    rows = []
    by_class = defaultdict(lambda: {"pass": 0, "total": 0, "reasons": defaultdict(int)})
    for ordinal in range(case_count):
        case = generate_case(seed, ordinal)
        try:
            verdict = score_episode(case, policy)
        except Exception as exc:
            verdict = {"pass": False, "reason": "CANDIDATE_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)}
        cls = case["case_class"]
        by_class[cls]["total"] += 1
        by_class[cls]["pass"] += int(bool(verdict["pass"]))
        by_class[cls]["reasons"][verdict["reason"]] += 1
        rows.append({"case_id": case["case_id"], "class": cls, "pass": bool(verdict["pass"]), "reason": verdict["reason"]})
    passed = sum(int(x["pass"]) for x in rows)
    return {
        "schema": "PROJECT_BRAIN_TOOL_DISCOVERY_INFORMATION_SAFE_PREFLIGHT_RESULT_V3",
        "seed": seed,
        "case_count": case_count,
        "passed": passed,
        "failed": case_count - passed,
        "all_pass": passed == case_count,
        "by_class": {
            cls: {
                "pass": v["pass"], "total": v["total"],
                "fraction": v["pass"] / v["total"] if v["total"] else 0.0,
                "reasons": dict(sorted(v["reasons"].items())),
            }
            for cls, v in sorted(by_class.items())
        },
        "failures": [x for x in rows if not x["pass"]],
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
