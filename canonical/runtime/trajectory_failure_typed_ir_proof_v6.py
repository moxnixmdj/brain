"""P1 typed causal proof V6 with executable hidden intervention replay.

V6 keeps the public V5 normalized trajectory interface and first-class SCOPE
mechanism, but replaces V5's oracle-list rescue predicate with an executable
hidden causal state transition. Repairs clear hidden local faults and terminal
health is recomputed over the action DAG. Zero terminal evidence is consumed.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TRAJECTORY_CAUSAL_IR_PROOF_V6"
DOMAINS = ("BROWSER", "FILESYSTEM", "TOOL_API", "ARTIFACT", "RESEARCH", "CODE")
KINDS = (
    "AUTHORITY", "SCOPE", "SCHEMA", "PROVENANCE", "INVARIANT",
    "STATE_TRANSITION", "TOOL_CONTRACT", "DEPENDENCY",
)
PATTERNS = ("SINGLE", "DELAYED", "INTERACTION", "AMBIGUOUS")


def _check(kind: str, aid: str, passed: bool) -> dict[str, Any]:
    return {
        "kind": kind,
        "id": f"{aid}:{kind}",
        "pass": passed,
        "evidence": [f"receipt:{aid}", f"check:{aid}:{kind}"],
    }


def _row(i: int, domain: str, *, reads: list[str], writes: list[str],
         depends_on: list[str], failed_kind: str | None = None,
         composition: str = "SEQUENTIAL") -> dict[str, Any]:
    aid = f"A{i}"
    checks = [_check("INVARIANT", aid, True)]
    if failed_kind is not None:
        checks.append(_check(failed_kind, aid, False))
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


def _repair(aid: str, kind: str) -> str:
    return f"restore:{aid}:{kind}"


def _parse_repair(token: str) -> tuple[str, str] | None:
    if not isinstance(token, str):
        return None
    p = token.split(":")
    if len(p) != 3 or p[0] != "restore" or not p[1] or not p[2]:
        return None
    return p[1], p[2]


def replay_terminal(case: Mapping[str, Any], repair_targets: list[str]) -> dict[str, Any]:
    """Apply repairs to hidden local faults and re-execute terminal health."""
    task = case.get("task")
    model = case.get("_causal_model")
    if not isinstance(task, Mapping) or not isinstance(model, Mapping):
        return {"status": "FAIL_CLOSED", "reason": "CASE_MODEL_INVALID"}

    rows = task.get("trajectory")
    terminal_resources = task.get("terminal_failed_resources")
    local_faults_raw = model.get("local_faults")
    if not isinstance(rows, list) or not isinstance(terminal_resources, list) or not isinstance(local_faults_raw, Mapping):
        return {"status": "FAIL_CLOSED", "reason": "CASE_MODEL_SCHEMA_INVALID"}

    local_faults = {str(k): str(v) for k, v in local_faults_raw.items()}
    cleared: set[str] = set()
    malformed: list[str] = []
    noncausal: list[str] = []
    for token in repair_targets:
        parsed = _parse_repair(token)
        if parsed is None:
            malformed.append(str(token))
            continue
        aid, kind = parsed
        if local_faults.get(aid) == kind:
            cleared.add(aid)
        else:
            noncausal.append(str(token))

    healthy: dict[str, bool] = {}
    last_writer: dict[str, str] = {}
    order: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            return {"status": "FAIL_CLOSED", "reason": "ROW_INVALID"}
        aid = row.get("action_id")
        deps = row.get("depends_on")
        reads = row.get("reads")
        writes = row.get("writes")
        comp = row.get("dependency_composition", "SEQUENTIAL")
        if (
            not isinstance(aid, str)
            or not isinstance(deps, list)
            or not isinstance(reads, list)
            or not isinstance(writes, list)
            or comp not in {"SEQUENTIAL", "CONJUNCTIVE", "ALTERNATIVE"}
        ):
            return {"status": "FAIL_CLOSED", "reason": "ROW_SCHEMA_INVALID"}
        if any(not isinstance(d, str) or d not in healthy for d in deps):
            return {"status": "FAIL_CLOSED", "reason": "NON_TOPOLOGICAL_DEPENDENCY"}

        effective = list(deps)
        for resource in reads:
            if not isinstance(resource, str):
                return {"status": "FAIL_CLOSED", "reason": "RESOURCE_INVALID"}
            writer = last_writer.get(resource)
            if writer is not None and writer not in effective:
                effective.append(writer)

        dep_states = [healthy[d] for d in effective]
        dependency_ok = any(dep_states) if comp == "ALTERNATIVE" and dep_states else all(dep_states)
        local_ok = aid not in local_faults or aid in cleared
        healthy[aid] = bool(local_ok and dependency_ok)
        order.append(aid)

        for resource in writes:
            if not isinstance(resource, str):
                return {"status": "FAIL_CLOSED", "reason": "RESOURCE_INVALID"}
            last_writer[resource] = aid

    terminal_actions: list[str] = []
    for resource in terminal_resources:
        if not isinstance(resource, str) or resource not in last_writer:
            return {"status": "FAIL_CLOSED", "reason": "TERMINAL_RESOURCE_HAS_NO_PRODUCER"}
        terminal_actions.append(last_writer[resource])

    terminal_healthy = all(healthy[x] for x in terminal_actions)
    return {
        "status": "TERMINAL_HEALTHY" if terminal_healthy else "TERMINAL_FAILED",
        "terminal_failed": not terminal_healthy,
        "terminal_actions": sorted(terminal_actions),
        "cleared_local_fault_actions": sorted(cleared),
        "malformed_repairs": sorted(malformed),
        "noncausal_or_wrong_kind_repairs": sorted(noncausal),
        "action_health": {aid: healthy[aid] for aid in order},
    }


def _root_tokens(case: Mapping[str, Any]) -> list[str]:
    faults = case["_causal_model"]["local_faults"]
    return sorted(_repair(str(aid), str(kind)) for aid, kind in faults.items())


def _minimal_rescuers(case: Mapping[str, Any]) -> list[list[str]]:
    tokens = _root_tokens(case)
    out: list[list[str]] = []
    for size in range(1, len(tokens) + 1):
        for subset in combinations(tokens, size):
            if replay_terminal(case, list(subset)).get("terminal_failed") is False:
                out.append(list(subset))
        if out:
            break
    return sorted(out)


def _derive_oracle(case: Mapping[str, Any]) -> dict[str, Any]:
    if replay_terminal(case, []).get("terminal_failed") is not True:
        raise AssertionError("BASELINE_MUST_FAIL")
    rescuers = _minimal_rescuers(case)
    if not rescuers:
        raise AssertionError("NO_RESCUING_INTERVENTION")
    faults = case["_causal_model"]["local_faults"]

    if len(rescuers) > 1:
        status = "AMBIGUOUS"
        roots = sorted({r.split(":")[1] for rs in rescuers for r in rs})
        critical = None
    else:
        roots = sorted(r.split(":")[1] for r in rescuers[0])
        status = "IDENTIFIED" if len(roots) == 1 else "INTERACTION"
        critical = roots[0]

    return {
        "status": status,
        "roots": roots,
        "critical": critical,
        "mechanisms": {aid: [str(faults[aid])] for aid in roots},
        "minimal_rescuing_repair_sets": rescuers,
        "baseline_terminal_failed": True,
    }


def generate_case(seed: int, *, pattern: str | None = None,
                  domain: str | None = None, kind: str | None = None) -> dict[str, Any]:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("SEED_INVALID")
    domain = domain or DOMAINS[seed % len(DOMAINS)]
    kind = kind or KINDS[(seed // len(DOMAINS)) % len(KINDS)]
    pattern = pattern or PATTERNS[seed % len(PATTERNS)]
    if domain not in DOMAINS or kind not in KINDS or pattern not in PATTERNS:
        raise ValueError("DOMAIN_KIND_OR_PATTERN_INVALID")

    p = f"{domain.lower()}:"
    if pattern == "SINGLE":
        rows = [
            _row(0, domain, reads=[], writes=[p+"seed"], depends_on=[]),
            _row(1, domain, reads=[p+"seed"], writes=[p+"root"], depends_on=["A0"], failed_kind=kind),
            _row(2, domain, reads=[p+"root"], writes=[p+"symptom"], depends_on=["A1"], failed_kind="INVARIANT"),
            _row(3, domain, reads=[p+"symptom"], writes=[p+"terminal"], depends_on=["A2"]),
        ]
        faults = {"A1": kind}
    elif pattern == "DELAYED":
        rows = [
            _row(0, domain, reads=[], writes=[p+"seed"], depends_on=[]),
            _row(1, domain, reads=[p+"seed"], writes=[p+"root"], depends_on=["A0"], failed_kind=kind),
            _row(2, domain, reads=[p+"root"], writes=[p+"mid1"], depends_on=["A1"]),
            _row(3, domain, reads=[p+"mid1"], writes=[p+"mid2"], depends_on=["A2"]),
            _row(4, domain, reads=[p+"mid2"], writes=[p+"late_symptom"], depends_on=["A3"], failed_kind="INVARIANT"),
            _row(5, domain, reads=[p+"late_symptom"], writes=[p+"terminal"], depends_on=["A4"]),
        ]
        faults = {"A1": kind}
    elif pattern == "INTERACTION":
        kind2 = KINDS[(KINDS.index(kind)+3) % len(KINDS)]
        rows = [
            _row(0, domain, reads=[], writes=[p+"seed"], depends_on=[]),
            _row(1, domain, reads=[p+"seed"], writes=[p+"left"], depends_on=["A0"], failed_kind=kind),
            _row(2, domain, reads=[p+"seed"], writes=[p+"right"], depends_on=["A0"], failed_kind=kind2),
            _row(3, domain, reads=[p+"left", p+"right"], writes=[p+"joined"],
                 depends_on=["A1", "A2"], composition="CONJUNCTIVE"),
            _row(4, domain, reads=[p+"joined"], writes=[p+"symptom"], depends_on=["A3"], failed_kind="INVARIANT"),
            _row(5, domain, reads=[p+"symptom"], writes=[p+"terminal"], depends_on=["A4"]),
        ]
        faults = {"A1": kind, "A2": kind2}
    else:
        kind2 = KINDS[(KINDS.index(kind)+1) % len(KINDS)]
        rows = [
            _row(0, domain, reads=[], writes=[p+"seed"], depends_on=[]),
            _row(1, domain, reads=[p+"seed"], writes=[p+"left"], depends_on=["A0"], failed_kind=kind),
            _row(2, domain, reads=[p+"seed"], writes=[p+"right"], depends_on=["A0"], failed_kind=kind2),
            _row(3, domain, reads=[p+"left", p+"right"], writes=[p+"merged"],
                 depends_on=["A1", "A2"], composition="ALTERNATIVE"),
            _row(4, domain, reads=[p+"merged"], writes=[p+"terminal"], depends_on=["A3"], failed_kind="INVARIANT"),
        ]
        faults = {"A1": kind, "A2": kind2}

    case = {
        "schema": SCHEMA,
        "behavior_id": "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "seed": seed,
        "task": {
            "domain": domain,
            "trajectory": rows,
            "terminal_failed_resources": [p+"terminal"],
            "goal": "LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_CONTRACT_REPAIR_WITHOUT_SELECTING_DOWNSTREAM_SYMPTOM",
        },
        "_causal_model": {"local_faults": faults},
    }
    case["_oracle"] = _derive_oracle(case)
    return case


def public_task(case: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in case.items() if not str(k).startswith("_")}


def _symptom_repairs(case: Mapping[str, Any]) -> list[str]:
    roots = set(case["_oracle"]["roots"])
    out: set[str] = set()
    for row in case["task"]["trajectory"]:
        aid = row["action_id"]
        if aid in roots:
            continue
        for check in row["checks"]:
            if check.get("pass") is False:
                out.add(_repair(aid, str(check["kind"])))
    return sorted(out)


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


def score_case(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(candidate, Mapping):
        return {"pass": False, "reason": "CANDIDATE_NOT_OBJECT"}
    oracle = case["_oracle"]
    status = candidate.get("status")
    if status not in _ALLOWED_KEYS:
        return {"pass": False, "reason": "STATUS_WRONG_OR_FAIL_CLOSED"}
    if set(candidate.keys()) != _ALLOWED_KEYS[status]:
        return {"pass": False, "reason": "OUTPUT_SCHEMA_NOT_EXACT"}

    got_roots = candidate.get("cause_action_ids")
    if not isinstance(got_roots, list):
        got_roots = []
    if status != oracle["status"] or sorted(map(str, got_roots)) != sorted(oracle["roots"]):
        return {"pass": False, "reason": "STATUS_OR_ROOT_SET_WRONG"}
    if candidate.get("critical_action_id") != oracle["critical"]:
        return {"pass": False, "reason": "CRITICAL_ACTION_WRONG"}

    if status == "IDENTIFIED":
        if candidate.get("cause_action_id") != oracle["critical"]:
            return {"pass": False, "reason": "UNIQUE_CAUSE_WRONG"}
        if candidate.get("mechanism_classes") != oracle["mechanisms"][oracle["critical"]]:
            return {"pass": False, "reason": "MECHANISM_CLASS_WRONG"}
        if not candidate.get("supporting_receipts"):
            return {"pass": False, "reason": "SUPPORTING_RECEIPTS_REQUIRED"}
    elif status == "INTERACTION":
        if candidate.get("mechanism_by_action") != oracle["mechanisms"]:
            return {"pass": False, "reason": "INTERACTION_MECHANISMS_WRONG"}
        if not candidate.get("supporting_receipts"):
            return {"pass": False, "reason": "SUPPORTING_RECEIPTS_REQUIRED"}
    else:
        if candidate.get("cause_action_id") is not None or not candidate.get("information_request"):
            return {"pass": False, "reason": "NONIDENTIFIABILITY_OVERCLAIM"}
        if len(oracle["minimal_rescuing_repair_sets"]) < 2:
            return {"pass": False, "reason": "AMBIGUITY_NOT_INTERVENTION_PROVED"}
        for repair_set in oracle["minimal_rescuing_repair_sets"]:
            if replay_terminal(case, repair_set).get("terminal_failed") is not False:
                return {"pass": False, "reason": "AMBIGUOUS_RESCUER_DOES_NOT_RESCUE"}
        return {"pass": True, "reason": "PASS__MULTIPLE_EXECUTABLE_RESCUERS"}

    repairs = sorted(str(x) for x in (candidate.get("repair_targets") or []))
    rescuers = oracle["minimal_rescuing_repair_sets"]
    if len(rescuers) != 1 or repairs != rescuers[0]:
        return {"pass": False, "reason": "FALSIFIABLE_REPAIR_TARGET_WRONG"}
    if replay_terminal(case, repairs).get("terminal_failed") is not False:
        return {"pass": False, "reason": "NOMINATED_REPAIR_DOES_NOT_RESCUE"}

    symptoms = _symptom_repairs(case)
    if symptoms and replay_terminal(case, symptoms).get("terminal_failed") is False:
        return {"pass": False, "reason": "SYMPTOM_ONLY_REPAIR_FALSELY_RESCUES"}

    if status == "INTERACTION":
        for size in range(len(repairs)):
            for subset in combinations(repairs, size):
                if replay_terminal(case, list(subset)).get("terminal_failed") is False:
                    return {"pass": False, "reason": "INCOMPLETE_INTERACTION_REPAIR_FALSELY_RESCUES"}

    return {"pass": True, "reason": "PASS__EXECUTABLE_INTERVENTION_RESCUE"}


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
        {"id": "SCOPE_TO_AUTHORITY_SWAP", "property": "WRONG_KIND_REPAIR_CANNOT_CLEAR_SCOPE_FAULT"},
        {"id": "SELECT_DOWNSTREAM_SYMPTOM", "property": "SYMPTOM_REPAIR_DOES_NOT_RESCUE_REEXECUTED_TERMINAL"},
        {"id": "PARTIAL_INTERACTION_REPAIR", "property": "CONJUNCTIVE_ROOT_SET_REQUIRES_ALL_REPAIRS"},
        {"id": "FORCE_UNIQUE_AMBIGUOUS_CAUSE", "property": "MULTIPLE_MINIMAL_RESCUERS_FORCE_ABSTENTION"},
        {"id": "ORACLE_LABEL_MUTATION", "property": "REPLAY_IS_DERIVED_FROM_CAUSAL_MODEL_NOT_ORACLE_LABELS"},
        {"id": "DROP_SUPPORTING_RECEIPTS", "property": "FAILED_CHECK_WITHOUT_RECEIPT_FAILS_CLOSED"},
    ]
