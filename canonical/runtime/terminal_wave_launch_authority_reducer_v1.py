"""Fail-closed launch-authority reducer for the route-specific terminal wave.

Launch authority is derived, never trusted from writable booleans. The reducer
requires:
1. current four-portfolio prequalification pass;
2. exact 12-contract active basis;
3. exact 12-route executor manifest;
4. current executor + test Git blob identities;
5. independent public-runner receipt for every current executor blob;
6. four real independently verified T0/T1/T2/T3 parent-case producers plus the exact frozen producer schedule binding;\n7. zero terminal results/evidence before launch.

This reducer grants no capability or family credit and does not create a beacon.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from canonical.runtime import terminal_prequalification_reducer as prequal

SCHEMA = "PROJECT_BRAIN_TERMINAL_WAVE_LAUNCH_AUTHORITY_VERDICT_V1"
MANIFEST = "canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json"
BASIS = "canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json"
PARENT_PRODUCERS = "canonical/governance/TERMINAL_PARENT_CASE_PRODUCER_MANIFEST_V1.json"
PARENT_PORTFOLIOS = ("T0", "T1", "T2", "T3")


def _load(root: Path, rel: str) -> dict[str, Any]:
    value = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(rel + ":NOT_OBJECT")
    return value


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + bytes([0]) + data).hexdigest()


def _independent_pass_status(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    u = value.upper()
    if any(x in u for x in ("PENDING", "STALE", "FAIL_CLOSED", "FAILURE")):
        return False
    return "INDEPENDENT" in u and "PASS" in u


def evaluate_documents(
    prequalification: dict[str, Any],
    manifest: dict[str, Any],
    basis: dict[str, Any],
    parent_producers: dict[str, Any],
    *,
    load_verification: Callable[[str], dict[str, Any]],
    blob_sha: Callable[[str], str | None],
) -> dict[str, Any]:
    errors: list[str] = []

    if prequalification.get("pass") is not True or prequalification.get("execution_authority") is not True:
        errors.append("PREQUALIFICATION_NOT_AUTHORIZED")

    producer_rows = parent_producers.get("portfolios")
    if not isinstance(producer_rows, dict):
        producer_rows = {}
        errors.append("PARENT_PRODUCER_PORTFOLIOS_INVALID")
    if set(producer_rows) != set(PARENT_PORTFOLIOS):
        errors.append("PARENT_PRODUCER_PORTFOLIO_SET_MISMATCH")

    required_semantic_flags = (
        "real_parent_case_producer",
        "post_freeze_selection_only",
        "same_case_instrumentation",
        "hidden_oracle_isolated",
        "parent_terminal_acceptance_derived",
        "direct_instrumentation_verdict_derived",
        "no_stub_receipts",
    )
    for portfolio in PARENT_PORTFOLIOS:
        row = producer_rows.get(portfolio)
        if not isinstance(row, dict):
            errors.append("PARENT_PRODUCER_MISSING:" + portfolio)
            continue
        if not _independent_pass_status(row.get("status")):
            errors.append("PARENT_PRODUCER_STATUS_NOT_CURRENT_INDEPENDENT_PASS:" + portfolio)
        for flag in required_semantic_flags:
            if row.get(flag) is not True:
                errors.append("PARENT_PRODUCER_SEMANTIC_FLAG_MISSING:" + portfolio + ":" + flag)

        producer = row.get("producer")
        tests = row.get("tests")
        producer_sha = row.get("producer_blob_sha")
        test_sha = row.get("test_blob_sha")
        if not all(isinstance(x, str) and x for x in (producer, tests, producer_sha, test_sha)):
            errors.append("PARENT_PRODUCER_BINDING_FIELDS_MISSING:" + portfolio)
            continue
        if blob_sha(producer) != producer_sha:
            errors.append("PARENT_PRODUCER_BLOB_DRIFT:" + portfolio)
        if blob_sha(tests) != test_sha:
            errors.append("PARENT_PRODUCER_TEST_BLOB_DRIFT:" + portfolio)

        receipt_path = row.get("independent_verification")
        if not isinstance(receipt_path, str) or not receipt_path:
            errors.append("PARENT_PRODUCER_INDEPENDENT_RECEIPT_MISSING:" + portfolio)
            continue
        try:
            receipt = load_verification(receipt_path)
        except Exception:
            errors.append("PARENT_PRODUCER_INDEPENDENT_RECEIPT_UNREADABLE:" + portfolio)
            continue
        if not _independent_pass_status(receipt.get("status")):
            errors.append("PARENT_PRODUCER_INDEPENDENT_RECEIPT_NOT_PASS:" + portfolio)
        if receipt.get("terminal_results_observed", 0) != 0:
            errors.append("PARENT_PRODUCER_RECEIPT_TERMINAL_RESULTS_NONZERO:" + portfolio)
        if receipt.get("fresh_terminal_evidence_consumed", 0) != 0:
            errors.append("PARENT_PRODUCER_RECEIPT_FRESH_TERMINAL_EVIDENCE_NONZERO:" + portfolio)
        exact = receipt.get("exact_brain_blobs")
        if not isinstance(exact, dict):
            errors.append("PARENT_PRODUCER_RECEIPT_EXACT_BLOBS_MISSING:" + portfolio)
        else:
            if exact.get(producer) != producer_sha:
                errors.append("PARENT_PRODUCER_RECEIPT_BLOB_NOT_CURRENT:" + portfolio)
            if exact.get(tests) != test_sha:
                errors.append("PARENT_PRODUCER_RECEIPT_TEST_BLOB_NOT_CURRENT:" + portfolio)
            runner_binding = row.get("runner_binding")
            if not isinstance(runner_binding, str) or not runner_binding:
                errors.append("PARENT_PRODUCER_RUNNER_BINDING_MISSING:" + portfolio)
            else:
                expected_binding_sha = exact.get(runner_binding)
                if not isinstance(expected_binding_sha, str) or not expected_binding_sha:
                    errors.append("PARENT_PRODUCER_RECEIPT_BINDING_BLOB_MISSING:" + portfolio)
                elif blob_sha(runner_binding) != expected_binding_sha:
                    errors.append("PARENT_PRODUCER_RUNNER_BINDING_BLOB_DRIFT:" + portfolio)
        verified = set(receipt.get("verified") or ())
        needed = {
            "REAL_PARENT_CASE_PRODUCER",
            "POST_FREEZE_SELECTION_ONLY",
            "SAME_CASE_INSTRUMENTATION",
            "PARENT_TERMINAL_ACCEPTANCE_DERIVED",
            "DIRECT_INSTRUMENTATION_VERDICT_DERIVED",
            "NO_STUB_RECEIPTS",
            "ZERO_TERMINAL_CASES_CONSUMED",
        }
        missing_verified = sorted(needed - verified)
        if missing_verified:
            errors.append(
                "PARENT_PRODUCER_RECEIPT_SEMANTICS_INCOMPLETE:"
                + portfolio
                + ":"
                + ",".join(missing_verified)
            )

    routes = manifest.get("routes")
    contracts = basis.get("contracts")
    if not isinstance(routes, list):
        routes = []
        errors.append("EXECUTOR_ROUTES_INVALID")
    if not isinstance(contracts, list):
        contracts = []
        errors.append("ACTIVE_BASIS_CONTRACTS_INVALID")

    route_ids = [r.get("behavior_id") for r in routes if isinstance(r, dict)]
    basis_ids = [r.get("behavior_id") for r in contracts if isinstance(r, dict)]
    if len(route_ids) != len(routes) or any(not isinstance(x, str) or not x for x in route_ids):
        errors.append("EXECUTOR_ROUTE_IDS_INVALID")
    if len(basis_ids) != len(contracts) or any(not isinstance(x, str) or not x for x in basis_ids):
        errors.append("ACTIVE_BASIS_IDS_INVALID")
    if len(set(route_ids)) != len(route_ids):
        errors.append("EXECUTOR_ROUTE_IDS_DUPLICATE")
    if len(set(basis_ids)) != len(basis_ids):
        errors.append("ACTIVE_BASIS_IDS_DUPLICATE")
    if set(route_ids) != set(basis_ids):
        errors.append("EXECUTOR_ROUTE_SET_MISMATCH")
    if len(set(route_ids)) != 12:
        errors.append("EXECUTOR_ROUTE_COUNT_NOT_12")

    for row in contracts:
        if not isinstance(row, dict):
            continue
        bid = str(row.get("behavior_id"))
        if row.get("proof_state") != "TERMINAL_ROUTE_FROZEN_ADMISSIBLE":
            errors.append("BASIS_ROUTE_NOT_ADMISSIBLE:" + bid)
        blockers = row.get("blockers")
        if not isinstance(blockers, list) or blockers:
            errors.append("BASIS_ROUTE_BLOCKED:" + bid)

    if manifest.get("route_count") != 12:
        errors.append("MANIFEST_ROUTE_COUNT_NOT_12")
    if manifest.get("implemented_executor_count") != 12:
        errors.append("MANIFEST_IMPLEMENTED_EXECUTOR_COUNT_NOT_12")
    if manifest.get("bound_executor_count") != 12:
        errors.append("MANIFEST_BOUND_EXECUTOR_COUNT_NOT_12")
    # launch_authority is OUTPUT, never consumed as a prerequisite.
    if manifest.get("terminal_results_observed", 0) != 0:
        errors.append("MANIFEST_TERMINAL_RESULTS_ALREADY_OBSERVED")
    if manifest.get("fresh_terminal_evidence_consumed", 0) != 0:
        errors.append("MANIFEST_FRESH_TERMINAL_EVIDENCE_NONZERO")

    for row in routes:
        if not isinstance(row, dict):
            continue
        bid = str(row.get("behavior_id"))
        status = row.get("executor_status")
        if not _independent_pass_status(status):
            errors.append("EXECUTOR_STATUS_NOT_CURRENT_INDEPENDENT_PASS:" + bid)

        executor = row.get("executor")
        tests = row.get("tests")
        executor_sha = row.get("executor_blob_sha")
        test_sha = row.get("executor_test_blob_sha")
        if not all(isinstance(x, str) and x for x in (executor, tests, executor_sha, test_sha)):
            errors.append("EXECUTOR_BINDING_FIELDS_MISSING:" + bid)
            continue

        actual_exec = blob_sha(executor)
        actual_test = blob_sha(tests)
        if actual_exec != executor_sha:
            errors.append("EXECUTOR_BLOB_DRIFT:" + bid)
        if actual_test != test_sha:
            errors.append("EXECUTOR_TEST_BLOB_DRIFT:" + bid)

        receipt_path = (
            row.get("independent_executor_verification")
            or row.get("executor_independent_verification")
        )
        if not isinstance(receipt_path, str) or not receipt_path:
            errors.append("EXECUTOR_INDEPENDENT_RECEIPT_MISSING:" + bid)
            continue
        try:
            receipt = load_verification(receipt_path)
        except Exception:
            errors.append("EXECUTOR_INDEPENDENT_RECEIPT_UNREADABLE:" + bid)
            continue

        if not _independent_pass_status(receipt.get("status")):
            errors.append("EXECUTOR_INDEPENDENT_RECEIPT_NOT_PASS:" + bid)
        if receipt.get("terminal_results_observed", 0) != 0:
            errors.append("EXECUTOR_RECEIPT_TERMINAL_RESULTS_NONZERO:" + bid)
        if receipt.get("fresh_terminal_evidence_consumed", 0) != 0:
            errors.append("EXECUTOR_RECEIPT_FRESH_TERMINAL_EVIDENCE_NONZERO:" + bid)

        exact = receipt.get("exact_brain_blobs")
        if not isinstance(exact, dict):
            errors.append("EXECUTOR_RECEIPT_EXACT_BLOBS_MISSING:" + bid)
        else:
            if exact.get(executor) != executor_sha:
                errors.append("EXECUTOR_RECEIPT_BLOB_NOT_CURRENT:" + bid)
            if exact.get(tests) != test_sha:
                errors.append("EXECUTOR_RECEIPT_TEST_BLOB_NOT_CURRENT:" + bid)

        if row.get("terminal_result_status") not in (None, "NOT_EXECUTED"):
            errors.append("EXECUTOR_ROUTE_ALREADY_EXECUTED:" + bid)

    errors = sorted(set(errors))
    passed = not errors
    return {
        "schema": SCHEMA,
        "pass": passed,
        "launch_authority": passed,
        "execution_authority": passed,
        "authorization": "T0_T1_T2_T3_ROUTE_SPECIFIC_PARALLEL_TERMINAL_WAVE" if passed else "NONE",
        "failed_predicates": errors,
        "route_count": len(set(route_ids)),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "rule": "DERIVE_LAUNCH_ONLY_FROM_CURRENT_PREQUALIFICATION__EXACT_CURRENT_INDEPENDENTLY_VERIFIED_EXECUTOR_BINDINGS__AND_FOUR_REAL_INDEPENDENTLY_VERIFIED_PARENT_CASE_PRODUCERS__WRITABLE_AUTHORITY_FLAGS_ARE_NONAUTHORITATIVE",
    }


def evaluate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    try:
        pre = prequal.evaluate(root)
        manifest = _load(root, MANIFEST)
        basis = _load(root, BASIS)
        parent_producers = _load(root, PARENT_PRODUCERS)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "launch_authority": False,
            "execution_authority": False,
            "authorization": "NONE",
            "failed_predicates": ["PRIMARY_INPUT_READ:" + type(exc).__name__],
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    def load_receipt(rel: str) -> dict[str, Any]:
        return _load(root, rel)

    def blob(rel: str) -> str | None:
        path = root / rel
        return _git_blob_sha(path) if path.is_file() else None

    return evaluate_documents(
        pre,
        manifest,
        basis,
        parent_producers,
        load_verification=load_receipt,
        blob_sha=blob,
    )


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root", type=Path, nargs="?", default=Path("."))
    out = evaluate(ap.parse_args().repo_root)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
