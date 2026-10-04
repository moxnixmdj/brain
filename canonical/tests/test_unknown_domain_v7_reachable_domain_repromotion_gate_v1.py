import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GATE=ROOT/"canonical/governance/UNKNOWN_DOMAIN_V7_REACHABLE_DOMAIN_ROOT3_REPROMOTION_GATE_20261005_V1.json"


def _gate():
    return json.loads(GATE.read_text(encoding="utf-8"))


def test_v7_repromotion_gate_is_outcome_blind_and_zero_credit():
    g=_gate()
    assert g["status"]=="FROZEN_OUTCOME_BLIND__EXACT_REACHABLE_BUILTIN_DOMAIN__INDEPENDENT_VERIFICATION_PENDING__ZERO_CREDIT"
    assert g["freeze_timing"]["independent_verifier_outcome_observed_at_freeze"] is False
    assert g["current_authority"]["proved_atomic"]==12
    assert g["current_authority"]["unresolved_atomic"]==26
    assert g["current_authority"]["terminal_achieved"] is False
    assert set(g["accounting"].values())=={0}


def test_v7_gate_binds_narrow_reachable_domain_not_isinstance_or_subclass_domain():
    g=_gate()
    d=g["successor_subject"]["reachable_production_domain"]
    assert d["beacon"]=="EXACT_BUILTIN_STR"
    assert d["evaluator_secret"]=="EXACT_BUILTIN_BYTES_LENGTH_32"
    assert set(d["unreachable_objects_are_not_part_of_the_theorem"])=={
        "INSTANCE___CLASS___SPOOF_PROXIES",
        "STR_SUBCLASSES",
        "BYTES_SUBCLASSES",
    }


def test_v7_gate_requires_independent_launcher_binding_before_12_to_13():
    g=_gate()
    required=set(g["promotion_predicate"]["all_required"])
    assert "INDEPENDENT_PR_2207_WORKFLOW_CONCLUSION_SUCCESS" in required
    assert "ALL_TWO_LAUNCHER_BLOBS_MATCH" in required
    assert "INDEPENDENT_RECEIPT_SCHEMA_STATUS_AND_ARTIFACT_BINDING_MATCH" in required
    assert "ZERO_PRODUCTION_OR_TERMINAL_CASES_CONSUMED" in required
    success=g["promotion_predicate"]["on_all_true"]
    assert success["proved_predicate_count_transition"]=="12_TO_13"
    assert success["unresolved_predicate_count_transition"]=="26_TO_25"
    assert success["family_remains_open_on"]=="MYSTERYMECHANISM_GE_49_55"


def test_v7_gate_fails_closed_without_independent_result():
    g=_gate()
    fail=g["promotion_predicate"]["on_any_false_missing_or_hash_mismatch"]
    assert fail["predicate_state"]=="EXTERNAL_BLOCKED"
    assert fail["proved_predicate_count_delta"]==0
    assert fail["unresolved_predicate_count_delta"]==0
