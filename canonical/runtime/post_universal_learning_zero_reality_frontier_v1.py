"""Recompute the zero-reality frontier after verified Tool Discovery scope discharge.

This reducer removes exactly one already-proved zero-reality proposition:
the frozen Tool Discovery target-scope completeness atom. It does not close
TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR. The remaining residual is matched
empirical learning-effectiveness noninferiority.

Zero acceptance/family/capability/ownership/execution/promotion/fresh-reality
credit is granted here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_POST_UNIVERSAL_LEARNING_ZERO_REALITY_FRONTIER_V1"

FRONT = "canonical/governance/CURRENT_27_ZERO_REALITY_FRONTIER_V2.json"
POSTV = "canonical/verification/POST_DUAL_JUDGMENT_ZERO_REALITY_FRONTIER_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
CERTS = "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"
SCOPE = "canonical/verification/TOOL_DISCOVERY_FROZEN_SCOPE_COMPLETENESS_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
LEARN = "canonical/verification/UNIVERSAL_LEARNING_CONTRACT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
SCHED = "canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json"
ROUTE = "canonical/governance/TOOL_DISCOVERY_CURRENT_ROUTE_SELECTION_V2.json"

EXPECTED = {
    FRONT: "bab3876a1c4bd6a065d20d42b320df4b4b3fa519",
    POSTV: "f7f60a5932ac305aa0db8aef2643119dd10b33d9",
    CERTS: "4b5517dbd12978f8ffe481fb775e85592c7790c8",
    SCOPE: "c9adf25c2e63f9e8b111f1d022acda264d6571f5",
    LEARN: "2bff1082b81755ff5f8e8f0e97587090cc873283",
    SCHED: "6717ff6bda388722b3a28f0ead66db7aadb8e0c7",
    ROUTE: "9b7662513d9e6b73b87a814daaf8c2b023c41559",
}

REQ = (
    "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_"
    "SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL"
)
CERT = "TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE"
PRED = "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
EMPIRICAL = "MATCHED_EMPIRICAL_LEARNING_EFFECTIVENESS_NONINFERIORITY"
PRIOR_DIRECT = {
    "FINANCE_UNCOVERED_SCOPE_AUDIT",
    "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
}


def _blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def evaluate() -> dict[str, Any]:
    drift = {
        path: {"expected": expected, "actual": _blob(path)}
        for path, expected in EXPECTED.items()
        if _blob(path) != expected
    }
    if drift:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__SOURCE_BLOB_DRIFT",
            "pass": False,
            "errors": ["SOURCE_BLOB_DRIFT"],
            "drift": drift,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }

    front = _load(FRONT)
    postv = _load(POSTV)
    certs = _load(CERTS)
    scope = _load(SCOPE)
    learn = _load(LEARN)
    sched = _load(SCHED)
    route = _load(ROUTE)
    errors: list[str] = []

    live = front.get("live_world") or {}
    if (
        live.get("proved_predicates"),
        live.get("unresolved_predicates"),
        live.get("active_zero_reality_requirements"),
        live.get("active_nondominated_certificates"),
    ) != (11, 27, 17, 14):
        errors.append("PRIOR_FRONTIER_NOT_11_27_17_14")
    if live.get("opus55_acceptance") != "4/19_PASS__15/19_OPEN":
        errors.append("PRIOR_ACCEPTANCE_DRIFT")

    reqs = list(front.get("active_required_propositions") or [])
    cert_ids = list(front.get("active_nondominated_certificate_ids") or [])
    if reqs.count(REQ) != 1:
        errors.append("TOOL_DISCOVERY_REQUIREMENT_NOT_EXACTLY_ONCE")
    if cert_ids.count(CERT) != 1:
        errors.append("TOOL_DISCOVERY_CERTIFICATE_NOT_EXACTLY_ONCE")

    post_verified = postv.get("verified") or {}
    if not str(postv.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("POST_DUAL_FRONTIER_NOT_INDEPENDENT_PASS")
    if (
        post_verified.get("current_zero_reality_requirements"),
        post_verified.get("current_nondominated_zero_reality_certificates"),
        post_verified.get("zero_reality_covered_predicates"),
        post_verified.get("primitive_zero_reality_work_units"),
        post_verified.get("matched_priority_child_facts"),
    ) != (17, 14, 25, 31, 16):
        errors.append("POST_DUAL_VERIFIED_COUNTS_DRIFT")
    if set(post_verified.get("direct_reality_blocked_predicates") or []) != PRIOR_DIRECT:
        errors.append("POST_DUAL_DIRECT_REALITY_SET_DRIFT")

    if not str(scope.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("TOOL_DISCOVERY_SCOPE_RECEIPT_NOT_INDEPENDENT_PASS")
    if scope.get("target_predicate") != PRED:
        errors.append("TOOL_DISCOVERY_SCOPE_TARGET_PREDICATE_DRIFT")
    if scope.get("target_proof_atom") != REQ:
        errors.append("TOOL_DISCOVERY_SCOPE_TARGET_ATOM_DRIFT")
    if scope.get("scope_semantics_discharged") is not True:
        errors.append("TOOL_DISCOVERY_SCOPE_NOT_DISCHARGED")
    if scope.get("complete_target_case_set") is not True:
        errors.append("TOOL_DISCOVERY_COMPLETE_TARGET_CASE_SET_NOT_TRUE")
    runner = scope.get("public_runner") or {}
    if runner.get("conclusion") != "success":
        errors.append("TOOL_DISCOVERY_SCOPE_RUNNER_NOT_SUCCESS")

    if not str(learn.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("UNIVERSAL_LEARNING_RECEIPT_NOT_INDEPENDENT_PASS")
    learning_runner = learn.get("independent_runner") or {}
    verified = learn.get("verified") or {}
    if learning_runner.get("conclusion") != "success":
        errors.append("UNIVERSAL_LEARNING_RUNNER_NOT_SUCCESS")
    if verified.get("structural_novelty_scope_closed_candidate") is not True:
        errors.append("UNIVERSAL_LEARNING_STRUCTURAL_SCOPE_NOT_CLOSED")
    if verified.get("separate_environment_enumeration_required") is not False:
        errors.append("UNIVERSAL_LEARNING_ENUMERATION_STILL_REQUIRED")
    if verified.get("remaining_residual_exact") != EMPIRICAL:
        errors.append("UNIVERSAL_LEARNING_EMPIRICAL_RESIDUAL_DRIFT")
    if verified.get("semantic_success_rate_proved") is not False:
        errors.append("SEMANTIC_SUCCESS_RATE_OVERCLAIM")
    if verified.get("tool_learning_noninferiority_proved") is not False:
        errors.append("TOOL_LEARNING_NONINFERIORITY_OVERCLAIM")

    cert_by_id = {
        str(c.get("id")): c
        for c in (certs.get("certificates") or [])
        if isinstance(c, Mapping) and c.get("id")
    }
    c = cert_by_id.get(CERT) or {}
    if set(c.get("requires") or []) != {REQ}:
        errors.append("TOOL_DISCOVERY_CERTIFICATE_REQUIREMENT_SET_DRIFT")
    if set(c.get("target_predicates") or []) != {PRED}:
        errors.append("TOOL_DISCOVERY_CERTIFICATE_TARGET_SET_DRIFT")

    if not str(sched.get("status") or "").startswith(
        "ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V13_CURRENT"
    ):
        errors.append("CURRENT_SCHEDULING_NOT_V13")
    if sched.get("fresh_reality_authority") is not False:
        errors.append("CURRENT_SCHEDULING_FRESH_REALITY_NOT_FALSE")
    if sched.get("execution_authority") is not False:
        errors.append("CURRENT_SCHEDULING_EXECUTION_AUTHORITY_LEAK")
    if sched.get("promotion_authority") is not False:
        errors.append("CURRENT_SCHEDULING_PROMOTION_AUTHORITY_LEAK")

    if not str(route.get("status") or "").startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V9"):
        errors.append("TOOL_DISCOVERY_CURRENT_ROUTE_NOT_V9_INDEPENDENT_PASS")
    if route.get("target_predicate") != PRED:
        errors.append("TOOL_DISCOVERY_CURRENT_ROUTE_TARGET_DRIFT")

    remaining_reqs = [x for x in reqs if x != REQ]
    remaining_certs = [x for x in cert_ids if x != CERT]
    direct = sorted(PRIOR_DIRECT | {PRED})

    if len(remaining_reqs) != 16:
        errors.append("POST_SCOPE_REQUIREMENT_COUNT_NOT_16")
    if len(remaining_certs) != 13:
        errors.append("POST_SCOPE_CERTIFICATE_COUNT_NOT_13")

    # Previous primitive decomposition = 17 parent requirements - 2 matched
    # aggregate requirements + 16 matched child facts = 31. The discharged
    # Tool Discovery requirement is non-matched, so exactly one primitive unit
    # is removed.
    primitive = len(remaining_reqs) - 2 + 16
    if primitive != 30:
        errors.append("POST_SCOPE_PRIMITIVE_WORK_UNITS_NOT_30")

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__TOOL_DISCOVERY_SCOPE_REQUIREMENT_DISCHARGED__"
            "16_ZERO_REALITY_REQUIREMENTS__13_CERTIFICATES__"
            "24_PREDICATES_ZERO_REALITY_COVERED__3_DIRECT_REALITY_BLOCKED__"
            "30_PRIMITIVE_ZERO_REALITY_WORK_UNITS__ZERO_CREDIT"
            if ok else "FAIL_CLOSED"
        ),
        "pass": ok,
        "errors": sorted(set(errors)),
        "live_world": {
            "registry_predicates": 38,
            "proved_predicates": 11,
            "unresolved_predicates": 27,
            "opus55_acceptance": "4/19_PASS__15/19_OPEN",
        },
        "transition": {
            "discharged_zero_reality_requirement": REQ if ok else None,
            "retired_zero_reality_certificate": CERT if ok else None,
            "transitioned_predicate": PRED if ok else None,
            "remaining_residual": EMPIRICAL if ok else None,
            "direct_reality_blocked_predicates": direct if ok else [],
        },
        "zero_reality_frontier": {
            "active_required_propositions": remaining_reqs if ok else [],
            "active_zero_reality_requirement_count": len(remaining_reqs) if ok else 0,
            "active_nondominated_certificate_ids": remaining_certs if ok else [],
            "active_nondominated_certificate_count": len(remaining_certs) if ok else 0,
            "zero_reality_covered_predicate_count": 24 if ok else 0,
            "primitive_zero_reality_work_units": primitive if ok else 0,
            "matched_priority_child_facts": 16 if ok else 0,
        },
        "hard_rules": [
            "SCOPE_COMPLETENESS_DISCHARGE_IS_NOT_TOOL_LEARNING_NONINFERIORITY",
            "UNIVERSAL_LEARNING_CONTROL_INVARIANTS_DO_NOT_PROVE_SEMANTIC_SUCCESS_RATE",
            "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR_REMAINS_OPEN",
            "MATCHED_EMPIRICAL_LEARNING_EFFECTIVENESS_NONINFERIORITY_REMAINS_OPEN",
            "NO_TERMINAL_REPLAY",
            "NO_FRESH_REALITY_AUTHORITY",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_EXECUTION_OR_PROMOTION_CREDIT",
        ],
        "new_reality_units_consumed": 0,
        "terminal_results_replayed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
