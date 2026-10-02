"""Adversarial audit for the frozen P1 composite proof-role reconciliation.

This does not create capability credit. It executes only pre-existing, pre-terminal
V4 candidate/proof code against the exact frozen semantic obligations already
named by P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.

The purpose is falsification: prove the proposed V4 proof-role partition only if
the frozen candidate/scorer actually makes each assigned obligation load-bearing.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from canonical.runtime import trajectory_failure_typed_ir_candidate_v4 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v4 as proof

SCHEMA = "PROJECT_BRAIN_P1_COMPOSITE_MUTATION_ADVERSARIAL_AUDIT_V1"


def _failed_check(public: dict[str, Any], action_id: str, kind: str) -> dict[str, Any]:
    for row in public["task"]["trajectory"]:
        if row["action_id"] != action_id:
            continue
        for check in row["checks"]:
            if check["kind"] == kind and check["pass"] is False:
                return check
    raise AssertionError(f"FAILED_CHECK_NOT_FOUND:{action_id}:{kind}")


def _row(public: dict[str, Any], action_id: str) -> dict[str, Any]:
    for row in public["task"]["trajectory"]:
        if row["action_id"] == action_id:
            return row
    raise AssertionError(f"ACTION_NOT_FOUND:{action_id}")


def audit() -> dict[str, Any]:
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}
    gaps: list[str] = []

    # 1) Frozen check: mechanism classification must be supported by visible
    # receipts. Remove only receipt support while preserving the failed typed
    # check itself. If the hidden scorer still gives full credit and the
    # candidate emits no supporting receipts, the support requirement is not
    # load-bearing in V4.
    provenance_case = proof.generate_case(
        91001, pattern="SINGLE", domain="RESEARCH", kind="PROVENANCE"
    )
    provenance_public = deepcopy(proof.public_task(provenance_case))
    root = provenance_case["_oracle"]["roots"][0]
    _failed_check(provenance_public, root, "PROVENANCE")["evidence"] = []
    provenance_out = candidate.solve(provenance_public)
    provenance_verdict = proof.score_case(provenance_case, provenance_out)
    provenance_support_is_load_bearing = not (
        provenance_verdict.get("pass") is True
        and provenance_out.get("mechanism_classes") == ["PROVENANCE"]
        and provenance_out.get("supporting_receipts") == []
    )
    checks["PROVENANCE_RECEIPT_SUPPORT_IS_LOAD_BEARING"] = provenance_support_is_load_bearing
    details["provenance_support_drop"] = {
        "candidate_status": provenance_out.get("status"),
        "mechanism_classes": provenance_out.get("mechanism_classes"),
        "supporting_receipts": provenance_out.get("supporting_receipts"),
        "hidden_score_pass": provenance_verdict.get("pass"),
    }
    if not provenance_support_is_load_bearing:
        gaps.extend([
            "CHECK:FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS:EMPTY_SUPPORT_NOT_REJECTED",
            "MUTATION:DROP_PROVENANCE_OR_DEPENDENCY_EDGE:PROVENANCE_SUPPORT_DROP_NOT_REJECTED",
        ])

    # 2) Dependency-edge half of DROP_PROVENANCE_OR_DEPENDENCY_EDGE. Break one
    # root->join dependency while preserving the original hidden oracle. A
    # correct hidden evaluator must reject the changed causal answer.
    dep_case = proof.generate_case(
        91002, pattern="INTERACTION", domain="TOOL_API", kind="DEPENDENCY"
    )
    dep_public = deepcopy(proof.public_task(dep_case))
    roots = list(dep_case["_oracle"]["roots"])
    dropped_root = roots[-1]
    dropped_row = _row(dep_public, dropped_root)
    dropped_resources = set(dropped_row["writes"])
    join = next(
        row for row in dep_public["task"]["trajectory"]
        if row.get("dependency_composition") == "CONJUNCTIVE"
    )
    join["depends_on"] = [x for x in join["depends_on"] if x != dropped_root]
    join["reads"] = [x for x in join["reads"] if x not in dropped_resources]
    dep_out = candidate.solve(dep_public)
    dep_verdict = proof.score_case(dep_case, dep_out)
    checks["DROPPED_DEPENDENCY_EDGE_IS_REJECTED"] = dep_verdict.get("pass") is False
    details["dependency_edge_drop"] = {
        "original_roots": roots,
        "candidate_roots_after_drop": dep_out.get("cause_action_ids"),
        "hidden_score_pass": dep_verdict.get("pass"),
    }
    if dep_verdict.get("pass") is not False:
        gaps.append("MUTATION:DROP_PROVENANCE_OR_DEPENDENCY_EDGE:DEPENDENCY_EDGE_DROP_NOT_REJECTED")

    # 3) DROP_CAUSAL_PREDECESSOR_IN_MULTI_STEP_CHAIN. The V4 delayed pattern
    # contains a late failed symptom. The candidate must still recover the
    # upstream failed predecessor rather than selecting that symptom.
    delayed_case = proof.generate_case(
        91003, pattern="DELAYED", domain="FILESYSTEM", kind="STATE_TRANSITION"
    )
    delayed_out = candidate.solve(deepcopy(proof.public_task(delayed_case)))
    delayed_root = delayed_case["_oracle"]["roots"][0]
    delayed_ok = (
        proof.score_case(delayed_case, delayed_out).get("pass") is True
        and delayed_out.get("cause_action_id") == delayed_root
    )
    checks["MULTISTEP_CAUSAL_PREDECESSOR_IS_PRESERVED"] = delayed_ok
    details["delayed_chain"] = {
        "expected_root": delayed_root,
        "candidate_root": delayed_out.get("cause_action_id"),
    }
    if not delayed_ok:
        gaps.append("MUTATION:DROP_CAUSAL_PREDECESSOR_IN_MULTI_STEP_CHAIN:UPSTREAM_ROOT_NOT_PRESERVED")

    # 4) IGNORE_VIOLATED_AUTHORITY_OR_INVARIANT. Delete the root authority
    # violation from candidate-visible input while retaining the original hidden
    # oracle. The hidden evaluator must refuse full credit.
    authority_case = proof.generate_case(
        91004, pattern="SINGLE", domain="BROWSER", kind="AUTHORITY"
    )
    authority_public = deepcopy(proof.public_task(authority_case))
    authority_root = authority_case["_oracle"]["roots"][0]
    rr = _row(authority_public, authority_root)
    rr["checks"] = [
        x for x in rr["checks"]
        if not (x["kind"] == "AUTHORITY" and x["pass"] is False)
    ]
    authority_out = candidate.solve(authority_public)
    authority_verdict = proof.score_case(authority_case, authority_out)
    authority_ok = authority_verdict.get("pass") is False
    checks["IGNORED_AUTHORITY_VIOLATION_IS_REJECTED"] = authority_ok
    details["authority_violation_drop"] = {
        "candidate_root": authority_out.get("cause_action_id"),
        "hidden_score_pass": authority_verdict.get("pass"),
    }
    if not authority_ok:
        gaps.append("MUTATION:IGNORE_VIOLATED_AUTHORITY_OR_INVARIANT:NOT_REJECTED")

    # 5) FORCE_UNIQUE_CAUSE_ON_NONIDENTIFIABLE_TRACE.
    ambiguous_case = proof.generate_case(
        91005, pattern="AMBIGUOUS", domain="ARTIFACT", kind="SCHEMA"
    )
    ambiguous_out = candidate.solve(deepcopy(proof.public_task(ambiguous_case)))
    ambiguous_ok = (
        proof.score_case(ambiguous_case, ambiguous_out).get("pass") is True
        and ambiguous_out.get("status") == "AMBIGUOUS"
        and ambiguous_out.get("cause_action_id") is None
        and bool(ambiguous_out.get("information_request"))
    )
    checks["NONIDENTIFIABILITY_IS_PRESERVED"] = ambiguous_ok
    if not ambiguous_ok:
        gaps.append("MUTATION:FORCE_UNIQUE_CAUSE_ON_NONIDENTIFIABLE_TRACE:NOT_REJECTED")

    # 6) SWAP_TOOL_OR_AUTHORITY_FAILURE_CLASS. Same causal shape, different
    # visible failed contract class. Mechanism output must track the class.
    authority_class_case = proof.generate_case(
        91006, pattern="SINGLE", domain="TOOL_API", kind="AUTHORITY"
    )
    tool_class_case = proof.generate_case(
        91007, pattern="SINGLE", domain="TOOL_API", kind="TOOL_CONTRACT"
    )
    authority_class_out = candidate.solve(deepcopy(proof.public_task(authority_class_case)))
    tool_class_out = candidate.solve(deepcopy(proof.public_task(tool_class_case)))
    class_swap_ok = (
        proof.score_case(authority_class_case, authority_class_out).get("pass") is True
        and proof.score_case(tool_class_case, tool_class_out).get("pass") is True
        and authority_class_out.get("mechanism_classes") == ["AUTHORITY"]
        and tool_class_out.get("mechanism_classes") == ["TOOL_CONTRACT"]
    )
    checks["MECHANISM_CLASS_TRACKS_VISIBLE_FAILED_CONTRACT"] = class_swap_ok
    if not class_swap_ok:
        gaps.append("MUTATION:SWAP_TOOL_OR_AUTHORITY_FAILURE_CLASS:CLASS_NOT_LOAD_BEARING")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__ALL_ASSIGNED_V4_FROZEN_OBLIGATIONS_LOAD_BEARING"
            if not gaps
            else "FAIL_CLOSED__P1_COMPOSITE_ROLE_GAPS_FOUND"
        ),
        "pass": not gaps,
        "checks": checks,
        "details": details,
        "gaps": sorted(gaps),
        "interpretation": (
            "A failing audit blocks P1 composite restoration. It does not alter "
            "the frozen candidate, terminal wave, acceptance credit, or family credit."
        ),
        "new_reality_units_consumed": 0,
        "terminal_results_replayed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(audit(), indent=2, sort_keys=True))
