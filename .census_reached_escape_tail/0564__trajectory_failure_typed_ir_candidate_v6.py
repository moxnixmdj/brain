"""Typed cross-domain trajectory causal-localization candidate V6.

The candidate receives only normalized trajectory IR, declared contracts/check
results, dependency/resource flow, terminal failed resources, and explicit
composition semantics. Hidden cause labels and intervention outcomes are never
visible.

It localizes root violated steps by backward causal relevance, rejects downstream
symptoms, classifies the violated contract mechanism, preserves ambiguity when
multiple independent roots survive, and emits conjunctive cause sets only when
the visible dependency graph explicitly requires the roots jointly.
"""
from __future__ import annotations
from typing import Any, Mapping


ALLOWED_KINDS = {
    "AUTHORITY",
    "SCHEMA",
    "PROVENANCE",
    "INVARIANT",
    "STATE_TRANSITION",
    "TOOL_CONTRACT",
    "DEPENDENCY",
    "SCOPE",
}


def _list_str(value: Any) -> list[str] | None:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        return None
    return list(value)


def _failed_checks(row: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    checks = row.get("checks")
    if not isinstance(checks, list):
        return None
    out: list[dict[str, Any]] = []
    for item in checks:
        if not isinstance(item, Mapping):
            return None
        kind = item.get("kind")
        cid = item.get("id")
        passed = item.get("pass")
        evidence = _list_str(item.get("evidence"))
        if kind not in ALLOWED_KINDS or not isinstance(cid, str) or not cid:
            return None
        if type(passed) is not bool or evidence is None:
            return None
        if not passed and not evidence:
            return None
        if not passed:
            out.append({
                "kind": kind,
                "id": cid,
                "evidence": evidence,
            })
    return out


def solve(public_case: Mapping[str, Any]) -> dict[str, Any]:
    task = public_case.get("task")
    if not isinstance(task, Mapping):
        return {"status": "FAIL_CLOSED", "reason": "TASK_INVALID"}
    rows = task.get("trajectory")
    terminal_failed = _list_str(task.get("terminal_failed_resources"))
    if not isinstance(rows, list) or not rows or terminal_failed is None or not terminal_failed:
        return {"status": "FAIL_CLOSED", "reason": "TRAJECTORY_OR_TERMINAL_FAILURE_INVALID"}

    by_id: dict[str, Mapping[str, Any]] = {}
    order: dict[str, int] = {}
    failed: dict[str, list[dict[str, Any]]] = {}
    reads: dict[str, set[str]] = {}
    writes: dict[str, set[str]] = {}
    explicit_deps: dict[str, set[str]] = {}
    composition: dict[str, str] = {}

    for idx, row in enumerate(rows):
        if not isinstance(row, Mapping):
            return {"status": "FAIL_CLOSED", "reason": "TRAJECTORY_ROW_INVALID"}
        aid = row.get("action_id")
        rds = _list_str(row.get("reads"))
        wrs = _list_str(row.get("writes"))
        deps = _list_str(row.get("depends_on"))
        comp = row.get("dependency_composition", "SEQUENTIAL")
        fc = _failed_checks(row)
        if (
            not isinstance(aid, str) or not aid or aid in by_id
            or rds is None or wrs is None or deps is None or fc is None
            or comp not in {"SEQUENTIAL", "CONJUNCTIVE", "ALTERNATIVE"}
        ):
            return {"status": "FAIL_CLOSED", "reason": "STEP_SCHEMA_INVALID"}
        if any(d not in by_id for d in deps):
            return {"status": "FAIL_CLOSED", "reason": "NON_TOPOLOGICAL_DEPENDENCY"}
        by_id[aid] = row
        order[aid] = idx
        failed[aid] = fc
        reads[aid] = set(rds)
        writes[aid] = set(wrs)
        explicit_deps[aid] = set(deps)
        composition[aid] = comp

    # Add dataflow edges from the latest prior producer of every read resource.
    deps: dict[str, set[str]] = {k: set(v) for k, v in explicit_deps.items()}
    last_writer: dict[str, str] = {}
    for row in rows:
        aid = row["action_id"]
        for resource in reads[aid]:
            p = last_writer.get(resource)
            if p is not None:
                deps[aid].add(p)
        for resource in writes[aid]:
            last_writer[resource] = aid

    # Actions directly responsible for the terminal failed resources.
    terminal_actions = {
        last_writer[r] for r in terminal_failed
        if r in last_writer
    }
    if not terminal_actions:
        return {"status": "ESCALATE", "reason": "NO_PRODUCER_FOR_TERMINAL_FAILED_RESOURCE"}

    # Backward causal slice from terminal actions.
    relevant: set[str] = set()
    stack = list(terminal_actions)
    while stack:
        aid = stack.pop()
        if aid in relevant:
            continue
        relevant.add(aid)
        stack.extend(deps[aid])

    relevant_failed = {aid for aid in relevant if failed[aid]}
    if not relevant_failed:
        return {"status": "ESCALATE", "reason": "NO_CONTRACT_VIOLATION_ON_TERMINAL_CAUSAL_SLICE"}

    # Ancestors restricted to relevant failed steps.
    ancestor_cache: dict[str, set[str]] = {}
    def ancestors(aid: str) -> set[str]:
        if aid in ancestor_cache:
            return ancestor_cache[aid]
        out: set[str] = set()
        todo = list(deps[aid])
        while todo:
            x = todo.pop()
            if x in out:
                continue
            out.add(x)
            todo.extend(deps[x])
        ancestor_cache[aid] = out
        return out

    roots = sorted(
        [
            aid for aid in relevant_failed
            if not (ancestors(aid) & relevant_failed)
        ],
        key=lambda x: order[x],
    )
    if not roots:
        return {"status": "FAIL_CLOSED", "reason": "NO_ROOT_VIOLATION"}

    def detail(aid: str) -> dict[str, Any]:
        checks = sorted(failed[aid], key=lambda x: (x["kind"], x["id"]))
        kinds = sorted({x["kind"] for x in checks})
        evidence = sorted({e for x in checks for e in x["evidence"]})
        repairs = sorted({f"restore:{aid}:{x['kind']}" for x in checks})
        return {
            "action_id": aid,
            "mechanism_classes": kinds,
            "supporting_receipts": evidence,
            "repair_targets": repairs,
        }

    if len(roots) == 1:
        root = roots[0]
        d = detail(root)
        return {
            "status": "IDENTIFIED",
            "cause_action_id": root,
            "cause_action_ids": [root],
            "critical_action_id": root,
            "mechanism_classes": d["mechanism_classes"],
            "supporting_receipts": d["supporting_receipts"],
            "repair_targets": d["repair_targets"],
            "reason": "UNIQUE_ROOT_CONTRACT_VIOLATION_ON_TERMINAL_CAUSAL_SLICE",
        }

    # A visible conjunctive downstream dependency can establish that multiple
    # independent root violations jointly form the causal repair set.
    root_set = set(roots)
    conjunctive_witnesses = []
    for aid in relevant:
        if composition[aid] != "CONJUNCTIVE":
            continue
        if root_set.issubset(ancestors(aid) | ({aid} if aid in root_set else set())):
            conjunctive_witnesses.append(aid)

    if conjunctive_witnesses:
        details = [detail(x) for x in roots]
        return {
            "status": "INTERACTION",
            "cause_action_id": roots[0],
            "cause_action_ids": roots,
            "critical_action_id": roots[0],
            "interaction_witness_action_ids": sorted(conjunctive_witnesses, key=lambda x: order[x]),
            "mechanism_by_action": {d["action_id"]: d["mechanism_classes"] for d in details},
            "supporting_receipts": sorted({e for d in details for e in d["supporting_receipts"]}),
            "repair_targets": sorted({r for d in details for r in d["repair_targets"]}),
            "reason": "MULTIPLE_ROOT_VIOLATIONS_JOIN_UNDER_VISIBLE_CONJUNCTIVE_DEPENDENCY",
        }

    return {
        "status": "AMBIGUOUS",
        "cause_action_id": None,
        "cause_action_ids": roots,
        "critical_action_id": None,
        "candidates": [detail(x) for x in roots],
        "reason": "MULTIPLE_INDEPENDENT_ROOT_CAUSES_SURVIVE_WITHOUT_DISCRIMINATOR",
        "information_request": "ACQUIRE_INTERVENTION_OR_ADDITIONAL_CAUSAL_DISCRIMINATOR",
    }
