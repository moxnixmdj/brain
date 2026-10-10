from __future__ import annotations

from dataclasses import dataclass
from typing import AbstractSet, Iterable


class EscapeReductionError(ValueError):
    pass


@dataclass(frozen=True)
class EscapeCertificate:
    target_subset_of_superdomain: bool
    undominated_escape_region: tuple[str, ...]
    target_escape_intersection: tuple[str, ...]
    target_dominance_certified: bool
    exact_target_membership_required: bool
    terminal_credit_delta: int = 0


def certify_undominated_escape_reduction(
    *,
    target: AbstractSet[str],
    superdomain: AbstractSet[str],
    brain_dominated: AbstractSet[str],
) -> EscapeCertificate:
    T=set(map(str,target))
    S=set(map(str,superdomain))
    D=set(map(str,brain_dominated))
    if not T <= S:
        raise EscapeReductionError("TARGET_NOT_SUBSET_OF_SUPERDOMAIN")
    if not D <= S:
        raise EscapeReductionError("BRAIN_DOMINATED_REGION_NOT_SUBSET_OF_SUPERDOMAIN")
    escape=S-D
    intersection=T & escape
    return EscapeCertificate(
        target_subset_of_superdomain=True,
        undominated_escape_region=tuple(sorted(escape)),
        target_escape_intersection=tuple(sorted(intersection)),
        target_dominance_certified=not intersection,
        exact_target_membership_required=False,
    )


def exclusion_certificate_suffices(
    *,
    superdomain: AbstractSet[str],
    brain_dominated: AbstractSet[str],
    excluded_from_target: AbstractSet[str],
) -> bool:
    S=set(map(str,superdomain))
    D=set(map(str,brain_dominated))
    E=set(map(str,excluded_from_target))
    if not D <= S:
        raise EscapeReductionError("BRAIN_DOMINATED_REGION_NOT_SUBSET_OF_SUPERDOMAIN")
    return (S-D) <= E


def residual_search_order(
    *,
    superdomain: AbstractSet[str],
    brain_dominated: AbstractSet[str],
    search_cost: dict[str,float] | None=None,
) -> tuple[str,...]:
    S=set(map(str,superdomain))
    D=set(map(str,brain_dominated))
    if not D <= S:
        raise EscapeReductionError("BRAIN_DOMINATED_REGION_NOT_SUBSET_OF_SUPERDOMAIN")
    escape=S-D
    costs=search_cost or {}
    return tuple(sorted(escape,key=lambda x:(float(costs.get(x,1.0)),x)))


def finite_counterexample_to_full_superdomain_dominance_necessity() -> dict:
    # Target uses only a. Superdomain also contains b. Brain dominates a but not b.
    # Full-S dominance fails, but target-relative dominance is still true because b
    # is soundly excluded from the target.
    cert=certify_undominated_escape_reduction(
        target={"a"},
        superdomain={"a","b"},
        brain_dominated={"a"},
    )
    exclusion=exclusion_certificate_suffices(
        superdomain={"a","b"},
        brain_dominated={"a"},
        excluded_from_target={"b"},
    )
    return {
        "target_relative_dominance_true":cert.target_dominance_certified,
        "full_superdomain_dominance_false":False,
        "escape_region":list(cert.undominated_escape_region),
        "target_escape_intersection":list(cert.target_escape_intersection),
        "escape_exclusion_suffices":exclusion,
        "exact_target_membership_required":cert.exact_target_membership_required,
        "terminal_credit_delta":0,
    }
