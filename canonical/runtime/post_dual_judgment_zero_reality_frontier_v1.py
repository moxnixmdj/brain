"""Recompute the zero-reality terminal frontier after dual judgment source admission.

This reducer consumes only independently verified current artifacts. It removes
exactly the zero-reality source requirements proven discharged by the shared
Finance/Unknown-Domain source-gate activation. It does not close either target
predicate and does not grant fresh-reality authority.

The two affected predicates transition from "zero-reality source acquisition
required" to "source admitted; direct frozen oracle remains reality-blocked".
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_POST_DUAL_JUDGMENT_ZERO_REALITY_FRONTIER_V1"

PATHS = {
    "dominance": "canonical/governance/CURRENT_27_INFORMATION_DOMINANCE_V1.json",
    "dominance_verification": "canonical/verification/CURRENT_27_INFORMATION_DOMINANCE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "frontier": "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json",
    "source_activation_verification": "canonical/verification/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "matched": "canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json",
    "scheduling": "canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json",
    "registry": "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json",
    "evidence": "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
}
EXPECTED = {
    PATHS["dominance"]: "fae786d6051277865ed6ecde69be5da98e2bf509",
    PATHS["dominance_verification"]: "1931ae5a7edb5dde2021a8a4f7e7a3ad0fd821f1",
    PATHS["frontier"]: "4b5517dbd12978f8ffe481fb775e85592c7790c8",
    PATHS["source_activation_verification"]: "6ec5f6d808c88bf9ea728fb7f259edc3b4ae5a51",
    PATHS["matched"]: "438e2775b64bee5ed6e792522ab35ebd0d6e1771",
    PATHS["scheduling"]: "54be838a5a0a9698398893ad113641496d5051b8",
    PATHS["registry"]: "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    PATHS["evidence"]: "0ed075c1efa053fe6e4eb3519d9903cf63fcf163",
}
EXPECTED_DISCHARGED = {
    "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_FINANCE_JUDGMENT_SOURCE_GATE_PASS",
    "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_UNKNOWN_DOMAIN_JUDGMENT_SOURCE_GATE_PASS",
}
EXPECTED_TRANSITION_CERTS = {
    "FINANCE_JUDGMENT_SOURCE_CERTIFICATE",
    "UNKNOWN_DOMAIN_JUDGMENT_SOURCE_CERTIFICATE",
}
EXPECTED_REALITY_BLOCKED = {
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

    dominance = _load(PATHS["dominance"])
    dominance_v = _load(PATHS["dominance_verification"])
    frontier = _load(PATHS["frontier"])
    source_v = _load(PATHS["source_activation_verification"])
    matched = _load(PATHS["matched"])
    scheduling = _load(PATHS["scheduling"])
    registry = _load(PATHS["registry"])
    evidence = _load(PATHS["evidence"])
    errors: list[str] = []

    live = dominance.get("live_world") or {}
    verified = dominance_v.get("verified") or {}
    if live.get("unresolved_predicates") != 27 or live.get("proved_predicates") != 11:
        errors.append("PREVIOUS_LIVE_WORLD_NOT_11_PROVED_27_OPEN")
    if verified.get("unresolved_predicates") != 27 or verified.get("proved_predicates") != 11:
        errors.append("PREVIOUS_DOMINANCE_VERIFICATION_COUNT_MISMATCH")
    if verified.get("unique_zero_reality_requirements") != 19:
        errors.append("PREVIOUS_ZERO_REALITY_REQUIREMENTS_NOT_19")
    if live.get("nondominated_certificate_count") != 16:
        errors.append("PREVIOUS_NONDOMINATED_CERTIFICATES_NOT_16")

    if not str(source_v.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("SOURCE_ACTIVATION_NOT_INDEPENDENT_PASS")
    sv = source_v.get("verified") or {}
    discharged = set(sv.get("discharged_requirements") or [])
    if discharged != EXPECTED_DISCHARGED:
        errors.append("DISCHARGED_REQUIREMENT_SET_MISMATCH")
    if sv.get("direct_oracle_leaves_executed") is not False:
        errors.append("DIRECT_ORACLE_LEAF_EXECUTION_OVERCLAIM")
    if sv.get("global_fresh_reality_authority") is not False:
        errors.append("SOURCE_ACTIVATION_FRESH_REALITY_OVERCLAIM")

    if scheduling.get("fresh_reality_authority") is not False:
        errors.append("CURRENT_SCHEDULING_FRESH_REALITY_NOT_FALSE")
    if not str(scheduling.get("status") or "").startswith(
        "ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V10_CURRENT"
    ):
        errors.append("CURRENT_SCHEDULING_NOT_V10")

    cert_by_id = {
        str(c.get("id")): c for c in (frontier.get("certificates") or [])
        if isinstance(c, Mapping) and c.get("id")
    }
    live_ids = set(dominance.get("nondominated_certificate_ids") or [])
    if len(live_ids) != 16:
        errors.append("LIVE_CERTIFICATE_ID_COUNT_NOT_16")

    transition_ids = {
        cid for cid in live_ids
        if set((cert_by_id.get(cid) or {}).get("requires") or []) <= discharged
        and set((cert_by_id.get(cid) or {}).get("requires") or [])
    }
    if transition_ids != EXPECTED_TRANSITION_CERTS:
        errors.append("SOURCE_DISCHARGE_CERTIFICATE_SET_MISMATCH")

    remaining_ids = sorted(live_ids - transition_ids)
    remaining_requirements: set[str] = set()
    zero_reality_covered: set[str] = set()
    for cid in remaining_ids:
        cert = cert_by_id.get(cid)
        if not cert:
            errors.append("CERTIFICATE_MISSING:" + cid)
            continue
        remaining_requirements.update(str(x) for x in cert.get("requires") or [])
        zero_reality_covered.update(str(x) for x in cert.get("target_predicates") or [])

    transitioned_targets: set[str] = set()
    for cid in transition_ids:
        transitioned_targets.update(
            str(x) for x in (cert_by_id.get(cid) or {}).get("target_predicates") or []
        )
    if transitioned_targets != EXPECTED_REALITY_BLOCKED:
        errors.append("REALITY_BLOCKED_TARGET_SET_MISMATCH")

    old_requirements = set(dominance.get("required_propositions") or [])
    if old_requirements - discharged != remaining_requirements:
        errors.append("REQUIREMENT_SUBTRACTION_NOT_EXACT")
    if len(remaining_requirements) != 17:
        errors.append("POST_DISCHARGE_REQUIREMENT_COUNT_NOT_17")
    if len(remaining_ids) != 14:
        errors.append("POST_DISCHARGE_CERTIFICATE_COUNT_NOT_14")

    predicate_ids = {
        str(row.get("id"))
        for row in (registry.get("predicates") or [])
        if isinstance(row, Mapping) and row.get("id")
    }
    proved_ids = {
        str(row.get("predicate_id"))
        for row in (evidence.get("claims") or [])
        if isinstance(row, Mapping)
        and row.get("predicate_id")
        and row.get("state") == "PROVED"
    }
    unresolved = predicate_ids - proved_ids
    if len(predicate_ids) != 38 or len(proved_ids) != 11 or len(unresolved) != 27:
        errors.append("REGISTRY_EVIDENCE_LIVE_WORLD_NOT_38_11_27")

    # V5 is a historical 31-predicate certificate carrier. Its certificate
    # target lists are intersected with the current receipt-derived 27 IDs.
    zero_reality_covered &= unresolved
    transitioned_targets &= unresolved
    if zero_reality_covered | transitioned_targets != unresolved:
        errors.append("POST_DISCHARGE_FRONTIER_COVERAGE_INCOMPLETE")
    if zero_reality_covered & transitioned_targets:
        errors.append("ZERO_REALITY_AND_REALITY_BLOCKED_TARGET_OVERLAP")
    if len(zero_reality_covered) != 25:
        errors.append("ZERO_REALITY_COVERED_PREDICATES_NOT_25")

    expected_matched = matched.get("expected") or {}
    if (
        expected_matched.get("primitive_residual_fact_count") != 16
        or expected_matched.get("shared_residual_group_count") != 0
    ):
        errors.append("MATCHED_RESIDUAL_NOT_16_PRIMITIVE_ZERO_SHARED")

    # Previous adaptive decomposition: 19 parent requirements - 2 matched
    # aggregate requirements + 16 target-specific matched facts = 33.
    # Exactly two non-matched source requirements are now discharged.
    primitive_zero_reality_work_units = len(remaining_requirements) - 2 + 16
    if primitive_zero_reality_work_units != 31:
        errors.append("POST_DISCHARGE_PRIMITIVE_WORK_UNITS_NOT_31")

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__POST_DUAL_SOURCE_GATE_FRONTIER__17_ZERO_REALITY_REQUIREMENTS__"
            "14_ZERO_REALITY_CERTIFICATES__25_PREDICATES_ZERO_REALITY_COVERED__"
            "2_DIRECT_REALITY_BLOCKED__31_PRIMITIVE_ZERO_REALITY_WORK_UNITS"
            if ok else "FAIL_CLOSED"
        ),
        "pass": ok,
        "errors": sorted(set(errors)),
        "live_world": {
            "proved_predicates": 11,
            "unresolved_predicates": 27,
            "opus55_acceptance": "4/19_PASS__15/19_OPEN",
        },
        "transition": {
            "discharged_zero_reality_requirements": sorted(discharged) if ok else [],
            "retired_zero_reality_certificate_ids": sorted(transition_ids) if ok else [],
            "direct_reality_blocked_predicates": sorted(transitioned_targets) if ok else [],
            "direct_reality_state": (
                "SOURCE_ADMITTED__FROZEN_DIRECT_ORACLE_REMAINS_UNEXECUTED__"
                "GLOBAL_FRESH_REALITY_AUTHORITY_FALSE"
            ),
        },
        "zero_reality_frontier": {
            "nondominated_certificate_ids": remaining_ids if ok else [],
            "nondominated_certificate_count": len(remaining_ids) if ok else 0,
            "required_propositions": sorted(remaining_requirements) if ok else [],
            "unique_zero_reality_requirement_count": len(remaining_requirements) if ok else 0,
            "covered_predicates": sorted(zero_reality_covered) if ok else [],
            "covered_predicate_count": len(zero_reality_covered) if ok else 0,
            "primitive_zero_reality_work_units": primitive_zero_reality_work_units if ok else 0,
            "matched_priority_child_facts": 16 if ok else 0,
        },
        "hard_rules": [
            "SOURCE_ADMISSION_IS_NOT_ACCEPTANCE_PREDICATE_CLOSURE",
            "THE_TWO_DIRECT_PREDICATES_REMAIN_OPEN",
            "NO_DIRECT_ORACLE_CASE_CONTENT_READ",
            "NO_FRESH_REALITY_WHILE_CURRENT_V10_AUTHORITY_FORBIDS_IT",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_FRONTIER_RECOMPUTATION",
        ],
        "new_reality_units_consumed": 0,
        "terminal_case_content_read": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
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
