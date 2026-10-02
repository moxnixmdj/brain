"""Information-safe proof route for TOOL_ROUTE_DISCOVERY_AND_SELECTION_001.

The candidate sees tool identities, costs, authorization/availability, the current
required capability set, prior probe receipts, and public version-change events.
True tool capabilities remain hidden. The candidate must discover enough capability
evidence through bounded safe probes to select the least-cost sufficient route,
reuse valid evidence on a second task, and invalidate stale evidence after a tool
version change.

No hidden capability table, ideal route, or reference action is candidate-visible.
This module is preflight/proof machinery and grants no capability credit by itself.
"""
from __future__ import annotations

from collections import defaultdict
import random
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_INFORMATION_SAFE_PROOF_V1"


def _valid_id(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def generate_case(seed: int, ordinal: int) -> dict[str, Any]:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("SEED")
    if not isinstance(ordinal, int) or ordinal < 0:
        raise ValueError("ORDINAL")
    r = random.Random((seed << 19) ^ ordinal ^ 0x70A1)
    suffix = str(r.randrange(10000, 99999))
    caps = [f"CAP_{i}_{suffix}" for i in range(4)]
    c0, c1, c2, c3 = caps
    tools = [
        {"tool_id": f"T1_{suffix}", "cost": 1.0, "available": True, "authorized": True},
        {"tool_id": f"T2_{suffix}", "cost": 2.0, "available": True, "authorized": True},
        {"tool_id": f"T3_{suffix}", "cost": 3.0, "available": True, "authorized": True},
        {"tool_id": f"T4_{suffix}", "cost": 4.0, "available": True, "authorized": True},
    ]
    hidden0 = {
        tools[0]["tool_id"]: {c0},
        tools[1]["tool_id"]: {c0, c1, c2},
        tools[2]["tool_id"]: {c1, c2, c3},
        tools[3]["tool_id"]: {c0, c1, c2, c3},
    }
    cls = ("NO_CHANGE", "SELECTED_TOOL_LOSES_CAPABILITY", "CHEAPER_TOOL_GAINS_CAPABILITY")[ordinal % 3]
    hidden1 = {k: set(v) for k, v in hidden0.items()}
    version_events: list[dict[str, Any]] = []
    if cls == "SELECTED_TOOL_LOSES_CAPABILITY":
        tid = tools[1]["tool_id"]
        hidden1[tid].discard(c2)
        version_events.append({
            "event_id": f"V-{seed}-{ordinal}",
            "kind": "TOOL_VERSION_CHANGED",
            "tool_id": tid,
            "new_epoch": 1,
        })
    elif cls == "CHEAPER_TOOL_GAINS_CAPABILITY":
        tid = tools[0]["tool_id"]
        hidden1[tid] |= {c1, c2}
        version_events.append({
            "event_id": f"V-{seed}-{ordinal}",
            "kind": "TOOL_VERSION_CHANGED",
            "tool_id": tid,
            "new_epoch": 1,
        })

    return {
        "schema": SCHEMA,
        "case_id": f"TOOL-DISCOVERY-{seed}-{ordinal}",
        "case_class": cls,
        "tools": tools,
        "stage1": {"task_id": f"S1-{seed}-{ordinal}", "required_capabilities": [c0, c1]},
        "stage2": {"task_id": f"S2-{seed}-{ordinal}", "required_capabilities": [c1, c2], "version_events": version_events},
        "_oracle": {"epoch0": hidden0, "epoch1": hidden1},
    }


def _epoch_map(case: Mapping[str, Any], stage: int) -> dict[str, int]:
    out = {str(t["tool_id"]): 0 for t in case["tools"]}
    if stage == 2:
        for ev in case["stage2"].get("version_events", []):
            if ev.get("kind") == "TOOL_VERSION_CHANGED":
                out[str(ev["tool_id"])] = int(ev["new_epoch"])
    return out


def _hidden_caps(case: Mapping[str, Any], stage: int, tool_id: str) -> set[str]:
    epochs = _epoch_map(case, stage)
    epoch = epochs.get(tool_id)
    if epoch is None:
        raise ValueError("UNKNOWN_TOOL")
    table = case["_oracle"]["epoch1" if epoch == 1 else "epoch0"]
    return set(table[tool_id])


def _public_stage(case: Mapping[str, Any], stage: int, receipts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    row = case["stage1"] if stage == 1 else case["stage2"]
    return {
        "schema": case["schema"],
        "case_id": case["case_id"],
        "stage": stage,
        "task_id": row["task_id"],
        "required_capabilities": list(row["required_capabilities"]),
        "tools": [dict(t) for t in case["tools"]],
        "prior_probe_receipts": [dict(x) for x in receipts],
        "version_events": [dict(x) for x in row.get("version_events", [])],
    }


def public_stage(case: Mapping[str, Any], stage: int, receipts: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    if stage not in (1, 2):
        raise ValueError("STAGE")
    return _public_stage(case, stage, receipts)


def _oracle_best_tool(case: Mapping[str, Any], stage: int) -> str:
    row = case["stage1"] if stage == 1 else case["stage2"]
    req = set(row["required_capabilities"])
    eligible = []
    for t in case["tools"]:
        if t.get("available") is not True or t.get("authorized") is not True:
            continue
        tid = str(t["tool_id"])
        if req.issubset(_hidden_caps(case, stage, tid)):
            eligible.append((float(t["cost"]), tid))
    if not eligible:
        raise ValueError("NO_SUFFICIENT_TOOL")
    eligible.sort()
    return eligible[0][1]


def _current_epoch(case: Mapping[str, Any], stage: int, tool_id: str) -> int:
    return _epoch_map(case, stage)[tool_id]


def _valid_receipt_map(case: Mapping[str, Any], stage: int, receipts: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], bool]:
    epochs = _epoch_map(case, stage)
    out: dict[tuple[str, str], bool] = {}
    for rec in receipts:
        tid = str(rec.get("tool_id") or "")
        cap = str(rec.get("capability") or "")
        epoch = rec.get("epoch")
        if tid not in epochs or not _valid_id(cap) or epoch != epochs[tid]:
            continue
        key = (tid, cap)
        if key in out and out[key] != bool(rec.get("supported")):
            raise ValueError("CONTRADICTORY_CURRENT_RECEIPTS")
        out[key] = bool(rec.get("supported"))
    return out


def _probe_receipt(case: Mapping[str, Any], stage: int, action: Mapping[str, Any], seq: int) -> dict[str, Any]:
    tid = str(action.get("tool_id") or "")
    cap = str(action.get("capability") or "")
    tool_ids = {str(t["tool_id"]) for t in case["tools"]}
    row = case["stage1"] if stage == 1 else case["stage2"]
    req = set(row["required_capabilities"])
    if tid not in tool_ids:
        raise ValueError("PROBE_UNKNOWN_TOOL")
    if cap not in req:
        raise ValueError("PROBE_IRRELEVANT_CAPABILITY")
    epoch = _current_epoch(case, stage, tid)
    supported = cap in _hidden_caps(case, stage, tid)
    return {
        "receipt_id": f"P-{case['case_id']}-{stage}-{seq}",
        "kind": "SAFE_CAPABILITY_PROBE",
        "stage": stage,
        "tool_id": tid,
        "capability": cap,
        "epoch": epoch,
        "supported": supported,
    }


def _selection_is_evidence_supported(
    case: Mapping[str, Any],
    stage: int,
    receipts: Sequence[Mapping[str, Any]],
    tool_id: str,
) -> bool:
    row = case["stage1"] if stage == 1 else case["stage2"]
    req = set(row["required_capabilities"])
    evidence = _valid_receipt_map(case, stage, receipts)
    return all(evidence.get((tool_id, cap)) is True for cap in req)


def execute_stage(
    case: Mapping[str, Any],
    stage: int,
    policy,
    receipts: list[dict[str, Any]],
    *,
    max_actions: int = 16,
) -> dict[str, Any]:
    seen_probe_keys: set[tuple[int, str, str, int]] = {
        (int(r["stage"]), str(r["tool_id"]), str(r["capability"]), int(r["epoch"]))
        for r in receipts
        if r.get("kind") == "SAFE_CAPABILITY_PROBE"
    }
    action_log = []
    for i in range(max_actions):
        public = _public_stage(case, stage, receipts)
        action = policy(public)
        if not isinstance(action, Mapping):
            return {"pass": False, "reason": "ACTION_NOT_MAPPING", "actions": action_log}
        kind = action.get("action")
        if kind == "PROBE":
            try:
                rec = _probe_receipt(case, stage, action, i)
            except Exception as exc:
                return {"pass": False, "reason": type(exc).__name__ + ":" + str(exc), "actions": action_log}
            key = (stage, rec["tool_id"], rec["capability"], rec["epoch"])
            if key in seen_probe_keys:
                return {"pass": False, "reason": "DUPLICATE_PROBE_SAME_EPOCH", "actions": action_log}
            seen_probe_keys.add(key)
            receipts.append(rec)
            action_log.append({"action": "PROBE", "tool_id": rec["tool_id"], "capability": rec["capability"], "epoch": rec["epoch"]})
            continue
        if kind == "SELECT":
            tid = str(action.get("tool_id") or "")
            expected = _oracle_best_tool(case, stage)
            if tid != expected:
                return {
                    "pass": False,
                    "reason": "NONOPTIMAL_OR_INSUFFICIENT_SELECTION",
                    "selected": tid,
                    "expected": expected,
                    "actions": action_log,
                }
            try:
                evidence_ok = _selection_is_evidence_supported(case, stage, receipts, tid)
            except Exception as exc:
                return {"pass": False, "reason": type(exc).__name__ + ":" + str(exc), "actions": action_log}
            if not evidence_ok:
                return {"pass": False, "reason": "SELECTION_WITHOUT_CURRENT_POSITIVE_EVIDENCE", "actions": action_log}
            action_log.append({"action": "SELECT", "tool_id": tid})
            return {
                "pass": True,
                "reason": "PASS",
                "selected": tid,
                "actions": action_log,
                "probe_count": sum(1 for x in action_log if x["action"] == "PROBE"),
            }
        return {"pass": False, "reason": "UNKNOWN_ACTION", "actions": action_log}
    return {"pass": False, "reason": "ACTION_BUDGET_EXHAUSTED", "actions": action_log}


def score_episode(case: Mapping[str, Any], policy) -> dict[str, Any]:
    receipts: list[dict[str, Any]] = []
    s1 = execute_stage(case, 1, policy, receipts)
    if not s1["pass"]:
        return {"schema": SCHEMA, "pass": False, "reason": "STAGE1_" + s1["reason"], "stage1": s1}
    s2 = execute_stage(case, 2, policy, receipts)
    if not s2["pass"]:
        return {"schema": SCHEMA, "pass": False, "reason": "STAGE2_" + s2["reason"], "stage1": s1, "stage2": s2}

    # Transfer requirement: unchanged evidence from stage 1 must be reused.
    # A probe may repeat only when a public version event advanced that tool's epoch.
    versioned = {str(x["tool_id"]) for x in case["stage2"].get("version_events", [])}
    s1_probes = {(x["tool_id"], x["capability"]) for x in s1["actions"] if x["action"] == "PROBE"}
    s2_probes = {(x["tool_id"], x["capability"]) for x in s2["actions"] if x["action"] == "PROBE"}
    repeated_without_change = sorted((s1_probes & s2_probes) - {(t, c) for t, c in s1_probes if t in versioned})
    if repeated_without_change:
        return {
            "schema": SCHEMA,
            "pass": False,
            "reason": "VALID_PRIOR_EVIDENCE_NOT_REUSED",
            "repeated": repeated_without_change,
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "reason": "PASS",
        "case_class": case["case_class"],
        "stage1": s1,
        "stage2": s2,
        "total_probes": s1["probe_count"] + s2["probe_count"],
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }


def run_batch(seed: int, case_count: int, policy) -> dict[str, Any]:
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
        "schema": "PROJECT_BRAIN_TOOL_DISCOVERY_INFORMATION_SAFE_PREFLIGHT_RESULT_V1",
        "seed": seed,
        "case_count": case_count,
        "passed": passed,
        "failed": case_count - passed,
        "all_pass": passed == case_count,
        "by_class": {
            cls: {
                "pass": v["pass"],
                "total": v["total"],
                "fraction": v["pass"] / v["total"] if v["total"] else 0.0,
                "reasons": dict(sorted(v["reasons"].items())),
            }
            for cls, v in sorted(by_class.items())
        },
        "failures": [x for x in rows if not x["pass"]],
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }
