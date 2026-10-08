from __future__ import annotations

from fractions import Fraction
import hashlib
import itertools
import json
import math
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_EXACT_LINEAR_PARAMETER_POLYTOPE_V1"
MAX_FEATURE_DIMENSION = 4
MAX_OBSERVATIONS = 16
MAX_ACTIVE_SETS = 100_000


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _fraction(value: Any, label: str) -> Fraction:
    """
    Parse only exact JSON-compatible rational encodings.

    Floats are deliberately rejected. A proof path must preserve the exact
    decimal/rational text supplied by the observation adapter instead of
    silently replacing it with an already-rounded binary float.
    """
    if isinstance(value, bool):
        raise ValueError(label + "_BOOL_INVALID")
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str) and value.strip():
        try:
            return Fraction(value.strip())
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(label + "_RATIONAL_INVALID") from exc
    raise ValueError(label + "_EXACT_RATIONAL_STRING_OR_INT_REQUIRED")


def _fstr(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _dot(left: Sequence[Fraction], right: Sequence[Fraction]) -> Fraction:
    return sum((a * b for a, b in zip(left, right)), Fraction(0, 1))


def _rank(rows: Sequence[Sequence[Fraction]]) -> int:
    if not rows:
        return 0
    matrix = [list(row) for row in rows]
    row_count = len(matrix)
    col_count = len(matrix[0])
    rank = 0
    for col in range(col_count):
        pivot = next((r for r in range(rank, row_count) if matrix[r][col] != 0), None)
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        p = matrix[rank][col]
        matrix[rank] = [x / p for x in matrix[rank]]
        for r in range(row_count):
            if r == rank:
                continue
            factor = matrix[r][col]
            if factor == 0:
                continue
            matrix[r] = [
                matrix[r][c] - factor * matrix[rank][c]
                for c in range(col_count)
            ]
        rank += 1
        if rank == row_count:
            break
    return rank


def _solve_square(
    matrix: Sequence[Sequence[Fraction]],
    rhs: Sequence[Fraction],
) -> tuple[Fraction, ...] | None:
    n = len(matrix)
    if n == 0 or len(rhs) != n or any(len(row) != n for row in matrix):
        return None
    aug = [list(row) + [rhs_i] for row, rhs_i in zip(matrix, rhs)]

    for col in range(n):
        pivot = next((r for r in range(col, n) if aug[r][col] != 0), None)
        if pivot is None:
            return None
        aug[col], aug[pivot] = aug[pivot], aug[col]
        p = aug[col][col]
        aug[col] = [x / p for x in aug[col]]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor == 0:
                continue
            aug[r] = [
                aug[r][c] - factor * aug[col][c]
                for c in range(n + 1)
            ]

    return tuple(aug[i][n] for i in range(n))


def _exact_vector(raw: Any, dimension: int | None, label: str) -> tuple[Fraction, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError(label + "_VECTOR_REQUIRED")
    if dimension is not None and len(raw) != dimension:
        raise ValueError(label + "_DIMENSION_MISMATCH")
    if not raw:
        raise ValueError(label + "_EMPTY")
    return tuple(_fraction(value, f"{label}_{i}") for i, value in enumerate(raw))


def solve(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    Exact set-membership inference for models linear in unknown coefficients.

    Observation contract:
        lower_i <= phi_i dot beta <= upper_i

    If the feature matrix has full column rank, the feasible coefficient set is
    bounded. The kernel enumerates every vertex by intersecting p active
    half-space boundaries, checks exact feasibility using Fraction arithmetic,
    and computes exact extrema of each requested linear prediction over the
    resulting bounded polytope.

    This proves only the coefficient-space statement for the supplied exact
    feature rows and observation intervals. It does not prove feature semantics,
    observation-noise coverage, candidate-family completeness, or any benchmark
    result.
    """
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_REQUIRED")
    if payload.get("feature_semantics_bound") is not True:
        return _fail("FEATURE_SEMANTICS_UNBOUND")
    if payload.get("observation_intervals_sound") is not True:
        return _fail("OBSERVATION_INTERVAL_SOUNDNESS_UNPROVED")

    observations_raw = payload.get("observations")
    if (
        not isinstance(observations_raw, Sequence)
        or isinstance(observations_raw, (str, bytes))
        or not observations_raw
        or len(observations_raw) > MAX_OBSERVATIONS
    ):
        return _fail("OBSERVATIONS_INVALID_OR_TOO_MANY")

    feature_rows: list[tuple[Fraction, ...]] = []
    output_intervals: list[tuple[Fraction, Fraction]] = []
    dimension: int | None = None

    try:
        for index, row in enumerate(observations_raw):
            if not isinstance(row, Mapping):
                return _fail(f"OBSERVATION_NOT_OBJECT:{index}")
            features = _exact_vector(
                row.get("features"),
                dimension,
                f"OBSERVATION_{index}_FEATURES",
            )
            if dimension is None:
                dimension = len(features)
                if dimension < 1 or dimension > MAX_FEATURE_DIMENSION:
                    return _fail("FEATURE_DIMENSION_OUT_OF_RANGE")
            raw_interval = row.get("output_interval")
            if (
                not isinstance(raw_interval, Sequence)
                or isinstance(raw_interval, (str, bytes))
                or len(raw_interval) != 2
            ):
                return _fail(f"OBSERVATION_OUTPUT_INTERVAL_INVALID:{index}")
            lo = _fraction(raw_interval[0], f"OBSERVATION_{index}_OUTPUT_LO")
            hi = _fraction(raw_interval[1], f"OBSERVATION_{index}_OUTPUT_HI")
            if lo > hi:
                return _fail(f"OBSERVATION_OUTPUT_INTERVAL_ORDER_INVALID:{index}")
            feature_rows.append(features)
            output_intervals.append((lo, hi))
    except ValueError as exc:
        return _fail("EXACT_INPUT_BINDING_FAILED", detail=str(exc))

    assert dimension is not None
    rank = _rank(feature_rows)
    if rank != dimension:
        return _fail(
            "FEATURE_MATRIX_NOT_FULL_COLUMN_RANK__COEFFICIENT_SET_MAY_BE_UNBOUNDED",
            feature_dimension=dimension,
            exact_rank=rank,
        )

    inequalities: list[tuple[tuple[Fraction, ...], Fraction]] = []
    for features, (lo, hi) in zip(feature_rows, output_intervals):
        inequalities.append((features, hi))
        inequalities.append((tuple(-x for x in features), -lo))

    active_set_count = math.comb(len(inequalities), dimension)
    if active_set_count > MAX_ACTIVE_SETS:
        return _fail(
            "ACTIVE_SET_ENUMERATION_BUDGET_EXCEEDED",
            active_set_count=active_set_count,
            max_active_sets=MAX_ACTIVE_SETS,
        )

    vertices: set[tuple[Fraction, ...]] = set()
    for indices in itertools.combinations(range(len(inequalities)), dimension):
        matrix = [inequalities[i][0] for i in indices]
        rhs = [inequalities[i][1] for i in indices]
        candidate = _solve_square(matrix, rhs)
        if candidate is None:
            continue
        if all(_dot(a, candidate) <= b for a, b in inequalities):
            vertices.add(candidate)

    if not vertices:
        return _fail(
            "NO_FEASIBLE_BOUNDED_PARAMETER_POLYTOPE_VERTEX",
            feature_dimension=dimension,
            exact_rank=rank,
            active_sets_checked=active_set_count,
        )

    ordered_vertices = sorted(vertices)
    coefficient_bounds = []
    for j in range(dimension):
        column = [vertex[j] for vertex in ordered_vertices]
        coefficient_bounds.append([_fstr(min(column)), _fstr(max(column))])

    canonical_vertices = [
        [_fstr(value) for value in vertex]
        for vertex in ordered_vertices
    ]
    vertex_set_sha256 = hashlib.sha256(
        json.dumps(
            canonical_vertices,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    queries_raw = payload.get("queries", [])
    if not isinstance(queries_raw, Sequence) or isinstance(queries_raw, (str, bytes)):
        return _fail("QUERIES_INVALID")
    predictions: list[dict[str, Any]] = []
    seen_query_ids: set[str] = set()
    try:
        for index, raw in enumerate(queries_raw):
            if not isinstance(raw, Mapping):
                return _fail(f"QUERY_NOT_OBJECT:{index}")
            query_id = raw.get("query_id")
            if (
                not isinstance(query_id, str)
                or not query_id
                or query_id in seen_query_ids
            ):
                return _fail(f"QUERY_ID_INVALID_OR_DUPLICATE:{index}")
            seen_query_ids.add(query_id)
            features = _exact_vector(
                raw.get("features"),
                dimension,
                f"QUERY_{query_id}_FEATURES",
            )
            values = [_dot(features, vertex) for vertex in ordered_vertices]
            predictions.append(
                {
                    "query_id": query_id,
                    "prediction_interval": [_fstr(min(values)), _fstr(max(values))],
                }
            )
    except ValueError as exc:
        return _fail("QUERY_EXACT_INPUT_BINDING_FAILED", detail=str(exc))

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__EXACT_BOUNDED_LINEAR_PARAMETER_POLYTOPE",
        "feature_dimension": dimension,
        "observation_count": len(feature_rows),
        "exact_feature_rank": rank,
        "inequality_count": len(inequalities),
        "active_sets_checked": active_set_count,
        "vertex_count": len(ordered_vertices),
        "vertex_set_sha256": vertex_set_sha256,
        "coefficient_bounds": coefficient_bounds,
        "query_predictions": predictions,
        "exact_arithmetic": "fractions.Fraction",
        "boundedness_rule": "FULL_COLUMN_RANK_OF_FEATURE_MATRIX",
        "extremum_rule": "LINEAR_OBJECTIVE_EXTREMA_OVER_NONEMPTY_BOUNDED_POLYTOPE_OCCUR_AT_VERTICES",
        "hard_boundary": (
            "PROVES_ONLY_THE_SUPPLIED_LINEAR_IN_COEFFICIENT_FEATURE_MODEL;"
            "CALLER_MUST_PROVE_FEATURE_SEMANTICS_OBSERVATION_INTERVAL_SOUNDNESS_"
            "AND_CANDIDATE_FAMILY_COVERAGE"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
