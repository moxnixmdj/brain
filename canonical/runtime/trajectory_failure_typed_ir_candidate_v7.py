"""P1 typed trajectory localizer V7: exact semantic repair-cutset inference.

V7 treats failure_semantics as load-bearing public information. DIRECT_CONTRACT
failures become repair variables; DERIVED_UPSTREAM failures never become roots.
The candidate compiles the visible trajectory DAG into a monotone health formula
and computes subset-minimal repair cutsets. It therefore handles serial co-faults,
conjunctive interactions, alternatives, delayed symptoms, and derived-only traces
without consulting hidden evaluator state.
"""
from __future__ import annotations
from typing import Any, Mapping

ALLOWED_KINDS = {
    "AUTHORITY", "SCHEMA", "PROVENANCE", "INVARIANT",
    "STATE_TRANSITION", "TOOL_CONTRACT", "DEPENDENCY", "SCOPE",
}
ALLOWED_FAILURE_SEMANTICS = {"DIRECT_CONTRACT", "DERIVED_UPSTREAM"}
MAX_MINIMAL_CUTSETS = 256


def _list_str(value: Any) -> list[str] | None:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        return None
    return list(value)


def _minimize(sets: list[frozenset[str]]) -> list[frozenset[str]]:
    unique = sorted(set(sets), key=lambda s: (len(s), tuple(sorted(s))))
    out: list[frozenset[str]] = []
    for item in unique:
        if any(prev.issubset(item) for prev in out):
            continue
        out.append(item)
        if len(out) > MAX_MINIMAL_CUTSETS:
            raise ValueError("CUTSET_FRONTIER_TOO_LARGE")
    return out


def _and_frontiers(parts: list[list[frozenset[str]]]) -> list[frozenset[str]]:
    acc = [frozenset()]
    for part in parts:
        acc = _minimize([a | b for a in acc for b in part])
    return acc


def _parse(public_case: Mapping[str, Any]) -> dict[str, Any]:
    task = public_case.get("task")
    if not isinstance(task, Mapping):
        raise ValueError("TASK_INVALID")
    rows = task.get("trajectory")
    terminal_failed = _list_str(task.get("terminal_failed_resources"))
    if not isinstance(rows, list) or not rows or terminal_failed is None or not terminal_failed:
        raise ValueError("TRAJECTORY_OR_TERMINAL_FAILURE_INVALID")

    by_id: dict[str, Mapping[str, Any]] = {}
    order: dict[str, int] = {}
    deps: dict[str, set[str]] = {}
    composition: dict[str, str] = {}
    direct_by_action: dict[str, list[dict[str, Any]]] = {}
    derived_by_action: dict[str, list[dict[str, Any]]] = {}
    last_writer: dict[str, str] = {}

    for idx, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError("TRAJECTORY_ROW_INVALID")
        aid = row.get("action_id")
        reads = _list_str(row.get("reads"))
        writes = _list_str(row.get("writes"))
        explicit = _list_str(row.get("depends_on"))
        comp = row.get("dependency_composition", "SEQUENTIAL")
        checks = row.get("checks")
        if (
            not isinstance(aid, str) or not aid or aid in by_id
            or reads is None or writes is None or explicit is None
            or comp not in {"SEQUENTIAL", "CONJUNCTIVE", "ALTERNATIVE"}
            or not isinstance(checks, list)
        ):
            raise ValueError("STEP_SCHEMA_INVALID")
        if any(d not in by_id for d in explicit):
            raise ValueError("NON_TOPOLOGICAL_DEPENDENCY")

        ds = set(explicit)
        for resource in reads:
            p = last_writer.get(resource)
            if p is not None:
                ds.add(p)

        direct: list[dict[str, Any]] = []
        derived: list[dict[str, Any]] = []
        for check in checks:
            if not isinstance(check, Mapping):
                raise ValueError("CHECK_INVALID")
            kind = check.get("kind")
            cid = check.get("id")
            passed = check.get("pass")
            evidence = _list_str(check.get("evidence"))
            if (
                kind not in ALLOWED_KINDS
                or not isinstance(cid, str) or not cid
                or type(passed) is not bool
                or evidence is None
            ):
                raise ValueError("CHECK_SCHEMA_INVALID")
            if passed:
                continue
            if not evidence:
                raise ValueError("FAILED_CHECK_WITHOUT_EVIDENCE")
            semantics = check.get("failure_semantics")
            if semantics not in ALLOWED_FAILURE_SEMANTICS:
                raise ValueError("FAILED_CHECK_SEMANTICS_MISSING_OR_INVALID")
            item = {
                "kind": kind,
                "id": cid,
                "evidence": list(evidence),
                "repair": f"restore:{aid}:{kind}",
            }
            if semantics == "DIRECT_CONTRACT":
                direct.append(item)
            else:
                derived.append(item)

        by_id[aid] = row
        order[aid] = idx
        deps[aid] = ds
        composition[aid] = comp
        direct_by_action[aid] = direct
        derived_by_action[aid] = derived
        for resource in writes:
            last_writer[resource] = aid

    missing = [r for r in terminal_failed if r not in last_writer]
    if missing:
        raise ValueError("TERMINAL_FAILED_RESOURCE_WITHOUT_PRODUCER")
    terminal_actions = {last_writer[r] for r in terminal_failed}
    if not terminal_actions:
        raise ValueError("NO_TERMINAL_ACTION")

    relevant: set[str] = set()
    stack = list(terminal_actions)
    while stack:
        aid = stack.pop()
        if aid in relevant:
            continue
        relevant.add(aid)
        stack.extend(deps[aid])

    return {
        "by_id": by_id, "order": order, "deps": deps, "composition": composition,
        "direct": direct_by_action, "derived": derived_by_action,
        "terminal_actions": terminal_actions, "relevant": relevant,
    }


