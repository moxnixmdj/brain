from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PATHS = {
    "authority": "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V16.json",
    "shared_tail": "canonical/governance/UNKNOWN_DOMAIN_SHARED_SEMANTIC_TAIL_COLLAPSE_20261007_V1.json",
    "two_behavior": "canonical/governance/UNKNOWN_DOMAIN_TWO_BEHAVIOR_SHARED_SEMANTIC_FRONTIER_REDUCTION_20261007_V1.json",
    "coalescence": "canonical/governance/TARGET_RELATIVE_SELECTED_SEMANTIC_DISCRIMINATOR_COALESCENCE_20261007_V1.json",
    "coalescence_verification": "canonical/verification/TARGET_RELATIVE_SELECTED_SEMANTIC_DISCRIMINATOR_WOLFRAM_VERIFICATION_20261007_V1.json",
    "k6": "canonical/governance/K6_POSITIVE_ADEQUACY_COVER_CERTIFICATE_THEOREM_20261006_V1.json",
    "k6_verification": "canonical/verification/K6_POSITIVE_ADEQUACY_COVER_CERTIFICATE_SPRITE_VERIFICATION_20261006_V1.json",
    "repair": "canonical/governance/UNKNOWN_DOMAIN_SPEC_ACCEPTANCE_ATOMICITY_TRUTH_REPAIR_20261007_V1.json",
}
EXPECTED = {
    PATHS["authority"]: "c1bc4543860be08f9014f69a212ba2222d8dba7c",
    PATHS["shared_tail"]: "069dd49aa1be27b218a66eb2f91c6de5cd49ff27",
    PATHS["two_behavior"]: "f90e67c07e2ea0da908d836b2574d667f5243d9e",
    PATHS["coalescence"]: "40407100382be8ffd729f4ef1d15a5f0068bedff",
    PATHS["coalescence_verification"]: "2913b491be9f88b6399bc9eb99a0294d01510e04",
    PATHS["k6"]: "8a235f91ad3064714fab3ea73b324487d9b7f8e5",
    PATHS["k6_verification"]: "de91c37808fe53bc133b399ebc7630f2b82bb0e3",
}

def blob_sha(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def verify() -> dict:
    errors: list[str] = []
    for rel, expected in EXPECTED.items():
        actual = blob_sha(rel)
        if actual != expected:
            errors.append(f"SOURCE_DRIFT:{rel}:{actual}")

    source = load(PATHS["two_behavior"])
    coal = load(PATHS["coalescence"])
    coal_v = load(PATHS["coalescence_verification"])
    repair = load(PATHS["repair"])

    if source["theorem"]["whole_behavior_acceptance_obligations_remaining"] != 2:
        errors.append("STALE_SOURCE_COUNT_CHANGED")

    deleted = set(coal["truth_repair"]["delete_as_separate_scheduling_residuals"])
    required_deleted = {
        "R1_COMPLETE_SEMANTIC_HYPOTHESIS_SET",
        "R2_PER_HYPOTHESIS_OUTCOME_MODEL_FOR_UNUSED_OR_UNSELECTED_SEMANTIC_WORLDS",
    }
    if not required_deleted.issubset(deleted):
        errors.append("COALESCENCE_DELETION_BOUNDARY_MISSING")

    if coal["truth_repair"]["coalesce_to_existing_interface"] != "K6_SOUND_POLICY_COVER_WITNESS_AND_SELECTED_DISCRIMINATOR_BINDING":
        errors.append("K6_INTERFACE_DRIFT")

    verified = set(coal_v["verified"])
    if "NO_NEW_INDEPENDENT_TERMINAL_TRUTH_OR_GENERIC_IMPLEMENTATION_GENERATOR_IS_ESTABLISHED_BY_R1_R2" not in verified:
        errors.append("INDEPENDENT_COALESCENCE_VERIFICATION_MISSING")

    tr = repair["truth_repair"]
    if tr["named_atomic_whole_behavior_acceptance_obligations_before"] != 2:
        errors.append("BEFORE_COUNT")
    if tr["named_atomic_whole_behavior_acceptance_obligations_after"] != 1:
        errors.append("AFTER_COUNT")
    if tr["remaining_named_atomic_whole_behavior"] != "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001":
        errors.append("REMAINING_ATOMIC_BEHAVIOR")
    if tr["spec_acceptance_selected_cell_obligations_remaining"] is not True:
        errors.append("SPEC_CELL_OBLIGATION_DROPPED")
    if tr["shared_semantic_tail_remaining"] is not True:
        errors.append("SEMANTIC_TAIL_OVERCLAIM")

    preserve = set(tr["preserve_exactly"])
    expected_preserve = {
        "SOUND_POSITIVE_ADEQUACY_PROOF_FOR_EVERY_POLICY_WORLD_CELL_ACTUALLY_USED_BY_THE_SELECTED_COVER",
        "TRUTHFUL_OBSERVATION_SEMANTICS_FOR_EVERY_SELECTED_DISCRIMINATOR_NEEDED_TO_CHOOSE_BETWEEN_DIFFERENT_CERTIFIED_POLICIES",
        "BOUND_TERMINAL_ORDER_AND_HARD_CONSTRAINTS_NEEDED_TO_VALIDATE_POSITIVE_EDGES",
        "FAIL_CLOSED_UNKNOWN_WHEN_NO_SOUND_COVER_IS_CERTIFIED_FROM_INCOMPLETE_INFORMATION",
    }
    if preserve != expected_preserve:
        errors.append("LOAD_BEARING_FACT_SET_DRIFT")

    hard = set(repair["hard_nonclaims"])
    for required in (
        "NO_CLAIM_SPECIFICATION_ACCEPTANCE_SELECTED_CELL_COVERAGE_IS_COMPLETE.",
        "NO_CLAIM_UNKNOWN_DOMAIN_ADAPTATION_IS_CLOSED.",
        "NO_CLAIM_COMPLETE_SELECTED_CONTEXT_ABC_OR_D_FINALITY_IS_CLOSED.",
    ):
        if required not in hard:
            errors.append("MISSING_NONCLAIM:" + required)

    return {
        "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_SPEC_ACCEPTANCE_ATOMICITY_TRUTH_REPAIR_VERIFIER_V1",
        "status": "PASS__STALE_ATOMIC_SPEC_ACCEPTANCE_OBLIGATION_DELETED__K6_SELECTED_CELL_FACTS_PRESERVED__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": errors,
        "named_atomic_whole_behavior_acceptance_obligations_before": 2,
        "named_atomic_whole_behavior_acceptance_obligations_after": 1 if not errors else None,
        "spec_acceptance_selected_cell_obligations_remaining": True,
        "unknown_domain_closed": False,
        "abc_closed": False,
        "d_finality_closed": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }

if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
