from canonical.runtime.matched_case_isolation_reset_v1 import (
    INPUT_SCHEMA,
    compile_isolation,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64
E = "e" * 64
F = "f" * 64


def base():
    return {
        "schema": INPUT_SCHEMA,
        "base": {
            "immutable_base_state_sha256": A,
            "brain_runtime_frozen": True,
            "opus_interface_frozen": True,
            "tool_authority_frozen": True,
            "read_only_shared_dependencies_only": True,
            "cross_case_persistent_memory_disabled": True,
            "cross_case_mutable_cache_disabled": True,
            "outbound_effects_case_namespaced": True,
            "case_namespace_destroyed_after_case": True,
            "external_mutable_services_resettable": True,
        },
        "cases": [
            {
                "case_id": "A",
                "immutable_base_state_sha256": A,
                "mutable_namespace_sha256": B,
                "case_initial_state_sha256": C,
                "brain_initial_state_sha256": C,
                "opus_initial_state_sha256": C,
                "prior_case_ids_consumed": [],
                "namespace_created_from_clean_base": True,
                "brain_run_confined_to_namespace": True,
                "future_opus_run_confined_to_same_namespace_semantics": True,
                "all_mutable_sinks_namespaced_or_restored": True,
                "post_case_namespace_destroyed": True,
                "external_mutable_state_restored": True,
                "no_result_dependent_case_generation": True,
                "no_result_dependent_runtime_mutation": True,
                "post_reset_base_state_sha256": A,
                "receipt": {
                    "receipt_sha256": D,
                    "independent_or_objective": True,
                },
            },
            {
                "case_id": "B",
                "immutable_base_state_sha256": A,
                "mutable_namespace_sha256": E,
                "case_initial_state_sha256": F,
                "brain_initial_state_sha256": F,
                "opus_initial_state_sha256": F,
                "prior_case_ids_consumed": [],
                "namespace_created_from_clean_base": True,
                "brain_run_confined_to_namespace": True,
                "future_opus_run_confined_to_same_namespace_semantics": True,
                "all_mutable_sinks_namespaced_or_restored": True,
                "post_case_namespace_destroyed": True,
                "external_mutable_state_restored": True,
                "no_result_dependent_case_generation": True,
                "no_result_dependent_runtime_mutation": True,
                "post_reset_base_state_sha256": A,
                "receipt": {
                    "receipt_sha256": B,
                    "independent_or_objective": True,
                },
            },
        ],
    }


def test_valid_isolation_passes():
    out = compile_isolation(base())
    assert out["status"] == "PASS__CASE_ISOLATED_OR_RESET_EQUIVALENT"
    assert out["residual_only_comparator_counterfactual_preserved"] is True
    assert out["case_count"] == 2


def test_prior_case_dependency_fails_closed():
    x = base()
    x["cases"][1]["prior_case_ids_consumed"] = ["A"]
    out = compile_isolation(x)
    assert out["status"] == "FAIL_CLOSED"


def test_namespace_reuse_fails_closed():
    x = base()
    x["cases"][1]["mutable_namespace_sha256"] = B
    out = compile_isolation(x)
    assert out["status"] == "FAIL_CLOSED"


def test_brain_opus_initial_state_mismatch_fails_closed():
    x = base()
    x["cases"][1]["opus_initial_state_sha256"] = C
    out = compile_isolation(x)
    assert out["status"] == "FAIL_CLOSED"


def test_failed_restore_fails_closed():
    x = base()
    x["cases"][0]["post_reset_base_state_sha256"] = C
    out = compile_isolation(x)
    assert out["status"] == "FAIL_CLOSED"


def test_hidden_mutable_sink_fails_closed():
    x = base()
    x["cases"][0]["all_mutable_sinks_namespaced_or_restored"] = False
    out = compile_isolation(x)
    assert out["status"] == "FAIL_CLOSED"


def test_result_dependent_runtime_mutation_fails_closed():
    x = base()
    x["cases"][0]["no_result_dependent_runtime_mutation"] = False
    out = compile_isolation(x)
    assert out["status"] == "FAIL_CLOSED"
