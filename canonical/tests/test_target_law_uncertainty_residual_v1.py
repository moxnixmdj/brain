from canonical.runtime.target_law_uncertainty_residual_v1 import (
    all_laws_top_element_certificate,
    finite_two_world_falsifier,
    target_law_residual,
    target_restriction_suffices,
)

SUCCESS={"failure":0.0,"success":1.0}
SAFE={"unsafe":0.0,"safe":1.0}


def rows(*pairs):
    return [{"id":k,"law":v} for k,v in pairs]


def test_absolute_top_brain_needs_zero_target_identity_information():
    out=target_law_residual(
        {"success":1.0},
        rows(
            ("t50",{"failure":0.5,"success":0.5}),
            ("t90",{"failure":0.1,"success":0.9}),
            ("t100",{"success":1.0}),
        ),
        evaluators=[SUCCESS],
    )
    assert out["comparator_free_positive_certificate"] is True
    assert out["undominated_residual_ids"]==[]
    assert out["exact_target_identity_required"] is False


def test_only_undominated_target_candidates_form_information_residual():
    out=target_law_residual(
        {"failure":0.1,"success":0.9},
        rows(
            ("t50",{"failure":0.5,"success":0.5}),
            ("t90",{"failure":0.1,"success":0.9}),
            ("t100",{"success":1.0}),
        ),
        evaluators=[SUCCESS],
    )
    assert out["dominated_candidate_ids"]==["t50","t90"]
    assert out["undominated_residual_ids"]==["t100"]
    assert out["comparator_or_structural_target_information_required"] is True


def test_structural_exclusion_of_all_bad_candidates_is_enough_without_exact_identity():
    out=target_law_residual(
        {"failure":0.1,"success":0.9},
        rows(
            ("t50",{"failure":0.5,"success":0.5}),
            ("t90",{"failure":0.1,"success":0.9}),
            ("t100",{"success":1.0}),
        ),
        evaluators=[SUCCESS],
    )
    assert target_restriction_suffices(out["undominated_residual_ids"],excluded_target_ids=["t100"]) is True
    assert target_restriction_suffices(out["undominated_residual_ids"],excluded_target_ids=[]) is False


def test_two_world_countermodel_shows_target_information_is_load_bearing_when_residual_nonempty():
    out=finite_two_world_falsifier(
        {"failure":0.1,"success":0.9},
        rows(
            ("dominated",{"failure":0.2,"success":0.8}),
            ("undominated",{"success":1.0}),
        ),
        evaluators=[SUCCESS],
    )
    assert out["countermodel_exists"] is True
    assert out["same_brain_side_information"] is True
    assert out["terminal_true_world_target_id"]=="dominated"
    assert out["terminal_false_world_target_id"]=="undominated"


def test_better_success_does_not_delete_residual_if_hard_constraint_can_regress():
    out=target_law_residual(
        {"success":0.95,"safe":0.90},
        rows(("target",{"success":0.90,"safe":0.99})),
        evaluators=[{"success":1.0,"safe":0.0}],
        hard_constraints=[{"evaluator":SAFE,"threshold":0.95}],
    )
    assert out["undominated_residual_ids"]==["target"]


def test_top_element_certificate_is_relative_to_complete_declared_law_space():
    out=all_laws_top_element_certificate(
        {"success":1.0},
        rows(
            ("a",{"failure":0.4,"success":0.6}),
            ("b",{"failure":0.01,"success":0.99}),
            ("c",{"success":1.0}),
        ),
        evaluators=[SUCCESS],
    )
    assert out["brain_is_top_over_declared_admissible_law_space"] is True
    assert out["target_law_information_required_if_target_is_proved_inside_declared_space"] is False


def test_if_all_possible_targets_are_bad_positive_certificate_is_already_impossible():
    out=finite_two_world_falsifier(
        {"failure":0.4,"success":0.6},
        rows(
            ("t90",{"failure":0.1,"success":0.9}),
            ("t100",{"success":1.0}),
        ),
        evaluators=[SUCCESS],
    )
    assert out["countermodel_exists"] is False
    assert out["positive_certificate_impossible_on_current_uncertainty_set"] is True
