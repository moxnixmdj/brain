from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_MATCHED_SUCCESS_ZERO_REALITY_CUT_VERIFIER_V1"

CUT = "canonical/governance/MATCHED_SUCCESS_ZERO_REALITY_CUT_20261006_V1.json"
PROTOCOLS = "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
SUPER = "canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json"
R3 = "canonical/governance/ROOT3_MATCHED_SUPERPORTFOLIO_MINIMUM_REALITY_BINDING_V1.json"
DIFF = "canonical/governance/DIFFERENTIAL_DOMINANCE_COMPILER_V1.json"
PREWAVE = "canonical/governance/BRAIN_FIRST_DIFFERENTIAL_PREWAVE_V1.json"
PREWAVE_VERIFY = "canonical/verification/BRAIN_FIRST_DIFFERENTIAL_PREWAVE_PUBLIC_RUNNER_VERIFICATION_20261006_V1.json"
MONO_COUNTERMODEL = "canonical/governance/MATCHED_SUCCESS_REDUCER_MONOTONICITY_COUNTERMODEL_V1.json"
OWN = "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"
CONTRACTS = "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"

EXPECTED = {
    PROTOCOLS: "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    SUPER: "d9ac894594ebcd2883520f7b7977a3548420541c",
    R3: "0fa75e451bba19754a4296283c0095e4182ca97d",
    DIFF: "1b7007fb469bf5c666c43bfb2fe871e1e10b16c6",
    PREWAVE: "43b5c74b5caf3b3065feaf98a87f798e7c14aead",
    PREWAVE_VERIFY: "9a9437a07f7dad464800a6eddb9776e63916317a",
    MONO_COUNTERMODEL: "c9fd8dac4de690c860455bd449d226fe20b7ec11",
    OWN: "01abb91c114576ac340816b052724150258726ff",
    CONTRACTS: "ee187f611a0e82b2de495ee377682f39bc31dd31",
}

TARGETS = {
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}

FAMILIES = {
    "COMPLEX_MULTI_TOOL_AGENCY",
    "INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT",
    "MULTI_CAPABILITY_COMPOSITION",
}

REQUIRED_PREMISE_IDS = {
    "MATCHED_SUCCESS_REDUCER_MONOTONICITY_AND_IDENTITY",
    "MATCHED_CASE_ISOLATION_OR_RESET_EQUIVALENCE",
    "FINITE_COMPLETE_CONTENT_ADDRESSED_MATCHED_SCOPE",
}


def blob(path: str) -> str:
    b = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


def load(path: str) -> dict[str, Any]:
    obj = json.loads((ROOT / path).read_text())
    if not isinstance(obj, dict):
        raise ValueError(path + ":OBJECT_REQUIRED")
    return obj


