from dataclasses import dataclass
from typing import AbstractSet

class CoverError(ValueError):
    pass

@dataclass(frozen=True)
class CoverVerdict:
    target_subset_superdomain: bool
    target_excluded_from_x: bool
    unresolved: tuple[str,...]
    target_in_dominated_region: bool
    certified: bool
    terminal_credit_delta: int = 0

def certify(*, target: AbstractSet[str], superdomain: AbstractSet[str], dominated: AbstractSet[str], excluded: AbstractSet[str]) -> CoverVerdict:
    U=set(map(str,target)); S=set(map(str,superdomain)); D=set(map(str,dominated)); X=set(map(str,excluded))
    if not U <= S:
        raise CoverError("TARGET_NOT_SUBSET_OF_SUPERDOMAIN")
    if not D <= S or not X <= S:
        raise CoverError("COVER_REGION_OUTSIDE_SUPERDOMAIN")
    target_excluded = not bool(U & X)
    unresolved = S - (D | X)
    target_in_d = U <= D
    return CoverVerdict(
        target_subset_superdomain=True,
        target_excluded_from_x=target_excluded,
        unresolved=tuple(sorted(unresolved)),
        target_in_dominated_region=target_in_d,
        certified=target_excluded and not unresolved and target_in_d,
    )

def exclusion_needed_for_fixed_d(*, superdomain: AbstractSet[str], dominated: AbstractSet[str]) -> set[str]:
    S=set(map(str,superdomain)); D=set(map(str,dominated))
    if not D <= S:
        raise CoverError("DOMINATED_NOT_SUBSET_OF_SUPERDOMAIN")
    return S-D

def cover_suffices_without_exact_target_identity(*, superdomain: AbstractSet[str], dominated: AbstractSet[str], excluded_from_target: AbstractSet[str]) -> bool:
    S=set(map(str,superdomain)); D=set(map(str,dominated)); X=set(map(str,excluded_from_target))
    if not D <= S or not X <= S:
        raise CoverError("REGION_OUTSIDE_SUPERDOMAIN")
    return S <= (D|X)
