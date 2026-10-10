from __future__ import annotations

from fractions import Fraction
from typing import Mapping, Sequence


class KernelError(ValueError):
    pass


def normalize_kernel(
    kernel: Mapping[str, Mapping[str, Fraction | int | float]],
    *,
    source_states: Sequence[str],
    target_states: Sequence[str],
) -> dict[str, dict[str, Fraction]]:
    X=tuple(map(str,source_states)); Y=tuple(map(str,target_states))
    if not X or not Y or len(set(X))!=len(X) or len(set(Y))!=len(Y):
        raise KernelError("STATE_DOMAIN_INVALID")
    out={}
    for x in X:
        row=kernel.get(x)
        if not isinstance(row,Mapping):
            raise KernelError("SOURCE_ROW_MISSING:"+x)
        nrow={y:Fraction(row.get(y,0)) for y in Y}
        if any(v<0 for v in nrow.values()):
            raise KernelError("NEGATIVE_PROBABILITY:"+x)
        if sum(nrow.values(),Fraction(0))!=1:
            raise KernelError("ROW_NOT_STOCHASTIC:"+x)
        out[x]=nrow
    return out


def deterministic_kernel(
    mapping: Mapping[str,str],
    *,
    source_states: Sequence[str],
    target_states: Sequence[str],
) -> dict[str,dict[str,Fraction]]:
    Y=set(map(str,target_states))
    raw={}
    for x in map(str,source_states):
        if x not in mapping or str(mapping[x]) not in Y:
            raise KernelError("DETERMINISTIC_MAPPING_INVALID:"+x)
        y0=str(mapping[x])
        raw[x]={y:Fraction(int(y==y0),1) for y in Y}
    return normalize_kernel(raw,source_states=source_states,target_states=target_states)


def compose_kernels(
    k1: Mapping[str,Mapping[str,Fraction|int|float]],
    k2: Mapping[str,Mapping[str,Fraction|int|float]],
    *,
    source_states: Sequence[str],
    middle_states: Sequence[str],
    target_states: Sequence[str],
) -> dict[str,dict[str,Fraction]]:
    A=normalize_kernel(k1,source_states=source_states,target_states=middle_states)
    B=normalize_kernel(k2,source_states=middle_states,target_states=target_states)
    Z=tuple(map(str,target_states))
    M=tuple(map(str,middle_states))
    out={}
    for x in map(str,source_states):
        out[x]={z:sum((A[x][m]*B[m][z] for m in M),Fraction(0)) for z in Z}
    return normalize_kernel(out,source_states=source_states,target_states=target_states)


def pullback(
    kernel: Mapping[str,Mapping[str,Fraction|int|float]],
    evaluator: Mapping[str,Fraction|int|float],
    *,
    source_states: Sequence[str],
    target_states: Sequence[str],
) -> dict[str,Fraction]:
    K=normalize_kernel(kernel,source_states=source_states,target_states=target_states)
    Y=tuple(map(str,target_states))
    g={y:Fraction(evaluator[y]) for y in Y}
    return {
        x:sum((K[x][y]*g[y] for y in Y),Fraction(0))
        for x in map(str,source_states)
    }


def finite_transform_representation_certificate(
    *,
    complete_source_state_bound: bool,
    complete_target_state_bound: bool,
    randomized_transform_distribution_bound: bool,
) -> dict:
    ok=bool(
        complete_source_state_bound
        and complete_target_state_bound
        and randomized_transform_distribution_bound
    )
    return {
        "status":"PASS__TRANSFORM_REPRESENTABLE_AS_STOCHASTIC_KERNEL" if ok else "FAIL_CLOSED",
        "pass":ok,
        "primitive_transform_taxonomy_required":False if ok else None,
        "required_remaining":[
            "CONTENT_ADDRESS_ACTUAL_LOAD_BEARING_TRANSFORM_KERNEL_OR_IMPLEMENTATION",
            "BIND_COMPLETE_SOURCE_STATE_INCLUDING_LOAD_BEARING_CONTEXT_HISTORY_AND_ROUTING_INPUTS",
            "BIND_TARGET_EVALUATOR_PULLBACKS",
            "BIND_HARD_CONSTRAINT_PREIMAGES_OR_FAIL_CLOSED_INVARIANTS",
        ] if ok else [],
        "terminal_credit_delta":0,
    }