def evaluate() -> dict[str, Any]:
    errors: list[str] = []
    for path, expected in EXPECTED.items():
        actual = blob(path)
        if actual != expected:
            errors.append(f"SOURCE_BLOB_DRIFT:{path}:{actual}")

    cut = load(CUT)
    protocols = load(PROTOCOLS)
    r3 = load(R3)
    prewave = load(PREWAVE)
    verify = load(PREWAVE_VERIFY)
    countermodel = load(MONO_COUNTERMODEL)
    own = load(OWN)

    if set(cut.get("target_predicates") or []) != TARGETS:
        errors.append("CUT_TARGET_SET_DRIFT")

    directly = set(
        ((prewave.get("scope_boundary") or {}).get("directly_applicable_to") or [])
    )
    if not TARGETS.issubset(directly):
        errors.append("PREWAVE_NOT_DIRECTLY_APPLICABLE_TO_ALL_THREE")

    if not str(verify.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("PREWAVE_INDEPENDENT_VERIFICATION_NOT_PASS")

    verified = set(verify.get("verified") or [])
    for required in {
        "ALL_BRAIN_SUCCESS_IMPLIES_ZERO_COMPARATOR_RESIDUAL",
        "ONLY_BRAIN_FAILURE_CASES_REMAIN_COMPARATOR_RELEVANT",
        "NONMONOTONE_REDUCER_OUTCOME_DEPENDENT_GENERATION_AND_CROSS_CASE_STATE_DEPENDENCE_FAIL_CLOSED",
    }:
        if required not in verified:
            errors.append("PREWAVE_VERIFIED_PROPERTY_MISSING:" + required)

    nonclaims = set(verify.get("hard_nonclaims") or [])
    for required in {
        "NO_CURRENT_MATCHED_REDUCER_MONOTONICITY_PROOF",
        "NO_CURRENT_COMPLETE_FINITE_MATCHED_CASE_UNIVERSE",
        "NO_TERMINAL_CASE_GENERATION_OR_EXECUTION",
    }:
        if required not in nonclaims:
            errors.append("PREWAVE_NONCLAIM_DRIFT:" + required)

    if "CONSERVATIVE_BOUND_ALONE_DOES_NOT_IMPLY_MONOTONICITY" not in str(
        countermodel.get("status") or ""
    ):
        errors.append("MONOTONICITY_COUNTERMODEL_STATUS_DRIFT")

    premises = cut.get("current_zero_reality_premises_open")
    if not isinstance(premises, list):
        errors.append("CUT_PREMISES_INVALID")
        premise_ids = set()
    else:
        premise_ids = {
            row.get("id")
            for row in premises
            if isinstance(row, Mapping) and row.get("state") == "OPEN"
        }
    if premise_ids != REQUIRED_PREMISE_IDS:
        errors.append("CUT_PREMISE_IDENTITY_DRIFT")

    protocol_families = {
        row.get("family")
        for row in protocols.get("protocols") or []
        if isinstance(row, Mapping)
        and row.get("family") in FAMILIES
        and row.get("status") == "DEFINED_RESULT_OPEN"
    }
    if protocol_families != FAMILIES:
        errors.append("TARGET_PROTOCOLS_NOT_ALL_OPEN")

    r3_rows = {
        row.get("predicate_id")
        for row in r3.get("matched_scope_targets") or []
        if isinstance(row, Mapping)
    }
    if not TARGETS.issubset(r3_rows):
        errors.append("THREE_TARGETS_NOT_ALL_IN_SHARED_SUPERPORTFOLIO")

    own_rows = {
        row.get("family"): row
        for row in own.get("rows") or []
        if isinstance(row, Mapping) and row.get("family") in FAMILIES
    }
    if set(own_rows) != FAMILIES:
        errors.append("OWNERSHIP_MATRIX_TARGET_ROWS_MISSING")
    for family, row in own_rows.items():
        if str(row.get("postwave_opus55_acceptance_status")) != "DEFINED_RESULT_OPEN":
            errors.append("OWNERSHIP_ACCEPTANCE_STATE_CHANGED:" + family)

    if cut.get("fresh_reality_authority") is not False:
        errors.append("FRESH_REALITY_OVERCLAIM")
    if cut.get("execution_authority") is not False:
        errors.append("EXECUTION_OVERCLAIM")
    if cut.get("promotion_authority") is not False:
        errors.append("PROMOTION_OVERCLAIM")

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__BRAIN_FIRST_DIFFERENTIAL_ROUTE_VERIFIED_CONDITIONALLY__THREE_ZERO_REALITY_PREMISES_OPEN__ZERO_CREDIT"
            if ok
            else "FAIL_CLOSED"
        ),
        "pass": ok,
        "errors": sorted(errors),
        "target_predicates": sorted(TARGETS) if ok else [],
        "open_zero_reality_premise_count": 3 if ok else None,
        "brain_first_can_reduce_opus_cases": True if ok else None,
        "best_case_opus_case_count": 0 if ok else None,
        "fresh_reality_authorized": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


if __name__ == "__main__":
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
