from __future__ import annotations

from fractions import Fraction
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_V1"
_SHA = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
ALLOWED_PROOF_CLASSES = {
    "AUTHENTIC_CURRENT_OWNER_SEMANTICS",
    "EXTENSIONALLY_EQUIVALENT_CURRENT_PREFERENCE_RELATION",
    "INDEPENDENTLY_VERIFIED_RESTRICTED_OWNER_CLASS",
    "EVALUATOR_INDEPENDENT_SCOPE_COMPLETE_BOUND",
}
FORBIDDEN_PROOF_CLASSES = {
    "PUBLIC_METHODOLOGY_ONLY",
    "PUBLIC_RUBRIC_ONLY",
    "HISTORICAL_V1_PROMPT_CARRYFORWARD",
    "UNVERIFIED_RECONSTRUCTED_GRADER",
}


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "UNRESOLVED__FAIL_CLOSED",
        "reason": reason,
        "promotion_authority": False,
        "gdpval_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
    out.update(extra)
    return out


def _vec(raw: Any, n: int | None = None) -> tuple[Fraction, ...] | None:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        return None
    try:
        v = tuple(Fraction(x) for x in raw)
    except (ValueError, TypeError, ZeroDivisionError):
        return None
    if n is not None and len(v) != n:
        return None
    return v


def _dot(a: Sequence[Fraction], b: Sequence[Fraction]) -> Fraction:
    return sum((x * y for x, y in zip(a, b)), Fraction(0))


def _receipt_ok(raw: Any) -> bool:
    if not isinstance(raw, Mapping):
        return False
    return (
        raw.get("verified") is True
        and raw.get("independent") is True
        and isinstance(raw.get("source_path"), str)
        and bool(raw["source_path"].strip())
        and isinstance(raw.get("source_sha"), str)
        and _SHA.fullmatch(raw["source_sha"]) is not None
    )


def verify(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        return _fail("MANIFEST_INVALID")

    proof = manifest.get("decomposition_proof")
    if not isinstance(proof, Mapping):
        return _fail("DECOMPOSITION_PROOF_MISSING")
    if proof.get("sound_complete_outer_approximation") is not True:
        return _fail("DECOMPOSITION_NOT_PROVED_SOUND_COMPLETE")
    proof_class = proof.get("proof_class")
    if proof_class in FORBIDDEN_PROOF_CLASSES:
        return _fail("FORBIDDEN_SEMANTIC_PROOF_CLASS", proof_class=proof_class)
    if proof_class not in ALLOWED_PROOF_CLASSES:
        return _fail("UNRECOGNIZED_SEMANTIC_PROOF_CLASS", proof_class=proof_class)
    if not _receipt_ok(proof.get("receipt")):
        return _fail("DECOMPOSITION_RECEIPT_INVALID")

    d = _vec(manifest.get("difference_vector"))
    if d is None:
        return _fail("DIFFERENCE_VECTOR_INVALID")
    n = len(d)
    if sum(d, Fraction(0)) != 0:
        return _fail("DIFFERENCE_VECTOR_NOT_ZERO_MASS")

    u0 = _vec(manifest.get("nominal_owner_direction"), n)
    if u0 is None:
        return _fail("NOMINAL_OWNER_DIRECTION_INVALID")

    raw_k = manifest.get("known_cone_generators", [])
    raw_b = manifest.get("bounded_uncertainty_vertices", [])
    raw_l = manifest.get("lineality_basis", [])
    for label, raw in (("KNOWN_CONE", raw_k), ("BOUNDED_UNCERTAINTY", raw_b), ("LINEALITY", raw_l)):
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            return _fail(f"{label}_COLLECTION_INVALID")

    K: list[tuple[Fraction, ...]] = []
    for i, raw in enumerate(raw_k):
        v = _vec(raw, n)
        if v is None:
            return _fail("KNOWN_CONE_GENERATOR_INVALID", index=i)
        K.append(v)

    B: list[tuple[Fraction, ...]] = []
    for i, raw in enumerate(raw_b):
        v = _vec(raw, n)
        if v is None:
            return _fail("BOUNDED_UNCERTAINTY_VERTEX_INVALID", index=i)
        B.append(v)
    if not B:
        B = [tuple(Fraction(0) for _ in range(n))]

    L: list[tuple[Fraction, ...]] = []
    for i, raw in enumerate(raw_l):
        v = _vec(raw, n)
        if v is None:
            return _fail("LINEALITY_BASIS_VECTOR_INVALID", index=i)
        L.append(v)

    cone_dots = [_dot(d, k) for k in K]
    for i, value in enumerate(cone_dots):
        if value < 0:
            return _fail(
                "KNOWN_CONE_DUAL_MEMBERSHIP_FAIL",
                generator_index=i,
                dot=str(value),
            )

    lineality_dots = [_dot(d, ell) for ell in L]
    for i, value in enumerate(lineality_dots):
        if value != 0:
            return _fail(
                "NONORTHOGONAL_ARBITRARY_LINEALITY",
                basis_index=i,
                dot=str(value),
                next_action="REMOVE_OR_BOUND_THIS_OWNER_UNCERTAINTY_DIRECTION_OR_PROVE_THE_BRAIN_OPUS_DIFFERENCE_VANISHES_ON_IT",
            )

    nominal = _dot(d, u0)
    bounded_dots = [_dot(d, b) for b in B]
    worst_bounded = min(bounded_dots)
    robust_margin = nominal + worst_bounded

    if robust_margin < 0:
        j = bounded_dots.index(worst_bounded)
        return _fail(
            "ROBUST_MARGIN_NEGATIVE",
            nominal_margin=str(nominal),
            worst_bounded_adjustment=str(worst_bounded),
            robust_margin=str(robust_margin),
            worst_bounded_vertex_index=j,
            next_action="SHRINK_THE_DIRECTIONAL_BOUNDED_UNCERTAINTY_OR_INCREASE_A_CERTIFIED_OWNER_RELEVANT_BRAIN_MARGIN",
        )

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__CONDITIONAL_HYBRID_EVALUATOR_UNCERTAINTY_CERTIFICATE",
        "dimension": n,
        "known_cone_generator_count": len(K),
        "bounded_uncertainty_vertex_count": len(B),
        "lineality_basis_count": len(L),
        "nominal_margin": str(nominal),
        "worst_bounded_adjustment": str(worst_bounded),
        "robust_margin": str(robust_margin),
        "theorem": (
            "IF_THE_TRUE_OWNER_EVALUATOR_DIRECTION_IS_CONTAINED_IN_THE_INDEPENDENTLY_"
            "VERIFIED_OUTER_DECOMPOSITION_u0_PLUS_CONE_K_PLUS_CONV_B_PLUS_SPAN_L__"
            "AND_d_IS_IN_THE_DUAL_OF_K__ORTHOGONAL_TO_L__AND_THE_NOMINAL_PLUS_"
            "WORST_BOUNDED_MARGIN_IS_NONNEGATIVE__THEN_BRAIN_IS_EXPECTED_UTILITY_"
            "NONINFERIOR_TO_OPUS55_FOR_EVERY_EVALUATOR_IN_THAT_OUTER_CLASS"
        ),
        "semantic_decomposition_proved_by_runtime": False,
        "promotion_authority": False,
        "gdpval_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
