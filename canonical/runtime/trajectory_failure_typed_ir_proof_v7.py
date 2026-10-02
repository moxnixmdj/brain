"""P1 V7 typed causal proof with forward action/resource intervention replay.

The evaluator applies candidate repairs to DIRECT_CONTRACT failures, then
recomputes action and resource validity in topological order. Dependency
composition is load-bearing:
- SEQUENTIAL / CONJUNCTIVE require every predecessor to remain valid.
- ALTERNATIVE requires at least one predecessor to remain valid.

DERIVED_UPSTREAM failures are symptoms. They clear only when the predecessor
state that produced them becomes valid; repairing a derived symptom is not a
causal repair.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TRAJECTORY_CAUSAL_IR_PROOF_V7"
DOMAINS = ("BROWSER", "FILESYSTEM", "TOOL_API", "ARTIFACT", "RESEARCH", "CODE")
KINDS = (
    "AUTHORITY", "SCOPE", "SCHEMA", "PROVENANCE",
    "INVARIANT", "STATE_TRANSITION", "TOOL_CONTRACT", "DEPENDENCY",
)
PATTERNS = ("SINGLE", "DELAYED", "INTERACTION", "AMBIGUOUS")


def _check(kind: str, aid: str, passed: bool, *, derived: bool = False) -> dict[str, Any]:
    return {
        "kind": kind,
        "id": f"{aid}:{kind}",
        "pass": passed,
        "evidence": [f"receipt:{aid}", f"check:{aid}:{kind}"],
        "failure_semantics": "DERIVED_UPSTREAM" if (not passed and derived) else "DIRECT_CONTRACT",
    }


def _row(
    i: int,
    domain: str,
    *,
    reads: list[str],
    writes: list[str],
    depends_on: list[str],
    failed_kind: str | None = None,
    composition: str = "SEQUENTIAL",
    derived_failure: bool = False,
) -> dict[str, Any]:
    aid = f"A{i}"
    checks = [_check("INVARIANT", aid, True)]
    if failed_kind is not None:
        checks.append(_check(failed_kind, aid, False, derived=derived_failure))
    return {
        "step": i,
        "action_id": aid,
        "domain": domain,
        "reads": reads,
        "writes": writes,
        "depends_on": depends_on,
        "dependency_composition": composition,
        "checks": checks,
    }


def generate_case(
    seed: int,
    *,
    pattern: str | None = None,
    domain: str | None = None,
    kind: str | None = None,
) -> dict[str, Any]:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("SEED_INVALID")
    domain = domain or DOMAINS[seed % len(DOMAINS)]
    kind = kind or KINDS[(seed // len(DOMAINS)) % len(KINDS)]
    pattern = pattern or PATTERNS[seed % len(PATTERNS)]
    if pattern not in PATTERNS:
        raise ValueError("PATTERN_INVALID")
    if domain not in DOMAINS or kind not in KINDS:
        raise ValueError("DOMAIN_OR_KIND_INVALID")

    p = f"{domain.lower()}:"
    if pattern == "SINGLE":
        rows = [
            _row(0, domain, reads=[], writes=[p + "seed"], depends_on=[]),
            _row(1, domain, reads=[p + "seed"], writes=[p + "root"], depends_on=["A0"], failed_kind=kind),
            _row(
                2, domain, reads=[p + "root"], writes=[p + "symptom"],
                depends_on=["A1"], failed_kind="INVARIANT", derived_failure=True,
            ),
            _row(3, domain, reads=[p + "symptom"], writes=[p + "terminal"], depends_on=["A2"]),
        ]
        oracle = {
            "status": "IDENTIFIED",
            "roots": ["A1"],
            "critical": "A1",
            "mechanisms": {"A1": [kind]},
        }
    elif pattern == "DELAYED":
        rows = [
            _row(0, domain, reads=[], writes=[p + "seed"], depends_on=[]),
            _row(1, domain, reads=[p + "seed"], writes=[p + "root"], depends_on=["A0"], failed_kind=kind),
            _row(2, domain, reads=[p + "root"], writes=[p + "mid1"], depends_on=["A1"]),
            _row(3, domain, reads=[p + "mid1"], writes=[p + "mid2"], depends_on=["A2"]),
            _row(
                4, domain, reads=[p + "mid2"], writes=[p + "late_symptom"],
                depends_on=["A3"], failed_kind="INVARIANT", derived_failure=True,
            ),
            _row(5, domain, reads=[p + "late_symptom"], writes=[p + "terminal"], depends_on=["A4"]),
        ]
        oracle = {
            "status": "IDENTIFIED",
            "roots": ["A1"],
            "critical": "A1",
            "mechanisms": {"A1": [kind]},
        }
    elif pattern == "INTERACTION":
        kind2 = KINDS[(KINDS.index(kind) + 3) % len(KINDS)]
        rows = [
            _row(0, domain, reads=[], writes=[p + "seed"], depends_on=[]),
            _row(1, domain, reads=[p + "seed"], writes=[p + "left"], depends_on=["A0"], failed_kind=kind),
            _row(2, domain, reads=[p + "seed"], writes=[p + "right"], depends_on=["A0"], failed_kind=kind2),
            _row(
                3, domain, reads=[p + "left", p + "right"], writes=[p + "joined"],
                depends_on=["A1", "A2"], composition="CONJUNCTIVE",
            ),
            _row(
                4, domain, reads=[p + "joined"], writes=[p + "symptom"],
                depends_on=["A3"], failed_kind="INVARIANT", derived_failure=True,
            ),
            _row(5, domain, reads=[p + "symptom"], writes=[p + "terminal"], depends_on=["A4"]),
        ]
        oracle = {
            "status": "INTERACTION",
            "roots": ["A1", "A2"],
            "critical": "A1",
            "mechanisms": {"A1": [kind], "A2": [kind2]},
        }
    else:
        kind2 = KINDS[(KINDS.index(kind) + 1) % len(KINDS)]
        rows = [
            _row(0, domain, reads=[], writes=[p + "seed"], depends_on=[]),
            _row(1, domain, reads=[p + "seed"], writes=[p + "left"], depends_on=["A0"], failed_kind=kind),
            _row(2, domain, reads=[p + "seed"], writes=[p + "right"], depends_on=["A0"], failed_kind=kind2),
            _row(
                3, domain, reads=[p + "left", p + "right"], writes=[p + "merged"],
                depends_on=["A1", "A2"], composition="ALTERNATIVE",
            ),
            _row(
                4, domain, reads=[p + "merged"], writes=[p + "terminal"],
                depends_on=["A3"], failed_kind="INVARIANT", derived_failure=True,
            ),
        ]
        oracle = {
            "status": "AMBIGUOUS",
            "roots": ["A1", "A2"],
            "critical": None,
            "mechanisms": {"A1": [kind], "A2": [kind2]},
        }

    return {
        "schema": SCHEMA,
        "behavior_id": "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "seed": seed,
        "task": {
            "domain": domain,
            "trajectory": rows,
            "terminal_failed_resources": [p + "terminal"],
            "goal": "LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_REPAIR_WITH_FORWARD_STATE_REPLAY",
        },
        "_oracle": oracle,
    }


def public_task(case: Mapping[str, Any]) -> dict[str, Any]:
    return {k: copy.deepcopy(v) for k, v in case.items() if k != "_oracle"}


def _repair_set(candidate: Mapping[str, Any]) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    repairs = candidate.get("repair_targets")
    if not isinstance(repairs, list):
        return out
    for raw in repairs:
        if not isinstance(raw, str):
            continue
        parts = raw.split(":")
        if len(parts) == 3 and parts[0] == "restore" and parts[1] and parts[2]:
            out.add((parts[1], parts[2]))
    return out


def execute_intervention(public_case: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Apply direct repairs and replay action/resource validity to terminal state."""
    task = public_case.get("task")
    if not isinstance(task, Mapping):
        return {"terminal_rescued": False, "reason": "TASK_INVALID"}
    rows = task.get("trajectory")
    terminal_resources = task.get("terminal_failed_resources")
    if not isinstance(rows, list) or not rows or not isinstance(terminal_resources, list) or not terminal_resources:
        return {"terminal_rescued": False, "reason": "TRAJECTORY_OR_TERMINAL_INVALID"}

    repairs = _repair_set(candidate)
    by_id: dict[str, Mapping[str, Any]] = {}
    deps: dict[str, set[str]] = {}
    composition: dict[str, str] = {}
    last_writer: dict[str, str] = {}

    for row in rows:
        if not isinstance(row, Mapping):
            return {"terminal_rescued": False, "reason": "ROW_INVALID"}
        aid = row.get("action_id")
        if not isinstance(aid, str) or not aid or aid in by_id:
            return {"terminal_rescued": False, "reason": "ACTION_ID_INVALID"}
        raw_deps = row.get("depends_on")
        raw_reads = row.get("reads")
        raw_writes = row.get("writes")
        comp = row.get("dependency_composition", "SEQUENTIAL")
        checks = row.get("checks")
        if (
            not isinstance(raw_deps, list)
            or not isinstance(raw_reads, list)
            or not isinstance(raw_writes, list)
            or not isinstance(checks, list)
            or comp not in {"SEQUENTIAL", "CONJUNCTIVE", "ALTERNATIVE"}
            or any(not isinstance(x, str) or not x for x in raw_deps + raw_reads + raw_writes)
        ):
            return {"terminal_rescued": False, "reason": "ROW_SCHEMA_INVALID"}
        if any(x not in by_id for x in raw_deps):
            return {"terminal_rescued": False, "reason": "NON_TOPOLOGICAL_DEPENDENCY"}

        by_id[aid] = row
        deps[aid] = set(raw_deps)
        composition[aid] = comp
        for resource in raw_reads:
            producer = last_writer.get(resource)
            if producer is not None:
                deps[aid].add(producer)
        for resource in raw_writes:
            last_writer[resource] = aid

    missing_terminal = sorted(
        r for r in terminal_resources if not isinstance(r, str) or r not in last_writer
    )
    if missing_terminal:
        return {
            "terminal_rescued": False,
            "reason": "TERMINAL_RESOURCE_HAS_NO_WRITER",
            "missing_terminal_resources": missing_terminal,
        }

    terminal_actions = {last_writer[str(r)] for r in terminal_resources}
    relevant_actions: set[str] = set()
    stack = list(terminal_actions)
    while stack:
        aid = stack.pop()
        if aid in relevant_actions:
            continue
        relevant_actions.add(aid)
        stack.extend(deps.get(aid, set()))

    action_valid: dict[str, bool] = {}
    baseline_action_valid: dict[str, bool] = {}
    action_reason: dict[str, list[str]] = {}
    resource_valid: dict[str, bool] = {}
    baseline_resource_valid: dict[str, bool] = {}
    matched_repairs: set[tuple[str, str]] = set()
    matched_relevant_repairs: set[tuple[str, str]] = set()
    active_direct: list[tuple[str, str]] = []
    active_derived: list[tuple[str, str]] = []

    for row in rows:
        aid = str(row["action_id"])
        comp = composition[aid]

        pred_values = [action_valid.get(x, False) for x in deps[aid]]
        baseline_pred_values = [baseline_action_valid.get(x, False) for x in deps[aid]]
        read_values = [resource_valid.get(str(x), False) for x in row.get("reads") or []]
        baseline_read_values = [
            baseline_resource_valid.get(str(x), False) for x in row.get("reads") or []
        ]

        def compose(values: list[bool]) -> bool:
            if not values:
                return True
            if comp == "ALTERNATIVE":
                return any(values)
            return all(values)

        predecessors_valid = compose(pred_values) and compose(read_values)
        baseline_predecessors_valid = (
            compose(baseline_pred_values) and compose(baseline_read_values)
        )

        direct_ok = True
        baseline_direct_ok = True
        row_derived: list[tuple[str, str]] = []
        reasons: list[str] = []

        for check in row["checks"]:
            if not isinstance(check, Mapping):
                return {"terminal_rescued": False, "reason": "CHECK_INVALID"}
            passed = check.get("pass")
            kind = check.get("kind")
            semantics = check.get("failure_semantics")
            if type(passed) is not bool or not isinstance(kind, str):
                return {"terminal_rescued": False, "reason": "CHECK_SCHEMA_INVALID"}
            if semantics not in {"DIRECT_CONTRACT", "DERIVED_UPSTREAM"}:
                return {"terminal_rescued": False, "reason": "FAILURE_SEMANTICS_INVALID"}
            if passed:
                continue

            key = (aid, kind)
            if semantics == "DIRECT_CONTRACT":
                baseline_direct_ok = False
                if key in repairs:
                    matched_repairs.add(key)
                    if aid in relevant_actions:
                        matched_relevant_repairs.add(key)
                else:
                    direct_ok = False
                    if aid in relevant_actions:
                        active_direct.append(key)
            else:
                row_derived.append(key)

        derived_ok = not row_derived or predecessors_valid
        baseline_derived_ok = not row_derived or baseline_predecessors_valid
        if row_derived and not predecessors_valid and aid in relevant_actions:
            active_derived.extend(row_derived)

        valid = predecessors_valid and direct_ok and derived_ok
        baseline_valid = (
            baseline_predecessors_valid and baseline_direct_ok and baseline_derived_ok
        )
        action_valid[aid] = valid
        baseline_action_valid[aid] = baseline_valid

        if not predecessors_valid:
            reasons.append("PREDECESSOR_OR_INPUT_RESOURCE_INVALID")
        if not direct_ok:
            reasons.append("DIRECT_CONTRACT_FAILURE_UNREPAIRED")
        if not derived_ok:
            reasons.append("DERIVED_UPSTREAM_FAILURE_ACTIVE")
        action_reason[aid] = reasons

        for resource in row.get("writes") or []:
            resource_valid[str(resource)] = valid
            baseline_resource_valid[str(resource)] = baseline_valid

    terminal_validity = {
        str(resource): bool(resource_valid.get(str(resource), False))
        for resource in terminal_resources
    }
    baseline_terminal_validity = {
        str(resource): bool(baseline_resource_valid.get(str(resource), False))
        for resource in terminal_resources
    }
    terminal_was_failed = not all(baseline_terminal_validity.values())
    terminal_rescued = (
        terminal_was_failed
        and all(terminal_validity.values())
        and bool(matched_relevant_repairs)
    )

    return {
        "terminal_rescued": terminal_rescued,
        "terminal_was_failed_before_intervention": terminal_was_failed,
        "baseline_terminal_resource_validity": baseline_terminal_validity,
        "terminal_resource_validity": terminal_validity,
        "action_validity": dict(action_valid),
        "action_failure_reasons": action_reason,
        "matched_direct_repairs": [f"{a}:{k}" for a, k in sorted(matched_repairs)],
        "matched_relevant_direct_repairs": [
            f"{a}:{k}" for a, k in sorted(matched_relevant_repairs)
        ],
        "active_relevant_direct_failures": [
            f"{a}:{k}" for a, k in sorted(active_direct)
        ],
        "active_relevant_derived_failures": [
            f"{a}:{k}" for a, k in sorted(active_derived)
        ],
        "reason": "TERMINAL_STATE_REPLAY_VALID" if terminal_rescued else "TERMINAL_STATE_REPLAY_FAILED",
    }


