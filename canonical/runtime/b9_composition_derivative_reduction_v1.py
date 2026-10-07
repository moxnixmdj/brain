from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


class B9ReductionError(ValueError):
    pass


@dataclass(frozen=True)
class B9Reduction:
    primitive_roles: tuple[str, ...]
    all_primitive_roles_dominated: bool
    composition_closure_bound: bool
    b9_independent_escape: bool
    b9_dominance_implied: bool
    terminal_credit_delta: int = 0


def reduce_b9(
    primitive_role_dominance: Mapping[str, bool],
    *,
    composition_closure_bound: bool,
) -> B9Reduction:
    if not isinstance(primitive_role_dominance, Mapping) or len(primitive_role_dominance) < 2:
        raise B9ReductionError("AT_LEAST_TWO_PRIMITIVE_ROLES_REQUIRED")
    roles=tuple(sorted(str(k) for k in primitive_role_dominance))
    if len(set(roles)) != len(roles):
        raise B9ReductionError("ROLE_ID_DUPLICATE")
    all_dom=all(primitive_role_dominance[r] is True for r in roles)
    closure=composition_closure_bound is True
    implied=all_dom and closure
    return B9Reduction(
        primitive_roles=roles,
        all_primitive_roles_dominated=all_dom,
        composition_closure_bound=closure,
        b9_independent_escape=False if closure else True,
        b9_dominance_implied=implied,
    )


def localize_b9_failure(
    primitive_role_dominance: Mapping[str,bool],
    *,
    composition_closure_bound: bool,
) -> dict:
    out=reduce_b9(
        primitive_role_dominance,
        composition_closure_bound=composition_closure_bound,
    )
    primitive_failures=sorted(
        str(k) for k,v in primitive_role_dominance.items() if v is not True
    )
    if out.b9_dominance_implied:
        cause="NO_B9_FAILURE_POSSIBLE_UNDER_BOUND_PREMISES"
    elif primitive_failures:
        cause="PRIMITIVE_ROLE_DOMINANCE_OPEN_OR_FALSE"
    else:
        cause="COMPOSITION_CLOSURE_OPEN_OR_FALSE"
    return {
        "primitive_failures":primitive_failures,
        "composition_closure_bound":out.composition_closure_bound,
        "b9_independent_escape":out.b9_independent_escape,
        "b9_dominance_implied":out.b9_dominance_implied,
        "localized_cause":cause,
        "terminal_credit_delta":0,
    }


def five_role_escape_projection(
    escape_roles: Sequence[str],
    *,
    composition_closure_bound: bool,
) -> tuple[str,...]:
    roles=set(map(str,escape_roles))
    if "B9_MULTI_ROLE_COMPOSITION" in roles and composition_closure_bound:
        roles.remove("B9_MULTI_ROLE_COMPOSITION")
    return tuple(sorted(roles))
