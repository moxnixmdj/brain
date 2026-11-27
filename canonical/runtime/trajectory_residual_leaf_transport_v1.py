from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BEHAVIOR = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
TARGET_FAMILIES = (
    "COMPLEX_MULTI_TOOL_AGENCY",
    "INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT",
    "MULTI_CAPABILITY_COMPOSITION",
)
FILES = {
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json": "ee187f611a0e82b2de495ee377682f39bc31dd31",
    "canonical/governance/P1_UNIVERSAL_SCOPE_RESTORATION_V9_CANDIDATE.json": "6ebaed1262bed76f003c2a337e3a80b3b099e9e0",
    "canonical/verification/P1_UNIVERSAL_SCOPE_RESTORATION_V9_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json": "2c6bb594d353e4c6a169821da5f84a91be212ca7",
}

def blob(path: str) -> str:
    b = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def load(path: str):
    return json.loads((ROOT / path).read_text())

def evaluate():
    drift = {
        p: {"expected": h, "actual": blob(p)}
        for p, h in FILES.items()
        if blob(p) != h
    }
    if drift:
        return {
            "pass": False,
            "status": "FAIL_CLOSED__SOURCE_BLOB_DRIFT",
            "drift": drift,
            "acceptance_credit_delta": 0,
        }

    registry = load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
    candidate = load("canonical/governance/P1_UNIVERSAL_SCOPE_RESTORATION_V9_CANDIDATE.json")
    verification = load("canonical/verification/P1_UNIVERSAL_SCOPE_RESTORATION_V9_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")

    errors = []
    if candidate.get("behavior_id") != BEHAVIOR:
        errors.append("CANDIDATE_BEHAVIOR_ID_MISMATCH")
    if verification.get("brain_candidate", {}).get("candidate_git_blob_sha") != FILES[
        "canonical/governance/P1_UNIVERSAL_SCOPE_RESTORATION_V9_CANDIDATE.json"
    ]:
        errors.append("VERIFICATION_DOES_NOT_BIND_CANDIDATE_BLOB")
    if not str(verification.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("P1_INDEPENDENT_VERIFICATION_NOT_PASS")

    verified = verification.get("verified", {})
    if verified.get("whole_p1_contract_restored") is not True:
        errors.append("WHOLE_P1_CONTRACT_NOT_RESTORED")
    if verified.get("whole_scope_contract_pass_count") != 12:
        errors.append("WHOLE_SCOPE_PASS_COUNT_NOT_12")
    if verified.get("whole_scope_quarantined_contract_count") != 0:
        errors.append("WHOLE_SCOPE_QUARANTINE_NONZERO")
    if verified.get("source_fresh_reality_units_consumed") != 0:
        errors.append("SOURCE_FRESH_REALITY_NONZERO")
    if verified.get("restoration_new_reality_units_consumed") != 0:
        errors.append("RESTORATION_FRESH_REALITY_NONZERO")
    if verified.get("terminal_results_replayed") != 0:
        errors.append("TERMINAL_RESULTS_REPLAYED")

    mappings = registry.get("family_to_residual_contracts", {})
    incidence = {}
    for family in TARGET_FAMILIES:
        leaves = mappings.get(family)
        if not isinstance(leaves, list):
            errors.append(f"MISSING_FAMILY_MAPPING:{family}")
            continue
        count = leaves.count(BEHAVIOR)
        incidence[family] = count
        if count != 1:
            errors.append(f"BEHAVIOR_INCIDENCE_NOT_EXACTLY_ONE:{family}:{count}")

    ok = not errors
    return {
        "pass": ok,
        "status": (
            "PASS__EXACT_BEHAVIOR_ID_FULL_SCOPE_LEAF_TRANSPORT__3_TARGET_INCIDENCES__ZERO_ACCEPTANCE_CREDIT"
            if ok else "FAIL_CLOSED"
        ),
        "behavior_id": BEHAVIOR,
        "target_families": list(TARGET_FAMILIES),
        "target_leaf_incidences": incidence,
        "discharged_leaf_incidence_count": 3 if ok else 0,
        "proof_basis": (
            "INDEPENDENTLY_VERIFIED_WHOLE_SCOPE_P1_CONTRACT_RESTORATION_PLUS_EXACT_SAME_BEHAVIOR_ID_IN_SAME_REGISTRY_BLOB"
        ),
        "hard_nonclaim": (
            "LEAF_TRANSPORT_DOES_NOT_BY_ITSELF_PROVE_ANY_OPUS55_ATOMIC_PREDICATE_OR_WHOLE_FAMILY; "
            "TARGET_SPECIFIC_LOSSLESS_SCOPE_DECOMPOSITION_AND_ANY_ROOT2_PERFORMANCE_OBLIGATIONS_REMAIN."
        ),
        "errors": errors,
        "new_reality_units_consumed": 0,
        "terminal_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "atomic_predicate_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }

if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