_ALLOWED_KEYS = {
    "IDENTIFIED": {
        "status", "cause_action_id", "cause_action_ids", "critical_action_id",
        "mechanism_classes", "supporting_receipts", "repair_targets", "reason",
    },
    "INTERACTION": {
        "status", "cause_action_id", "cause_action_ids", "critical_action_id",
        "interaction_witness_action_ids", "mechanism_by_action", "supporting_receipts",
        "repair_targets", "reason",
    },
    "AMBIGUOUS": {
        "status", "cause_action_id", "cause_action_ids", "critical_action_id",
        "candidates", "reason", "information_request",
    },
}


def score_case(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(candidate, Mapping):
        return {"pass": False, "reason": "CANDIDATE_NOT_OBJECT"}
    status = candidate.get("status")
    if status not in _ALLOWED_KEYS:
        return {"pass": False, "reason": "STATUS_WRONG_OR_FAIL_CLOSED"}
    if set(candidate.keys()) != _ALLOWED_KEYS[status]:
        return {"pass": False, "reason": "OUTPUT_SCHEMA_NOT_EXACT"}

    oracle = case["_oracle"]
    got_roots = candidate.get("cause_action_ids")
    if not isinstance(got_roots, list):
        got_roots = []
    roots = sorted(str(x) for x in got_roots)
    expected = sorted(oracle["roots"])
    if status != oracle["status"] or roots != expected:
        return {
            "pass": False,
            "reason": "STATUS_OR_ROOT_SET_WRONG",
            "expected_status": oracle["status"],
            "expected_roots": expected,
        }
    if candidate.get("critical_action_id") != oracle["critical"]:
        return {"pass": False, "reason": "CRITICAL_ACTION_WRONG"}

    if oracle["status"] == "IDENTIFIED":
        if candidate.get("cause_action_id") != oracle["critical"]:
            return {"pass": False, "reason": "UNIQUE_CAUSE_WRONG"}
        if candidate.get("mechanism_classes") != oracle["mechanisms"][oracle["critical"]]:
            return {"pass": False, "reason": "MECHANISM_CLASS_WRONG"}
        if not candidate.get("supporting_receipts"):
            return {"pass": False, "reason": "SUPPORTING_RECEIPTS_REQUIRED"}
    elif oracle["status"] == "INTERACTION":
        if candidate.get("mechanism_by_action") != oracle["mechanisms"]:
            return {"pass": False, "reason": "INTERACTION_MECHANISMS_WRONG"}
        if not candidate.get("supporting_receipts"):
            return {"pass": False, "reason": "SUPPORTING_RECEIPTS_REQUIRED"}
    else:
        if candidate.get("cause_action_id") is not None:
            return {"pass": False, "reason": "NONIDENTIFIABILITY_OVERCLAIM"}
        if not candidate.get("information_request"):
            return {"pass": False, "reason": "MISSING_INFORMATION_REQUEST"}
        candidates = candidate.get("candidates")
        if not isinstance(candidates, list) or len(candidates) < 2:
            return {"pass": False, "reason": "AMBIGUOUS_REPAIR_ALTERNATIVES_MISSING"}
        rescuers = []
        for item in candidates:
            if not isinstance(item, Mapping):
                continue
            iv = execute_intervention(
                public_task(case),
                {"repair_targets": list(item.get("repair_targets") or [])},
            )
            if iv.get("terminal_rescued") is True:
                rescuers.append(item.get("action_id"))
        if len(set(rescuers)) < 2:
            return {
                "pass": False,
                "reason": "NONIDENTIFIABILITY_NOT_ESTABLISHED_BY_MULTIPLE_RESCUERS",
                "rescuers": rescuers,
            }
        baseline = execute_intervention(public_task(case), {"repair_targets": []})
        if baseline.get("terminal_rescued") is True:
            return {"pass": False, "reason": "AMBIGUOUS_BASELINE_FALSE_RESCUE"}
        return {
            "pass": True,
            "reason": "PASS__MULTIPLE_INDEPENDENT_RESCUERS_ESTABLISH_NONIDENTIFIABILITY",
            "intervention_rescue_verified": False,
            "alternative_rescuers": sorted(set(str(x) for x in rescuers)),
        }

    repairs = sorted(str(x) for x in (candidate.get("repair_targets") or []))
    expected_repairs = sorted(
        f"restore:{aid}:{kind}"
        for aid, kinds in oracle["mechanisms"].items()
        for kind in kinds
    )
    if repairs != expected_repairs:
        return {
            "pass": False,
            "reason": "FALSIFIABLE_REPAIR_TARGET_WRONG",
            "expected_repair_targets": expected_repairs,
        }

    intervention = execute_intervention(public_task(case), candidate)
    if intervention.get("terminal_rescued") is not True:
        return {
            "pass": False,
            "reason": "INTERVENTION_DID_NOT_RESCUE_TERMINAL_STATE",
            "intervention": intervention,
        }
    return {
        "pass": True,
        "reason": "PASS__LOCALIZATION_AND_FORWARD_TERMINAL_STATE_RESCUE",
        "intervention_rescue_verified": True,
        "intervention": intervention,
    }


def suite_cases() -> list[dict[str, Any]]:
    out = []
    seed = 70000
    for domain in DOMAINS:
        for kind in KINDS:
            for pattern in PATTERNS:
                out.append(generate_case(seed, pattern=pattern, domain=domain, kind=kind))
                seed += 1
    return out


def anti_shortcut_mutations() -> list[dict[str, str]]:
    return [
        {"id": "DERIVED_ONLY_NOT_ROOT", "property": "DERIVED_UPSTREAM_FAILURE_MUST_NOT_BE_PROMOTED_TO_CAUSAL_ROOT"},
        {"id": "SCOPE_FIRST_CLASS", "property": "SCOPE_MUST_REMAIN_DISTINCT_FROM_AUTHORITY"},
        {"id": "DELAY_SYMPTOM", "property": "ROOT_CAUSE_MUST_SURVIVE_LONG_CAUSAL_DELAY"},
        {"id": "CONJUNCTIVE_PARTIAL_REPAIR", "property": "ALL_CONJUNCTIVE_ROOTS_MUST_BE_REPAIRED"},
        {"id": "ALTERNATIVE_MULTIPLE_RESCUERS", "property": "INDEPENDENT_RESCUERS_ESTABLISH_NONIDENTIFIABILITY"},
        {"id": "SYMPTOM_ONLY_REPAIR", "property": "DERIVED_SYMPTOM_REPAIR_CANNOT_RESCUE_UNREPAIRED_ROOT"},
        {"id": "ORPHAN_TERMINAL", "property": "TERMINAL_RESOURCE_WITHOUT_VALID_WRITER_CANNOT_RESCUE"},
        {"id": "IRRELEVANT_REPAIR", "property": "UNMATCHED_REPAIR_TOKEN_CANNOT_CREATE_RESCUE"},
        {"id": "PROVENANCE_REQUIRED", "property": "DIRECT_FAILURE_SUPPORTING_RECEIPTS_ARE_LOAD_BEARING"},
    ]
