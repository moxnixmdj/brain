from copy import deepcopy
from pathlib import Path

from canonical.runtime import current_one_shot_projection_v1 as projection

ROOT = Path(__file__).resolve().parents[2]
KNOWN_WAKES = [
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
    "NEW_AUTHENTICATED_SENSE_DISCRIMINATOR_OBSERVATION_RECEIPT"
]


def _r2(wakes):
    return {
        "current_cell_classifications": {
            "FINANCE_SEMANTIC_ADEQUACY_TAIL": {
                "state": "INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
                "wake_on": list(wakes),
                "information_theoretic_externality_proved": False,
            }
        }
    }


def test_known_eleven_wakes_collapse_to_three_effect_classes():
    out = projection._finance_wake_effect_projection(_r2(KNOWN_WAKES))
    assert out["status"] == "PASS__FINANCE_WAKE_EFFECT_QUOTIENT"
    assert out["concrete_wake_condition_count"] == 11
    assert out["decision_effect_class_count"] == 3
    assert out["all_wakes_classified"] is True
    assert out["dedupe_by_effect_class_authorized"] is True
    assert len(out["effect_groups"]["COMMON_POLICY_ADEQUACY_BYPASS"]) == 1
    assert len(out["effect_groups"]["DIRECT_END_TO_END_ADEQUACY_BYPASS"]) == 1
    assert len(out["effect_groups"]["AUTHENTICATED_WORLD_DISCRIMINATOR_OR_CONSTRAINT"]) == 9
    assert out["information_theoretic_externality_proved"] is False
    assert out["terminal_credit_delta"] == 0


def test_future_unknown_wake_is_never_silently_deduplicated():
    wakes = deepcopy(KNOWN_WAKES)
    wakes.append("FUTURE_UNMODELED_POLICY_CHANGING_WAKE")
    out = projection._finance_wake_effect_projection(_r2(wakes))
    assert out["status"] == "FAIL_CLOSED__UNCLASSIFIED_FINANCE_WAKE_PRESERVED_SEPARATELY"
    assert out["concrete_wake_condition_count"] == 12
    assert out["decision_effect_class_count"] == 4
    assert out["all_wakes_classified"] is False
    assert out["dedupe_by_effect_class_authorized"] is False
    assert out["unclassified_wakes"] == ["FUTURE_UNMODELED_POLICY_CHANGING_WAKE"]
    assert any(key.startswith("UNCLASSIFIED_WAKE::") for key in out["effect_groups"])
    assert out["terminal_credit_delta"] == 0


def test_dynamic_projection_reads_current_r2_and_preserves_zero_credit():
    out = projection.evaluate(ROOT)
    assert out["pass"] is True, out["errors"]
    finance = out["current_r2"]["finance_wake_effect_projection"]
    assert finance["concrete_wake_condition_count"] == 11
    assert finance["decision_effect_class_count"] == 3
    assert finance["all_wakes_classified"] is True
    assert finance["dedupe_by_effect_class_authorized"] is True
    assert finance["preserve_concrete_wake_routes_for_provenance"] is True
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
