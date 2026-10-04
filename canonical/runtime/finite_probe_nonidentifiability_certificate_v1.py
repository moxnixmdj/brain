"""Exact finite-probe non-identifiability certificate.

For any finite set of distinct or repeated d-dimensional rational probe points,
construct two total polynomial laws that agree at every observed probe and differ
at a rational witness outside the probe set.

This establishes a narrow impossibility result: finite observations alone cannot
universally identify an unrestricted mathematical function. It does NOT say a
restricted published mechanism class is unlearnable, and it grants no benchmark
or terminal credit.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Iterable, Sequence

SCHEMA = "PROJECT_BRAIN_FINITE_PROBE_NONIDENTIFIABILITY_CERTIFICATE_V1"


def _point(raw: Sequence[object]) -> tuple[Fraction, ...]:
    if isinstance(raw, (str, bytes)) or not raw:
        raise ValueError("POINT_INVALID")
    return tuple(Fraction(str(x)) for x in raw)


def _sqdist(a: tuple[Fraction, ...], b: tuple[Fraction, ...]) -> Fraction:
    if len(a) != len(b):
        raise ValueError("DIMENSION_MISMATCH")
    return sum((x-y)*(x-y) for x,y in zip(a,b))


def adversary_value(x: Sequence[object], probes: Iterable[Sequence[object]]) -> Fraction:
    xp = _point(x)
    ps = [_point(p) for p in probes]
    if not ps or any(len(p) != len(xp) for p in ps):
        raise ValueError("PROBES_INVALID")
    out = Fraction(1,1)
    for p in ps:
        out *= _sqdist(xp,p)
    return out


def witness_outside(probes: Iterable[Sequence[object]]) -> tuple[Fraction, ...]:
    ps = [_point(p) for p in probes]
    if not ps:
        raise ValueError("PROBES_REQUIRED")
    d = len(ps[0])
    if d < 1 or any(len(p) != d for p in ps):
        raise ValueError("PROBE_DIMENSION_INVALID")
    used = set(ps)
    # Deterministic integer diagonal search. A finite set cannot cover it.
    k = 0
    while True:
        w = tuple(Fraction(k+i+1,1) for i in range(d))
        if w not in used:
            return w
        k += d + 1


def prove(probes: Iterable[Sequence[object]]) -> dict:
    ps = [_point(p) for p in probes]
    if not ps:
        raise ValueError("PROBES_REQUIRED")
    d = len(ps[0])
    if any(len(p) != d for p in ps):
        raise ValueError("PROBE_DIMENSION_INVALID")
    w = witness_outside(ps)

    # f0(x)=0. f1(x)=product_i ||x-p_i||^2.
    # Every observed p_k zeros its own factor. At w, every squared distance is
    # strictly positive because w differs from every p_i.
    observed_f1 = [adversary_value(p, ps) for p in ps]
    witness_f1 = adversary_value(w, ps)
    assert all(v == 0 for v in observed_f1)
    assert witness_f1 > 0

    return {
        "schema": SCHEMA,
        "status": "PASS__FINITE_PROBES_CANNOT_UNIVERSALLY_IDENTIFY_UNRESTRICTED_FUNCTION_CLASS",
        "dimension": d,
        "probe_count": len(ps),
        "witness": [str(x) for x in w],
        "f0_on_all_probes": "0",
        "f1_on_all_probes": ["0" for _ in ps],
        "f0_at_witness": "0",
        "f1_at_witness": str(witness_f1),
        "construction": "F1_EQUALS_PRODUCT_OVER_PROBES_OF_SUM_OF_SQUARED_COORDINATE_DISTANCES",
        "deduction": (
            "ANY_TRANSCRIPT_CONTAINING_ONLY_THESE_FINITE_INPUT_OUTPUT_PROBES_IS_"
            "COMPATIBLE_WITH_AT_LEAST_TWO_TOTAL_POLYNOMIAL_LAWS_THAT_DISAGREE_ELSEWHERE"
        ),
        "hard_nonclaims": [
            "DOES_NOT_PROVE_A_PUBLISHED_RESTRICTED_MECHANISM_CLASS_UNLEARNABLE",
            "DOES_NOT_INFER_ANY_MYSTERYMECHANISM_PRIVATE_TASK_IDENTITY",
            "DOES_NOT_CLAIM_ANY_PRIVATE_BENCHMARK_SCORE",
            "ZERO_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_CREDIT",
        ],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(prove([(0,0),(1,1),(2,3),(5,8),(13,21)]), indent=2, sort_keys=True))
