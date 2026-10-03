"""Executable structural counterfactual proof envelope V6 for P1.

This module evaluates intervention rescue by re-executing hidden structural worlds.
It deliberately does not decide rescue by comparing proposed repairs with an oracle
repair set. The public candidate sees only normalized trajectory IR; hidden worlds
and expected causal labels remain evaluator-private.

Zero terminal replay. Zero fresh reality. Zero capability/family credit.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_P1_EXECUTABLE_COUNTERFACTUAL_PROOF_V6"
DOMAINS = ("BROWSER", "FILESYSTEM", "TOOL_API", "ARTIFACT", "RESEARCH", "CODE")
KINDS = (
    "AUTHORITY",
    "SCOPE",
    "SCHEMA",
    "PROVENANCE",
    "INVARIANT",
    "STATE_TRANSITION",
    "TOOL_CONTRACT",
    "DEPENDENCY",
)
PATTERNS = ("SINGLE", "DELAYED", "INTERACTION", "AMBIGUOUS")


def _check(kind: str, aid: str, passed: bool) -> dict[str, Any]:
    return {
        "kind": kind,
        "id": f"{aid}:{kind}",
        "pass": passed,
        "evidence": [f"receipt:{aid}", f"check:{aid}:{kind}"],
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
) -> dict[str, Any]:
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


def _parse_repair(value: str) -> tuple[str, str] | None:
    if not isinstance(value, str):
        return None
    parts = value.split(":")
    if len(parts) != 3 or parts[0] != "restore" or not parts[1] or not parts[2]:
        return None
    return parts[1], parts[2]


def _hidden_world(
    *,
    world_id: str,
    faults: Mapping[str, str],
    alternative_selector: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "world_id": world_id,
        "latent_faults": dict(faults),
        "alternative_selector": dict(alternative_selector or {}),
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
    if domain not in DOMAINS or kind not in KINDS or pattern not in PATTERNS:
        raise ValueError("DOMAIN_KIND_OR_PATTERN_INVALID")

    p = f"{domain.lower()}:"
    rows: list[dict[str, Any]]
    oracle: dict[str, Any]
    worlds: list[dict[str, Any]]

    if pattern == "SINGLE":
        rows = [
            _row(0, domain, reads=[], writes=[p + "seed"], depends_on=[]),
            _row(
                1,
                domain,
                reads=[p + "seed"],
                writes=[p + "root"],
                depends_on=["A0"],
                failed_kind=kind,
            ),
            _row(
                2,
                domain,
                reads=[p + "root"],
                writes=[p + "symptom"],
                depends_on=["A1"],
                failed_kind="INVARIANT",
            ),
            _row(
                3,
                domain,
                reads=[p + "symptom"],
                writes=[p + "terminal"],
                depends_on=["A2"],
            ),
        ]
        oracle = {
            "status": "IDENTIFIED",
            "roots": ["A1"],
            "critical": "A1",
            "mechanisms": {"A1": [kind]},
        }
        worlds = [_hidden_world(world_id="W0", faults={"A1": kind})]

    elif pattern == "DELAYED":
        rows = [
            _row(0, domain, reads=[], writes=[p + "seed"], depends_on=[]),
            _row(
                1,
                domain,
                reads=[p + "seed"],
                writes=[p + "root"],
                depends_on=["A0"],
                failed_kind=kind,
            ),
            _row(2, domain, reads=[p + "root"], writes=[p + "mid1"], depends_on=["A1"]),
            _row(3, domain, reads=[p + "mid1"], writes=[p + "mid2"], depends_on=["A2"]),
            _row(
                4,
                domain,
                reads=[p + "mid2"],
                writes=[p + "late_symptom"],
                depends_on=["A3"],
                failed_kind="INVARIANT",
            ),
            _row(
                5,
                domain,
                reads=[p + "late_symptom"],
                writes=[p + "terminal"],
                depends_on=["A4"],
            ),
        ]
        oracle = {
            "status": "IDENTIFIED",
            "roots": ["A1"],
            "critical": "A1",
            "mechanisms": {"A1": [kind]},
        }
        worlds = [_hidden_world(world_id="W0", faults={"A1": kind})]

    elif pattern == "INTERACTION":
        kind2 = KINDS[(KINDS.index(kind) + 3) % len(KINDS)]
        rows = [
            _row(0, domain, reads=[], writes=[p + "seed"], depends_on=[]),
            _row(
                1,
                domain,
                reads=[p + "seed"],
                writes=[p + "left"],
                depends_on=["A0"],
                failed_kind=kind,
            ),
            _row(
                2,
                domain,
                reads=[p + "seed"],
                writes=[p + "right"],
                depends_on=["A0"],
                failed_kind=kind2,
            ),
            _row(
                3,
                domain,
                reads=[p + "left", p + "right"],
                writes=[p + "joined"],
                depends_on=["A1", "A2"],
                composition="CONJUNCTIVE",
            ),
            _row(
                4,
                domain,
                reads=[p + "joined"],
                writes=[p + "symptom"],
                depends_on=["A3"],
                failed_kind="INVARIANT",
            ),
            _row(
                5,
                domain,
                reads=[p + "symptom"],
                writes=[p + "terminal"],
                depends_on=["A4"],
            ),
        ]
        oracle = {
            "status": "INTERACTION",
            "roots": ["A1", "A2"],
            "critical": "A1",
            "mechanisms": {"A1": [kind], "A2": [kind2]},
        }
        worlds = [
            _hidden_world(
                world_id="W0",
                faults={"A1": kind, "A2": kind2},
            )
        ]

    else:  # AMBIGUOUS
        kind2 = KINDS[(KINDS.index(kind) + 1) % len(KINDS)]
        rows = [
            _row(0, domain, reads=[], writes=[p + "seed"], depends_on=[]),
            _row(
                1,
                domain,
                reads=[p + "seed"],
                writes=[p + "left"],
                depends_on=["A0"],
                failed_kind=kind,
            ),
            _row(
                2,
                domain,
                reads=[p + "seed"],
                writes=[p + "right"],
                depends_on=["A0"],
                failed_kind=kind2,
            ),
            _row(
                3,
                domain,
                reads=[p + "left", p + "right"],
                writes=[p + "merged"],
                depends_on=["A1", "A2"],
                composition="ALTERNATIVE",
            ),
            _row(
                4,
                domain,
                reads=[p + "merged"],
                writes=[p + "terminal"],
                depends_on=["A3"],
            ),
        ]
        oracle = {
            "status": "AMBIGUOUS",
            "roots": ["A1", "A2"],
            "critical": None,
            "mechanisms": {"A1": [kind], "A2": [kind2]},
        }
        # Same public trace, two latent causal worlds. In each world the
        # alternative merge depends on a different branch.
        worlds = [
            _hidden_world(
                world_id="W_LEFT",
                faults={"A1": kind},
                alternative_selector={"A3": "A1"},
            ),
            _hidden_world(
                world_id="W_RIGHT",
                faults={"A2": kind2},
                alternative_selector={"A3": "A2"},
            ),
        ]

    case = {
        "schema": SCHEMA,
        "behavior_id": "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "seed": seed,
        "pattern": pattern,
        "task": {
            "domain": domain,
            "trajectory": rows,
            "terminal_failed_resources": [p + "terminal"],
            "goal": (
                "LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_CONTRACT_REPAIR_WITHOUT_"
                "SELECTING_DOWNSTREAM_SYMPTOM"
            ),
        },
        "_oracle": oracle,
        "_worlds": worlds,
    }
    baseline = evaluate_intervention(case, [])
    if baseline["all_worlds_terminal_success"]:
        raise AssertionError("GENERATED_CASE_NOT_FAILED_AT_BASELINE")
    return case


def public_task(case: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in case.items() if not str(k).startswith("_")}


def _execute_world(
    case: Mapping[str, Any],
    world: Mapping[str, Any],
    repairs: set[tuple[str, str]],
) -> dict[str, Any]:
    task = case.get("task")
    if not isinstance(task, Mapping):
        raise ValueError("TASK_INVALID")
    rows = task.get("trajectory")
    terminal_failed = task.get("terminal_failed_resources")
    if not isinstance(rows, list) or not rows or not isinstance(terminal_failed, list):
        raise ValueError("TRAJECTORY_INVALID")

    latent_faults = world.get("latent_faults")
    selectors = world.get("alternative_selector")
    if not isinstance(latent_faults, Mapping) or not isinstance(selectors, Mapping):
        raise ValueError("WORLD_INVALID")

    action_valid: dict[str, bool] = {}
    resource_valid: dict[str, bool] = {}
    producer: dict[str, str] = {}

    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("ROW_INVALID")
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
        ):
            raise ValueError("ROW_SHAPE_INVALID")

        explicit_dep_valid = [action_valid.get(str(d), False) for d in deps]
        read_valid = [resource_valid.get(str(r), False) for r in reads]

        if comp == "ALTERNATIVE":
            selected = selectors.get(aid)
            if not isinstance(selected, str) or selected not in deps:
                raise ValueError("ALTERNATIVE_SELECTOR_INVALID")
            deps_ok = action_valid.get(selected, False)
            selected_writes: set[str] = set()
            for prior in rows:
                if isinstance(prior, Mapping) and prior.get("action_id") == selected:
                    selected_writes = {str(x) for x in prior.get("writes", [])}
                    break
            # Only reads from the selected latent branch are load-bearing in this
            # hidden world. Non-selected public alternatives are observationally
            # present but causally inactive.
            relevant_reads = [
                resource_valid.get(str(r), False)
                for r in reads
                if str(r) in selected_writes
            ]
            reads_ok = all(relevant_reads) if relevant_reads else deps_ok
        else:
            deps_ok = all(explicit_dep_valid) if deps else True
            reads_ok = all(read_valid) if reads else True

        fault_kind = latent_faults.get(aid)
        fault_active = False
        if isinstance(fault_kind, str):
            fault_active = (aid, fault_kind) not in repairs

        valid = bool(deps_ok and reads_ok and not fault_active)
        action_valid[aid] = valid
        for w in writes:
            resource = str(w)
            resource_valid[resource] = valid
            producer[resource] = aid

    terminal_status: dict[str, bool] = {}
    for r in terminal_failed:
        resource = str(r)
        terminal_status[resource] = bool(resource_valid.get(resource, False))
    terminal_success = bool(terminal_status) and all(terminal_status.values())
    return {
        "world_id": world.get("world_id"),
        "terminal_success": terminal_success,
        "terminal_resources": terminal_status,
        "action_validity": action_valid,
        "resource_validity": resource_valid,
        "producer": producer,
    }


def evaluate_intervention(
    case: Mapping[str, Any],
    repair_targets: list[str],
) -> dict[str, Any]:
    parsed: set[tuple[str, str]] = set()
    invalid: list[str] = []
    for raw in repair_targets:
        item = _parse_repair(raw)
        if item is None:
            invalid.append(str(raw))
        else:
            parsed.add(item)
    if invalid:
        return {
            "status": "INVALID_REPAIR_TARGET",
            "invalid_repair_targets": sorted(invalid),
            "world_results": [],
            "any_world_terminal_success": False,
            "all_worlds_terminal_success": False,
        }

    worlds = case.get("_worlds")
    if not isinstance(worlds, list) or not worlds:
        raise ValueError("HIDDEN_WORLDS_MISSING")
    results = [_execute_world(case, world, parsed) for world in worlds]
    successes = [bool(x["terminal_success"]) for x in results]
    return {
        "status": "EXECUTED",
        "world_results": results,
        "any_world_terminal_success": any(successes),
        "all_worlds_terminal_success": all(successes),
    }


def _expected_repairs(oracle: Mapping[str, Any]) -> list[str]:
    return sorted(
        _repair(str(aid), str(kind))
        for aid, kinds in (oracle.get("mechanisms") or {}).items()
        for kind in kinds
    )


def _symptom_repairs(case: Mapping[str, Any]) -> list[str]:
    oracle = case["_oracle"]
    roots = set(oracle["roots"])
    out: list[str] = []
    for row in case["task"]["trajectory"]:
        aid = row["action_id"]
        if aid in roots:
            continue
        for check in row["checks"]:
            if check["pass"] is False:
                out.append(_repair(aid, check["kind"]))
    return sorted(out)


def score_case(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(candidate, Mapping):
        return {"pass": False, "reason": "CANDIDATE_NOT_OBJECT"}
    oracle = case["_oracle"]
    status = candidate.get("status")
    got_roots = candidate.get("cause_action_ids")
    if not isinstance(got_roots, list):
        got_roots = []
    roots = sorted(str(x) for x in got_roots)
    expected_roots = sorted(str(x) for x in oracle["roots"])
    if status != oracle["status"] or roots != expected_roots:
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
    elif status == "AMBIGUOUS":
        if candidate.get("cause_action_id") is not None:
            return {"pass": False, "reason": "NONIDENTIFIABILITY_OVERCLAIM"}
        if not candidate.get("information_request"):
            return {"pass": False, "reason": "MISSING_INFORMATION_REQUEST"}
        # Each observationally possible root repair rescues a different hidden
        # world, but no single repair rescues all worlds. Therefore the trace
        # does not identify one intervention.
        per_root = []
        for aid, kinds in oracle["mechanisms"].items():
            for kind in kinds:
                iv = evaluate_intervention(case, [_repair(aid, kind)])
                per_root.append(iv)
                if iv["any_world_terminal_success"] is not True:
                    return {"pass": False, "reason": "AMBIGUOUS_ROOT_REPAIR_RESCUES_NO_WORLD"}
                if iv["all_worlds_terminal_success"] is True:
                    return {"pass": False, "reason": "AMBIGUOUS_SINGLE_REPAIR_FALSELY_UNIVERSAL"}
        if len(per_root) < 2:
            return {"pass": False, "reason": "AMBIGUOUS_WORLD_SET_TOO_SMALL"}
        return {"pass": True, "reason": "PASS__STRUCTURAL_NONIDENTIFIABILITY"}

    repairs = sorted(str(x) for x in (candidate.get("repair_targets") or []))
    expected_repairs = _expected_repairs(oracle)
    if repairs != expected_repairs:
        return {"pass": False, "reason": "FALSIFIABLE_REPAIR_TARGET_WRONG"}

    iv = evaluate_intervention(case, repairs)
    if iv["all_worlds_terminal_success"] is not True:
        return {"pass": False, "reason": "NOMINATED_REPAIR_DOES_NOT_EXECUTABLY_RESCUE"}

    symptoms = _symptom_repairs(case)
    if symptoms:
        symptom_iv = evaluate_intervention(case, symptoms)
        if symptom_iv["any_world_terminal_success"] is True:
            return {"pass": False, "reason": "SYMPTOM_ONLY_REPAIR_FALSELY_RESCUES"}

    if status == "INTERACTION":
        for repair in repairs:
            partial = evaluate_intervention(case, [repair])
            if partial["any_world_terminal_success"] is True:
                return {"pass": False, "reason": "PARTIAL_INTERACTION_REPAIR_FALSELY_RESCUES"}

    return {
        "pass": True,
        "reason": "PASS__STRUCTURAL_COUNTERFACTUAL_REEXECUTION_RESCUES",
    }


def suite_cases() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seed = 70000
    for domain in DOMAINS:
        for kind in KINDS:
            for pattern in PATTERNS:
                out.append(
                    generate_case(
                        seed,
                        pattern=pattern,
                        domain=domain,
                        kind=kind,
                    )
                )
                seed += 1
    return out


def summary() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "domain_count": len(DOMAINS),
        "mechanism_class_count": len(KINDS),
        "causal_pattern_count": len(PATTERNS),
        "cross_product_case_count": len(suite_cases()),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(summary(), indent=2, sort_keys=True))
