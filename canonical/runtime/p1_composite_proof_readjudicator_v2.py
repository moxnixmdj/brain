"""Fail-closed P1 composite-proof readjudicator over predeclared semantics.

This module does not modify the Brain candidate, replay Terminal V3, or add a new
P1 semantic requirement. It re-adjudicates the already-frozen P1 check/mutation
set using the exact existing V4 candidate and terminal contract-native scorer.

The only strengthened step is evidence-aware adjudication of two predeclared V4
mutations that the older scorer failed to make load-bearing:
- DROP_PROVENANCE_OR_DEPENDENCY_EDGE
- UNFALSIFIABLE_DIAGNOSIS

All credit remains zero until independent verification binds exact blobs.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import contract_native_proof_suites as terminal_suite
from canonical.runtime import trajectory_failure_typed_ir_candidate_v4 as v4_candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v4 as v4_proof

ROOT = Path(__file__).resolve().parents[2]
BINDING = ROOT / "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
RECON = ROOT / "canonical/governance/P1_COMPOSITE_PROOF_ROLE_RECONCILIATION_V1.json"
SCHEMA = "PROJECT_BRAIN_P1_COMPOSITE_PROOF_READJUDICATOR_V2"
BEHAVIOR = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"NOT_OBJECT:{path}")
    return value


def _visible_failed_evidence(public: Mapping[str, Any], action_id: str) -> list[str]:
    task = public.get("task")
    if not isinstance(task, Mapping):
        return []
    rows = task.get("trajectory")
    if not isinstance(rows, list):
        return []
    out: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping) or row.get("action_id") != action_id:
            continue
        checks = row.get("checks")
        if not isinstance(checks, list):
            continue
        for check in checks:
            if not isinstance(check, Mapping) or check.get("pass") is not False:
                continue
            evidence = check.get("evidence")
            if not isinstance(evidence, list):
                continue
            for item in evidence:
                if isinstance(item, str) and item:
                    out.add(item)
    return sorted(out)


def score_v4_strict(
    case: Mapping[str, Any],
    public: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the frozen V4 oracle plus visibility/load-bearing evidence checks."""
    base = v4_proof.score_case(case, candidate)
    if not base.get("pass"):
        return {**base, "strict_pass": False}

    status = candidate.get("status")
    roots = candidate.get("cause_action_ids")
    if not isinstance(roots, list) or any(not isinstance(x, str) or not x for x in roots):
        return {"pass": False, "strict_pass": False, "reason": "ROOT_SET_SCHEMA_INVALID"}

    if status in {"IDENTIFIED", "INTERACTION"}:
        expected = sorted({e for aid in roots for e in _visible_failed_evidence(public, aid)})
        got = candidate.get("supporting_receipts")
        if (
            not expected
            or not isinstance(got, list)
            or any(not isinstance(x, str) or not x for x in got)
            or sorted(set(got)) != expected
        ):
            return {
                "pass": False,
                "strict_pass": False,
                "reason": "VISIBLE_SUPPORTING_RECEIPTS_NOT_LOAD_BEARING",
                "expected_visible_receipts": expected,
            }
    elif status == "AMBIGUOUS":
        details = candidate.get("candidates")
        if not isinstance(details, list):
            return {"pass": False, "strict_pass": False, "reason": "AMBIGUOUS_CANDIDATE_DETAILS_MISSING"}
        by_action = {
            d.get("action_id"): d
            for d in details
            if isinstance(d, Mapping) and isinstance(d.get("action_id"), str)
        }
        for aid in roots:
            expected = _visible_failed_evidence(public, aid)
            detail = by_action.get(aid)
            got = detail.get("supporting_receipts") if isinstance(detail, Mapping) else None
            if (
                not expected
                or not isinstance(got, list)
                or any(not isinstance(x, str) or not x for x in got)
                or sorted(set(got)) != expected
            ):
                return {
                    "pass": False,
                    "strict_pass": False,
                    "reason": "AMBIGUOUS_VISIBLE_SUPPORTING_RECEIPTS_NOT_LOAD_BEARING",
                    "action_id": aid,
                    "expected_visible_receipts": expected,
                }

    diagnosis = candidate.get("diagnosis")
    if diagnosis is not None:
        if not isinstance(diagnosis, Mapping):
            return {"pass": False, "strict_pass": False, "reason": "DIAGNOSIS_SCHEMA_INVALID"}
        support = diagnosis.get("supporting_receipts")
        all_visible = sorted({e for aid in roots for e in _visible_failed_evidence(public, aid)})
        if (
            diagnosis.get("falsifiable") is not True
            or not isinstance(support, list)
            or not support
            or any(not isinstance(x, str) or not x for x in support)
            or not set(support).issubset(set(all_visible))
        ):
            return {
                "pass": False,
                "strict_pass": False,
                "reason": "UNFALSIFIABLE_OR_UNSUPPORTED_DIAGNOSIS",
            }

    return {**base, "strict_pass": True}


