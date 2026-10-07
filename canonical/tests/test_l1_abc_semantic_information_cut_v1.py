from canonical.runtime.l1_abc_semantic_information_cut_verifier_v1 import (
    cell_information_route,
    global_abc_gate,
    verify,
)


def test_current_information_cut_verifies():
    out = verify()
    assert out["pass"], out
    assert out["representation_complete_does_not_close_abc"] is True
    assert out["global_coverage_route_count"] == 4
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0


def test_representation_scope_alone_never_closes_abc():
    assert global_abc_gate(
        representation_complete=True,
        coverage_route=None,
        all_cells_semantically_complete=True,
        all_cells_positive_adequacy=True,
        all_reached_transforms_local_c=True,
    ) is False


def test_unclassified_context_fails_closed():
    assert cell_information_route("X_UNCLASSIFIED") == "FAIL_CLOSED_UNCLASSIFIED"


def test_explicit_complete_evaluator_can_close_target_free():
    assert cell_information_route(
        "E_EXACT",
        complete_evaluator=True,
        positive_adequacy=True,
    ) == "TARGET_FREE_CERTIFIED"


def test_monotone_top_support_can_close_target_free():
    assert cell_information_route(
        "M_RESTRICTED",
        monotone_class_proved=True,
        top_support=True,
    ) == "TARGET_FREE_CERTIFIED"


def test_hidden_measure_separating_context_does_not_fake_target_free():
    assert cell_information_route("H_SEPARATING") == (
        "TARGET_LAW_OR_STRONGER_CERTIFICATE_REQUIRED"
    )


def test_stronger_scope_complete_certificate_can_bypass_cell_route():
    assert cell_information_route(
        "H_SEPARATING",
        stronger_certificate=True,
    ) == "STRONGER_SCOPE_COMPLETE_CERTIFICATE"
