import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "canonical/governance/UNKNOWN_DOMAIN_V6_SUBCLASS_REPAIR_ROOT3_REPROMOTION_GATE_20261005_V1.json"


def test_repromotion_gate_is_outcome_blind_and_fail_closed():
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    assert gate["status"].startswith("FROZEN_OUTCOME_BLIND__ZERO_CREDIT")
    assert gate["current_authority"]["proved_atomic"] == 12
    assert gate["current_authority"]["unresolved_atomic"] == 26
    assert gate["current_authority"]["predicate_state"] == "EXTERNAL_BLOCKED"

    verifier = gate["independent_verifier_contract"]
    required = set(verifier["required_properties"])
    assert "STR_SUBCLASS_OVERRIDE_STRIP_IS_EXPLICITLY_ATTACKED" in required
    assert "STR_SUBCLASS_OVERRIDE_ENCODE_IS_EXPLICITLY_ATTACKED" in required
    assert "BYTES_SUBCLASS_OVERRIDE_BYTES_IS_EXPLICITLY_ATTACKED" in required
    assert "ADVERSARIAL_SUBCLASS_BEACON_AND_SECRET_PATHS_EXECUTE_ALL_27_CASES_THROUGH_EXACT_CANDIDATE_HARNESS_AND_SCORER" in required

    pred = gate["promotion_predicate"]
    assert pred["on_all_true"]["proved_predicate_count_transition"] == "12_TO_13"
    assert pred["on_all_true"]["unresolved_predicate_count_transition"] == "26_TO_25"
    assert pred["on_all_true"]["family_credit_delta"] == 0
    assert pred["on_any_false_missing_or_hash_mismatch"]["predicate_state"] == "EXTERNAL_BLOCKED"
    assert gate["accounting"]["acceptance_credit_delta"] == 0


def test_gate_binds_exact_repaired_subject_and_frozen_semantics():
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    blobs = gate["repaired_candidate"]["required_blobs"]
    assert blobs["canonical/runtime/unknown_domain_direct_hidden_generator_v5.py"] == "d087601a62a0b8ec9ab264487fb0b27a6246b977"
    assert blobs["canonical/tests/test_unknown_domain_direct_v5.py"] == "c98733407d594c3fa5713de5742022325463f390"
    assert blobs["canonical/runtime/unknown_domain_direct_v6_universal_proof_v1.py"] == "4a3e72b365ffa7e163abc63d197fcd386bdd104d"

    bridge = gate["frozen_semantic_bridge"]
    assert bridge["protocol_git_blob_sha"] == "fd586455d582c38c7062ffe735f86cb9f2e803ab"
    assert bridge["evaluator_git_blob_sha"] == "52090daf78d12020af48c1b6ffaea056d9029e1b"
