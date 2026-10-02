"""P1 typed causal proof V6 with execution-based hidden intervention replay.

V5's causal classifier is preserved. The rescue evaluator is replaced: repair
labels are applied to hidden injected root faults and the public trajectory graph
is re-executed to the declared terminal resources. A missing/corrupt task,
trajectory, dependency, fault witness, or terminal producer fails closed.

This remains zero-terminal-evidence prewave proof. It cannot grant terminal,
capability, family, execution, or promotion authority by itself.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as v5

SCHEMA = "PROJECT_BRAIN_TRAJECTORY_CAUSAL_IR_PROOF_V6"
DOMAINS = v5.DOMAINS
KINDS = v5.KINDS
PATTERNS = ("SINGLE", "DELAYED", "INTERACTION", "AMBIGUOUS")

_ALLOWED_KEYS = {
    "IDENTIFIED": {
        "status", "cause_action_id", "cause_action_ids", "critical_action_id",
        "mechanism_classes", "supporting_receipts", "repair_targets", "reason",
    },
    "INTERACTION": {
        "status", "cause_action_id", "cause_action_ids", "critical_action_id",
        "interaction_witness_action_ids", "mechanism_by_action",
        "supporting_receipts", "repair_targets", "reason",
    },
    "AMBIGUOUS": {
        "status", "cause_action_id", "cause_action_ids", "critical_action_id",
        "candidates", "reason", "information_request",
    },
}


def _list_str(value: Any) -> list[str] | None:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        return None
    return list(value)


def generate_case(
    seed: int,
    *,
    pattern: str | None = None,
    domain: str | None = None,
    kind: str | None = None,
) -> dict[str, Any]:
    case = copy.deepcopy(v5.generate_case(seed, pattern=pattern, domain=domain, kind=kind))
    oracle = case["_oracle"]
    case.pop("_intervention_model", None)
    case["_fault_injections"] = sorted(
        [
            {"action_id": aid, "kind": mechanism}
            for aid, mechanisms in oracle["mechanisms"].items()
            for mechanism in mechanisms
        ],
        key=lambda x: (x["action_id"], x["kind"]),
    )
    case["schema"] = SCHEMA
    return case


def public_task(case: Mapping[str, Any]) -> dict[str, Any]:
    return {k: copy.deepcopy(v) for k, v in case.items() if not str(k).startswith("_")}


def _repair_target(aid: str, kind: str) -> str:
    return f"restore:{aid}:{kind}"


def _expected_root_repairs(case: Mapping[str, Any]) -> list[str]:
    oracle = case["_oracle"]
    return sorted(
        _repair_target(str(aid), str(kind))
        for aid, kinds in oracle["mechanisms"].items()
        for kind in kinds
    )


def _symptom_targets(case: Mapping[str, Any]) -> list[str]:
    roots = set(case["_oracle"]["roots"])
    out: set[str] = set()
    task = case.get("task")
    if not isinstance(task, Mapping):
        return []
    rows = task.get("trajectory")
    if not isinstance(rows, list):
        return []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        aid = row.get("action_id")
        if not isinstance(aid, str) or aid in roots:
            continue
        checks = row.get("checks")
        if not isinstance(checks, list):
            continue
        for check in checks:
            if (
                isinstance(check, Mapping)
                and check.get("pass") is False
                and isinstance(check.get("kind"), str)
            ):
                out.add(_repair_target(aid, str(check["kind"])))
    return sorted(out)


def execute_after_intervention(
    case: Mapping[str, Any],
    repair_targets: list[str],
) -> dict[str, Any]:
    """Apply repairs and re-execute the hidden fault model over the trajectory."""
    task = case.get("task")
    if not isinstance(task, Mapping):
        return {"valid": False, "rescued": False, "reason": "TASK_MISSING_OR_INVALID"}

    rows = task.get("trajectory")
    terminal_failed = _list_str(task.get("terminal_failed_resources"))
    if not isinstance(rows, list) or not rows or terminal_failed is None or not terminal_failed:
        return {"valid": False, "rescued": False, "reason": "TRAJECTORY_OR_TERMINAL_INVALID"}

    injections = case.get("_fault_injections")
    if not isinstance(injections, list) or not injections:
        return {"valid": False, "rescued": False, "reason": "HIDDEN_FAULT_INJECTIONS_MISSING"}

    by_id: dict[str, Mapping[str, Any]] = {}
    deps: dict[str, set[str]] = {}
    composition: dict[str, str] = {}
    reads: dict[str, set[str]] = {}
    writes: dict[str, set[str]] = {}
    failed_checks: dict[str, set[str]] = {}

    for row in rows:
        if not isinstance(row, Mapping):
            return {"valid": False, "rescued": False, "reason": "ROW_INVALID"}
        aid = row.get("action_id")
        rds = _list_str(row.get("reads"))
        wrs = _list_str(row.get("writes"))
        explicit = _list_str(row.get("depends_on"))
        comp = row.get("dependency_composition", "SEQUENTIAL")
        checks = row.get("checks")
        if (
            not isinstance(aid, str) or not aid or aid in by_id
            or rds is None or wrs is None or explicit is None
            or comp not in {"SEQUENTIAL", "CONJUNCTIVE", "ALTERNATIVE"}
            or not isinstance(checks, list)
            or any(d not in by_id for d in explicit)
        ):
            return {"valid": False, "rescued": False, "reason": "ROW_SCHEMA_OR_TOPOLOGY_INVALID"}

        failed: set[str] = set()
        for check in checks:
            if not isinstance(check, Mapping):
                return {"valid": False, "rescued": False, "reason": "CHECK_INVALID"}
            kind = check.get("kind")
            passed = check.get("pass")
            evidence = _list_str(check.get("evidence"))
            if kind not in KINDS or type(passed) is not bool or evidence is None:
                return {"valid": False, "rescued": False, "reason": "CHECK_SCHEMA_INVALID"}
            if passed is False:
                if not evidence:
                    return {"valid": False, "rescued": False, "reason": "FAILED_CHECK_WITHOUT_EVIDENCE"}
                failed.add(str(kind))

        by_id[aid] = row
        deps[aid] = set(explicit)
        composition[aid] = str(comp)
        reads[aid] = set(rds)
        writes[aid] = set(wrs)
        failed_checks[aid] = failed

    # Reconstruct dataflow edges from the actual trajectory being evaluated.
    last_writer: dict[str, str] = {}
    for row in rows:
        aid = str(row["action_id"])
        for resource in reads[aid]:
            producer = last_writer.get(resource)
            if producer is not None:
                deps[aid].add(producer)
        for resource in writes[aid]:
            last_writer[resource] = aid

    terminal_actions: list[str] = []
    for resource in terminal_failed:
        producer = last_writer.get(resource)
        if producer is None:
            return {"valid": False, "rescued": False, "reason": "TERMINAL_RESOURCE_HAS_NO_PRODUCER"}
        terminal_actions.append(producer)

    hidden_faults: set[tuple[str, str]] = set()
    for item in injections:
        if not isinstance(item, Mapping):
            return {"valid": False, "rescued": False, "reason": "FAULT_INJECTION_INVALID"}
        aid = item.get("action_id")
        kind = item.get("kind")
        if not isinstance(aid, str) or kind not in KINDS or aid not in by_id:
            return {"valid": False, "rescued": False, "reason": "FAULT_INJECTION_SCHEMA_INVALID"}
        # Hidden injections must be visibly witnessed by a failed check in the task.
        if str(kind) not in failed_checks[aid]:
            return {"valid": False, "rescued": False, "reason": "FAULT_NOT_WITNESSED_BY_VISIBLE_CHECK"}
        hidden_faults.add((aid, str(kind)))

    valid_targets: set[str] = set()
    for aid, kinds in failed_checks.items():
        for kind in kinds:
            valid_targets.add(_repair_target(aid, kind))

    repairs = {str(x) for x in repair_targets}
    if any(x not in valid_targets for x in repairs):
        return {"valid": False, "rescued": False, "reason": "REPAIR_TARGET_NOT_A_VISIBLE_FAILED_CHECK"}

    repaired_faults = {
        (aid, kind)
        for aid, kind in hidden_faults
        if _repair_target(aid, kind) in repairs
    }
    active_faults = hidden_faults - repaired_faults

    unhealthy: dict[str, bool] = {}
    for row in rows:
        aid = str(row["action_id"])
        local_fault = any(faid == aid for faid, _ in active_faults)
        dep_states = [unhealthy[d] for d in deps[aid]]
        comp = composition[aid]
        if comp in {"SEQUENTIAL", "CONJUNCTIVE"}:
            dependency_failure = any(dep_states)
        else:  # ALTERNATIVE: at least one healthy alternative is sufficient.
            dependency_failure = bool(dep_states) and all(dep_states)
        unhealthy[aid] = local_fault or dependency_failure

    terminal_is_failed = any(unhealthy[aid] for aid in terminal_actions)
    return {
        "valid": True,
        "rescued": not terminal_is_failed,
        "reason": "TERMINAL_RESCUED" if not terminal_is_failed else "TERMINAL_STILL_FAILED",
        "terminal_failed": terminal_is_failed,
        "active_hidden_faults": sorted([list(x) for x in active_faults]),
        "terminal_action_ids": sorted(set(terminal_actions)),
        "unhealthy_action_ids": sorted([aid for aid, bad in unhealthy.items() if bad]),
    }


def score_case(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(candidate, Mapping):
        return {"pass": False, "reason": "CANDIDATE_NOT_OBJECT"}
    oracle = case.get("_oracle")
    if not isinstance(oracle, Mapping):
        return {"pass": False, "reason": "ORACLE_MISSING"}

    status = candidate.get("status")
    if status not in _ALLOWED_KEYS:
        return {"pass": False, "reason": "STATUS_WRONG_OR_FAIL_CLOSED"}
    if set(candidate.keys()) != _ALLOWED_KEYS[str(status)]:
        return {"pass": False, "reason": "OUTPUT_SCHEMA_NOT_EXACT"}

    got_roots = candidate.get("cause_action_ids")
    if not isinstance(got_roots, list):
        return {"pass": False, "reason": "CAUSE_SET_INVALID"}
    roots = sorted(str(x) for x in got_roots)
    expected = sorted(str(x) for x in oracle["roots"])
    if status != oracle["status"] or roots != expected:
        return {"pass": False, "reason": "STATUS_OR_ROOT_SET_WRONG"}
    if candidate.get("critical_action_id") != oracle["critical"]:
        return {"pass": False, "reason": "CRITICAL_ACTION_WRONG"}

    if status == "IDENTIFIED":
        critical = str(oracle["critical"])
        if candidate.get("cause_action_id") != critical:
            return {"pass": False, "reason": "UNIQUE_CAUSE_WRONG"}
        if candidate.get("mechanism_classes") != oracle["mechanisms"][critical]:
            return {"pass": False, "reason": "MECHANISM_CLASS_WRONG"}
        if not candidate.get("supporting_receipts"):
            return {"pass": False, "reason": "SUPPORTING_RECEIPTS_REQUIRED"}
    elif status == "INTERACTION":
        if candidate.get("mechanism_by_action") != oracle["mechanisms"]:
            return {"pass": False, "reason": "INTERACTION_MECHANISMS_WRONG"}
        if not candidate.get("supporting_receipts"):
            return {"pass": False, "reason": "SUPPORTING_RECEIPTS_REQUIRED"}
    else:
        if candidate.get("cause_action_id") is not None:
            return {"pass": False, "reason": "NONIDENTIFIABILITY_OVERCLAIM"}
        if not candidate.get("information_request"):
            return {"pass": False, "reason": "MISSING_INFORMATION_REQUEST"}

        no_repair = execute_after_intervention(case, [])
        if not no_repair["valid"] or no_repair["rescued"]:
            return {"pass": False, "reason": "AMBIGUOUS_BASELINE_EXECUTION_INVALID"}

        alternative_rescues = []
        for aid in expected:
            mechanisms = oracle["mechanisms"][aid]
            repairs = [_repair_target(aid, str(kind)) for kind in mechanisms]
            iv = execute_after_intervention(case, repairs)
            if iv["valid"] and iv["rescued"]:
                alternative_rescues.append(aid)
        if sorted(alternative_rescues) != expected:
            return {"pass": False, "reason": "AMBIGUOUS_CAUSAL_EQUIVALENCE_NOT_EXECUTION_VERIFIED"}
        return {"pass": True, "reason": "PASS__EXECUTION_VERIFIED_NONIDENTIFIABILITY"}

    repairs = sorted(str(x) for x in (candidate.get("repair_targets") or []))
    expected_repairs = _expected_root_repairs(case)
    if repairs != expected_repairs:
        return {"pass": False, "reason": "FALSIFIABLE_REPAIR_TARGET_WRONG"}

    baseline = execute_after_intervention(case, [])
    if not baseline["valid"] or baseline["rescued"]:
        return {"pass": False, "reason": "BASELINE_TERMINAL_FAILURE_NOT_REPRODUCED"}

    iv = execute_after_intervention(case, repairs)
    if not iv["valid"] or iv["rescued"] is not True:
        return {"pass": False, "reason": "NOMINATED_REPAIR_DOES_NOT_EXECUTION_RESCUE"}

    symptoms = _symptom_targets(case)
    if symptoms:
        symptom_iv = execute_after_intervention(case, symptoms)
        if not symptom_iv["valid"] or symptom_iv["rescued"] is True:
            return {"pass": False, "reason": "SYMPTOM_ONLY_REPAIR_FALSELY_RESCUES"}

    if status == "INTERACTION":
        for repair in repairs:
            partial = execute_after_intervention(case, [repair])
            if not partial["valid"] or partial["rescued"] is True:
                return {"pass": False, "reason": "PARTIAL_INTERACTION_REPAIR_FALSELY_RESCUES"}

    return {"pass": True, "reason": "PASS__EXECUTION_BASED_LOCALIZATION_AND_INTERVENTION_RESCUE"}


def suite_cases() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seed = 80000
    for domain in DOMAINS:
        for kind in KINDS:
            for pattern in PATTERNS:
                out.append(generate_case(seed, pattern=pattern, domain=domain, kind=kind))
                seed += 1
    return out
