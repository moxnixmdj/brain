"""Fail-closed integrity guard for the independently authorized terminal-wave world.

The latest independent authority-derivation receipt binds exact Git blobs for the
registry, active proof basis, V2 population protocol, and prequalification manifest.
This guard enforces those bindings before any terminal launcher may run.

It consumes no terminal cases and grants no capability/family credit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

RECEIPT = Path("canonical/verification/TERMINAL_AUTHORITY_DERIVATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
AUTHORITY = Path("canonical/governance/TERMINAL_WAVE_EXECUTION_AUTHORITY_V1.json")
SCHEMA = "PROJECT_BRAIN_TERMINAL_AUTHORITY_INTEGRITY_GUARD_V1"

REQUIRED = (
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json",
    "canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json",
    "canonical/governance/GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json",
    "canonical/governance/EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1.json",
)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("NOT_OBJECT:" + str(path))
    return obj


def evaluate(root: Path = Path(".")) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []
    try:
        receipt = _load(root / RECEIPT)
        authority = _load(root / AUTHORITY)
    except Exception as exc:
        return {
            "schema": SCHEMA, "pass": False, "launch_integrity": False,
            "errors": ["CONTROL_READ_FAILURE:" + type(exc).__name__],
            "terminal_results_observed": 0, "fresh_terminal_evidence_consumed": 0,
            "capability_credit_delta": 0, "family_credit_delta": 0,
        }

    if not str(receipt.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("AUTHORITY_RECEIPT_NOT_INDEPENDENT_PASS")
    reducer = receipt.get("reducer_output")
    if not isinstance(reducer, dict) or reducer.get("pass") is not True or reducer.get("execution_authority") is not True:
        errors.append("AUTHORITY_RECEIPT_REDUCER_NOT_PASS")
    if reducer.get("authorization") != "T0_T1_T2_T3_PARALLEL_TERMINAL_WAVE":
        errors.append("AUTHORITY_RECEIPT_AUTHORIZATION_MISMATCH")
    if authority.get("execution_authority") is not True:
        errors.append("CURRENT_EXECUTION_AUTHORITY_FALSE")
    if authority.get("terminal_results_observed") != 0:
        errors.append("TERMINAL_RESULTS_ALREADY_OBSERVED")
    if authority.get("fresh_terminal_evidence_consumed") != 0:
        errors.append("FRESH_TERMINAL_EVIDENCE_ALREADY_CONSUMED")

    exact = receipt.get("exact_brain_blobs")
    if not isinstance(exact, dict):
        exact = {}
        errors.append("EXACT_BRAIN_BLOBS_INVALID")

    rows = []
    for rel in REQUIRED:
        expected = exact.get(rel)
        if not isinstance(expected, str) or not expected:
            errors.append("EXPECTED_BLOB_MISSING:" + rel)
            continue
        try:
            observed = git_blob_sha((root / rel).read_bytes())
        except Exception as exc:
            errors.append("BOUND_FILE_READ_FAILURE:" + rel + ":" + type(exc).__name__)
            continue
        match = observed == expected
        if not match:
            errors.append("BOUND_BLOB_DRIFT:" + rel + ":" + observed + "!=" + expected)
        rows.append({"path": rel, "expected_blob_sha": expected, "observed_blob_sha": observed, "match": match})

    conditions = authority.get("conditions")
    required_conditions = {
        "CURRENT_ACTIVE_CONTRACT_REGISTRY_EXACTLY_MATCHES_AUTHORIZED_RECEIPT",
        "CURRENT_ACTIVE_TERMINAL_PROOF_BASIS_EXACTLY_MATCHES_AUTHORIZED_RECEIPT",
        "CURRENT_TERMINAL_POPULATION_PROTOCOL_EXACTLY_MATCHES_AUTHORIZED_RECEIPT",
        "CURRENT_PREQUALIFICATION_MANIFEST_EXACTLY_MATCHES_AUTHORIZED_RECEIPT",
    }
    if not isinstance(conditions, list) or not required_conditions.issubset(set(conditions)):
        errors.append("AUTHORITY_EXACT_BINDING_CONDITIONS_MISSING")

    passed = not errors
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": "PASS_EXACT_AUTHORIZED_WORLD" if passed else "FAIL_CLOSED",
        "launch_integrity": passed,
        "bound_files": rows,
        "errors": sorted(set(errors)),
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "rule": "ANY_AUTHORIZED_BLOB_DRIFT_BLOCKS_TERMINAL_LAUNCH_BEFORE_CASE_GENERATION",
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
