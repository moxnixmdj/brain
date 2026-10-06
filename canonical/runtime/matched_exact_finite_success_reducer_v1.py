from __future__ import annotations

from fractions import Fraction
from typing import Iterable, Mapping, Any

SCHEMA = "PROJECT_BRAIN_MATCHED_EXACT_FINITE_SUCCESS_REDUCER_V1"


class MatchedReducerError(ValueError):
    pass


def _normalize_cases(cases: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = list(cases)
    if not rows:
        raise MatchedReducerError("CASES_EMPTY")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise MatchedReducerError(f"CASE_{i}_NOT_OBJECT")
        cid = row.get("case_id")
        success = row.get("success")
        verified = row.get("verified")
        if not isinstance(cid, str) or not cid.strip():
            raise MatchedReducerError(f"CASE_{i}_ID_INVALID")
        cid = cid.strip()
        if cid in seen:
            raise MatchedReducerError("CASE_ID_DUPLICATE:" + cid)
        seen.add(cid)
        if not isinstance(success, bool):
            raise MatchedReducerError(f"CASE_{i}_SUCCESS_NOT_BOOL")
        if verified is not True:
            raise MatchedReducerError(f"CASE_{i}_NOT_VERIFIED")
        out.append({"case_id": cid, "success": success, "verified": True})
    out.sort(key=lambda x: x["case_id"])
    return out


def reduce_exact(cases: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = _normalize_cases(cases)
    n = len(rows)
    k = sum(1 for row in rows if row["success"])
    value = Fraction(k, n)
    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_FINITE_SCOPE_SUCCESS_FRACTION",
        "case_count": n,
        "success_count": k,
        "success_fraction_numerator": value.numerator,
        "success_fraction_denominator": value.denominator,
        "success_fraction": k / n,
        "successful_case_ids": [r["case_id"] for r in rows if r["success"]],
        "failed_case_ids": [r["case_id"] for r in rows if not r["success"]],
        "terminal_credit_delta": 0,
        "acceptance_credit_delta": 0,
    }


def compare(brain_cases: Iterable[Mapping[str, Any]],
            comparator_cases: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    brain = _normalize_cases(brain_cases)
    comp = _normalize_cases(comparator_cases)
    brain_ids = [x["case_id"] for x in brain]
    comp_ids = [x["case_id"] for x in comp]
    if brain_ids != comp_ids:
        raise MatchedReducerError("CASE_UNIVERSE_MISMATCH")
    bmap = {x["case_id"]: x["success"] for x in brain}
    cmap = {x["case_id"]: x["success"] for x in comp}
    forbidden = sorted(cid for cid in brain_ids if cmap[cid] and not bmap[cid])
    b = reduce_exact(brain)
    c = reduce_exact(comp)
    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_FINITE_SCOPE_COMPARISON",
        "case_count": len(brain_ids),
        "brain_success_count": b["success_count"],
        "comparator_success_count": c["success_count"],
        "brain_success_fraction": b["success_fraction"],
        "comparator_success_fraction": c["success_fraction"],
        "comparator_success_set_subset_of_brain": not forbidden,
        "forbidden_comparator_success_brain_failure_case_ids": forbidden,
        "noninferior_on_declared_finite_scope":
            b["success_count"] >= c["success_count"],
        "pointwise_differential_dominance":
            not forbidden,
        "terminal_credit_delta": 0,
        "acceptance_credit_delta": 0,
    }


def monotonicity_witness(n: int, k0: int, k1: int) -> dict[str, Any]:
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise MatchedReducerError("N_INVALID")
    for label, k in (("K0", k0), ("K1", k1)):
        if isinstance(k, bool) or not isinstance(k, int) or not 0 <= k <= n:
            raise MatchedReducerError(label + "_INVALID")
    if k1 < k0:
        raise MatchedReducerError("K1_LT_K0")
    a = Fraction(k0, n)
    b = Fraction(k1, n)
    return {
        "schema": SCHEMA,
        "status": "PASS__MONOTONE",
        "n": n,
        "k0": k0,
        "k1": k1,
        "r0_numerator": a.numerator,
        "r0_denominator": a.denominator,
        "r1_numerator": b.numerator,
        "r1_denominator": b.denominator,
        "r1_ge_r0": b >= a,
        "terminal_credit_delta": 0,
    }
