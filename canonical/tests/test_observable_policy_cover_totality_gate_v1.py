from canonical.runtime.observable_policy_cover_totality_gate_v1 import evaluate


def receipt(**extra):
    return {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        **extra,
    }


def base():
    return {
        "state_id": "S",
        "worlds": [{"world_id": "w0"}, {"world_id": "w1"}, {"world_id": "w2"}],
        "world_set_completeness_receipt": receipt(
            policy_relevant_world_set_complete=True,
            state_id="S",
        ),
        "policies": [
            {
                "policy_id": "p0",
                "adequate_world_ids": ["w0", "w1"],
                "cost_units": 2,
                "adequacy_receipt": receipt(
                    policy_id="p0",
                    policy_adequate_on_every_listed_world=True,
                    brain_owned=True,
                    deployed_exact=True,
                    resource_bound_proved=True,
                ),
            },
            {
                "policy_id": "p1",
                "adequate_world_ids": ["w2"],
                "cost_units": 1,
                "adequacy_receipt": receipt(
                    policy_id="p1",
                    policy_adequate_on_every_listed_world=True,
                    brain_owned=True,
                    deployed_exact=True,
                    resource_bound_proved=True,
                ),
            },
        ],
        "discriminators": [
            {
                "discriminator_id": "d",
                "cost_units": 3,
                "outcomes": {"w0": "a", "w1": "a", "w2": "b"},
                "truth_safety_receipt": receipt(
                    discriminator_id="d",
                    outcome_map_complete=True,
                    truth_preserving=True,
                    safe_on_entire_state=True,
                    resource_bound_proved=True,
                ),
            }
        ],
    }


def test_positive_cover_builds_strict_refinement_tree():
    out = evaluate(base())
    assert out["pass"] is True
    assert out["bound_state_totality_proved"] is True
    assert out["decision_tree"]["discriminator_id"] == "d"
    assert out["minimum_worst_case_resource_bound_units"] == 5.0
    assert out["u_empty_authorized"] is False
    assert out["terminal_authority"] is False


def test_common_policy_stops_without_discriminator():
    p = base()
    p["policies"][0]["adequate_world_ids"] = ["w0", "w1", "w2"]
    p["discriminators"] = []
    out = evaluate(p)
    assert out["pass"] is True
    assert out["decision_tree"]["terminal_policy_id"] == "p0"
    assert out["minimum_worst_case_resource_bound_units"] == 2.0


def test_indistinguishable_disjoint_policy_regions_remain_unresolved():
    p = base()
    p["discriminators"][0]["outcomes"] = {"w0": "same", "w1": "same", "w2": "same"}
    out = evaluate(p)
    assert out["pass"] is False
    assert out["status"].startswith("UNRESOLVED")
    assert out["negative_impossibility_authorized"] is False
    assert sorted(out["unresolved_observational_classes"][0]) == ["w0", "w1", "w2"]


def test_fake_library_completeness_mapping_cannot_authorize_impossibility():
    p = base()
    p["discriminators"][0]["outcomes"] = {"w0": 0, "w1": 0, "w2": 0}
    p["discriminator_library_scope_complete"] = True
    p["discriminator_library_completeness_receipt"] = {"anything": True}
    out = evaluate(p)
    assert out["pass"] is False
    assert out["negative_impossibility_authorized"] is False


def test_authenticated_library_completeness_can_label_negative_boundary():
    p = base()
    p["discriminators"][0]["outcomes"] = {"w0": 0, "w1": 0, "w2": 0}
    p["discriminator_library_scope_complete"] = True
    p["discriminator_library_completeness_receipt"] = receipt(
        discriminator_library_scope_complete=True,
        state_id="S",
    )
    out = evaluate(p)
    assert out["pass"] is False
    assert out["negative_impossibility_authorized"] is True
    assert out["terminal_authority"] is False


def test_missing_world_in_outcome_map_fails_closed():
    p = base()
    del p["discriminators"][0]["outcomes"]["w2"]
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "DISCRIMINATOR_OUTCOME_MAP_INCOMPLETE"


def test_unsound_policy_receipt_fails_closed():
    p = base()
    p["policies"][0]["adequacy_receipt"]["independent_verified"] = False
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"].startswith("POLICY_ADEQUACY_RECEIPT_INVALID")


def test_dict_outcomes_are_canonicalized_not_order_sensitive():
    p = base()
    p["worlds"] = [{"world_id": "w0"}, {"world_id": "w1"}]
    p["policies"] = [
        {
            "policy_id": "p0",
            "adequate_world_ids": ["w0"],
            "cost_units": 1,
            "adequacy_receipt": receipt(
                policy_id="p0",
                policy_adequate_on_every_listed_world=True,
                brain_owned=True,
                deployed_exact=True,
                resource_bound_proved=True,
            ),
        },
        {
            "policy_id": "p1",
            "adequate_world_ids": ["w1"],
            "cost_units": 1,
            "adequacy_receipt": receipt(
                policy_id="p1",
                policy_adequate_on_every_listed_world=True,
                brain_owned=True,
                deployed_exact=True,
                resource_bound_proved=True,
            ),
        },
    ]
    p["discriminators"][0]["outcomes"] = {
        "w0": {"a": 1, "b": 2},
        "w1": {"b": 2, "a": 1},
    }
    out = evaluate(p)
    assert out["pass"] is False
    assert out["unresolved_observational_classes"] == [["w0", "w1"]]


def test_cheaper_truthful_discriminator_beats_available_common_policy():
    p = base()
    p["policies"].append({
        "policy_id": "p_all",
        "adequate_world_ids": ["w0", "w1", "w2"],
        "cost_units": 100,
        "adequacy_receipt": receipt(
            policy_id="p_all",
            policy_adequate_on_every_listed_world=True,
            brain_owned=True,
            deployed_exact=True,
            resource_bound_proved=True,
        ),
    })
    p["discriminators"][0]["cost_units"] = 1
    out = evaluate(p)
    assert out["pass"] is True
    assert out["minimum_worst_case_resource_bound_units"] == 3.0
    assert out["decision_tree"]["discriminator_id"] == "d"
    assert out["terminal_credit_delta"] == 0


def test_equal_cost_prefers_common_adequate_policy_without_observation():
    p = base()
    p["policies"].append({
        "policy_id": "p_all",
        "adequate_world_ids": ["w0", "w1", "w2"],
        "cost_units": 3,
        "adequacy_receipt": receipt(
            policy_id="p_all",
            policy_adequate_on_every_listed_world=True,
            brain_owned=True,
            deployed_exact=True,
            resource_bound_proved=True,
        ),
    })
    p["discriminators"][0]["cost_units"] = 1
    out = evaluate(p)
    assert out["pass"] is True
    assert out["decision_tree"]["terminal_policy_id"] == "p_all"
    assert out["minimum_worst_case_resource_bound_units"] == 3.0


def test_nonfinite_or_unrepresentable_policy_cost_fails_closed():
    for cost in (float("nan"), float("inf"), float("-inf"), 10**1000):
        p = base()
        p["policies"][0]["cost_units"] = cost
        out = evaluate(p)
        assert out["pass"] is False
        assert out["reason"] == "POLICY_COST_INVALID"


def test_nonfinite_discriminator_cost_fails_closed():
    for cost in (float("nan"), float("inf"), float("-inf")):
        p = base()
        p["discriminators"][0]["cost_units"] = cost
        out = evaluate(p)
        assert out["pass"] is False
        assert out["reason"] == "DISCRIMINATOR_COST_INVALID"
