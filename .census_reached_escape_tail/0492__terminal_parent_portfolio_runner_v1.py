"""Concrete zero-cost parent-portfolio runner for the terminal T0/T1/T2/T3 wave.

The runner materializes the six non-standalone multiplex behaviors from their
already-frozen information-safe proof suites. CAD is not executed twice: its T0
parent receipt reuses the single deduplicated direct CAD terminal result.

Real execution is fail-closed on global launch authority. Preterminal rehearsal
uses fixed sentinel commitment/beacon values and is explicitly non-evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import contract_native_brain_candidate as contract_candidate
from canonical.runtime import contract_native_proof_suites as contract_suite
from canonical.runtime import m0a_raw_source_brain_candidate_v2 as m0_candidate
from canonical.runtime import m0a_raw_source_terminal_suite_v2 as m0_suite
from canonical.runtime import native_artifact_cross_format_candidate_v1 as native_candidate
from canonical.runtime import native_artifact_cross_format_proof_v1 as native_suite
from canonical.runtime import portfolio_multiplex_terminal_instrumentation_v1 as multiplex

SCHEMA = "PROJECT_BRAIN_TERMINAL_PARENT_PORTFOLIO_RUNNER_V1"
ROOT = Path(__file__).resolve().parents[2]
BINDING_PATH = "canonical/governance/TERMINAL_PARENT_PORTFOLIO_RUNNER_BINDING_V1.json"
AUTHORITY_PATH = "canonical/governance/TERMINAL_WAVE_EXECUTION_AUTHORITY_V1.json"
MANIFEST_PATH = "canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json"

PORTFOLIOS = ("T0", "T1", "T2", "T3")
CAD = "CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001"
M0 = "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001"
NATIVE = "NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001"
STRUCTURED = "STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001"
P1 = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
P2 = "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
P3 = "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"

REHEARSAL_COMMITMENT = "PROJECT_BRAIN_PRETERMINAL_REHEARSAL_COMMITMENT_V1"
REHEARSAL_BEACON = "PROJECT_BRAIN_PRETERMINAL_REHEARSAL_BEACON_V1"


def _load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(rel + ":NOT_OBJECT")
    return value


def _git_blob_sha(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + bytes([0]) + data
    ).hexdigest()


def derive_seed(commitment: str, beacon: str, case_id: str) -> int:
    if not all(isinstance(x, str) and x for x in (commitment, beacon, case_id)):
        raise ValueError("NONEMPTY_SEED_BINDINGS_REQUIRED")
    raw = (
        b"PROJECT_BRAIN_TERMINAL_V2\0"
        + commitment.encode()
        + b"\0"
        + beacon.encode()
        + b"\0"
        + case_id.encode()
    )
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big", signed=False)


def static_preflight() -> dict[str, Any]:
    errors: list[str] = []
    try:
        binding = _load(BINDING_PATH)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["BINDING_READ:" + type(exc).__name__],
            "terminal_result": False,
        }

    exact = binding.get("exact_brain_blobs")
    if not isinstance(exact, dict):
        errors.append("EXACT_BLOBS_MISSING")
        exact = {}
    for rel, expected in sorted(exact.items()):
        try:
            actual = _git_blob_sha(str(rel))
        except Exception as exc:
            errors.append("BOUND_BLOB_READ:" + str(rel) + ":" + type(exc).__name__)
            continue
        if actual != expected:
            errors.append("BOUND_BLOB_DRIFT:" + str(rel))

    schedules = binding.get("schedules")
    required = {M0, NATIVE, STRUCTURED, P1, P2, P3, CAD}
    if not isinstance(schedules, dict) or set(schedules) != required:
        errors.append("SCHEDULE_SET_MISMATCH")

    expected_bound = set(multiplex.bound_behavior_ids())
    if expected_bound != required:
        errors.append("MULTIPLEX_BINDING_SET_MISMATCH")

    for behavior_id, row in multiplex.BINDINGS.items():
        parents = tuple(row.get("portfolios") or ())
        if not parents or any(p not in PORTFOLIOS for p in parents):
            errors.append("INVALID_PARENT_BINDING:" + behavior_id)

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "bound_behavior_ids": sorted(required),
        "terminal_result": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def _real_execution_authorized() -> None:
    authority = _load(AUTHORITY_PATH)
    manifest = _load(MANIFEST_PATH)
    if authority.get("execution_authority") is not True:
        raise ValueError("GLOBAL_EXECUTION_AUTHORITY_REQUIRED")
    if manifest.get("launch_authority") is not True:
        raise ValueError("ROUTE_SPECIFIC_LAUNCH_AUTHORITY_REQUIRED")
    if manifest.get("bound_executor_count") != 12:
        raise ValueError("TWELVE_BOUND_EXECUTORS_REQUIRED")
    if authority.get("terminal_results_observed", 0) != 0:
        raise ValueError("TERMINAL_RESULTS_ALREADY_OBSERVED")
    if authority.get("fresh_terminal_evidence_consumed", 0) != 0:
        raise ValueError("FRESH_TERMINAL_EVIDENCE_ALREADY_CONSUMED")


def _case_id(behavior_id: str, portfolio: str, index: int) -> str:
    return f"{behavior_id}::PARENT_{portfolio}_V1::slot::{index:04d}"


def _run_m0(portfolio: str, commitment: str, beacon: str, count: int) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    by_class: dict[str, int] = {}
    for i in range(count):
        cid = _case_id(M0, portfolio, i)
        seed = derive_seed(commitment, beacon, cid)
        case = m0_suite.generate_case(seed, i)
        by_class[str(case.get("case_class"))] = by_class.get(str(case.get("case_class")), 0) + 1
        public = m0_suite.public_task(case)
        try:
            candidate = m0_candidate.solve(public)
            verdict = m0_suite.score_case(case, candidate)
        except Exception as exc:
            verdict = {"pass": False, "reason": "EXCEPTION:" + type(exc).__name__}
        if verdict.get("pass") is not True:
            failures.append({"case_id": cid, "reason": verdict.get("reason")})
    return {
        "behavior_id": M0,
        "pass": not failures,
        "case_count": count,
        "case_classes": by_class,
        "failure_count": len(failures),
        "failures": failures[:20],
    }


def _run_contract_native(
    behavior_id: str,
    portfolio: str,
    commitment: str,
    beacon: str,
    count: int,
) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    by_difficulty = {str(i): 0 for i in range(1, 6)}
    for i in range(count):
        difficulty = 1 + (i % 5)
        by_difficulty[str(difficulty)] += 1
        cid = _case_id(behavior_id, portfolio, i)
        seed = derive_seed(commitment, beacon, cid)
        case = contract_suite.generate_case(behavior_id, seed, difficulty)
        public = contract_suite.public_task(case)
        try:
            candidate = contract_candidate.solve(public)
            verdict = contract_suite.score_case(case, candidate)
        except Exception as exc:
            verdict = {"pass": False, "reason": "EXCEPTION:" + type(exc).__name__}
        if verdict.get("pass") is not True:
            failures.append({
                "case_id": cid,
                "difficulty": difficulty,
                "reason": verdict.get("reason") or verdict.get("reasons"),
            })
    return {
        "behavior_id": behavior_id,
        "pass": not failures,
        "case_count": count,
        "difficulty_counts": by_difficulty,
        "failure_count": len(failures),
        "failures": failures[:20],
    }


def _run_native(portfolio: str, commitment: str, beacon: str, count: int) -> dict[str, Any]:
    formats = tuple(native_suite.FORMATS)
    if count % len(formats) != 0:
        raise ValueError("NATIVE_COUNT_MUST_COVER_FORMATS_EVENLY")
    failures: list[dict[str, Any]] = []
    by_format = {fmt: 0 for fmt in formats}
    for i in range(count):
        fmt = formats[i % len(formats)]
        by_format[fmt] += 1
        cid = _case_id(NATIVE, portfolio, i)
        seed = derive_seed(commitment, beacon, cid)
        case = native_suite.generate_case(fmt, seed)
        public = native_suite.public_task(case)
        try:
            candidate = native_candidate.solve(public)
            verdict = native_suite.score_case(case, candidate)
        except Exception as exc:
            verdict = {"pass": False, "reason": "EXCEPTION:" + type(exc).__name__}
        if verdict.get("pass") is not True:
            failures.append({"case_id": cid, "format": fmt, "reason": verdict.get("reason")})
    return {
        "behavior_id": NATIVE,
        "pass": not failures,
        "case_count": count,
        "format_counts": by_format,
        "failure_count": len(failures),
        "failures": failures[:20],
    }


def _run_behavior(
    behavior_id: str,
    portfolio: str,
    *,
    commitment: str,
    beacon: str,
    direct_results: Mapping[str, Mapping[str, Any]],
    schedules: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    schedule = schedules[behavior_id]
    count = int(schedule.get("case_count", 0))
    if behavior_id == CAD:
        result = direct_results.get(CAD)
        if not isinstance(result, Mapping):
            return {"behavior_id": CAD, "pass": False, "reason": "CAD_DIRECT_RESULT_REQUIRED"}
        return {
            "behavior_id": CAD,
            "pass": result.get("pass") is True and result.get("terminal_result") is True,
            "case_count": int(result.get("case_count", result.get("sample_count", 128)) or 128),
            "reused_direct_result": True,
        }
    if behavior_id == M0:
        return _run_m0(portfolio, commitment, beacon, count)
    if behavior_id == NATIVE:
        return _run_native(portfolio, commitment, beacon, count)
    if behavior_id in {STRUCTURED, P1, P2, P3}:
        return _run_contract_native(behavior_id, portfolio, commitment, beacon, count)
    return {"behavior_id": behavior_id, "pass": False, "reason": "UNSUPPORTED_MULTIPLEX_BEHAVIOR"}


def _run_portfolio(
    portfolio: str,
    *,
    commitment: str,
    beacon: str,
    direct_results: Mapping[str, Mapping[str, Any]],
    require_authority: bool,
) -> dict[str, Any]:
    if portfolio not in PORTFOLIOS:
        raise ValueError("UNKNOWN_PORTFOLIO:" + str(portfolio))
    if not isinstance(direct_results, Mapping):
        raise ValueError("DIRECT_RESULTS_MAPPING_REQUIRED")
    preflight = static_preflight()
    if not preflight["pass"]:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_PREPARE",
            "pass": False,
            "portfolio": portfolio,
            "preflight": preflight,
            "receipts": [],
            "terminal_result": False,
        }
    if require_authority:
        _real_execution_authorized()

    binding = _load(BINDING_PATH)
    schedules = binding["schedules"]
    behaviors = sorted(
        behavior_id
        for behavior_id, row in multiplex.BINDINGS.items()
        if portfolio in tuple(row.get("portfolios") or ())
    )
    component_results = {
        behavior_id: _run_behavior(
            behavior_id,
            portfolio,
            commitment=commitment,
            beacon=beacon,
            direct_results=direct_results,
            schedules=schedules,
        )
        for behavior_id in behaviors
    }
    parent_pass = bool(component_results) and all(
        row.get("pass") is True for row in component_results.values()
    )

    receipts = []
    for behavior_id in behaviors:
        component = component_results[behavior_id]
        receipts.append({
            "behavior_id": behavior_id,
            "portfolio": portfolio,
            "case_id": f"{portfolio}::{behavior_id}::aggregate::{component.get('case_count', 0)}",
            "candidate_package_commitment": commitment,
            "post_freeze_beacon": beacon,
            "binding_blob": multiplex.BINDINGS[behavior_id]["binding_blob"],
            "load_bearing": True,
            "direct_instrumentation_pass": component.get("pass") is True,
            "parent_terminal_acceptance_pass": parent_pass,
            "case_replaced": False,
            "tuning_replay": False,
            "result_to_runtime_feedback": False,
            "candidate_visible_keys": ["PUBLIC_TASK_PAYLOAD_ONLY"],
            "claims_behavior_credit": False,
        })

    return {
        "schema": SCHEMA,
        "status": "PASS" if parent_pass else "FAIL_CLOSED",
        "pass": parent_pass,
        "portfolio": portfolio,
        "component_results": component_results,
        "receipts": receipts,
        "case_replacement": False,
        "tuning_replay": False,
        "terminal_result": require_authority,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def execute_parent_portfolio(
    portfolio: str,
    *,
    commitment: str,
    beacon: str,
    direct_results: Mapping[str, Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Real terminal execution entrypoint. Global launch authority is mandatory."""
    out = _run_portfolio(
        portfolio,
        commitment=commitment,
        beacon=beacon,
        direct_results=direct_results,
        require_authority=True,
    )
    # A failing parent observation is terminal evidence, not an orchestration
    # exception. Return its fail-closed receipts so the launcher can continue
    # executing the remaining frozen parent portfolios exactly once and reduce
    # the whole wave without replacement or tuning replay.
    return list(out["receipts"])


def rehearse_parent_portfolio(portfolio: str) -> dict[str, Any]:
    """Zero-terminal-evidence rehearsal on sentinel seeds only."""
    fake_direct = {
        CAD: {
            "behavior_id": CAD,
            "pass": True,
            "terminal_result": True,
            "case_count": 128,
            "preterminal_stub": True,
        }
    }
    return _run_portfolio(
        portfolio,
        commitment=REHEARSAL_COMMITMENT,
        beacon=REHEARSAL_BEACON,
        direct_results=fake_direct,
        require_authority=False,
    )


def rehearse_all_portfolios() -> dict[str, Any]:
    rows = {p: rehearse_parent_portfolio(p) for p in PORTFOLIOS}
    passed = all(row.get("pass") is True for row in rows.values())
    return {
        "schema": SCHEMA,
        "status": "PASS" if passed else "FAIL_CLOSED",
        "pass": passed,
        "portfolios": rows,
        "terminal_result": False,
        "fresh_terminal_evidence_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(rehearse_all_portfolios(), indent=2, sort_keys=True))