def _partition_exact(binding: Mapping[str, Any], recon: Mapping[str, Any]) -> dict[str, Any]:
    evaluator = binding.get("evaluator")
    if not isinstance(evaluator, Mapping):
        return {"pass": False, "errors": ["BINDING_EVALUATOR_MISSING"]}

    errors: list[str] = []
    for required_key, role_key, label in [
        ("required_checks", "proof_roles", "CHECK"),
        ("required_mutations", "mutation_roles", "MUTATION"),
    ]:
        required = evaluator.get(required_key)
        roles = recon.get(role_key)
        if not isinstance(required, list) or not isinstance(roles, Mapping):
            errors.append(f"{label}_INPUT_INVALID")
            continue
        flat: list[str] = []
        for value in roles.values():
            if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
                errors.append(f"{label}_ROLE_INVALID")
                continue
            flat.extend(value)
        duplicates = sorted({x for x in flat if flat.count(x) > 1})
        missing = sorted(set(required) - set(flat))
        extra = sorted(set(flat) - set(required))
        if duplicates:
            errors.append(f"{label}_OVERLAP:" + ",".join(duplicates))
        if missing:
            errors.append(f"{label}_MISSING:" + ",".join(missing))
        if extra:
            errors.append(f"{label}_EXTRA:" + ",".join(extra))
    return {"pass": not errors, "errors": errors}


