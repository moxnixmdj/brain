"""Adaptive terminal-closure controller V2.

V2 preserves the independently verified V1 controller as an immutable inner
compiler. It validates the current V13/Retrieval-V5 scheduling authority and
the independently verified post-dual zero-reality delta, then projects only
those already-verified control-plane changes into V1's scheduling-only output.

No acceptance, family, capability, ownership, execution, promotion, or
fresh-reality authority can originate here.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import adaptive_terminal_closure_controller_v1 as v1

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_ADAPTIVE_TERMINAL_CLOSURE_CONTROLLER_V2"

PATHS = {
    "v1": "canonical/runtime/adaptive_terminal_closure_controller_v1.py",
    "registry": "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json",
    "evidence": "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
    "frontier": "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json",
    "dominance": "canonical/governance/CURRENT_27_INFORMATION_DOMINANCE_V1.json",
    "dominance_v": "canonical/verification/CURRENT_27_INFORMATION_DOMINANCE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "matched": "canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json",
    "matched_v": "canonical/verification/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_EXECUTION_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json",
    "ownership": "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json",
    "authority": "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
    "scheduling": "canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json",
    "post_dual": "canonical/governance/POST_DUAL_JUDGMENT_ZERO_REALITY_FRONTIER_V1.json",
    "post_dual_v": "canonical/verification/POST_DUAL_JUDGMENT_ZERO_REALITY_FRONTIER_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "dual_source_v": "canonical/verification/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
}

PINNED = {
    PATHS["v1"]: "06d16ef1e8caa08835bc4e958c3047833bf52a32",
    PATHS["scheduling"]: "6717ff6bda388722b3a28f0ead66db7aadb8e0c7",
    PATHS["post_dual"]: "3b62096fdba09a41096f9aba12f9ec04d810cac8",
    PATHS["post_dual_v"]: "f7f60a5932ac305aa0db8aef2643119dd10b33d9",
    PATHS["dual_source_v"]: "6ec5f6d808c88bf9ea728fb7f259edc3b4ae5a51",
}

DISCHARGED = {
    "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_FINANCE_JUDGMENT_SOURCE_GATE_PASS",
    "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_UNKNOWN_DOMAIN_JUDGMENT_SOURCE_GATE_PASS",
}


def _blob(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(rel + ":NOT_OBJECT")
    return value


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "incremental_spend_usd": 0,
        "new_reality_units_consumed": 0,
    }


def evaluate() -> dict[str, Any]:
    errors: list[str] = []
    for rel, expected in PINNED.items():
        actual = _blob(rel)
        if actual != expected:
            errors.append(f"PINNED_BLOB_DRIFT:{rel}:{actual}:{expected}")
    if errors:
        return _fail(*errors)

    scheduling = _load(PATHS["scheduling"])
    post_dual = _load(PATHS["post_dual"])
    post_dual_v = _load(PATHS["post_dual_v"])
    dual_source_v = _load(PATHS["dual_source_v"])

    if not str(scheduling.get("status") or "").startswith(
        "ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V13_CURRENT"
    ):
        errors.append("CURRENT_SCHEDULING_NOT_V13")
    if scheduling.get("fresh_reality_authority") is not False:
        errors.append("V13_FRESH_REALITY_AUTHORITY_NOT_FALSE")
    retrieval = scheduling.get("mandatory_tool_discovery_retrieval") or {}
    if retrieval.get("authority") != "V5_OVER_V4_OVER_V3_OVER_VERIFIED_V2_BASE":
        errors.append("RETRIEVAL_V5_CHAIN_NOT_CURRENT")
    if retrieval.get("gate_git_blob_sha") != "c3324e574c1fafb6aaab443f49b7a9600966e754":
        errors.append("RETRIEVAL_V5_GATE_HASH_MISMATCH")
    for key in (
        "direct_bypass_allowed",
        "failed_or_partial_source_cell_consumes_epoch",
        "consumed_source_epoch_replay_allowed",
        "no_result_means_nonexistence",
    ):
        if retrieval.get(key) is not False:
            errors.append("RETRIEVAL_V5_FAIL_CLOSED_RULE_VIOLATION:" + key)

    pdv = post_dual_v.get("verified") or {}
    if not str(post_dual_v.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("POST_DUAL_FRONTIER_NOT_INDEPENDENT_PASS")
    if (
        pdv.get("current_zero_reality_requirements"),
        pdv.get("current_nondominated_zero_reality_certificates"),
        pdv.get("primitive_zero_reality_work_units"),
        pdv.get("matched_priority_child_facts"),
    ) != (17, 14, 31, 16):
        errors.append("POST_DUAL_VERIFIED_CARDINALITY_MISMATCH")
    if pdv.get("current_global_fresh_reality_authority") is not False:
        errors.append("POST_DUAL_FRESH_REALITY_OVERCLAIM")

    expected = post_dual.get("expected") or {}
    if (
        expected.get("current_zero_reality_requirements"),
        expected.get("current_nondominated_zero_reality_certificates"),
        expected.get("primitive_zero_reality_work_units"),
        expected.get("matched_priority_child_facts"),
    ) != (17, 14, 31, 16):
        errors.append("POST_DUAL_PROJECTION_CARDINALITY_MISMATCH")

    dsv = dual_source_v.get("verified") or {}
    if not str(dual_source_v.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("DUAL_SOURCE_GATE_NOT_INDEPENDENT_PASS")
    if set(dsv.get("discharged_requirements") or []) != DISCHARGED:
        errors.append("DUAL_SOURCE_DISCHARGED_SET_MISMATCH")
    if dsv.get("direct_oracle_leaves_executed") is not False:
        errors.append("DUAL_SOURCE_DIRECT_REALITY_OVERCLAIM")
    if dsv.get("global_fresh_reality_authority") is not False:
        errors.append("DUAL_SOURCE_FRESH_REALITY_OVERCLAIM")

    if errors:
        return _fail(*errors)

    # V1 is independently verified for all unchanged logic. Supply a strictly
    # local compatibility view only after V13/V5 has been independently
    # validated above. The compatibility object is never emitted as authority.
    compat = copy.deepcopy(scheduling)
    compat["status"] = "ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V10_CURRENT__V2_COMPATIBILITY_VIEW"
    compat["mandatory_tool_discovery_retrieval"] = {
        "mandatory": True,
        "v3_activation_git_blob_sha": retrieval.get("v5_activation_git_blob_sha"),
        "pre_v3_epoch_exhaustion_allowed": False,
        "consumed_source_epoch_replay_allowed": False,
    }

    out = v1.evaluate(
        _load(PATHS["registry"]),
        _load(PATHS["evidence"]),
        _load(PATHS["frontier"]),
        _load(PATHS["dominance"]),
        _load(PATHS["dominance_v"]),
        _load(PATHS["matched"]),
        _load(PATHS["matched_v"]),
        _load(PATHS["ownership"]),
        _load(PATHS["authority"]),
        compat,
    )
    if out.get("pass") is not True:
        return _fail("V1_INNER_COMPILER_FAILED:" + ",".join(out.get("errors") or []))

    units = [
        copy.deepcopy(row)
        for row in (out.get("acceptance_work_units") or [])
        if row.get("work_unit_id") not in DISCHARGED
    ]
    for row in units:
        if row.get("mandatory_tool_discovery_v3_gate") is True:
            row.pop("mandatory_tool_discovery_v3_gate", None)
            row["mandatory_tool_discovery_v5_gate"] = True
            hints = list(row.get("source_hints") or [])
            if hints:
                hints[0] = (
                    "MANDATORY_TOOL_DISCOVERY_V5_OVER_V4_OVER_V3_OVER_"
                    "VERIFIED_V2_BASE_RETRIEVAL_GATE"
                )
            row["source_hints"] = hints

    if len(units) != 31:
        return _fail("POST_DUAL_PRIMITIVE_WORK_UNIT_COUNT_NOT_31")

    out = copy.deepcopy(out)
    out["schema"] = SCHEMA
    out["status"] = (
        "PASS__V13_V5_POST_DUAL_ADAPTIVE_PARALLEL_FRONTIER__"
        "31_PRIMITIVE_ZERO_REALITY_WORK_UNITS__ZERO_CREDIT"
    )
    out["acceptance_work_units"] = units
    out["live_world"]["nondominated_certificates"] = 14
    out["live_world"]["verified_zero_reality_requirements"] = 17
    out["action_refinement"]["coarse_zero_reality_requirements"] = 17
    out["action_refinement"]["direct_nonmatched_work_units"] = 15
    out["action_refinement"]["primitive_acceptance_work_units"] = 31
    out["execution_policy"].pop("tool_discovery_v3_gate_mandatory", None)
    out["execution_policy"]["tool_discovery_v5_gate_mandatory"] = True
    out["post_dual_transition"] = {
        "discharged_zero_reality_requirements": sorted(DISCHARGED),
        "direct_reality_blocked_predicates": list(
            pdv.get("direct_reality_blocked_predicates") or []
        ),
        "source_admission_is_acceptance": False,
    }
    out["compatibility"] = {
        "inner_controller": "V1_IMMUTABLE",
        "current_scheduling": "V13",
        "tool_discovery_retrieval": "V5_OVER_V4_OVER_V3_OVER_V2",
        "post_dual_frontier": "17_REQUIREMENTS__14_CERTIFICATES__31_PRIMITIVE_UNITS",
        "compatibility_projection_has_authority": False,
    }
    out["hard_rules"] = list(out.get("hard_rules") or []) + [
        "V13_V5_VALIDATED_BEFORE_V1_COMPATIBILITY_PROJECTION",
        "POST_DUAL_TWO_SOURCE_REQUIREMENTS_REMOVED_ONLY_BY_INDEPENDENT_RECEIPT",
        "FINANCE_AND_UNKNOWN_DIRECT_PREDICATES_REMAIN_REALITY_BLOCKED",
        "COMPATIBILITY_PROJECTION_IS_INTERNAL_ONLY_AND_HAS_ZERO_AUTHORITY",
    ]
    return out


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
