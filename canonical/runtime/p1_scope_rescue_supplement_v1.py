"""Minimal fresh supplement for the two irreducible P1 whole-scope obligations.

This is not a Terminal V3 replay. The old immutable wave is untouched.
The supplement exercises only:
  1. explicit SCOPE as a first-class causal failure mechanism; and
  2. post-intervention terminal rescue over delayed and multi-root typed traces.

The case structure is frozen in code. A post-freeze seed only randomizes opaque
action/resource names, so results cannot change which semantic dimensions are
tested.
"""
from __future__ import annotations

import argparse
import json
import random
from typing import Any, Mapping

from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate_v5

SCHEMA = "PROJECT_BRAIN_P1_SCOPE_RESCUE_SUPPLEMENT_V1"
BEHAVIOR = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
DOMAINS = ("BROWSER", "FILESYSTEM", "TOOL_API", "ARTIFACT", "RESEARCH", "CODE")
KINDS = tuple(sorted(candidate_v5.ALLOWED_KINDS))
PATTERNS = ("DELAYED", "INTERACTION")


def _ids(seed: int, count: int) -> list[str]:
    r = random.Random(seed)
    out: list[str] = []
    seen: set[str] = set()
    while len(out) < count:
        value = f"N{r.randrange(10**9):09d}"
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _check(kind: str, aid: str, passed: bool) -> dict[str, Any]:
    return {
        "kind": kind,
        "id": f"{aid}:{kind}",
        "pass": passed,
        "evidence": [f"receipt:{aid}", f"check:{aid}:{kind}"],
    }


def _row(
    aid: str,
    domain: str,
    *,
    reads: list[str],
    writes: list[str],
    depends_on: list[str],
    failed_kind: str | None = None,
    composition: str = "SEQUENTIAL",
) -> dict[str, Any]:
    checks = [_check("INVARIANT", aid, True)]
    if failed_kind is not None:
        checks.append(_check(failed_kind, aid, False))
    return {
        "action_id": aid,
        "domain": domain,
        "reads": reads,
        "writes": writes,
        "depends_on": depends_on,
        "dependency_composition": composition,
        "checks": checks,
    }


def generate_case(seed: int, *, domain: str, kind: str, pattern: str) -> dict[str, Any]:
    if domain not in DOMAINS or kind not in KINDS or pattern not in PATTERNS:
        raise ValueError("DIMENSION_INVALID")
    names = _ids(seed, 6)
    a0, a1, a2, a3, a4, a5 = names
    prefix = f"{domain.lower()}:{seed:x}:"
    if pattern == "DELAYED":
        rows = [
            _row(a0, domain, reads=[], writes=[prefix+"seed"], depends_on=[]),
            _row(a1, domain, reads=[prefix+"seed"], writes=[prefix+"root"], depends_on=[a0], failed_kind=kind),
            _row(a2, domain, reads=[prefix+"root"], writes=[prefix+"mid1"], depends_on=[a1]),
            _row(a3, domain, reads=[prefix+"mid1"], writes=[prefix+"mid2"], depends_on=[a2]),
            _row(a4, domain, reads=[prefix+"mid2"], writes=[prefix+"symptom"], depends_on=[a3], failed_kind="INVARIANT"),
            _row(a5, domain, reads=[prefix+"symptom"], writes=[prefix+"terminal"], depends_on=[a4]),
        ]
        oracle = {
            "status": "IDENTIFIED",
            "roots": [a1],
            "critical": a1,
            "mechanisms": {a1: [kind]},
            "symptom_actions": [a4],
        }
    else:
        kind2 = KINDS[(KINDS.index(kind) + 3) % len(KINDS)]
        rows = [
            _row(a0, domain, reads=[], writes=[prefix+"seed"], depends_on=[]),
            _row(a1, domain, reads=[prefix+"seed"], writes=[prefix+"left"], depends_on=[a0], failed_kind=kind),
            _row(a2, domain, reads=[prefix+"seed"], writes=[prefix+"right"], depends_on=[a0], failed_kind=kind2),
            _row(
                a3,
                domain,
                reads=[prefix+"left", prefix+"right"],
                writes=[prefix+"joined"],
                depends_on=[a1, a2],
                composition="CONJUNCTIVE",
            ),
            _row(a4, domain, reads=[prefix+"joined"], writes=[prefix+"symptom"], depends_on=[a3], failed_kind="INVARIANT"),
            _row(a5, domain, reads=[prefix+"symptom"], writes=[prefix+"terminal"], depends_on=[a4]),
        ]
        oracle = {
            "status": "INTERACTION",
            "roots": [a1, a2],
            "critical": a1,
            "mechanisms": {a1: [kind], a2: [kind2]},
            "symptom_actions": [a4],
        }
    return {
        "schema": SCHEMA,
        "behavior_id": BEHAVIOR,
        "seed": seed,
        "task": {
            "domain": domain,
            "trajectory": rows,
            "terminal_failed_resources": [prefix+"terminal"],
            "goal": "LOCALIZE_CAUSAL_ROOT_CLASSIFY_MECHANISM_AND_NOMINATE_RESCUING_REPAIR",
        },
        "_oracle": oracle,
    }


