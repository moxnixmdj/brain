from copy import deepcopy

from canonical.runtime.recovery_semantic_implication_audit_v1 import (
    CAUSAL_TARGET_ATOM,
    EARLIEST_TARGET_ATOM,
    P1_BINDING_BLOB,
    evaluate,
)


def _target():
    return {
        "targets": [
            {
                "predicate_id": "RECOVERY_TERMINAL_NONINFERIOR",
                "atom_sources": [
                    {"atom": "dimension:semantic_self_check"},
                    {"atom": "dimension:counterexample_discovery"},
                    {"atom": EARLIEST_TARGET_ATOM},
                    {"atom": "dimension:repair_selection"},
                    {"atom": "dimension:recovery_after_injected_failure"},
                    {"atom": "metric:terminal_recovery"},
                ],
                "metric_requirement_sources": [
                    {"metric": "terminal_recovery_noninferiority"}
                ],
            },
            {
                "predicate_id": "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
                "atom_sources": [
                    {"atom": EARLIEST_TARGET_ATOM},
                    {"atom": CAUSAL_TARGET_ATOM},
                    {"atom": "metric:true_root_cause_topk"},
                ],
                "metric_requirement_sources": [
                    {"metric": "causal_localization_noninferiority"}
                ],
            },
            {
                "predicate_id": "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
                "atom_sources": [
                    {"atom": "invariant:zero_critical_fail_closed_misses"}
                ],
                "metric_requirement_sources": [
                    {"metric": "critical_fail_closed_misses"}
                ],
            },
        ]
    }


def _binding():
    return {
        "behavior_id": "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "evaluator": {
            "required_checks": [
                "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE",
                "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE",
                "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT",
            ]
        },
        "terminal_acceptance": {
            "any_load_bearing_p1_failure_blocks_behavior_proof": True,
            "proof_rule": (
                "FOR_EACH_CASE__DIRECT_P1_INTERVENTION_RESCUE_INSTRUMENTATION_MUST_PASS"
            ),
        },
        "contamination": {
            "post_freeze_case_specific_tuning": False,
            "case_replacement": False,
            "result_to_runtime_feedback_during_wave": False,
            "evaluator_or_threshold_edit_after_first_terminal_result": False,
            "terminal_case_selection_before_route_freeze": False,
        },
    }


def _receipt(portfolio):
    return {
        "behavior_id": "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "binding_blob": P1_BINDING_BLOB,
        "direct_instrumentation_pass": True,
        "load_bearing": True,
        "parent_terminal_acceptance_pass": True,
        "case_replaced": False,
        "tuning_replay": False,
        "result_to_runtime_feedback": False,
        "portfolio": portfolio,
    }


def _wave():
    return {
        "status": (
            "ONE_SHOT_TERMINAL_WAVE_PASS__IMMUTABLE_PUBLIC_RUNNER_RECEIPT__"
            "NO_REPLAY_AUTHORIZED"
        ),
        "result_guards": {
            "no_case_replacement": True,
            "no_tuning_replay": True,
            "result_to_runtime_feedback_during_wave": False,
        },
        "reduction_input": {
            "wave": {
                "parent_portfolio_receipts": {
                    "T0": [_receipt("T0")],
                    "T2": [_receipt("T2")],
                }
            }
        },
    }


def test_positive_causal_atom_and_earliest_countermodel():
    out = evaluate(
        target_normalization=_target(),
        p1_binding=_binding(),
        terminal_wave=_wave(),
    )
    assert out["pass"] is True
    assert out["closed_predicates"] == []
    assert [x["atom"] for x in out["candidate_positive_atom_bindings"]] == [
        CAUSAL_TARGET_ATOM
    ]
    cert = out["nonimplication_certificates"][0]
    assert cert["atom"] == EARLIEST_TARGET_ATOM
    assert cert["countermodel"]["p1_disjunction_satisfied"] is True
    assert cert["countermodel"]["target_atom_satisfied"] is False
    assert all(x["state"] == "OPEN" for x in out["metric_bounds"])
    assert out["predicate_credit_delta"] == 0
    assert out["promotion_authority"] is False


def test_missing_symptom_negative_control_fails_closed():
    binding = _binding()
    binding["evaluator"]["required_checks"].remove(
        "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT"
    )
    out = evaluate(
        target_normalization=_target(),
        p1_binding=binding,
        terminal_wave=_wave(),
    )
    assert out["pass"] is False
    assert any("P1_CAUSAL_RESCUE_CHECKS_MISSING" in x for x in out["errors"])


def test_binding_blob_drift_fails_closed():
    wave = _wave()
    wave["reduction_input"]["wave"]["parent_portfolio_receipts"]["T2"][0][
        "binding_blob"
    ] = "deadbeef"
    out = evaluate(
        target_normalization=_target(),
        p1_binding=_binding(),
        terminal_wave=wave,
    )
    assert out["pass"] is False
    assert "P1_BINDING_BLOB_MISMATCH:T2" in out["errors"]


def test_replay_or_feedback_fails_closed():
    wave = _wave()
    wave["reduction_input"]["wave"]["parent_portfolio_receipts"]["T0"][0][
        "tuning_replay"
    ] = True
    out = evaluate(
        target_normalization=_target(),
        p1_binding=_binding(),
        terminal_wave=wave,
    )
    assert out["pass"] is False
    assert "P1_RECEIPT_TUNING_REPLAY:T0" in out["errors"]


def test_stricter_earliest_atom_is_never_promoted_from_or_literal():
    out = evaluate(
        target_normalization=_target(),
        p1_binding=_binding(),
        terminal_wave=_wave(),
    )
    promoted = {
        x["atom"] for x in out["candidate_positive_atom_bindings"]
    }
    assert EARLIEST_TARGET_ATOM not in promoted
