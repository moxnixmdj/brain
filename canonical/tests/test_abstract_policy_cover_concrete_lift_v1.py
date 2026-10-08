from canonical.runtime.abstract_policy_cover_concrete_lift_v1 import evaluate, _digest


def _base():
    totality = {
        "pass": True,
        "status": "PASS__BOUND_STATE_TERMINAL_OR_STRICT_REFINEMENT_TOTALITY",
        "state_id": "S1",
        "bound_state_totality_proved": True,
        "unresolved_observational_classes": [],
        "decision_tree": {
            "discriminator_id": "D1",
            "worst_case_remaining_cost_units": 2.0,
            "outcome_partitions": [
                {"world_ids": ["W0"], "next": {"terminal_policy_id": "P0", "worst_case_remaining_cost_units": 1.0}},
                {"world_ids": ["W1"], "next": {"terminal_policy_id": "P1", "worst_case_remaining_cost_units": 1.0}},
            ],
        },
    }
    tsha = _digest(totality)
    dsha = _digest(totality["decision_tree"])
    common = {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "scope_id": "CLOSED_SCOPE",
        "state_id": "S1",
        "abstract_totality_result_sha256": tsha,
        "decision_tree_sha256": dsha,
    }
    return {
        "scope_id": "CLOSED_SCOPE",
        "state_id": "S1",
        "abstract_totality_result": totality,
        "abstraction_soundness_receipt": {
            **common,
            "concrete_scope_frozen": True,
            "every_concrete_context_represented": True,
            "abstraction_is_sound_overapproximation": True,
            "uncertainty_only_widens_abstract_state": True,
            "unproved_refinement_can_never_remove_concrete_possibilities": True,
        },
        "policy_lift_receipts": [
            {
                **common,
                "policy_id": pid,
                "abstract_policy_region_implies_concrete_adequacy": True,
                "brain_owned": True,
                "deployed_exact": True,
                "resource_bound_proved": True,
            }
            for pid in ("P0", "P1")
        ],
        "discriminator_lift_receipts": [
            {
                **common,
                "discriminator_id": "D1",
                "concrete_observation_refines_to_declared_abstract_outcome": True,
                "truth_preserving_on_scope": True,
                "safe_on_scope": True,
                "resource_bound_proved": True,
            }
        ],
    }


def test_positive_two_leaf_lift():
    out = evaluate(_base())
    assert out["pass"] is True
    assert out["concrete_scope_adaptive_policy_totality_proved"] is True
    assert out["used_policy_ids"] == ["P0", "P1"]
    assert out["used_discriminator_ids"] == ["D1"]
    assert out["basis_completeness_required_for_positive_proof"] is False
    assert out["u_empty_authorized"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0


def test_common_policy_tree_needs_no_discriminator_receipt():
    p = _base()
    p["abstract_totality_result"]["decision_tree"] = {
        "terminal_policy_id": "P0",
        "worst_case_remaining_cost_units": 0.0,
    }
    tsha = _digest(p["abstract_totality_result"])
    dsha = _digest(p["abstract_totality_result"]["decision_tree"])
    for row in [p["abstraction_soundness_receipt"], *p["policy_lift_receipts"]]:
        row["abstract_totality_result_sha256"] = tsha
        row["decision_tree_sha256"] = dsha
    p["policy_lift_receipts"] = [p["policy_lift_receipts"][0]]
    p["discriminator_lift_receipts"] = []
    out = evaluate(p)
    assert out["pass"] is True
    assert out["used_policy_ids"] == ["P0"]
    assert out["used_discriminator_ids"] == []


def test_missing_abstraction_coverage_fails_closed():
    p = _base()
    p["abstraction_soundness_receipt"]["every_concrete_context_represented"] = False
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "ABSTRACTION_SOUNDNESS_RECEIPT_INVALID"


def test_missing_policy_receipt_fails_closed():
    p = _base()
    p["policy_lift_receipts"] = p["policy_lift_receipts"][:1]
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "POLICY_LIFT_RECEIPTS_INVALID"


def test_policy_soundness_cannot_self_weaken():
    p = _base()
    p["policy_lift_receipts"][0]["abstract_policy_region_implies_concrete_adequacy"] = False
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "POLICY_LIFT_RECEIPTS_INVALID"


def test_missing_discriminator_receipt_fails_closed():
    p = _base()
    p["discriminator_lift_receipts"] = []
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "DISCRIMINATOR_LIFT_RECEIPTS_INVALID"


def test_unsound_discriminator_fails_closed():
    p = _base()
    p["discriminator_lift_receipts"][0]["truth_preserving_on_scope"] = False
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "DISCRIMINATOR_LIFT_RECEIPTS_INVALID"


def test_totality_false_fails_closed():
    p = _base()
    p["abstract_totality_result"]["bound_state_totality_proved"] = False
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "ABSTRACT_TOTALITY_NOT_POSITIVELY_PROVED"


def test_tree_hash_binding_blocks_substitution():
    p = _base()
    p["abstract_totality_result"]["decision_tree"]["outcome_partitions"][0]["next"]["terminal_policy_id"] = "P9"
    out = evaluate(p)
    assert out["pass"] is False


def test_invalid_nonterminal_tree_fails_closed():
    p = _base()
    p["abstract_totality_result"]["decision_tree"] = {"discriminator_id": "D1", "outcome_partitions": []}
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "ABSTRACT_DECISION_TREE_INVALID"