def public_task(case: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in case.items() if k != "_oracle"}


def _repair_target(aid: str, kind: str) -> str:
    return f"restore:{aid}:{kind}"


def _repair_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(x) for x in value}


def apply_intervention(case: Mapping[str, Any], repair_targets: Any) -> dict[str, Any]:
    """Evaluate the hidden causal rescue model.

    A terminal failure persists until every independently causal root violation
    is repaired. Downstream symptom repair has no effect on causal roots.
    """
    oracle = case["_oracle"]
    repairs = _repair_set(repair_targets)
    required = {
        _repair_target(aid, kind)
        for aid, kinds in oracle["mechanisms"].items()
        for kind in kinds
    }
    unrepaired = sorted(required - repairs)
    return {
        "terminal_pass": not unrepaired,
        "required_root_repairs": sorted(required),
        "applied_repairs": sorted(repairs),
        "unrepaired_root_repairs": unrepaired,
    }


def score_case(case: Mapping[str, Any], output: Mapping[str, Any]) -> dict[str, Any]:
    oracle = case["_oracle"]
    reasons: list[str] = []
    roots = sorted(str(x) for x in (output.get("cause_action_ids") or []))
    expected_roots = sorted(oracle["roots"])
    if output.get("status") != oracle["status"] or roots != expected_roots:
        reasons.append("STATUS_OR_ROOT_SET_WRONG")
    if output.get("critical_action_id") != oracle["critical"]:
        reasons.append("CRITICAL_ACTION_WRONG")

    if oracle["status"] == "IDENTIFIED":
        root = oracle["critical"]
        if output.get("cause_action_id") != root:
            reasons.append("UNIQUE_CAUSE_WRONG")
        if output.get("mechanism_classes") != oracle["mechanisms"][root]:
            reasons.append("MECHANISM_CLASS_WRONG")
    else:
        if output.get("mechanism_by_action") != oracle["mechanisms"]:
            reasons.append("INTERACTION_MECHANISMS_WRONG")

    expected_repairs = sorted(
        _repair_target(aid, kind)
        for aid, kinds in oracle["mechanisms"].items()
        for kind in kinds
    )
    actual_repairs = sorted(_repair_set(output.get("repair_targets")))
    if actual_repairs != expected_repairs:
        reasons.append("REPAIR_TARGET_SET_WRONG")

    rescue = apply_intervention(case, actual_repairs)
    if rescue["terminal_pass"] is not True:
        reasons.append("CANDIDATE_REPAIR_DOES_NOT_RESCUE_TERMINAL")

    symptom_repairs = [
        _repair_target(aid, "INVARIANT")
        for aid in oracle["symptom_actions"]
    ]
    symptom_control = apply_intervention(case, symptom_repairs)
    if symptom_control["terminal_pass"] is not False:
        reasons.append("SYMPTOM_ONLY_REPAIR_FALSELY_RESCUES")

    partial_controls: list[dict[str, Any]] = []
    if len(expected_repairs) > 1:
        for dropped in expected_repairs:
            subset = [x for x in expected_repairs if x != dropped]
            verdict = apply_intervention(case, subset)
            partial_controls.append({"dropped": dropped, "terminal_pass": verdict["terminal_pass"]})
            if verdict["terminal_pass"] is not False:
                reasons.append("PARTIAL_INTERACTION_REPAIR_FALSELY_RESCUES")

    return {
        "pass": not reasons,
        "reasons": reasons,
        "candidate_rescue": rescue,
        "symptom_only_control": symptom_control,
        "partial_interaction_controls": partial_controls,
    }


