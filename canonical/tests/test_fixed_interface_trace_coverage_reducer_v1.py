from __future__ import annotations

from canonical.runtime.fixed_interface_trace_coverage_reducer_v1 import evaluate


def witness(**updates):
    value = {
        "target_rule": "USEFUL_BEHAVIOR_NOT_INTERNAL_IMPLEMENTATION",
        "included_behavior_interface_mediated": True,
        "profile_union_interface_complete": True,
        "interface_completeness_independently_verified": True,
        "interface_alphabet": {
            "external_inputs": [
                "TEXT",
                "IMAGE_OR_SCREENSHOT",
                "TOOL_RESULT_OR_SERVER_TOOL_RESULT",
                "TOOL_OR_ENVIRONMENT_STATE_ENCODED_THROUGH_DOCUMENTED_CONTENT_BLOCKS",
            ],
            "model_emissions": [
                "TEXT",
                "STRUCTURED_TOOL_USE_OR_SERVER_TOOL_USE_REQUEST",
            ],
        },
        "trace_operations": [
            "SEQUENCE",
            "BRANCH",
            "LOOP",
            "PARALLEL_TOOL_CALL_GROUP",
            "PAUSE_AND_CONTINUE",
            "STATE_CARRY_FORWARD",
        ],
        "all_finite_well_formed_traces_in_domain": True,
    }
    value.update(updates)
    return value


def test_trace_coverage_passes_without_role_or_family_totality_fields():
    out = evaluate(witness())
    assert out["target_coverage_proved"] is True
    assert out["role_classification_totality_required_for_coverage"] is False
    assert out["family_semantic_totality_required_for_coverage"] is False
    assert out["domain_dominance_proved"] is False
    assert out["terminal_finality"] is False


def test_explicit_false_role_and_family_totality_do_not_change_extensional_coverage():
    value = witness(
        role_classification_totality=False,
        family_semantic_totality=False,
    )
    out = evaluate(value)
    assert out["target_coverage_proved"] is True


def test_profile_union_interface_incompleteness_fails_closed():
    out = evaluate(witness(profile_union_interface_complete=False))
    assert out["target_coverage_proved"] is False
    assert "PROFILE_UNION_INTERFACE_NOT_COMPLETE" in out["failures"]


def test_unverified_interface_completeness_fails_closed():
    out = evaluate(witness(interface_completeness_independently_verified=False))
    assert out["target_coverage_proved"] is False
    assert "INTERFACE_COMPLETENESS_NOT_INDEPENDENTLY_VERIFIED" in out["failures"]


def test_hidden_implementation_target_rule_cannot_use_trace_coverage():
    out = evaluate(witness(target_rule="INCLUDE_HIDDEN_IMPLEMENTATION"))
    assert out["target_coverage_proved"] is False
    assert "TARGET_RULE_NOT_OBSERVABLE_BEHAVIOR" in out["failures"]


def test_non_interface_mediated_target_behavior_fails_closed():
    out = evaluate(witness(included_behavior_interface_mediated=False))
    assert out["target_coverage_proved"] is False
    assert "TARGET_BOUNDARY_NOT_INTERFACE_MEDIATED" in out["failures"]


def test_missing_trace_operation_fails_closed():
    value = witness()
    value["trace_operations"] = [
        "SEQUENCE",
        "BRANCH",
        "LOOP",
        "PAUSE_AND_CONTINUE",
        "STATE_CARRY_FORWARD",
    ]
    out = evaluate(value)
    assert out["target_coverage_proved"] is False
    assert any(x.startswith("TRACE_OPERATIONS_INCOMPLETE:") for x in out["failures"])


def test_empty_interface_alphabet_fails_closed():
    value = witness()
    value["interface_alphabet"] = {
        "external_inputs": [],
        "model_emissions": [],
    }
    out = evaluate(value)
    assert out["target_coverage_proved"] is False
    assert "EXTERNAL_INPUT_ALPHABET_INVALID" in out["failures"]
    assert "MODEL_EMISSION_ALPHABET_INVALID" in out["failures"]


def test_trace_language_must_be_closed():
    out = evaluate(witness(all_finite_well_formed_traces_in_domain=False))
    assert out["target_coverage_proved"] is False
    assert "TRACE_LANGUAGE_NOT_CLOSED" in out["failures"]