def _v4_baseline(case: Mapping[str, Any], public: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate = v4_candidate.solve(public)
    verdict = score_v4_strict(case, public, candidate)
    return candidate, verdict


def mutation_trials() -> dict[str, dict[str, Any]]:
    trials: dict[str, dict[str, Any]] = {}

    # 1. Ignore violated authority/invariant.
    case = v4_proof.generate_case(61001, pattern="SINGLE", domain="BROWSER", kind="AUTHORITY")
    public = copy.deepcopy(v4_proof.public_task(case))
    for row in public["task"]["trajectory"]:
        if row["action_id"] == "A1":
            for check in row["checks"]:
                if check.get("pass") is False:
                    check["pass"] = True
    candidate = v4_candidate.solve(public)
    verdict = score_v4_strict(case, public, candidate)
    trials["IGNORE_VIOLATED_AUTHORITY_OR_INVARIANT"] = {"killed": not verdict.get("pass"), "verdict": verdict}

    # 2. Force a unique cause on an ambiguous trace.
    case = v4_proof.generate_case(61002, pattern="AMBIGUOUS", domain="TOOL_API", kind="SCHEMA")
    public = v4_proof.public_task(case)
    candidate, baseline = _v4_baseline(case, public)
    mutated = copy.deepcopy(candidate)
    mutated.update({
        "status": "IDENTIFIED",
        "cause_action_id": "A1",
        "cause_action_ids": ["A1"],
        "critical_action_id": "A1",
        "mechanism_classes": ["SCHEMA"],
        "supporting_receipts": _visible_failed_evidence(public, "A1"),
        "repair_targets": ["restore:A1:SCHEMA"],
    })
    verdict = score_v4_strict(case, public, mutated)
    trials["FORCE_UNIQUE_CAUSE_ON_NONIDENTIFIABLE_TRACE"] = {
        "baseline_pass": baseline.get("pass") is True,
        "killed": not verdict.get("pass"),
        "verdict": verdict,
    }

    # 3. Drop a causal predecessor from a delayed chain.
    case = v4_proof.generate_case(61003, pattern="DELAYED", domain="FILESYSTEM", kind="DEPENDENCY")
    public = copy.deepcopy(v4_proof.public_task(case))
    for row in public["task"]["trajectory"]:
        if row["action_id"] == "A2":
            row["depends_on"] = []
            row["reads"] = []
    candidate = v4_candidate.solve(public)
    verdict = score_v4_strict(case, public, candidate)
    trials["DROP_CAUSAL_PREDECESSOR_IN_MULTI_STEP_CHAIN"] = {"killed": not verdict.get("pass"), "verdict": verdict}

    # 4. Swap an authority failure class.
    case = v4_proof.generate_case(61004, pattern="SINGLE", domain="BROWSER", kind="AUTHORITY")
    public = copy.deepcopy(v4_proof.public_task(case))
    for row in public["task"]["trajectory"]:
        if row["action_id"] == "A1":
            for check in row["checks"]:
                if check.get("pass") is False:
                    check["kind"] = "SCHEMA"
                    check["id"] = "A1:SCHEMA"
    candidate = v4_candidate.solve(public)
    verdict = score_v4_strict(case, public, candidate)
    trials["SWAP_TOOL_OR_AUTHORITY_FAILURE_CLASS"] = {"killed": not verdict.get("pass"), "verdict": verdict}

    # 5. Drop all visible provenance/support receipts.
    case = v4_proof.generate_case(61005, pattern="SINGLE", domain="RESEARCH", kind="PROVENANCE")
    public = copy.deepcopy(v4_proof.public_task(case))
    for row in public["task"]["trajectory"]:
        for check in row["checks"]:
            if check.get("pass") is False:
                check["evidence"] = []
    candidate = v4_candidate.solve(public)
    old_verdict = v4_proof.score_case(case, candidate)
    verdict = score_v4_strict(case, public, candidate)
    trials["DROP_PROVENANCE_OR_DEPENDENCY_EDGE"] = {
        "old_scorer_passed": old_verdict.get("pass") is True,
        "killed": not verdict.get("pass"),
        "verdict": verdict,
    }

    # 6. Inject an explicitly unfalsifiable diagnosis.
    case = v4_proof.generate_case(61006, pattern="SINGLE", domain="RESEARCH", kind="PROVENANCE")
    public = v4_proof.public_task(case)
    candidate, baseline = _v4_baseline(case, public)
    mutated = copy.deepcopy(candidate)
    mutated["diagnosis"] = {
        "claim": "AN_UNOBSERVABLE_FORCE_CAUSED_THE_FAILURE",
        "falsifiable": False,
        "supporting_receipts": [],
    }
    verdict = score_v4_strict(case, public, mutated)
    trials["UNFALSIFIABLE_DIAGNOSIS"] = {
        "baseline_pass": baseline.get("pass") is True,
        "killed": not verdict.get("pass"),
        "verdict": verdict,
    }

    # Terminal role mutations are already load-bearing in the frozen scorer.
    tcase = terminal_suite.generate_case(BEHAVIOR, seed=62001, difficulty=5)
    gold = terminal_suite.oracle_candidate(tcase)
    base = terminal_suite.score_case(tcase, gold)
    cause = tcase["_oracle"]["cause_step"]

    downstream = dict(gold)
    downstream["cause_step"] = cause + 1
    downstream["repair_id"] = f"repair_{cause + 1}"
    verdict = terminal_suite.score_case(tcase, downstream)
    trials["SELECT_DOWNSTREAM_SYMPTOM"] = {
        "baseline_pass": base.get("pass") is True,
        "killed": not verdict.get("pass"),
        "verdict": verdict,
    }

    later_step = min(cause + 2, len(tcase["task"]["trajectory"]) - 2)
    later = dict(gold)
    later["cause_step"] = later_step
    later["repair_id"] = f"repair_{later_step}"
    verdict = terminal_suite.score_case(tcase, later)
    trials["SELECT_LATER_CORRELATED_STEP"] = {
        "baseline_pass": base.get("pass") is True,
        "killed": not verdict.get("pass"),
        "verdict": verdict,
    }

    no_rescue = dict(gold)
    no_rescue["repair_id"] = f"repair_{cause + 1}"
    verdict = terminal_suite.score_case(tcase, no_rescue)
    trials["REPAIR_TARGET_WITH_NO_RESCUE"] = {
        "baseline_pass": base.get("pass") is True,
        "killed": not verdict.get("pass"),
        "verdict": verdict,
    }

    return trials


def evaluate() -> dict[str, Any]:
    binding = _load(BINDING)
    recon = _load(RECON)
    errors: list[str] = []

    if binding.get("behavior_id") != BEHAVIOR or recon.get("behavior_id") != BEHAVIOR:
        errors.append("BEHAVIOR_ID_DRIFT")

    partition = _partition_exact(binding, recon)
    if not partition["pass"]:
        errors.extend(partition["errors"])

    # Re-adjudicate the complete existing V4 synthetic cross product with the
    # stricter evidence-aware scorer. This is not Terminal V3 replay.
    baseline_failures: list[int] = []
    for case in v4_proof.suite_cases():
        public = v4_proof.public_task(case)
        candidate = v4_candidate.solve(public)
        verdict = score_v4_strict(case, public, candidate)
        if not verdict.get("pass"):
            baseline_failures.append(case["seed"])

    trials = mutation_trials()
    required_mutations = set(binding["evaluator"]["required_mutations"])
    killed = {mid for mid, row in trials.items() if row.get("killed") is True}
    missing_trials = sorted(required_mutations - set(trials))
    surviving = sorted(required_mutations - killed)

    if baseline_failures:
        errors.append("STRICT_V4_BASELINE_REGRESSION")
    if missing_trials:
        errors.append("MUTATION_TRIALS_MISSING:" + ",".join(missing_trials))
    if surviving:
        errors.append("MUTATIONS_SURVIVED:" + ",".join(surviving))

    semantic_repair_complete = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__PREDECLARED_P1_MUTATIONS_KILLED__EXACT_PARTITION__INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT"
            if semantic_repair_complete
            else "FAIL_CLOSED__P1_READJUDICATION_INCOMPLETE"
        ),
        "behavior_id": BEHAVIOR,
        "partition_exact": partition["pass"],
        "strict_v4_baseline_case_count": len(v4_proof.suite_cases()),
        "strict_v4_baseline_failures": baseline_failures,
        "required_mutation_count": len(required_mutations),
        "mutation_trial_count": len(trials),
        "killed_mutation_count": len(killed),
        "surviving_required_mutations": surviving,
        "mutation_results": trials,
        "errors": sorted(set(errors)),
        "semantic_repair_complete": semantic_repair_complete,
        "candidate_composite_restoration_admissible_after_independent_verification": semantic_repair_complete,
        "whole_p1_contract_restored": False,
        "independent_verification_required": True,
        "terminal_results_replayed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "incremental_spend_usd": 0,
        "predicate_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "rule": (
            "READJUDICATE_ONLY_PREDECLARED_P1_CHECKS_AND_MUTATIONS__"
            "NO_CANDIDATE_CHANGE__NO_TERMINAL_V3_REPLAY__"
            "NO_CREDIT_BEFORE_INDEPENDENT_EXACT_BLOB_VERIFICATION"
        ),
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["semantic_repair_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