def suite_cases(post_freeze_seed: int) -> list[dict[str, Any]]:
    if not isinstance(post_freeze_seed, int) or isinstance(post_freeze_seed, bool):
        raise ValueError("POST_FREEZE_SEED_INVALID")
    cases: list[dict[str, Any]] = []
    index = 0
    for domain in DOMAINS:
        for kind in KINDS:
            for pattern in PATTERNS:
                case_seed = post_freeze_seed * 1000003 + index * 7919 + 17
                cases.append(generate_case(case_seed, domain=domain, kind=kind, pattern=pattern))
                index += 1
    return cases


def run_suite(post_freeze_seed: int) -> dict[str, Any]:
    cases = suite_cases(post_freeze_seed)
    failures: list[dict[str, Any]] = []
    scope_cases = 0
    rescue_passes = 0
    symptom_negative_control_passes = 0
    interaction_partial_control_checks = 0
    dimensions = {"domains": set(), "kinds": set(), "patterns": set()}
    for case in cases:
        dimensions["domains"].add(case["task"]["domain"])
        dimensions["patterns"].add(case["_oracle"]["status"])
        for kinds in case["_oracle"]["mechanisms"].values():
            dimensions["kinds"].update(kinds)
        if any("SCOPE" in kinds for kinds in case["_oracle"]["mechanisms"].values()):
            scope_cases += 1
        output = candidate_v5.solve(public_task(case))
        verdict = score_case(case, output)
        if verdict["candidate_rescue"]["terminal_pass"]:
            rescue_passes += 1
        if verdict["symptom_only_control"]["terminal_pass"] is False:
            symptom_negative_control_passes += 1
        interaction_partial_control_checks += len(verdict["partial_interaction_controls"])
        if not verdict["pass"]:
            failures.append({
                "seed": case["seed"],
                "domain": case["task"]["domain"],
                "oracle": case["_oracle"],
                "output": output,
                "verdict": verdict,
            })

    expected = len(DOMAINS) * len(KINDS) * len(PATTERNS)
    dimension_ok = (
        dimensions["domains"] == set(DOMAINS)
        and dimensions["kinds"] == set(KINDS)
        and dimensions["patterns"] == {"IDENTIFIED", "INTERACTION"}
    )
    passed = (
        len(cases) == expected
        and not failures
        and scope_cases > 0
        and rescue_passes == expected
        and symptom_negative_control_passes == expected
        and interaction_partial_control_checks == len(DOMAINS) * len(KINDS) * 2
        and dimension_ok
    )
    return {
        "schema": SCHEMA,
        "status": "PASS" if passed else "FAIL_CLOSED",
        "pass": passed,
        "post_freeze_seed": post_freeze_seed,
        "case_count": len(cases),
        "expected_case_count": expected,
        "failures": failures,
        "dimensions": {
            "domains": sorted(dimensions["domains"]),
            "kinds": sorted(dimensions["kinds"]),
            "patterns": sorted(dimensions["patterns"]),
        },
        "explicit_scope_cases": scope_cases,
        "candidate_terminal_rescue_passes": rescue_passes,
        "symptom_only_negative_control_passes": symptom_negative_control_passes,
        "interaction_partial_repair_negative_control_checks": interaction_partial_control_checks,
        "terminal_v3_replayed": False,
        "old_terminal_case_executions_consumed": 0,
        "fresh_supplement_case_executions": len(cases),
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--out")
    args = parser.parse_args()
    result = run_suite(args.seed)
    payload = json.dumps(result, indent=2, sort_keys=True)
    print(payload)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
