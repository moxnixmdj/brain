from __future__ import annotations

import copy

from canonical.runtime.brain_first_differential_prewave_v1 import (
    SCHEMA,
    compile_brain_first_prewave,
)

SHA = "a" * 40


def receipt(path):
    return {"path": path, "git_blob_sha": SHA}


def base():
    return {
        "schema": SCHEMA,
        "scope": {
            "finite": True,
            "complete": True,
            "frozen": True,
            "content_addressed": True,
            "shared_binary_success_criterion": True,
            "case_generation_outcome_independent": True,
            "post_freeze_generation": True,
            "contamination_clean": True,
            "case_outcomes_isolated_or_reset_equivalent": True,
            "receipt": receipt("canonical/scope.json"),
        },
        "freeze": {
            "brain_commit_frozen": True,
            "brain_runtime_frozen": True,
            "dependencies_frozen": True,
            "scorer_frozen": True,
            "tool_authority_boundary_frozen": True,
            "target_identity_exact_opus55_frozen": True,
            "comparator_neutral_interface_frozen": True,
            "future_comparator_must_conform": True,
            "no_brain_repair_after_exposure": True,
            "no_brain_replay_after_exposure": True,
            "receipt": receipt("canonical/freeze.json"),
        },
        "reducer": {
            "monotone_under_success_set_inclusion": True,
            "same_reducer_for_brain_and_comparator": True,
            "receipt": receipt("canonical/reducer.json"),
        },
        "cases": [
            {
                "case_id": "A",
                "brain": {
                    "success": True,
                    "verified": True,
                    "receipt": receipt("canonical/brain-A.json"),
                },
            },
            {
                "case_id": "B",
                "brain": {
                    "success": True,
                    "verified": True,
                    "receipt": receipt("canonical/brain-B.json"),
                },
            },
        ],
    }


def test_all_brain_success_needs_zero_comparator_cases():
    out = compile_brain_first_prewave(base())
    assert out["status"] == "CANDIDATE_COMPARATOR_FREE_DIFFERENTIAL_DOMINANCE"
    assert out["differential_dominance_proved"] is True
    assert out["comparator_execution_required"] is False
    assert out["comparator_cases_required"] == []
    assert out["execution_authority"] is False


def test_only_brain_failures_become_comparator_residual():
    x = base()
    x["cases"][1]["brain"]["success"] = False
    out = compile_brain_first_prewave(x)
    assert out["status"] == "RESIDUAL_COMPARATOR_OPEN"
    assert out["brain_failure_residual_ids"] == ["B"]
    assert out["unresolved_residual_ids"] == ["B"]


def test_comparator_failure_on_every_residual_proves_pointwise_dominance():
    x = base()
    x["cases"][1]["brain"]["success"] = False
    x["cases"][1]["comparator"] = {
        "exact_opus55": True,
        "interface_conformant": True,
        "verified": True,
        "success": False,
        "receipt": receipt("canonical/opus-B.json"),
    }
    out = compile_brain_first_prewave(x)
    assert out["status"] == "CANDIDATE_RESIDUAL_ONLY_DIFFERENTIAL_DOMINANCE"
    assert out["differential_dominance_proved"] is True
    assert out["comparator_executed_case_count"] == 1


def test_opus_success_on_brain_failure_is_direct_counterexample():
    x = base()
    x["cases"][1]["brain"]["success"] = False
    x["cases"][1]["comparator"] = {
        "exact_opus55": True,
        "interface_conformant": True,
        "verified": True,
        "success": True,
        "receipt": receipt("canonical/opus-B.json"),
    }
    out = compile_brain_first_prewave(x)
    assert out["status"] == "VERIFIED_DIFFERENTIAL_COUNTEREXAMPLE"
    assert out["counterexample_case_ids"] == ["B"]
    assert out["differential_dominance_proved"] is False


def test_nonmonotone_reducer_fails_closed():
    x = base()
    x["reducer"]["monotone_under_success_set_inclusion"] = False
    out = compile_brain_first_prewave(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "MONOTONE_UNDER_SUCCESS_SET_INCLUSION_NOT_TRUE" in out["errors"][0]


def test_outcome_dependent_case_generation_fails_closed():
    x = base()
    x["scope"]["case_generation_outcome_independent"] = False
    out = compile_brain_first_prewave(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "CASE_GENERATION_OUTCOME_INDEPENDENT_NOT_TRUE" in out["errors"][0]


def test_stateful_cross_case_dependency_fails_closed():
    x = base()
    x["scope"]["case_outcomes_isolated_or_reset_equivalent"] = False
    out = compile_brain_first_prewave(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "CASE_OUTCOMES_ISOLATED_OR_RESET_EQUIVALENT_NOT_TRUE" in out["errors"][0]


def test_brain_repair_after_exposure_is_forbidden():
    x = base()
    x["freeze"]["no_brain_repair_after_exposure"] = False
    out = compile_brain_first_prewave(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "NO_BRAIN_REPAIR_AFTER_EXPOSURE_NOT_TRUE" in out["errors"][0]


def test_proxy_comparator_on_residual_fails_closed():
    x = base()
    x["cases"][1]["brain"]["success"] = False
    x["cases"][1]["comparator"] = {
        "exact_opus55": False,
        "interface_conformant": True,
        "verified": True,
        "success": False,
        "receipt": receipt("canonical/proxy-B.json"),
    }
    out = compile_brain_first_prewave(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "COMPARATOR_NOT_EXACT_OPUS55" in out["errors"][0]


def test_nonconformant_future_comparator_fails_closed():
    x = base()
    x["cases"][1]["brain"]["success"] = False
    x["cases"][1]["comparator"] = {
        "exact_opus55": True,
        "interface_conformant": False,
        "verified": True,
        "success": False,
        "receipt": receipt("canonical/opus-B.json"),
    }
    out = compile_brain_first_prewave(x)
    assert out["status"] == "FAIL_CLOSED"
    assert "COMPARATOR_INTERFACE_NONCONFORMANT" in out["errors"][0]


if __name__ == "__main__":
    test_all_brain_success_needs_zero_comparator_cases()
    test_only_brain_failures_become_comparator_residual()
    test_comparator_failure_on_every_residual_proves_pointwise_dominance()
    test_opus_success_on_brain_failure_is_direct_counterexample()
    test_nonmonotone_reducer_fails_closed()
    test_outcome_dependent_case_generation_fails_closed()
    test_stateful_cross_case_dependency_fails_closed()
    test_brain_repair_after_exposure_is_forbidden()
    test_proxy_comparator_on_residual_fails_closed()
    test_nonconformant_future_comparator_fails_closed()
    print("test_brain_first_differential_prewave_v1: PASS")
