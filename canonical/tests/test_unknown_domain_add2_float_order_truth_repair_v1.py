from canonical.runtime import unknown_domain_direct_candidate_v2 as candidate
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as old_harness
from canonical.runtime import unknown_domain_direct_execution_harness_v2 as new_harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as generator
from canonical.runtime import unknown_domain_direct_hidden_scorer_v2 as new_scorer


BEACON = "BEACON-000049-VALID"


def _fixture():
    return generator.generate_qualification_fixture_population(beacon=BEACON)


def test_exact_add2_float_order_counterexample_falsifies_v1_exact_equality():
    pop = _fixture()
    visible = pop["visible_cases"][4]
    hidden = pop["hidden_records"][4]
    assert hidden["latent_primitive_program"]["op"] == "ADD2"

    out = old_harness.execute_case(
        candidate_step=candidate.step,
        case_visible=visible,
        hidden_record=hidden,
    )
    assert out["scorer_result"]["pass"] is False
    assert "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in out["scorer_result"]["errors"]

    predicted = out["candidate_terminal_action"]["terminal_consequence"]
    gold = hidden["gold_terminal_consequence"]
    assert predicted != gold
    assert abs(predicted - gold) < 1e-12
    assert set(out["candidate_terminal_action"]["support_feature_ids"]) == set(
        hidden["transfer_relevant_feature_ids"]
    )


def test_v2_scorer_repairs_only_numeric_representation_artifact():
    pop = _fixture()
    visible = pop["visible_cases"][4]
    hidden = pop["hidden_records"][4]

    out = new_harness.execute_case(
        candidate_step=candidate.step,
        case_visible=visible,
        hidden_record=hidden,
    )
    assert out["scorer_result"]["pass"] is True
    assert out["scorer_result"]["errors"] == []


def test_truth_repaired_harness_passes_all_27_zero_production_fixture_cases():
    pop = _fixture()
    results = []
    for visible, hidden in zip(pop["visible_cases"], pop["hidden_records"], strict=True):
        out = new_harness.execute_case(
            candidate_step=candidate.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        results.append(out["scorer_result"])

    agg = new_scorer.aggregate(results)
    assert agg["all_27_cases_pass"] is True
    assert agg["transfer_leaf_pass"] is True
    assert agg["abstention_leaf_pass"] is True
    assert pop["production"] is False
