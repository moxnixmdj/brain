from canonical.runtime.g6u_minimum_separator_kernel_v1 import (
    SeparatorContext,
    SeparatorRoute,
    classify_separator_route,
    indistinguishable_binary_success_bound,
    verify_separator_normal_form,
)


def test_complete_verifier_is_sufficient_separator_route():
    assert classify_separator_route(
        SeparatorContext(complete_verifier_before_deadline=True)
    ) == SeparatorRoute.ABSOLUTE_VERIFIER


def test_discriminator_requires_availability_deadline_and_resource():
    good = SeparatorContext(
        discriminator_available=True,
        discriminator_before_deadline=True,
        discriminator_within_resource_bound=True,
    )
    assert classify_separator_route(good) == SeparatorRoute.AUTHORIZED_DISCRIMINATOR

    for broken in (
        SeparatorContext(
            discriminator_available=False,
            discriminator_before_deadline=True,
            discriminator_within_resource_bound=True,
        ),
        SeparatorContext(
            discriminator_available=True,
            discriminator_before_deadline=False,
            discriminator_within_resource_bound=True,
        ),
        SeparatorContext(
            discriminator_available=True,
            discriminator_before_deadline=True,
            discriminator_within_resource_bound=False,
        ),
    ):
        assert classify_separator_route(broken) == SeparatorRoute.IRREDUCIBLE_GAP


def test_owned_prior_is_separator_route():
    assert classify_separator_route(
        SeparatorContext(owned_prior_separates=True)
    ) == SeparatorRoute.OWNED_PRIOR


def test_uncertainty_preservation_only_when_terminally_free():
    assert classify_separator_route(
        SeparatorContext(abstention_allowed_without_terminal_loss=True)
    ) == SeparatorRoute.UNCERTAINTY_PRESERVATION
    assert classify_separator_route(SeparatorContext()) == SeparatorRoute.IRREDUCIBLE_GAP


def test_information_blind_binary_cut_is_half():
    assert indistinguishable_binary_success_bound() == 0.5


def test_compiled_normal_form_controls():
    out = verify_separator_normal_form()
    assert out["status"] == "PASS__G6U_SEPARATOR_NORMAL_FORM_CONTROLS"
    assert out["terminal_credit_delta"] == 0
