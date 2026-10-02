#!/usr/bin/env python3
"""Validate the frozen direct-objective T3 research-control binding.

Prewave only. No terminal beacon is consumed, no terminal cases are selected,
and no execution/promotion/capability/family authority is granted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import research_control_information_safe_candidate as candidate
from canonical.runtime import research_control_information_safe_proof as proof

BINDING = "canonical/governance/RESEARCH_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"
OBJECTIVE_INPUT = "canonical/governance/OBJECTIVE_ORACLE_DOMINANCE_LIVE_INPUT_V1.json"
PREFLIGHT_RECEIPT = "canonical/verification/RESEARCH_CONTROL_INFORMATION_SAFE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
BEHAVIOR = "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001"
PROOF_MODE = "T3_MULTIPLEXED_DIRECT_OBJECTIVE_RESEARCH_CONTROL_GATE"


def _git_blob_sha_bytes(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _git_blob_sha(path: Path) -> str:
    return _git_blob_sha_bytes(path.read_bytes())


def _read(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("NOT_OBJECT")
    return obj


def validate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []
    try:
        binding = _read(root / BINDING)
        objective = _read(root / OBJECTIVE_INPUT)
        receipt = _read(root / PREFLIGHT_RECEIPT)
    except Exception as exc:
        return {
            "schema": "PROJECT_BRAIN_RESEARCH_T3_OBJECTIVE_BINDING_VALIDATION_V1",
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["INPUT_READ_FAILURE:" + type(exc).__name__],
            "execution_authority": False,
            "promotion_authority": False,
            "terminal_results_observed": 0,
            "fresh_terminal_evidence_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    if binding.get("behavior_id") != BEHAVIOR:
        errors.append("BEHAVIOR_ID_MISMATCH")
    if binding.get("proof_mode") != PROOF_MODE:
        errors.append("PROOF_MODE_MISMATCH")
    if binding.get("execution_authority") is not False or binding.get("promotion_authority") is not False:
        errors.append("SOURCE_BINDING_AUTHORITY_MUST_REMAIN_FALSE")

    observed: dict[str, str] = {}
    for label, row in (binding.get("exact_bound_blobs") or {}).items():
        if not isinstance(row, Mapping):
            errors.append(f"BLOB_BINDING_INVALID:{label}")
            continue
        rel = row.get("path")
        expected = row.get("blob_sha")
        if not isinstance(rel, str) or not rel or not isinstance(expected, str) or not expected:
            errors.append(f"BLOB_BINDING_INVALID:{label}")
            continue
        p = root / rel
        if not p.is_file():
            errors.append(f"BLOB_MISSING:{label}:{rel}")
            continue
        got = _git_blob_sha(p)
        observed[label] = got
        if got != expected:
            errors.append(f"BLOB_SHA_MISMATCH:{label}:{got}")

    contracts = objective.get("contracts")
    if not isinstance(contracts, list):
        errors.append("OBJECTIVE_CONTRACTS_INVALID")
        contracts = []
    rows = [x for x in contracts if isinstance(x, Mapping) and x.get("behavior_id") == BEHAVIOR]
    if len(rows) != 1:
        errors.append("OBJECTIVE_RESEARCH_ROW_COUNT_INVALID")
        row = {}
    else:
        row = rows[0]
    required = row.get("required_dimensions") if isinstance(row, Mapping) else None
    declared = binding.get("objective_dimensions")
    if not isinstance(required, list) or not isinstance(declared, list) or set(required) != set(declared):
        errors.append("OBJECTIVE_DIMENSION_BINDING_MISMATCH")
    dimensions = row.get("dimensions") if isinstance(row, Mapping) else None
    if not isinstance(dimensions, list):
        errors.append("OBJECTIVE_DIMENSIONS_INVALID")
        dimensions = []
    for d in dimensions:
        if not isinstance(d, Mapping):
            errors.append("OBJECTIVE_DIMENSION_NOT_OBJECT")
            continue
        did = d.get("id")
        for key in ("objective", "falsifiable", "hidden_from_candidate", "terminal_load_bearing"):
            if d.get(key) is not True:
                errors.append(f"OBJECTIVE_DIMENSION_NOT_LOAD_BEARING:{did}:{key}")
        if not d.get("existing_evidence"):
            errors.append(f"OBJECTIVE_DIMENSION_EVALUATOR_MISSING:{did}")
    if row and row.get("candidate_receives_hidden_oracle") is not False:
        errors.append("OBJECTIVE_HIDDEN_ORACLE_BOUNDARY_INVALID")

    pool = binding.get("source_pool") or {}
    domains = list(pool.get("domain_cycle") or [])
    if domains != list(proof.DOMAINS):
        errors.append("DOMAIN_CYCLE_MISMATCH")
    count = pool.get("terminal_sample_count")
    if not isinstance(count, int) or count <= 0 or not domains or count % len(domains) != 0:
        errors.append("TERMINAL_SAMPLE_COUNT_NOT_COMPLETE_DOMAIN_CYCLES")
    if binding.get("acceptance", {}).get("hle_score_equivalence_claimed") is not False:
        errors.append("HLE_EQUIVALENCE_OVERCLAIM")
    if binding.get("acceptance", {}).get("hle_content_required_for_direct_objective_route") is not False:
        errors.append("DIRECT_ROUTE_STILL_REQUIRES_HLE")

    selector = binding.get("selector") or {}
    for key in ("beacon_known_before_freeze", "adaptive_case_selection", "case_replacement", "tuning_replay"):
        if selector.get(key) is not False:
            errors.append(f"SELECTOR_{key.upper()}_NOT_FALSE")

    if selector.get("protocol") != "GLOBAL_TERMINAL_SELECTION_KERNEL_V1":
        errors.append("SELECTOR_PROTOCOL_NOT_IMMUTABLE_KERNEL")
    sel_sem = binding.get("selection_semantics") or {}
    kernel = (binding.get("exact_bound_blobs") or {}).get("selection_kernel") or {}
    if sel_sem.get("kernel") != kernel.get("path") or sel_sem.get("kernel_blob_sha") != kernel.get("blob_sha"):
        errors.append("SELECTION_KERNEL_BINDING_MISMATCH")

    info = binding.get("information_boundary") or {}
    hidden = set(info.get("hidden_from_candidate") or [])
    if "SOURCE_SUPPORT_TRUTH_BEFORE_FETCH" not in hidden or "COMPLETE_HIDDEN_REQUIREMENT_SUPPORT_GRAPH" not in hidden:
        errors.append("HIDDEN_ORACLE_BOUNDARY_INCOMPLETE")
    if info.get("candidate_receives_hidden_oracle") is not False:
        errors.append("CANDIDATE_RECEIVES_HIDDEN_ORACLE")

    if receipt.get("behavior_contract") != BEHAVIOR:
        errors.append("PREFLIGHT_RECEIPT_BEHAVIOR_MISMATCH")
    if not str(receipt.get("status", "")).startswith("INDEPENDENT_PASS"):
        errors.append("PREFLIGHT_RECEIPT_NOT_PASS")
    if receipt.get("workflow_conclusion") != "success":
        errors.append("PREFLIGHT_WORKFLOW_NOT_SUCCESS")
    if receipt.get("terminal_results_observed") != 0 or receipt.get("fresh_terminal_evidence_consumed") != 0:
        errors.append("PREFLIGHT_RECEIPT_CONSUMED_TERMINAL_EVIDENCE")
    exact = receipt.get("exact_brain_blobs")
    if not isinstance(exact, Mapping):
        errors.append("PREFLIGHT_EXACT_BLOBS_INVALID")
    else:
        for label in ("candidate", "objective_oracle", "objective_tests"):
            bound = (binding.get("exact_bound_blobs") or {}).get(label) or {}
            rel = bound.get("path")
            sha = bound.get("blob_sha")
            if rel and exact.get(rel) != sha:
                errors.append(f"PREFLIGHT_EXACT_BLOB_MISMATCH:{label}")

    # Fresh prewave diagnostic only. This uses a fixed diagnostic seed, never the
    # post-freeze terminal beacon.
    diagnostic_count = 180
    result = proof.run_batch(20261002, diagnostic_count, candidate.next_action)
    if result.get("all_pass") is not True:
        errors.append("SIX_DOMAIN_DIAGNOSTIC_FAILED")
    by_domain = result.get("by_domain") or {}
    if set(by_domain) != set(proof.DOMAINS):
        errors.append("DIAGNOSTIC_DOMAIN_COVERAGE_INCOMPLETE")
    expected_each = diagnostic_count // len(proof.DOMAINS)
    for domain in proof.DOMAINS:
        d = by_domain.get(domain) or {}
        if d.get("total") != expected_each or d.get("pass") != d.get("total"):
            errors.append(f"DIAGNOSTIC_DOMAIN_FAILED:{domain}")

    # Inspect representative candidate-visible states for hidden truth leakage.
    for ordinal in range(len(proof.DOMAINS)):
        case = proof.generate_case(99117, ordinal)
        public = proof.public_state(case)
        raw = json.dumps(public, sort_keys=True)
        if "_oracle" in public or "_oracle" in raw:
            errors.append(f"HIDDEN_ORACLE_LEAK:{ordinal}")

    gates = binding.get("route_gates") or {}
    for key in (
        "candidate_package_frozen",
        "executable_evaluator_bound",
        "population_or_source_pool_frozen",
        "information_boundary_frozen",
        "post_freeze_selector_frozen",
        "terminal_parent_binding_frozen",
    ):
        if gates.get(key) is not True:
            errors.append(f"ROUTE_GATE_NOT_FROZEN:{key}")
    independent = gates.get("independent_verification_pass")
    prewave_admissible = binding.get("prewave_admissible")
    if not isinstance(independent, bool):
        errors.append("INDEPENDENT_VERIFICATION_GATE_NOT_BOOLEAN")
    elif prewave_admissible is not independent:
        errors.append("PREWAVE_ADMISSIBILITY_VERIFICATION_STATE_MISMATCH")
    elif independent:
        expected_promoted_status = (
            "FROZEN_PREWAVE_BINDING__SELECTION_KERNEL_REBOUND__"
            "INDEPENDENT_PASS__PREWAVE_ADMISSIBLE__ZERO_TERMINAL_RESULTS"
        )
        if binding.get("status") != expected_promoted_status:
            errors.append("PROMOTED_STATUS_MISMATCH")
        receipt_rel = binding.get("independent_verification")
        if not isinstance(receipt_rel, str) or not receipt_rel:
            errors.append("PROMOTION_RECEIPT_PATH_MISSING")
        else:
            try:
                promotion_receipt = _read(root / receipt_rel)
            except Exception as exc:
                errors.append("PROMOTION_RECEIPT_READ_FAILURE:" + type(exc).__name__)
            else:
                if promotion_receipt.get("behavior_id") != BEHAVIOR:
                    errors.append("PROMOTION_RECEIPT_BEHAVIOR_MISMATCH")
                if not str(promotion_receipt.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
                    errors.append("PROMOTION_RECEIPT_NOT_INDEPENDENT_PASS")
                if promotion_receipt.get("workflow_conclusion") != "success":
                    errors.append("PROMOTION_RECEIPT_WORKFLOW_NOT_SUCCESS")
                if promotion_receipt.get("terminal_results_observed") != 0 or promotion_receipt.get("fresh_terminal_evidence_consumed") != 0:
                    errors.append("PROMOTION_RECEIPT_CONSUMED_TERMINAL_EVIDENCE")
                exact_receipt = promotion_receipt.get("exact_brain_blobs")
                expected_base_sha = exact_receipt.get(BINDING) if isinstance(exact_receipt, Mapping) else None
                if not isinstance(expected_base_sha, str) or not expected_base_sha:
                    errors.append("PROMOTION_RECEIPT_BASE_BINDING_SHA_MISSING")
                else:
                    base = json.loads(json.dumps(binding))
                    base["status"] = (
                        "FROZEN_PREWAVE_BINDING__SELECTION_KERNEL_REBOUND__"
                        "INDEPENDENT_VERIFICATION_PENDING__ZERO_TERMINAL_RESULTS"
                    )
                    base["route_gates"]["independent_verification_pass"] = False
                    base["prewave_admissible"] = False
                    base.pop("independent_verification", None)
                    base_bytes = (json.dumps(base, indent=2) + "\n").encode("utf-8")
                    reconstructed_base_sha = _git_blob_sha_bytes(base_bytes)
                    if reconstructed_base_sha != expected_base_sha:
                        errors.append(
                            "PROMOTION_TRANSITION_BASE_SHA_MISMATCH:"
                            + reconstructed_base_sha
                            + "!="
                            + expected_base_sha
                        )
    else:
        expected_pending_status = (
            "FROZEN_PREWAVE_BINDING__SELECTION_KERNEL_REBOUND__"
            "INDEPENDENT_VERIFICATION_PENDING__ZERO_TERMINAL_RESULTS"
        )
        if binding.get("status") != expected_pending_status:
            errors.append("PREPROMOTION_STATUS_MISMATCH")
        if binding.get("independent_verification") is not None:
            errors.append("PREPROMOTION_RECEIPT_MUST_BE_ABSENT")

    return {
        "schema": "PROJECT_BRAIN_RESEARCH_T3_OBJECTIVE_BINDING_VALIDATION_V1",
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "diagnostic_case_count": diagnostic_count,
        "diagnostic_all_pass": result.get("all_pass") is True,
        "diagnostic_domains": sorted(by_domain),
        "bound_blob_count": len(observed),
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "incremental_spend_usd": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "rule": "DIRECT_OBJECTIVE_ROUTE_MAY_DELETE_HLE_PREWAVE_DEPENDENCY_ONLY_AFTER_EXACT_BINDING_AND_INDEPENDENT_VERIFICATION__NO_HLE_SCORE_EQUIVALENCE__NO_TERMINAL_CREDIT",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = ap.parse_args()
    out = validate(args.root)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
