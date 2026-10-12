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
    "NEW_AUTHENTICATED_CONTEXT_SOURCE_AND_FIELD_SEMANTICS_BINDING_OUTSIDE_VERIFIED_SEC_COMPANYCONCEPT_SEC_INLINE_XBRL_STANDARD_FASB_AND_SAME_FILING_ISSUER_EXTENSION_DOCUMENTATION_SCOPES",
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

def test_historical_pre_issuer_extension_wake_remains_classified():
    wakes = deepcopy(KNOWN_WAKES)
    wakes[5] = (
        "NEW_AUTHENTICATED_CONTEXT_SOURCE_AND_FIELD_SEMANTICS_BINDING_OUTSIDE_"
        "VERIFIED_SEC_COMPANYCONCEPT_AND_SEC_INLINE_XBRL_STANDARD_FASB_SCOPES"
    )
    out = projection._finance_wake_effect_projection(_r2(wakes))
    assert out["status"] == "PASS__FINANCE_WAKE_EFFECT_QUOTIENT"
    assert out["all_wakes_classified"] is True
    assert out["decision_effect_class_count"] == 3


def test_dynamic_projection_exposes_exact_default_runtime_separately_from_r2_baseline():
    out = projection.evaluate(ROOT)
    assert out["pass"] is True, out["errors"]
    assert out["current_r2"]["role"] == (
        "SCHEDULER_AND_ACTIVATION_BASELINE__NOT_DEFAULT_RUNTIME_SOURCE_SELECTOR"
    )
    live = out["default_runtime_integration"]
    assert live["scheduler_baseline"]["activation_route_count"] == 39
    assert live["scheduler_baseline"]["runtime_path"] == (
        "canonical/runtime/r2_direct_end_to_end_adequacy_v19.py"
    )
    assert live["scheduler_baseline"]["runtime_git_blob_sha"] == projection._blob(
        ROOT / projection.PATHS["v19"]
    )
    assert live["scheduler_baseline"]["is_default_runtime_source_selector"] is False
    assert live["effective_static_backend"]["runtime_path"] == (
        "canonical/runtime/r2_direct_end_to_end_adequacy_v21.py"
    )
    assert live["effective_static_backend"]["static_route_count"] == 41
    assert live["effective_static_backend"]["lineage"] == ["V21", "V20", "V19"]
    assert live["dynamic_admission"]["dynamic_route_count"] == 4
    assert live["effective_known_direct_route_count"] == 45
    assert live["scheduler_snapshot_is_default_runtime_source_selector"] is False
    assert live["semantic_truth_authority"] is False
    assert live["terminal_authority"] is False
    assert live["terminal_credit_delta"] == 0


def test_default_runtime_projection_rejects_tampered_v21_binding():
    default_runtime = projection._load(ROOT / projection.PATHS["default_runtime"])
    pointer = projection._load(ROOT / projection.PATHS["pointer"])
    admissions_pointer = projection._load(
        ROOT / projection.PATHS["dynamic_admissions_pointer"]
    )
    admissions_manifest = projection._load(
        ROOT / projection.PATHS["dynamic_admissions_manifest"]
    )
    actual = {
        name: projection._blob(ROOT / rel)
        for name, rel in projection.PATHS.items()
    }
    tampered = deepcopy(default_runtime)
    tampered["r2_default_route_runtime"]["verified_static_backend"][
        "runtime_git_blob_sha"
    ] = "0" * 40
    live, errors = projection._default_runtime_projection(
        pointer,
        tampered,
        admissions_pointer,
        admissions_manifest,
        actual,
    )
    assert "DEFAULT_RUNTIME_V21_BLOB_MISMATCH" in errors
    assert live["terminal_authority"] is False

