import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PATH=ROOT/"canonical/governance/UNKNOWN_DOMAIN_V6_SUBCLASS_REPAIR_ROOT3_REPROMOTION_GATE_20261005_V2.json"

def test_v2_is_outcome_blind_and_supersedes_v1():
    g=json.loads(PATH.read_text(encoding="utf-8"))
    assert g["status"].startswith("FROZEN_OUTCOME_BLIND__SUPERSEDES_V1")
    assert g["freeze_timing"]["independent_verifier_outcome_observed"] is False
    assert g["freeze_timing"]["independent_verifier_pull_request_created"] is False
    assert g["current_authority"]["proved_atomic"]==12
    assert g["current_authority"]["unresolved_atomic"]==26
    assert "V1_IS_SUPERSEDED_AND_MUST_NOT_AUTHORIZE_REPROMOTION" in g["hard_rules"]

def test_v2_binds_buffer_safe_repair_and_required_attacks():
    g=json.loads(PATH.read_text(encoding="utf-8"))
    b=g["repaired_candidate"]["required_blobs"]
    assert b["canonical/runtime/unknown_domain_direct_hidden_generator_v5.py"]=="60373126f3ee27368ae06e6d7d559f1b826d90d4"
    assert b["canonical/tests/test_unknown_domain_direct_v5.py"]=="5bc00ff6f7671ad43acb04a6fe4c3b6d1893c380"
    assert b["canonical/runtime/unknown_domain_direct_v6_universal_proof_v1.py"]=="58d3a61f5e2cb24b4387ddd817b64f897f62fe06"
    required=set(g["independent_verifier_contract"]["required_properties"])
    for item in (
        "STR_SUBCLASS_OVERRIDE_GETATTRIBUTE_IS_EXPLICITLY_ATTACKED",
        "STR_SUBCLASS_OVERRIDE_LEN_IS_EXPLICITLY_ATTACKED",
        "BYTES_SUBCLASS_OVERRIDE_BUFFER_IS_EXPLICITLY_ATTACKED",
        "BYTES_SUBCLASS_OVERRIDE_GETITEM_IS_EXPLICITLY_ATTACKED",
        "ADVERSARIAL_STR_BEACON_AND_STR_SECRET_EXECUTE_ALL_27_CASES_THROUGH_EXACT_HARNESS_AND_SCORER",
    ):
        assert item in required
    assert g["promotion_predicate"]["on_any_false_missing_or_hash_mismatch"]["predicate_state"]=="EXTERNAL_BLOCKED"
    assert g["accounting"]["acceptance_credit_delta"]==0
