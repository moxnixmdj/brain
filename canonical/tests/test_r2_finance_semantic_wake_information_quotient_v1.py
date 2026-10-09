import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Q = ROOT / "canonical/governance/R2_FINANCE_SEMANTIC_WAKE_INFORMATION_QUOTIENT_20261009_V1.json"
S = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V56.json"

EXPECTED = {
    "NEW_AUTHENTIC_POLICY_CHANGING_SOURCE_OR_CONTEXT_FACT",
    "NEW_SCOPE_COMPLETE_SOUND_FINANCE_INTERPRETATION_OR_CONSTRAINT_BOUND",
    "NEW_COMMON_POLICY_ADEQUACY_CERTIFICATE_ROBUST_TO_THE_SURVIVING_COUNTERMODEL",
    "NEW_DIRECT_END_TO_END_FINANCE_ADEQUACY_CERTIFICATE",
    "NEW_CONTENT_ADDRESSED_COMPLETE_FINANCE_SOURCE_OR_CONVENTION_SCOPE_BOUND_OUTSIDE_VERIFIED_FIBO_Q2_2026_FULL_RELEASE_295_FILE_SCOPE",
    "NEW_AUTHENTICATED_CONTEXT_SOURCE_AND_FIELD_SEMANTICS_BINDING_OUTSIDE_VERIFIED_SEC_COMPANYCONCEPT_AND_SEC_INLINE_XBRL_STANDARD_FASB_SCOPES",
    "NEW_AUTHENTICATED_COMPLETE_BOUNDED_DENOTATION_EXTENSION_OR_SET_RELATION_EVIDENCE_OUTSIDE_VERIFIED_FIBO_Q2_2026_FULL_RELEASE_295_FILE_SCOPE",
    "NEW_TASK_SPECIFIC_OEWN_TERMINAL_SIGNATURE_OR_DISCRIMINATOR_BINDING_FOR_SURVIVING_RELEASE_RELATIVE_SENSES",
    "NEW_AUTHENTICATED_CONTEXT_OR_RELATION_EVIDENCE_THAT_DISCRIMINATES_SURVIVING_SENSES",
    "NEW_AUTHENTICATED_OEWN_DECISION_MANIFEST_BINDING_COMPLETE_TERMINAL_SIGNATURES_TO_ALL_RELEASE_RELATIVE_SENSES",
    "NEW_AUTHENTICATED_SENSE_DISCRIMINATOR_OBSERVATION_RECEIPT",
}

def test_finance_wake_quotient_is_total_and_noninflating():
    q=json.loads(Q.read_text(encoding="utf-8"))
    assert set(q["normalization_map"]) == EXPECTED
    assert len(q["normalization_map"]) == 11
    classes=set(q["normalization_map"].values())
    assert classes == {
        "COMMON_POLICY_ADEQUACY_BYPASS",
        "DIRECT_END_TO_END_ADEQUACY_BYPASS",
        "AUTHENTICATED_WORLD_DISCRIMINATOR_OR_CONSTRAINT",
    }
    assert q["prestate"]["information_theoretic_externality_proved"] is False
    assert q["theorem"]["does_not_prove_finance_closed"] is True
    assert q["theorem"]["does_not_prove_externality"] is True
    assert q["accounting"]["acceptance_credit_delta"] == 0
    assert q["accounting"]["terminal_credit_delta"] == 0

def test_scheduler_preserves_concrete_wakes_but_schedules_by_effect_class():
    q=json.loads(Q.read_text(encoding="utf-8"))
    s=json.loads(S.read_text(encoding="utf-8"))
    fq=s["finance_semantic_wake_information_quotient"]
    assert fq["path"] == "canonical/governance/R2_FINANCE_SEMANTIC_WAKE_INFORMATION_QUOTIENT_20261009_V1.json"
    assert fq["effect_class_count"] == 3
    assert fq["concrete_wake_condition_count"] == 11
    assert fq["preserve_concrete_wake_routes_for_provenance"] is True
    assert fq["finance_tail_closed"] is False
    assert fq["information_theoretic_externality_proved"] is False
    assert s["accounting"]["terminal_credit_delta"] == 0