def _cutsets(parsed: Mapping[str, Any]) -> list[frozenset[str]]:
    deps = parsed["deps"]
    comp = parsed["composition"]
    direct = parsed["direct"]
    memo: dict[str, list[frozenset[str]]] = {}

    def healthy_cutsets(aid: str) -> list[frozenset[str]]:
        if aid in memo:
            return memo[aid]
        own = frozenset(item["repair"] for item in direct[aid])
        parents = sorted(deps[aid])
        if not parents:
            dep_frontier = [frozenset()]
        elif comp[aid] == "ALTERNATIVE":
            dep_frontier = _minimize([s for parent in parents for s in healthy_cutsets(parent)])
        else:
            dep_frontier = _and_frontiers([healthy_cutsets(parent) for parent in parents])
        out = _minimize([own | s for s in dep_frontier])
        memo[aid] = out
        return out

    terminal_parts = [healthy_cutsets(a) for a in sorted(parsed["terminal_actions"])]
    return _and_frontiers(terminal_parts)


def _direct_detail(parsed: Mapping[str, Any], aid: str) -> dict[str, Any]:
    checks = parsed["direct"][aid]
    return {
        "action_id": aid,
        "mechanism_classes": sorted({x["kind"] for x in checks}),
        "supporting_receipts": sorted({e for x in checks for e in x["evidence"]}),
        "repair_targets": sorted({x["repair"] for x in checks}),
    }


def _repair_to_action(repair: str) -> str:
    parts = repair.split(":", 2)
    return parts[1] if len(parts) == 3 else ""


def solve(public_case: Mapping[str, Any]) -> dict[str, Any]:
    try:
        p = _parse(public_case)
        cutsets = _cutsets(p)
    except ValueError as exc:
        return {"status": "FAIL_CLOSED", "reason": str(exc)}

    relevant_direct_actions = sorted(
        [aid for aid in p["relevant"] if p["direct"][aid]],
        key=lambda x: p["order"][x],
    )

    if not relevant_direct_actions:
        return {
            "status": "AMBIGUOUS",
            "cause_action_id": None,
            "cause_action_ids": [],
            "critical_action_id": None,
            "candidates": [],
            "reason": "ONLY_DERIVED_FAILURES_VISIBLE__NO_DIRECT_CAUSAL_ROOT",
            "information_request": "ACQUIRE_UPSTREAM_DIRECT_FAILURE_EVIDENCE_OR_CAUSAL_DISCRIMINATOR",
        }

    cutsets = [s for s in cutsets if s]
    if not cutsets:
        return {"status": "FAIL_CLOSED", "reason": "NO_NONEMPTY_REPAIR_CUTSET"}

    if len(cutsets) > 1:
        union_actions = sorted(
            {_repair_to_action(r) for cs in cutsets for r in cs},
            key=lambda x: p["order"].get(x, 10**9),
        )
        candidates = []
        for cs in cutsets:
            actions = sorted(
                {_repair_to_action(r) for r in cs},
                key=lambda x: p["order"].get(x, 10**9),
            )
            candidates.append({
                "cause_action_ids": actions,
                "repair_targets": sorted(cs),
                "mechanism_by_action": {
                    aid: _direct_detail(p, aid)["mechanism_classes"] for aid in actions
                },
                "supporting_receipts": sorted({
                    e for aid in actions for e in _direct_detail(p, aid)["supporting_receipts"]
                }),
            })
        return {
            "status": "AMBIGUOUS",
            "cause_action_id": None,
            "cause_action_ids": union_actions,
            "critical_action_id": None,
            "candidates": candidates,
            "reason": "MULTIPLE_SUBSET_MINIMAL_REPAIR_CUTSETS_SURVIVE_VISIBLE_SEMANTICS",
            "information_request": "ACQUIRE_INTERVENTION_OR_ADDITIONAL_CAUSAL_DISCRIMINATOR",
        }

    cutset = cutsets[0]
    actions = sorted(
        {_repair_to_action(r) for r in cutset},
        key=lambda x: p["order"].get(x, 10**9),
    )
    if not actions:
        return {"status": "FAIL_CLOSED", "reason": "CUTSET_ACTION_MAPPING_INVALID"}

    if len(actions) == 1:
        aid = actions[0]
        detail = _direct_detail(p, aid)
        if sorted(cutset) != detail["repair_targets"]:
            return {"status": "FAIL_CLOSED", "reason": "ACTION_DIRECT_REPAIR_SET_MISMATCH"}
        return {
            "status": "IDENTIFIED",
            "cause_action_id": aid,
            "cause_action_ids": [aid],
            "critical_action_id": aid,
            "mechanism_classes": detail["mechanism_classes"],
            "supporting_receipts": detail["supporting_receipts"],
            "repair_targets": sorted(cutset),
            "reason": "UNIQUE_SUBSET_MINIMAL_VISIBLE_REPAIR_CUTSET",
        }

    details = [_direct_detail(p, aid) for aid in actions]
    witnesses = sorted(
        set(actions) | {
            aid for aid in p["relevant"] if p["composition"][aid] == "CONJUNCTIVE"
        },
        key=lambda x: p["order"][x],
    )
    return {
        "status": "INTERACTION",
        "cause_action_id": actions[0],
        "cause_action_ids": actions,
        "critical_action_id": actions[0],
        "interaction_witness_action_ids": witnesses,
        "mechanism_by_action": {d["action_id"]: d["mechanism_classes"] for d in details},
        "supporting_receipts": sorted({e for d in details for e in d["supporting_receipts"]}),
        "repair_targets": sorted(cutset),
        "reason": "UNIQUE_MULTI_ACTION_SUBSET_MINIMAL_VISIBLE_REPAIR_CUTSET",
    }
