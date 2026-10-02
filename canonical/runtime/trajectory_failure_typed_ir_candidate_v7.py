"""Typed cross-domain trajectory causal-localization candidate V7.

V7 replaces V6's "earliest failed ancestor" heuristic with a direct causal
cutset over the candidate-visible terminal causal slice.

Load-bearing rules:
* DERIVED_UPSTREAM failures are symptoms, never causal roots by themselves.
* DIRECT_CONTRACT failures remain independent faults even when another direct
  fault is their ancestor. A serial co-fault therefore requires the full direct
  repair set.
* Explicit ALTERNATIVE composition preserves non-identifiability.
* Explicit CONJUNCTIVE composition, or a serial chain of distinct direct faults,
  yields a joint causal repair set.
* Failed checks must explicitly declare failure_semantics. Missing/unknown
  semantics fail closed.

The candidate consumes no hidden oracle labels or intervention outcomes.
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
ALLOWED_FAILURE_SEMANTICS = {"DIRECT_CONTRACT", "DERIVED_UPSTREAM"}


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
        if not passed:
            semantics = item.get("failure_semantics")
            if semantics not in ALLOWED_FAILURE_SEMANTICS:
                return None
            if not evidence:
                return None
            out.append({
                "kind": kind,
                "id": cid,
                "evidence": evidence,
                "failure_semantics": semantics,
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

    deps: dict[str, set[str]] = {k: set(v) for k, v in explicit_deps.items()}
    last_writer: dict[str, str] = {}
    for row in rows:
        aid = str(row["action_id"])
        for resource in reads[aid]:
            p = last_writer.get(resource)
            if p is not None:
                deps[aid].add(p)
        for resource in writes[aid]:
            last_writer[resource] = aid

    terminal_actions = {last_writer[r] for r in terminal_failed if r in last_writer}
    if not terminal_actions:
        return {"status": "ESCALATE", "reason": "NO_PRODUCER_FOR_TERMINAL_FAILED_RESOURCE"}

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

    direct_failed: dict[str, list[dict[str, Any]]] = {}
    derived_failed: dict[str, list[dict[str, Any]]] = {}
    for aid in relevant_failed:
        direct = [x for x in failed[aid] if x["failure_semantics"] == "DIRECT_CONTRACT"]
        derived = [x for x in failed[aid] if x["failure_semantics"] == "DERIVED_UPSTREAM"]
        if direct:
            direct_failed[aid] = direct
        if derived:
            derived_failed[aid] = derived

    if not direct_failed:
        return {
            "status": "ESCALATE",
            "reason": "ONLY_DERIVED_UPSTREAM_FAILURES_VISIBLE__NO_DIRECT_CAUSAL_ROOT_PROVED",
        }

    direct_actions = sorted(direct_failed, key=lambda x: order[x])
    direct_set = set(direct_actions)

    def detail(aid: str) -> dict[str, Any]:
        checks = sorted(direct_failed[aid], key=lambda x: (x["kind"], x["id"]))
        kinds = sorted({x["kind"] for x in checks})
        evidence = sorted({e for x in checks for e in x["evidence"]})
        repairs = sorted({f"restore:{aid}:{x['kind']}" for x in checks})
        return {
            "action_id": aid,
            "mechanism_classes": kinds,
            "supporting_receipts": evidence,
            "repair_targets": repairs,
        }

    if len(direct_actions) == 1:
        root = direct_actions[0]
        d = detail(root)
        return {
            "status": "IDENTIFIED",
            "cause_action_id": root,
            "cause_action_ids": [root],
            "critical_action_id": root,
            "mechanism_classes": d["mechanism_classes"],
            "supporting_receipts": d["supporting_receipts"],
            "repair_targets": d["repair_targets"],
            "reason": "UNIQUE_DIRECT_CONTRACT_FAILURE_ON_TERMINAL_CAUSAL_SLICE",
        }

    # An explicit alternative merge spanning the direct faults is
    # observationally non-identifying: do not force a repair set.
    alternative_witnesses = []
    for aid in relevant:
        if composition[aid] != "ALTERNATIVE":
            continue
        span = ancestors(aid) | ({aid} if aid in direct_set else set())
        if direct_set.issubset(span):
            alternative_witnesses.append(aid)
    if alternative_witnesses:
        return {
            "status": "AMBIGUOUS",
            "cause_action_id": None,
            "cause_action_ids": direct_actions,
            "critical_action_id": None,
            "candidates": [detail(x) for x in direct_actions],
            "reason": "MULTIPLE_DIRECT_CONTRACT_FAILURES_SURVIVE_UNDER_VISIBLE_ALTERNATIVE_COMPOSITION",
            "information_request": "ACQUIRE_INTERVENTION_OR_ADDITIONAL_CAUSAL_DISCRIMINATOR",
        }

    conjunctive_witnesses = []
    for aid in relevant:
        if composition[aid] != "CONJUNCTIVE":
            continue
        span = ancestors(aid) | ({aid} if aid in direct_set else set())
        if direct_set.issubset(span):
            conjunctive_witnesses.append(aid)

    # A later DIRECT_CONTRACT failure is not a derived symptom. If another
    # direct fault is its ancestor, repairing only the ancestor cannot clear the
    # later direct check. Preserve both in the causal cutset.
    serial_witnesses = [
        aid for aid in direct_actions
        if ancestors(aid) & direct_set
    ]

    if conjunctive_witnesses or serial_witnesses:
        details = [detail(x) for x in direct_actions]
        witnesses = sorted(
            set(conjunctive_witnesses) | set(serial_witnesses),
            key=lambda x: order[x],
        )
        return {
            "status": "INTERACTION",
            "cause_action_id": direct_actions[0],
            "cause_action_ids": direct_actions,
            "critical_action_id": direct_actions[0],
            "interaction_witness_action_ids": witnesses,
            "mechanism_by_action": {
                d["action_id"]: d["mechanism_classes"] for d in details
            },
            "supporting_receipts": sorted({
                e for d in details for e in d["supporting_receipts"]
            }),
            "repair_targets": sorted({
                r for d in details for r in d["repair_targets"]
            }),
            "reason": (
                "MULTIPLE_DIRECT_CONTRACT_FAILURES_FORM_A_VISIBLE_CAUSAL_CUTSET__"
                "ALL_DIRECT_REPAIRS_REQUIRED_FOR_FORWARD_RESCUE"
            ),
        }

    return {
        "status": "AMBIGUOUS",
        "cause_action_id": None,
        "cause_action_ids": direct_actions,
        "critical_action_id": None,
        "candidates": [detail(x) for x in direct_actions],
        "reason": "MULTIPLE_DIRECT_CAUSES_WITHOUT_VISIBLE_JOINT_OR_ORDERED_RESCUE_PROOF",
        "information_request": "ACQUIRE_INTERVENTION_OR_ADDITIONAL_CAUSAL_DISCRIMINATOR",
    }
