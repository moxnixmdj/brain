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
OWN = "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"
CONTRACTS = "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"

EXPECTED = {
    PROTOCOLS: "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    SUPER: "d9ac894594ebcd2883520f7b7977a3548420541c",
    R3: "0fa75e451bba19754a4296283c0095e4182ca97d",
    DIFF: "1b7007fb469bf5c666c43bfb2fe871e1e10b16c6",
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

RESIDUAL_EXAMPLES = {
    "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",
    "BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001",
    "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
    "TASK_TO_DELEGATION_GRAPH_001",
    "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001",
    "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001",
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
    superp = load(SUPER)
    r3 = load(R3)
    diff = load(DIFF)
    own = load(OWN)
    contracts = load(CONTRACTS)

    if set(cut.get("target_predicates") or []) != TARGETS:
        errors.append("CUT_TARGET_SET_DRIFT")

    protocol_families = {
        row.get("family")
        for row in protocols.get("protocols") or []
        if isinstance(row, Mapping)
        and row.get("family") in FAMILIES
        and row.get("status") == "DEFINED_RESULT_OPEN"
    }
    if protocol_families != FAMILIES:
        errors.append("TARGET_PROTOCOLS_NOT_ALL_OPEN")

    cg = superp.get("case_generation") or {}
    if not (
        cg.get("generated_now") is False
        and cg.get("exposed_now") is False
        and cg.get("beacon_known_now") is False
    ):
        errors.append("SUPERPORTFOLIO_CASE_GENERATION_STATE_CHANGED")

    ca = superp.get("comparator_admissibility") or {}
    if ca.get("current_state") != "BLOCKED":
        errors.append("COMPARATOR_ADMISSIBILITY_STATE_CHANGED")

    diff_props = set(diff.get("required_scope_properties") or [])
    for required in {
        "FROZEN",
        "COMPLETE",
        "FINITE",
        "INDEPENDENTLY_VERIFIED",
        "SHARED_SUCCESS_CRITERION",
        "SHARED_AUTHORITY_BOUNDARY",
        "CONTAMINATION_CLEAN",
    }:
        if required not in diff_props:
            errors.append("DIFFERENTIAL_SCOPE_REQUIREMENT_DRIFT:" + required)

    r3_rows = {
        row.get("predicate_id")
        for row in r3.get("matched_scope_targets") or []
        if isinstance(row, Mapping)
    }
    if not TARGETS.issubset(r3_rows):
        errors.append("THREE_TARGETS_NOT_ALL_IN_SHARED_SUPERPORTFOLIO")

    compression = r3.get("execution_compression") or {}
    if compression.get("shared_future_superportfolio_wave_count") != 1:
        errors.append("SHARED_WAVE_COUNT_DRIFT")
    if compression.get("per_family_verdicts_remain_independent") is not True:
        errors.append("PER_FAMILY_VERDICT_INDEPENDENCE_DRIFT")

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

    contract_ids = {
        row.get("behavior_id")
        for row in contracts.get("active_contracted_residuals") or []
        if isinstance(row, Mapping)
    }
    if not RESIDUAL_EXAMPLES.issubset(contract_ids):
        errors.append("SHARED_CAUSAL_RESIDUAL_SET_DRIFT")

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
            "PASS__CURRENT_ZERO_REALITY_ROUTES_DO_NOT_CLOSE_THREE_MATCHED_SUCCESS_TARGETS__ONE_SHARED_FALLBACK_PRESERVED__ZERO_CREDIT"
            if ok
            else "FAIL_CLOSED"
        ),
        "pass": ok,
        "errors": sorted(errors),
        "target_predicates": sorted(TARGETS) if ok else [],
        "shared_empirical_wave_count": 1 if ok else None,
        "superportfolio_cases_generated_now": False if ok else None,
        "comparator_currently_admissible": False if ok else None,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


if __name__ == "__main__":
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
