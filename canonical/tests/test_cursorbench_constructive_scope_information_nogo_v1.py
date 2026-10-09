from canonical.runtime.cursorbench_constructive_scope_information_nogo_v1 import (
    two_world_countermodel,
    verify,
)

def test_two_world_hidden_grader_countermodel():
    out = two_world_countermodel(
        same_preterminal_view=True,
        accepting_sets_disjoint=True,
    )
    assert out["pass"] is True
    assert out["deterministic_all_members_guarantee_possible"] is False
    assert out["randomized_probability_one_both_worlds_possible"] is False

def test_countermodel_requires_indistinguishability():
    out = two_world_countermodel(
        same_preterminal_view=False,
        accepting_sets_disjoint=True,
    )
    assert out["pass"] is False
    assert "WORLDS_DISTINGUISHABLE_PRETERMINALLY" in out["errors"]

def test_countermodel_requires_disjoint_acceptance():
    out = two_world_countermodel(
        same_preterminal_view=True,
        accepting_sets_disjoint=False,
    )
    assert out["pass"] is False
    assert "ACCEPTING_SETS_NOT_DISJOINT" in out["errors"]

def test_bound_current_information_nogo():
    out = verify()
    assert out["pass"] is True, out
    assert out["scope_complete"] is True
    assert out["positive_adequacy_cover_closed"] is False
    assert out["constructive_scope_theorem_from_current_information_only_authorized"] is False
    assert out["new_target_relevant_information_required_to_exclude_countermodel"] is True
    assert out["actual_cursorbench_conflict_pair_claimed"] is False
    assert out["v5_inadequacy_claimed"] is False
    assert out["terminal_credit_delta"] == 0
