"""Information-safe dynamic proof for TASK_TO_DELEGATION_GRAPH_001.

The candidate first plans from explicit task/worker contracts. Only after that plan
is fixed does it receive a live receipt that falsifies one worker or step
assumption. It must replan the remaining critical path without replaying completed
work, violating dependencies, assigning an incompatible worker, or losing receipt
provenance.

The hidden oracle contains only the independent optimum. It is never included in a
candidate-visible payload. This module grants no capability credit by itself.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations, permutations
import math
import random
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_DYNAMIC_DELEGATION_REASSIGNMENT_PROOF_V1"


def _valid_id(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _steps(task: Mapping[str, Any], receipt: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    disabled = set()
    if receipt and receipt.get("kind") == "STEP_UNAVAILABLE":
        disabled.add(str(receipt.get("entity_id")))
    out: dict[str, dict[str, Any]] = {}
    for row in task.get("steps", []):
        sid = row.get("id")
        if not _valid_id(sid) or sid in out:
            raise ValueError("STEP_ID_INVALID_OR_DUPLICATE")
        req = set(row.get("requires", []))
        prod = set(row.get("produces", []))
        cap = row.get("capability")
        cost = row.get("cost")
        if not prod or any(not _valid_id(x) for x in req | prod) or not _valid_id(cap):
            raise ValueError("STEP_CONTRACT_INVALID:" + str(sid))
        if not isinstance(cost, (int, float)) or isinstance(cost, bool) or not math.isfinite(float(cost)) or float(cost) < 0:
            raise ValueError("STEP_COST_INVALID:" + str(sid))
        out[str(sid)] = {
            "requires": req,
            "produces": prod,
            "capability": str(cap),
            "cost": float(cost),
            "available": sid not in disabled and row.get("available", True) is True,
        }
    return out


def _workers(task: Mapping[str, Any], receipt: Mapping[str, Any] | None = None) -> dict[str, set[str]]:
    unavailable: set[str] = set()
    removed: dict[str, set[str]] = defaultdict(set)
    if receipt:
        kind = receipt.get("kind")
        wid = str(receipt.get("entity_id") or "")
        if kind == "WORKER_UNAVAILABLE":
            unavailable.add(wid)
        elif kind == "WORKER_CAPABILITY_REMOVED":
            removed[wid].add(str(receipt.get("capability") or ""))
    out: dict[str, set[str]] = {}
    for row in task.get("workers", []):
        wid = row.get("id")
        if not _valid_id(wid) or wid in out:
            raise ValueError("WORKER_ID_INVALID_OR_DUPLICATE")
        if wid in unavailable:
            continue
        caps = {str(x) for x in row.get("capabilities", []) if _valid_id(x)}
        caps -= removed.get(str(wid), set())
        if not caps:
            continue
        out[str(wid)] = caps
    return out


def _facts_after_completed(task: Mapping[str, Any], completed: Sequence[str]) -> set[str]:
    steps = _steps(task)
    facts = set(task.get("initial_facts", []))
    seen: set[str] = set()
    for sid in completed:
        if sid not in steps or sid in seen:
            raise ValueError("COMPLETED_TASK_INVALID:" + str(sid))
        if not steps[sid]["requires"].issubset(facts):
            raise ValueError("COMPLETED_TASK_PRECONDITION_INVALID:" + str(sid))
        facts |= steps[sid]["produces"]
        seen.add(sid)
    return facts


def _optimal_plan(
    task: Mapping[str, Any],
    *,
    completed: Sequence[str] = (),
    receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    steps = _steps(task, receipt)
    initial = _facts_after_completed(task, completed)
    required = set(task.get("required_outputs", []))
    if not required:
        raise ValueError("REQUIRED_OUTPUTS_EMPTY")
    ids = sorted(sid for sid, row in steps.items() if row["available"] and sid not in set(completed))
    if len(ids) > 10:
        raise ValueError("STEP_BOUND_EXCEEDED")

    best = None
    for k in range(len(ids) + 1):
        for subset in combinations(ids, k):
            for order in permutations(subset):
                facts = set(initial)
                producer: dict[str, str] = {}
                deps: dict[str, list[str]] = {}
                ok = True
                for sid in order:
                    row = steps[sid]
                    if not row["requires"].issubset(facts):
                        ok = False
                        break
                    direct: set[str] = set()
                    for fact in row["requires"]:
                        if fact not in initial and fact in producer:
                            direct.add(producer[fact])
                    deps[sid] = sorted(direct)
                    for fact in row["produces"]:
                        if fact not in facts:
                            producer[fact] = sid
                    facts |= row["produces"]
                if not ok or not required.issubset(facts):
                    continue
                cost = sum(steps[sid]["cost"] for sid in order)
                key = (cost, len(order), tuple(order))
                if best is None or key < best[0]:
                    best = (key, {
                        "task_ids": list(order),
                        "dependencies": deps,
                        "total_cost": cost,
                    })
    if best is None:
        raise ValueError("NO_EXECUTABLE_PLAN")
    return best[1]


def _ready(completed: set[str], selected: set[str], deps: Mapping[str, Sequence[str]]) -> list[str]:
    return sorted(sid for sid in selected - completed if set(deps[sid]).issubset(completed))


def _wave_matchings(ready: Sequence[str], steps: Mapping[str, Mapping[str, Any]], workers: Mapping[str, set[str]]):
    for k in range(1, min(len(ready), len(workers)) + 1):
        for tasks in combinations(ready, k):
            for worker_ids in permutations(sorted(workers), k):
                pairs = dict(zip(tasks, worker_ids))
                if all(steps[sid]["capability"] in workers[wid] for sid, wid in pairs.items()):
                    yield pairs


def _minimum_waves(
    task: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    receipt: Mapping[str, Any] | None = None,
) -> int:
    steps = _steps(task, receipt)
    workers = _workers(task, receipt)
    selected = set(plan["task_ids"])
    deps = plan["dependencies"]
    frontier = {frozenset(): 0}
    seen = {frozenset()}
    while frontier:
        nxt = {}
        for state, depth in frontier.items():
            completed = set(state)
            if completed == selected:
                return depth
            ready = _ready(completed, selected, deps)
            for pairs in _wave_matchings(ready, steps, workers):
                ns = frozenset(completed | set(pairs))
                if ns not in seen:
                    seen.add(ns)
                    nxt[ns] = depth + 1
        frontier = nxt
    raise ValueError("NO_FEASIBLE_WORKER_SCHEDULE")


def _validate_schedule(
    task: Mapping[str, Any],
    candidate: Mapping[str, Any],
    optimum: Mapping[str, Any],
    *,
    receipt: Mapping[str, Any] | None = None,
) -> tuple[bool, str]:
    steps = _steps(task, receipt)
    workers = _workers(task, receipt)
    ids = candidate.get("task_ids")
    deps = candidate.get("dependencies")
    assignment = candidate.get("assignment")
    waves = candidate.get("waves")

    if not isinstance(ids, list) or len(ids) != len(set(ids)):
        return False, "TASK_IDS_INVALID"
    if ids != optimum["task_ids"]:
        return False, "NONOPTIMAL_OR_INCOMPLETE_TASK_SEQUENCE"
    if not isinstance(deps, Mapping) or deps != optimum["dependencies"]:
        return False, "DEPENDENCY_GRAPH_MISMATCH"
    if not isinstance(assignment, Mapping) or set(assignment) != set(ids):
        return False, "ASSIGNMENT_INVALID"
    for sid, wid in assignment.items():
        if wid not in workers or sid not in steps or steps[sid]["capability"] not in workers[wid]:
            return False, "WORKER_CAPABILITY_MISMATCH"
    if not isinstance(waves, list) or (ids and not waves):
        return False, "WAVES_INVALID"

    completed: set[str] = set()
    seen: set[str] = set()
    for wave in waves:
        if not isinstance(wave, list) or not wave or len(wave) != len(set(wave)):
            return False, "WAVE_INVALID"
        used_workers: set[str] = set()
        for sid in wave:
            if sid not in ids or sid in seen:
                return False, "WAVE_TASK_INVALID_OR_DUPLICATE"
            if not set(deps[sid]).issubset(completed):
                return False, "WAVE_DEPENDENCY_VIOLATION"
            wid = assignment[sid]
            if wid in used_workers:
                return False, "WORKER_DOUBLE_BOOKED"
            used_workers.add(wid)
        completed |= set(wave)
        seen |= set(wave)
    if seen != set(ids):
        return False, "WAVE_COVERAGE_INCOMPLETE"
    if len(waves) != _minimum_waves(task, optimum, receipt=receipt):
        return False, "NONOPTIMAL_PARALLEL_WAVE_COUNT"
    return True, "PASS"


def _score_stage(
    task: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    completed: Sequence[str] = (),
    receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        optimum = _optimal_plan(task, completed=completed, receipt=receipt)
        ok, reason = _validate_schedule(task, candidate, optimum, receipt=receipt)
        return {
            "pass": ok,
            "reason": reason,
            "oracle_task_ids": optimum["task_ids"],
            "oracle_total_cost": optimum["total_cost"],
            "oracle_min_waves": _minimum_waves(task, optimum, receipt=receipt),
        }
    except Exception as exc:
        return {"pass": False, "reason": type(exc).__name__ + ":" + str(exc)}


def generate_case(seed: int, ordinal: int) -> dict[str, Any]:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("SEED")
    if not isinstance(ordinal, int) or ordinal < 0:
        raise ValueError("ORDINAL")
    r = random.Random((seed << 17) ^ ordinal ^ 0xD311)
    suffix = str(r.randrange(1000, 9999))
    raw, x, y, z, final = (f"RAW_{suffix}", f"X_{suffix}", f"Y_{suffix}", f"Z_{suffix}", f"FINAL_{suffix}")
    parse, reason, retrieve, integrate, review = (
        f"PARSE_{suffix}", f"REASON_{suffix}", f"RETRIEVE_{suffix}", f"INTEGRATE_{suffix}", f"REVIEW_{suffix}"
    )
    a, b, b2, c, d = (f"A_{suffix}", f"B_{suffix}", f"B2_{suffix}", f"C_{suffix}", f"D_{suffix}")
    w1, w2, w3, w4 = (f"W1_{suffix}", f"W2_{suffix}", f"W3_{suffix}", f"W4_{suffix}")

    task = {
        "initial_facts": [raw],
        "required_outputs": [final],
        "steps": [
            {"id": a, "requires": [raw], "produces": [x], "cost": 1, "capability": parse},
            {"id": b, "requires": [x], "produces": [y], "cost": 1, "capability": reason},
            {"id": b2, "requires": [x], "produces": [y], "cost": 3, "capability": review},
            {"id": c, "requires": [x], "produces": [z], "cost": 1, "capability": retrieve},
            {"id": d, "requires": [y, z], "produces": [final], "cost": 1, "capability": integrate},
        ],
        "workers": [
            {"id": w1, "capabilities": [parse, reason]},
            {"id": w2, "capabilities": [retrieve, integrate]},
            {"id": w3, "capabilities": [retrieve, integrate]},
            {"id": w4, "capabilities": [review]},
        ],
    }
    cls = ("WORKER_UNAVAILABLE", "STEP_UNAVAILABLE", "WORKER_CAPABILITY_REMOVED")[ordinal % 3]
    if cls == "WORKER_UNAVAILABLE":
        receipt = {
            "receipt_id": f"R-{seed}-{ordinal}",
            "kind": cls,
            "entity_id": w2,
            "completed_task_ids": [a],
            "observed": f"{w2} became unavailable after {a} completed",
        }
    elif cls == "STEP_UNAVAILABLE":
        receipt = {
            "receipt_id": f"R-{seed}-{ordinal}",
            "kind": cls,
            "entity_id": b,
            "completed_task_ids": [a],
            "observed": f"{b} became unavailable after {a} completed",
        }
    else:
        receipt = {
            "receipt_id": f"R-{seed}-{ordinal}",
            "kind": cls,
            "entity_id": w2,
            "capability": integrate,
            "completed_task_ids": [a],
            "observed": f"{w2} lost capability {integrate} after {a} completed",
        }

    return {
        "schema": SCHEMA,
        "case_id": f"DELEGATION-DYNAMIC-{seed}-{ordinal}",
        "case_class": cls,
        "task": task,
        "_oracle": {"receipt": receipt},
    }


def public_initial(case: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": case["schema"],
        "case_id": case["case_id"],
        "task": case["task"],
    }


def public_after_receipt(case: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": case["schema"],
        "case_id": case["case_id"],
        "task": case["task"],
        "receipt": dict(case["_oracle"]["receipt"]),
    }


def score_episode(
    case: Mapping[str, Any],
    initial_candidate: Mapping[str, Any],
    revised_candidate: Mapping[str, Any],
) -> dict[str, Any]:
    initial = _score_stage(case["task"], initial_candidate)
    if not initial["pass"]:
        return {"schema": SCHEMA, "pass": False, "reason": "INITIAL_" + initial["reason"], "initial": initial}

    receipt = case["_oracle"]["receipt"]
    completed = list(receipt["completed_task_ids"])
    revised_ids = revised_candidate.get("task_ids")
    if not isinstance(revised_ids, list):
        return {"schema": SCHEMA, "pass": False, "reason": "REVISED_TASK_IDS_INVALID"}
    if set(completed) & set(revised_ids):
        return {"schema": SCHEMA, "pass": False, "reason": "COMPLETED_WORK_REPLAYED"}
    if revised_candidate.get("receipt_id") != receipt["receipt_id"]:
        return {"schema": SCHEMA, "pass": False, "reason": "RECEIPT_PROVENANCE_MISSING"}
    prov = revised_candidate.get("revision_provenance")
    expected_prov = {
        "kind": receipt["kind"],
        "entity_id": receipt["entity_id"],
        "completed_task_ids": completed,
    }
    if receipt.get("capability") is not None:
        expected_prov["capability"] = receipt["capability"]
    if prov != expected_prov:
        return {"schema": SCHEMA, "pass": False, "reason": "REVISION_PROVENANCE_MISMATCH"}

    revised = _score_stage(case["task"], revised_candidate, completed=completed, receipt=receipt)
    if not revised["pass"]:
        return {"schema": SCHEMA, "pass": False, "reason": "REVISED_" + revised["reason"], "initial": initial, "revised": revised}

    changed = initial_candidate.get("task_ids") != revised_candidate.get("task_ids") or initial_candidate.get("assignment") != revised_candidate.get("assignment")
    if not changed:
        return {"schema": SCHEMA, "pass": False, "reason": "RECEIPT_DID_NOT_CHANGE_PLAN_OR_ASSIGNMENT"}

    return {
        "schema": SCHEMA,
        "pass": True,
        "reason": "PASS",
        "case_class": case["case_class"],
        "initial": initial,
        "revised": revised,
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }


def run_batch(seed: int, case_count: int, initial_solver, update_solver) -> dict[str, Any]:
    rows = []
    by_class = defaultdict(lambda: {"pass": 0, "total": 0, "reasons": defaultdict(int)})
    for ordinal in range(case_count):
        case = generate_case(seed, ordinal)
        try:
            first = initial_solver(public_initial(case))
            second = update_solver(public_after_receipt(case), first)
            verdict = score_episode(case, first, second)
        except Exception as exc:
            verdict = {"pass": False, "reason": "CANDIDATE_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)}
        cls = case["case_class"]
        by_class[cls]["total"] += 1
        by_class[cls]["pass"] += int(bool(verdict["pass"]))
        by_class[cls]["reasons"][verdict["reason"]] += 1
        rows.append({"case_id": case["case_id"], "class": cls, "pass": bool(verdict["pass"]), "reason": verdict["reason"]})

    passed = sum(int(x["pass"]) for x in rows)
    summary = {
        cls: {
            "pass": val["pass"],
            "total": val["total"],
            "fraction": val["pass"] / val["total"] if val["total"] else 0.0,
            "reasons": dict(sorted(val["reasons"].items())),
        }
        for cls, val in sorted(by_class.items())
    }
    return {
        "schema": "PROJECT_BRAIN_DYNAMIC_DELEGATION_REASSIGNMENT_PREFLIGHT_RESULT_V1",
        "seed": seed,
        "case_count": case_count,
        "passed": passed,
        "failed": case_count - passed,
        "all_pass": passed == case_count,
        "by_class": summary,
        "failures": [x for x in rows if not x["pass"]],
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }
