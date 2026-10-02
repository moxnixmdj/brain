"""Fail-closed validator for the direct objective delegation T2 prewave binding.

This validates binding identity and runs one nonterminal diagnostic cycle across
all 11 frozen generator classes. It never consumes the post-freeze beacon, grants
terminal credit, or treats the diagnostic cycle as open-domain exhaustive proof.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import delegation_whole_scope_candidate_v2 as candidate
from canonical.runtime import delegation_whole_scope_proof_v2 as v2
from canonical.runtime import delegation_structural_variety_proof_v3 as v3

SCHEMA = "PROJECT_BRAIN_DELEGATION_T2_OBJECTIVE_BINDING_VALIDATION_V1"
MANIFEST = "canonical/governance/DELEGATION_T2_OBJECTIVE_TERMINAL_BINDING_V1.json"
EXPECTED_CYCLE = [
    "V2_BASE_PARALLEL","V2_RESOURCE_CONFLICT","V2_WORKER_UNAVAILABLE",
    "V2_STEP_UNAVAILABLE","V2_WORKER_CAPABILITY_REMOVED","V2_RESOURCE_CAPACITY_CHANGED",
    "V3_CHAIN","V3_FORK_JOIN","V3_FANOUT_JOIN","V3_DUAL_ROOT_FANIN","V3_ALTERNATIVE_PLAN",
]

def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

def validate(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "schema": SCHEMA, "status": "FAIL_CLOSED", "pass": False,
            "errors": ["MANIFEST_READ_FAILURE:" + type(exc).__name__],
            "execution_authority": False, "promotion_authority": False,
            "capability_credit_delta": 0, "family_credit_delta": 0,
        }
    if not isinstance(manifest, Mapping):
        errors.append("MANIFEST_NOT_OBJECT")
        manifest = {}

    if manifest.get("behavior_id") != "TASK_TO_DELEGATION_GRAPH_001":
        errors.append("BEHAVIOR_ID_INVALID")
    if manifest.get("proof_mode") != "T2_MULTIPLEXED_DIRECT_OBJECTIVE_DELEGATION_GATE":
        errors.append("PROOF_MODE_INVALID")
    if manifest.get("old_512_population_disposition") != "DIAGNOSTIC_PREFLIGHT_ONLY__MUST_NOT_BE_USED_AS_EXHAUSTIVE_OPEN_DOMAIN_TERMINAL_PROOF":
        errors.append("OLD_512_DISPOSITION_INVALID")

    source = manifest.get("source_pool")
    if not isinstance(source, Mapping):
        errors.append("SOURCE_POOL_INVALID")
    else:
        if source.get("terminal_sample_count") != 132:
            errors.append("TERMINAL_SAMPLE_COUNT_INVALID")
        if source.get("class_cycle") != EXPECTED_CYCLE:
            errors.append("CLASS_CYCLE_INVALID")
        if source.get("terminal_scope_claim") != "DIRECT_OBJECTIVE_INSTRUMENTATION_INSIDE_T2__NOT_EXHAUSTIVE_PROOF_OF_ALL_OPEN_DOMAIN_TASK_GRAPHS":
            errors.append("OPEN_DOMAIN_NONCLAIM_MISSING")

    selector = manifest.get("selector")
    if not isinstance(selector, Mapping):
        errors.append("SELECTOR_INVALID")
    else:
        required = {
            "beacon_known_before_freeze": False,
            "adaptive_case_selection": False,
            "case_replacement": False,
            "tuning_replay": False,
        }
        for key, expected in required.items():
            if selector.get(key) is not expected:
                errors.append("SELECTOR_" + key.upper() + "_INVALID")

    boundary = manifest.get("information_boundary")
    if not isinstance(boundary, Mapping) or boundary.get("candidate_receives_hidden_oracle") is not False:
        errors.append("INFORMATION_BOUNDARY_INVALID")

    gates = manifest.get("route_gates")
    if not isinstance(gates, Mapping):
        errors.append("ROUTE_GATES_INVALID")
    else:
        for key in (
            "candidate_package_frozen","executable_evaluator_bound",
            "population_or_source_pool_frozen","information_boundary_frozen",
            "post_freeze_selector_frozen","terminal_parent_binding_frozen",
        ):
            if gates.get(key) is not True:
                errors.append("GATE_NOT_FROZEN:" + key)
        if gates.get("independent_verification_pass") is not False:
            errors.append("INDEPENDENT_VERIFICATION_MUST_REMAIN_PENDING_IN_SOURCE_MANIFEST")

    bound = manifest.get("exact_bound_blobs")
    if not isinstance(bound, Mapping):
        errors.append("EXACT_BOUND_BLOBS_INVALID")
    else:
        for name, row in bound.items():
            if not isinstance(row, Mapping):
                errors.append("BOUND_ROW_INVALID:" + str(name))
                continue
            rel = row.get("path")
            expected = row.get("blob_sha")
            if not isinstance(rel, str) or not rel or not isinstance(expected, str) or not expected:
                errors.append("BOUND_IDENTITY_INVALID:" + str(name))
                continue
            path = root / rel
            if not path.exists():
                errors.append("BOUND_PATH_MISSING:" + rel)
                continue
            actual = _git_blob_sha(path)
            if actual != expected:
                errors.append("BOUND_BLOB_MISMATCH:" + rel)

    diagnostic: list[dict[str, Any]] = []
    # One fixed prewave-only diagnostic cycle. This is deliberately not the terminal selector.
    for ordinal in range(6):
        try:
            case = v2.generate_case(0x5A17D3, ordinal)
            first = candidate.solve_initial(v2.public_initial(case))
            revised = candidate.solve_after_receipt(v2.public_after_receipt(case), first)
            verdict = v2.score_episode(case, first, revised)
            label = "V2_" + str(case.get("case_class"))
            passed = verdict.get("pass") is True
        except Exception as exc:
            label = EXPECTED_CYCLE[ordinal]
            passed = False
            verdict = {"reason": type(exc).__name__ + ":" + str(exc)}
        diagnostic.append({"class": label, "pass": passed, "reason": verdict.get("reason")})
        if label != EXPECTED_CYCLE[ordinal] or not passed:
            errors.append("V2_DIAGNOSTIC_FAIL:" + EXPECTED_CYCLE[ordinal])

    for j in range(5):
        ordinal = j
        try:
            case = v3.generate_case(0x31C0DE, ordinal)
            verdict = v3.score_case(case, candidate.solve_initial(v3.public_case(case)))
            label = "V3_" + str(case.get("case_class"))
            passed = verdict.get("pass") is True
        except Exception as exc:
            label = EXPECTED_CYCLE[6 + j]
            passed = False
            verdict = {"reason": type(exc).__name__ + ":" + str(exc)}
        diagnostic.append({"class": label, "pass": passed, "reason": verdict.get("reason")})
        if label != EXPECTED_CYCLE[6 + j] or not passed:
            errors.append("V3_DIAGNOSTIC_FAIL:" + EXPECTED_CYCLE[6 + j])

    return {
        "schema": SCHEMA,
        "status": "PREWAVE_BINDING_VALID" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "behavior_id": "TASK_TO_DELEGATION_GRAPH_001",
        "diagnostic_class_count": len(diagnostic),
        "diagnostic": diagnostic,
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "errors": sorted(set(errors)),
    }

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root", type=Path)
    args = ap.parse_args()
    out = validate(args.repo_root)
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
