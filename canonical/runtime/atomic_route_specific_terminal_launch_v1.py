"""Atomic route-specific terminal launch capsule for Project Brain V2.

This module is deliberately fail-closed.  It does not create a post-freeze
beacon and cannot grant capability or family credit.  Its job is to:

1. derive current executor validity from exact content-addressed receipts,
2. build one immutable prelaunch commitment,
3. shadow-check the complete launch graph without generating terminal cases,
4. accept only genuine same-parent T0/T1/T2/T3 instrumentation receipts, and
5. dispatch the six route-specific direct populations only after canonical
   execution authority is true.

The legacy global-12-slot launcher remains inadmissible under V2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import cad_t0_route_specific_terminal_executor_v1 as cad
from canonical.runtime import direct_route_terminal_executors_v1 as direct
from canonical.runtime import portfolio_multiplex_terminal_instrumentation_v1 as multiplex
from canonical.runtime import saccr_route_specific_terminal_executor_v1 as saccr
from canonical.runtime.terminal_route_execution_plan_validator import validate as validate_plan

SCHEMA = "PROJECT_BRAIN_ATOMIC_ROUTE_SPECIFIC_TERMINAL_LAUNCH_V1"
PLAN = Path("canonical/governance/TERMINAL_ROUTE_EXECUTION_PLAN_V1.json")
MANIFEST = Path("canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json")
AUTHORITY = Path("canonical/governance/TERMINAL_WAVE_EXECUTION_AUTHORITY_V1.json")
PROTOCOL = Path("canonical/governance/GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json")
SELECTION_KERNEL = Path("canonical/governance/GLOBAL_TERMINAL_SELECTION_KERNEL_V1.json")

CAD_ID = "CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001"
SACCR_ID = "SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001"

DIRECT_IDS = {
    CAD_ID,
    SACCR_ID,
    direct.BROWSER_ID,
    direct.DELEGATION_ID,
    direct.TOOL_ID,
    direct.RESEARCH_ID,
}
MULTIPLEX_IDS = {
    multiplex.M0,
    multiplex.NATIVE,
    multiplex.STRUCTURED,
    multiplex.P2,
    multiplex.P3,
    multiplex.P1,
}
EXPECTED_IDS = DIRECT_IDS | MULTIPLEX_IDS

REQUIRED_MULTIPLEX_PARENTS = {
    multiplex.M0: {"T0", "T1", "T2", "T3"},
    multiplex.STRUCTURED: {"T0", "T1"},
    multiplex.P1: {"T0", "T2"},
    multiplex.P2: {"T1"},
    multiplex.NATIVE: {"T1"},
    multiplex.P3: {"T1", "T3"},
}


def _read_json(root: Path, rel: Path | str) -> dict[str, Any]:
    path = root / rel
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(rel))
    return value


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _bound_paths(value: Any):
    if isinstance(value, Mapping):
        if isinstance(value.get("path"), str) and isinstance(value.get("blob_sha"), str):
            yield value["path"], value["blob_sha"]
        for child in value.values():
            yield from _bound_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from _bound_paths(child)


def _verification_path(row: Mapping[str, Any]) -> str | None:
    value = row.get("independent_executor_verification")
    if not isinstance(value, str) or not value:
        value = row.get("executor_independent_verification")
    return value if isinstance(value, str) and value else None


def derive_executor_state(root: Path = Path(".")) -> dict[str, Any]:
    """Recompute executor readiness from current bytes plus independent receipts.

    Hand-maintained status/count fields are treated only as mirrors.
    """
    errors: list[str] = []
    manifest = _read_json(root, MANIFEST)
    routes = manifest.get("routes")
    if not isinstance(routes, list):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["MANIFEST_ROUTES_INVALID"],
            "derived_bound_executor_count": 0,
            "launch_authority": False,
        }

    seen: set[str] = set()
    rows: dict[str, Any] = {}
    valid_count = 0

    for i, row in enumerate(routes):
        if not isinstance(row, Mapping):
            errors.append(f"ROUTE_ROW_INVALID:{i}")
            continue
        bid = row.get("behavior_id")
        if not isinstance(bid, str) or not bid:
            errors.append(f"BEHAVIOR_ID_INVALID:{i}")
            continue
        if bid in seen:
            errors.append("DUPLICATE_BEHAVIOR:" + bid)
            continue
        seen.add(bid)

        local_errors: list[str] = []
        executor = row.get("executor")
        tests = row.get("tests")
        expected_executor = row.get("executor_blob_sha")
        expected_tests = row.get("executor_test_blob_sha")
        verification = _verification_path(row)

        if not all(isinstance(x, str) and x for x in (executor, tests, expected_executor, expected_tests, verification)):
            local_errors.append("BINDING_FIELDS_INCOMPLETE")
            receipt = {}
        else:
            ep = root / executor
            tp = root / tests
            if not ep.is_file():
                local_errors.append("EXECUTOR_MISSING")
            elif _git_blob_sha(ep) != expected_executor:
                local_errors.append("EXECUTOR_BLOB_DRIFT")
            if not tp.is_file():
                local_errors.append("TEST_MISSING")
            elif _git_blob_sha(tp) != expected_tests:
                local_errors.append("TEST_BLOB_DRIFT")

            try:
                receipt = _read_json(root, verification)
            except Exception as exc:
                receipt = {}
                local_errors.append("RECEIPT_READ:" + type(exc).__name__)

            status = str(receipt.get("status", ""))
            if not status.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
                local_errors.append("RECEIPT_NOT_INDEPENDENT_PASS")
            exact = receipt.get("exact_brain_blobs")
            if not isinstance(exact, Mapping):
                local_errors.append("RECEIPT_EXACT_BLOBS_MISSING")
            else:
                if exact.get(executor) != expected_executor:
                    local_errors.append("RECEIPT_EXECUTOR_BLOB_MISMATCH")
                if exact.get(tests) != expected_tests:
                    local_errors.append("RECEIPT_TEST_BLOB_MISMATCH")

        valid = not local_errors
        valid_count += int(valid)
        rows[bid] = {
            "valid": valid,
            "executor": executor,
            "tests": tests,
            "verification": verification,
            "errors": sorted(set(local_errors)),
        }

    if seen != EXPECTED_IDS:
        errors.append(
            "ROUTE_SET_MISMATCH:missing="
            + ",".join(sorted(EXPECTED_IDS - seen))
            + ";extra="
            + ",".join(sorted(seen - EXPECTED_IDS))
        )
    if manifest.get("route_count") != 12:
        errors.append("MANIFEST_ROUTE_COUNT_MIRROR_MISMATCH")
    if manifest.get("bound_executor_count") != valid_count:
        errors.append(
            f"MANIFEST_BOUND_COUNT_MIRROR_MISMATCH:{manifest.get('bound_executor_count')}!={valid_count}"
        )

    passed = not errors and valid_count == 12 and seen == EXPECTED_IDS
    return {
        "schema": SCHEMA,
        "status": "PASS" if passed else "FAIL_CLOSED",
        "pass": passed,
        "derived_bound_executor_count": valid_count,
        "route_count": len(seen),
        "routes": rows,
        "errors": sorted(set(errors)),
        "launch_authority": False,
        "terminal_case_generation_performed": False,
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def build_prelaunch_commitment(root: Path = Path(".")) -> dict[str, Any]:
    """Build a deterministic content-addressed commitment without terminal cases."""
    errors: list[str] = []
    plan = _read_json(root, PLAN)
    plan_verdict = validate_plan(root, plan)
    if plan_verdict.get("pass") is not True:
        errors.append("EXECUTION_PLAN_INVALID")

    manifest = _read_json(root, MANIFEST)
    protocol = _read_json(root, PROTOCOL)
    selection = _read_json(root, SELECTION_KERNEL)
    executor_state = derive_executor_state(root)
    if executor_state.get("pass") is not True:
        errors.append("EXECUTOR_STATE_INVALID")

    active = protocol.get("active_contracts")
    if not isinstance(active, list) or set(active) != EXPECTED_IDS or len(active) != 12:
        errors.append("PROTOCOL_ACTIVE_CONTRACT_SET_MISMATCH")

    files: dict[str, str] = {}

    def bind(rel: str, expected: str | None = None):
        path = root / rel
        if not path.is_file():
            errors.append("COMMITMENT_FILE_MISSING:" + rel)
            return
        actual = _git_blob_sha(path)
        if expected is not None and actual != expected:
            errors.append("COMMITMENT_BLOB_DRIFT:" + rel)
        files[rel] = actual

    bind(str(PLAN))
    bind(str(MANIFEST))
    bind(str(PROTOCOL))
    bind(str(SELECTION_KERNEL))

    for rel, expected in _bound_paths(plan):
        bind(rel, expected)

    routes = manifest.get("routes") if isinstance(manifest.get("routes"), list) else []
    for row in routes:
        if not isinstance(row, Mapping):
            continue
        for path_key, sha_key in (("executor", "executor_blob_sha"), ("tests", "executor_test_blob_sha")):
            rel = row.get(path_key)
            expected = row.get(sha_key)
            if isinstance(rel, str) and isinstance(expected, str):
                bind(rel, expected)
        verification = _verification_path(row)
        if verification:
            bind(verification)

    payload = {
        "schema": "PROJECT_BRAIN_ATOMIC_TERMINAL_PRELAUNCH_COMMITMENT_V1",
        "active_behavior_ids": sorted(EXPECTED_IDS),
        "files": dict(sorted(files.items())),
        "execution_plan_sha256": _canonical_sha256(plan),
        "manifest_sha256": _canonical_sha256(manifest),
        "protocol_sha256": _canonical_sha256(protocol),
        "selection_kernel_sha256": _canonical_sha256(selection),
    }
    commitment = _canonical_sha256(payload)
    passed = not errors and plan_verdict.get("pass") is True and executor_state.get("pass") is True
    return {
        "schema": SCHEMA,
        "status": "PASS" if passed else "FAIL_CLOSED",
        "pass": passed,
        "candidate_package_commitment": commitment if passed else None,
        "commitment_payload": payload,
        "execution_plan_validation": plan_verdict,
        "executor_state": executor_state,
        "errors": sorted(set(errors)),
        "post_freeze_beacon_constructed": False,
        "terminal_case_generation_performed": False,
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def shadow_preflight(root: Path = Path(".")) -> dict[str, Any]:
    """Prove launch wiring as far as possible without consuming fresh reality."""
    commitment = build_prelaunch_commitment(root)
    authority = _read_json(root, AUTHORITY)
    authority_true = authority.get("execution_authority") is True
    ready = bool(commitment.get("pass") and authority_true)
    return {
        "schema": SCHEMA,
        "status": "READY_FOR_ONE_SHOT_TERMINAL_LAUNCH" if ready else "PRELAUNCH_NOT_AUTHORIZED",
        "pass": ready,
        "commitment_valid": commitment.get("pass") is True,
        "candidate_package_commitment": commitment.get("candidate_package_commitment"),
        "derived_bound_executor_count": commitment.get("executor_state", {}).get("derived_bound_executor_count"),
        "canonical_execution_authority": authority_true,
        "authorization": authority.get("authorization"),
        "post_freeze_beacon_constructed": False,
        "terminal_case_generation_performed": False,
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "errors": commitment.get("errors", []),
    }


def validate_parent_observations(
    parent_observations: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    commitment: str,
    beacon: str,
) -> dict[str, Any]:
    """Validate genuine same-parent terminal observations for six multiplex routes."""
    errors: list[str] = []
    if not isinstance(parent_observations, Mapping):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["PARENT_OBSERVATIONS_MAPPING_REQUIRED"],
            "results": {},
        }

    keys = set(parent_observations)
    if keys != MULTIPLEX_IDS:
        errors.append(
            "MULTIPLEX_SET_MISMATCH:missing="
            + ",".join(sorted(MULTIPLEX_IDS - keys))
            + ";extra="
            + ",".join(sorted(keys - MULTIPLEX_IDS))
        )

    results: dict[str, Any] = {}
    for bid in sorted(MULTIPLEX_IDS):
        raw = parent_observations.get(bid)
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
            errors.append("PARENT_OBSERVATIONS_REQUIRED:" + bid)
            continue
        rows = list(raw)
        load_parents: set[str] = set()
        for i, row in enumerate(rows):
            if not isinstance(row, Mapping):
                errors.append(f"PARENT_ROW_INVALID:{bid}:{i}")
                continue
            if row.get("candidate_package_commitment") != commitment:
                errors.append(f"COMMITMENT_MISMATCH:{bid}:{i}")
            if row.get("post_freeze_beacon") != beacon:
                errors.append(f"BEACON_MISMATCH:{bid}:{i}")
            if row.get("load_bearing") is True:
                portfolio = row.get("portfolio")
                if isinstance(portfolio, str):
                    load_parents.add(portfolio)

        missing = REQUIRED_MULTIPLEX_PARENTS[bid] - load_parents
        if missing:
            errors.append("MISSING_LOAD_BEARING_PARENT_COVERAGE:" + bid + ":" + ",".join(sorted(missing)))

        try:
            reduced = multiplex.reduce_behavior_receipts(bid, rows)
        except Exception as exc:
            reduced = {"status": "FAIL_CLOSED", "errors": ["REDUCER_EXCEPTION:" + type(exc).__name__]}
        results[bid] = reduced
        if reduced.get("status") != "PASS_COMPONENT":
            errors.append("MULTIPLEX_REDUCTION_FAIL:" + bid)

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "results": results,
        "errors": sorted(set(errors)),
        "terminal_results_observed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def execute_real(
    *,
    commitment: str,
    beacon: str,
    parent_observations: Mapping[str, Sequence[Mapping[str, Any]]],
    root: Path = Path("."),
) -> dict[str, Any]:
    """One-shot V2 dispatcher.  No branch executes unless every guard passes first."""
    if not isinstance(commitment, str) or not commitment:
        raise ValueError("COMMITMENT_REQUIRED")
    if not isinstance(beacon, str) or not beacon:
        raise ValueError("POST_FREEZE_BEACON_REQUIRED")

    preflight = shadow_preflight(root)
    if preflight.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_PRELAUNCH_NOT_AUTHORIZED",
            "pass": False,
            "preflight": preflight,
            "direct_results": {},
            "multiplex_results": {},
            "terminal_results_observed": 0,
            "fresh_terminal_evidence_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    if commitment != preflight.get("candidate_package_commitment"):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_COMMITMENT_MISMATCH",
            "pass": False,
            "terminal_results_observed": 0,
            "fresh_terminal_evidence_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    parent = validate_parent_observations(parent_observations, commitment=commitment, beacon=beacon)
    if parent.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_PARENT_OBSERVATIONS",
            "pass": False,
            "parent_validation": parent,
            "direct_results": {},
            "multiplex_results": {},
            "terminal_results_observed": 0,
            "fresh_terminal_evidence_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    # Begin direct terminal reality only after every structural/authority/parent guard.
    direct_results: dict[str, Any] = {
        CAD_ID: cad.execute_cad_route(commitment=commitment, beacon=beacon, root=root),
        SACCR_ID: saccr.execute_terminal(
            candidate_package_commitment=commitment,
            post_freeze_beacon=beacon,
            root=root,
        ),
    }
    for bid in (direct.BROWSER_ID, direct.DELEGATION_ID, direct.TOOL_ID, direct.RESEARCH_ID):
        direct_results[bid] = direct.execute_direct_route(bid, commitment=commitment, beacon=beacon)

    direct_pass = all(result.get("pass") is True for result in direct_results.values())
    multiplex_pass = all(
        result.get("status") == "PASS_COMPONENT"
        for result in parent.get("results", {}).values()
    )
    exact_coverage = set(direct_results) == DIRECT_IDS and set(parent.get("results", {})) == MULTIPLEX_IDS
    passed = direct_pass and multiplex_pass and exact_coverage

    return {
        "schema": SCHEMA,
        "status": "PASS" if passed else "FAIL_CLOSED",
        "pass": passed,
        "candidate_package_commitment": commitment,
        "post_freeze_beacon": beacon,
        "direct_results": direct_results,
        "multiplex_results": parent.get("results", {}),
        "exact_12_behavior_coverage": exact_coverage,
        "no_case_replacement": True,
        "no_tuning_replay": True,
        "result_to_runtime_feedback": False,
        "terminal_results_observed": 12,
        "fresh_terminal_evidence_consumed": "ONE_ATOMIC_TERMINAL_WAVE",
        "capability_credit_delta": "DEFER_TO_TERMINAL_REDUCER",
        "family_credit_delta": "DEFER_TO_TERMINAL_REDUCER",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--shadow", action="store_true")
    ap.add_argument("--commitment")
    ap.add_argument("--beacon")
    ap.add_argument("--parent-observations", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    if args.shadow:
        out = shadow_preflight(args.root)
    else:
        if not args.commitment or not args.beacon or args.parent_observations is None:
            ap.error("real launch requires --commitment --beacon --parent-observations")
        parent = json.loads(args.parent_observations.read_text(encoding="utf-8"))
        out = execute_real(
            commitment=args.commitment,
            beacon=args.beacon,
            parent_observations=parent,
            root=args.root,
        )

    text = json.dumps(out, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if out.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
