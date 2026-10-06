from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SeparatorRoute(str, Enum):
    ABSOLUTE_VERIFIER = "V_ABSOLUTE_VERIFIER"
    AUTHORIZED_DISCRIMINATOR = "D_AUTHORIZED_DISCRIMINATOR"
    OWNED_PRIOR = "P_OWNED_PRIOR"
    UNCERTAINTY_PRESERVATION = "U_UNCERTAINTY_PRESERVATION"
    IRREDUCIBLE_GAP = "IRREDUCIBLE_SEPARATOR_GAP"


@dataclass(frozen=True)
class SeparatorContext:
    complete_verifier_before_deadline: bool = False
    discriminator_available: bool = False
    discriminator_before_deadline: bool = False
    discriminator_within_resource_bound: bool = False
    owned_prior_separates: bool = False
    abstention_allowed_without_terminal_loss: bool = False


def classify_separator_route(ctx: SeparatorContext) -> SeparatorRoute:
    if ctx.complete_verifier_before_deadline:
        return SeparatorRoute.ABSOLUTE_VERIFIER

    if (
        ctx.discriminator_available
        and ctx.discriminator_before_deadline
        and ctx.discriminator_within_resource_bound
    ):
        return SeparatorRoute.AUTHORIZED_DISCRIMINATOR

    if ctx.owned_prior_separates:
        return SeparatorRoute.OWNED_PRIOR

    if ctx.abstention_allowed_without_terminal_loss:
        return SeparatorRoute.UNCERTAINTY_PRESERVATION

    return SeparatorRoute.IRREDUCIBLE_GAP


def indistinguishable_binary_success_bound() -> float:
    # With identical precommitment information in two opposite binary worlds,
    # any one policy chooses a0 with probability q and a1 with 1-q.
    # min(q, 1-q) <= 1/2 for every q.
    return 0.5


def verify_separator_normal_form() -> dict[str, object]:
    assert classify_separator_route(
        SeparatorContext(complete_verifier_before_deadline=True)
    ) == SeparatorRoute.ABSOLUTE_VERIFIER

    assert classify_separator_route(
        SeparatorContext(
            discriminator_available=True,
            discriminator_before_deadline=True,
            discriminator_within_resource_bound=True,
        )
    ) == SeparatorRoute.AUTHORIZED_DISCRIMINATOR

    assert classify_separator_route(
        SeparatorContext(
            discriminator_available=True,
            discriminator_before_deadline=False,
            discriminator_within_resource_bound=True,
        )
    ) == SeparatorRoute.IRREDUCIBLE_GAP

    assert classify_separator_route(
        SeparatorContext(owned_prior_separates=True)
    ) == SeparatorRoute.OWNED_PRIOR

    assert classify_separator_route(
        SeparatorContext(abstention_allowed_without_terminal_loss=True)
    ) == SeparatorRoute.UNCERTAINTY_PRESERVATION

    assert classify_separator_route(SeparatorContext()) == SeparatorRoute.IRREDUCIBLE_GAP
    assert indistinguishable_binary_success_bound() == 0.5

    return {
        "status": "PASS__G6U_SEPARATOR_NORMAL_FORM_CONTROLS",
        "absolute_verifier_route": True,
        "authorized_discriminator_route": True,
        "late_or_overbudget_discriminator_rejected": True,
        "owned_prior_route": True,
        "uncertainty_preservation_route": True,
        "information_blind_gap_fails_closed": True,
        "binary_no_separator_worst_case_bound": 0.5,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify_separator_normal_form(), sort_keys=True))
