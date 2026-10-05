"""P1 V6 executable causal cut-set kernel.

For trajectories whose causal semantics are explicit in the normalized IR, derive
minimal repair sets by executing the declared dependency semantics. This is not a
label oracle: a repair receives causal credit only when recomputing the graph
changes the terminal outcome from failed to successful.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Mapping

ALLOWED_KINDS = {
    "AUTHORITY", "SCOPE", "SCHEMA", "PROVENANCE", "INVARIANT",
    "STATE_TRANSITION", "TOOL_CONTRACT", "DEPENDENCY",
}
ALLOWED_COMPOSITION = {"SEQUENTIAL", "CONJUNCTIVE", "ALTERNATIVE"}
MAX_REPAIR_ATOMS = 16


def _list_str(v: Any) -> list[str] | None:
    if not isinstance(v, list) or any(not isinstance(x, str) or not x for x in v):
        return None
    return list(v)


def _parse(task: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str], dict[str, str]] | None:
    rows = task.get("trajectory")
    terminal = _list_str(task.get("terminal_failed_resources"))
    if not isinstance(rows, list) or not rows or terminal is None or not terminal:
        return None
    by_id: dict[str, dict[str, Any]] = {}
    last_writer: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            return None
        aid = row.get("action_id")
        deps = _list_str(row.get("depends_on"))
        reads = _list_str(row.get("reads"))
        writes = _list_str(row.get("writes"))
        comp = row.get("dependency_composition", "SEQUENTIAL")
        checks = row.get("checks")
        if (
            not isinstance(aid, str) or not aid or aid in by_id
            or deps is None or reads is None or writes is None
            or comp not in ALLOWED_COMPOSITION or not isinstance(checks, list)
            or any(d not in by_id for d in deps)
        ):
            return None
        normalized_checks = []
        seen_check_ids: set[str] = set()
        for check in checks:
            if not isinstance(check, Mapping):
                return None
            cid = check.get("id")
            kind = check.get("kind")
            passed = check.get("pass")
            evidence = _list_str(check.get("evidence"))
            if (
                not isinstance(cid, str) or not cid or cid in seen_check_ids
                or kind not in ALLOWED_KINDS or type(passed) is not bool
                or evidence is None or (passed is False and not evidence)
            ):
                return None
            seen_check_ids.add(cid)
            normalized_checks.append({
                "id": cid, "kind": kind, "pass": passed, "evidence": evidence,
            })
        all_deps = set(deps)
        for resource in reads:
            if resource in last_writer:
                all_deps.add(last_writer[resource])
        by_id[aid] = {
            "action_id": aid,
            "deps": tuple(sorted(all_deps)),
            "composition": comp,
            "checks": tuple(normalized_checks),
            "writes": tuple(writes),
        }
        for resource in writes:
            last_writer[resource] = aid
    if any(r not in last_writer for r in terminal):
        return None
    terminal_writers = {r: last_writer[r] for r in terminal}
    return by_id, terminal, terminal_writers


def _success(parsed: tuple[dict[str, dict[str, Any]], list[str], dict[str, str]], repaired: frozenset[str]) -> bool:
    by_id, terminal, terminal_writers = parsed
    available: dict[str, bool] = {}
    for aid, row in by_id.items():
        local_ok = all(c["pass"] or c["id"] in repaired for c in row["checks"])
        deps = row["deps"]
        if not deps:
            deps_ok = True
        elif row["composition"] == "ALTERNATIVE":
            deps_ok = any(available[d] for d in deps)
        else:
            deps_ok = all(available[d] for d in deps)
        available[aid] = local_ok and deps_ok
    return all(available[terminal_writers[r]] for r in terminal)


def _repair_atoms(by_id: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for aid, row in by_id.items():
        for check in row["checks"]:
            if check["pass"] is False:
                out.append({
                    "check_id": check["id"],
                    "action_id": aid,
                    "kind": check["kind"],
                    "repair_target": f"restore:{aid}:{check['kind']}:{check['id']}",
                    "evidence": list(check["evidence"]),
                })
    return out


def _minimal_rescue_sets(parsed, atoms: list[dict[str, Any]]) -> list[frozenset[str]]:
    ids = [a["check_id"] for a in atoms]
    if len(ids) > MAX_REPAIR_ATOMS:
        return []
    rescuers: list[frozenset[str]] = []
    for n in range(len(ids) + 1):
        for combo in combinations(ids, n):
            s = frozenset(combo)
            if any(prev.issubset(s) for prev in rescuers):
                continue
            if _success(parsed, s):
                rescuers.append(s)
    return rescuers


def solve(public_case: Mapping[str, Any]) -> dict[str, Any]:
    task = public_case.get("task")
    if not isinstance(task, Mapping):
        return {"status": "FAIL_CLOSED", "reason": "TASK_INVALID"}
    parsed = _parse(task)
    if parsed is None:
        return {"status": "FAIL_CLOSED", "reason": "TRAJECTORY_SEMANTICS_INVALID"}
    by_id, _, _ = parsed
    if _success(parsed, frozenset()):
        return {"status": "FAIL_CLOSED", "reason": "DECLARED_TERMINAL_FAILURE_NOT_REPRODUCED"}
    atoms = _repair_atoms(by_id)
    if not atoms:
        return {"status": "ESCALATE", "reason": "NO_EXECUTABLE_REPAIR_ATOMS"}
    if len(atoms) > MAX_REPAIR_ATOMS:
        return {"status": "ESCALATE", "reason": "REPAIR_SPACE_EXCEEDS_EXACT_BOUND"}
    rescuers = _minimal_rescue_sets(parsed, atoms)
    if not rescuers:
        return {"status": "ESCALATE", "reason": "NO_DECLARED_REPAIR_RESCUES_TERMINAL_OUTCOME"}

    atom_by_id = {a["check_id"]: a for a in atoms}

    def describe(s: frozenset[str]) -> dict[str, Any]:
        selected = [atom_by_id[cid] for cid in sorted(s)]
        return {
            "check_ids": sorted(s),
            "action_ids": sorted({x["action_id"] for x in selected}),
            "mechanism_classes": sorted({x["kind"] for x in selected}),
            "repair_targets": sorted(x["repair_target"] for x in selected),
            "supporting_receipts": sorted({e for x in selected for e in x["evidence"]}),
        }

    desc = [describe(s) for s in rescuers]
    if len(rescuers) > 1:
        return {
            "status": "AMBIGUOUS",
            "minimal_rescue_sets": desc,
            "reason": "MULTIPLE_DISTINCT_MINIMAL_EXECUTABLE_RESCUE_SETS",
            "information_request": "ACQUIRE_DISCRIMINATING_INTERVENTION_OR_STRONGER_CAUSAL_SEMANTICS",
        }

    d = desc[0]
    status = "IDENTIFIED" if len(d["check_ids"]) == 1 else "INTERACTION"
    return {
        "status": status,
        "cause_action_ids": d["action_ids"],
        "mechanism_classes": d["mechanism_classes"],
        "repair_targets": d["repair_targets"],
        "supporting_receipts": d["supporting_receipts"],
        "minimal_repair_check_ids": d["check_ids"],
        "reason": "UNIQUE_MINIMAL_EXECUTABLE_REPAIR_SET_RESCUES_TERMINAL_OUTCOME",
    }
