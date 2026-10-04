"""Deterministic zero-learned-byte expression-tree symbolic regression for H100 Gate 1.

This module expands the existing bounded numeric mechanism synthesizer with a
small, explicit expression grammar and deterministic beam enumeration. It is
intended to discover nested saturation/correction mechanisms from structured
numeric observations without neural weights, external model calls, dynamic code
execution, random search, or hidden state.

It is a candidate generator only. Exact synthetic recovery does not imply
MysteryMechanism, unknown-domain, family, ownership, or H100 terminal credit.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_H100_EXPRESSION_TREE_SYMBOLIC_REGRESSION_V1"
_EPS = 1e-12
_UNARY = ("neg", "abs", "square", "sqrt_abs", "log1p_abs", "sat")
_BINARY = ("add", "sub", "mul", "stable_div")
_COMMUTATIVE = {"add", "mul"}


class ExpressionTreeError(ValueError):
    pass


def _finite(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ExpressionTreeError(field.upper() + "_INVALID")
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise ExpressionTreeError(field.upper() + "_INVALID") from exc
    if not math.isfinite(x):
        raise ExpressionTreeError(field.upper() + "_NONFINITE")
    return x


def _normalize_rows(rows: Sequence[Mapping[str, Any]], target: str, inputs: Sequence[str] | None):
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or len(rows) < 8:
        raise ExpressionTreeError("AT_LEAST_EIGHT_ROWS_REQUIRED")
    target = str(target or "").strip()
    if not target:
        raise ExpressionTreeError("TARGET_REQUIRED")
    first = rows[0]
    if not isinstance(first, Mapping) or target not in first:
        raise ExpressionTreeError("TARGET_MISSING")
    if inputs is None:
        names = sorted(str(k) for k in first.keys() if str(k) != target)
    else:
        names = [str(x).strip() for x in inputs if str(x).strip()]
    if not names or len(names) != len(set(names)) or target in names or len(names) > 4:
        raise ExpressionTreeError("INPUTS_INVALID_OR_TOO_MANY")
    out = []
    expected = set(names + [target])
    for i, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise ExpressionTreeError(f"ROW_NOT_MAPPING:{i}")
        if not expected.issubset(set(str(k) for k in raw.keys())):
            raise ExpressionTreeError(f"ROW_SCHEMA_MISMATCH:{i}")
        row = {name: _finite(raw[name], name) for name in names}
        row[target] = _finite(raw[target], target)
        out.append(row)
    return target, tuple(names), out


def _nrmse(actual: Sequence[float], predicted: Sequence[float]) -> float:
    if len(actual) != len(predicted) or len(actual) < 2:
        return math.inf
    mean = sum(actual) / len(actual)
    spread = math.sqrt(sum((x - mean) ** 2 for x in actual) / len(actual))
    scale = max(spread, max(abs(x) for x in actual) * 1e-9, _EPS)
    rmse = math.sqrt(sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual))
    return rmse / scale


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
    n = len(vector)
    if n == 0 or len(matrix) != n or any(len(row) != n for row in matrix):
        return None
    a = [list(map(float, row)) + [float(vector[i])] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) <= 1e-10:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        divisor = a[col][col]
        a[col] = [x / divisor for x in a[col]]
        for row in range(n):
            if row == col:
                continue
            factor = a[row][col]
            if abs(factor) <= _EPS:
                continue
            a[row] = [x - factor * y for x, y in zip(a[row], a[col])]
    result = [a[i][-1] for i in range(n)]
    return result if all(math.isfinite(x) for x in result) else None


def _fit_linear_features(features: Sequence[Sequence[float]], target: Sequence[float]) -> list[float] | None:
    if not target or any(len(f) != len(target) for f in features):
        return None
    p = len(features) + 1
    xtx = [[0.0] * p for _ in range(p)]
    xty = [0.0] * p
    for row_index, y in enumerate(target):
        row = [1.0] + [float(f[row_index]) for f in features]
        for i in range(p):
            xty[i] += row[i] * float(y)
            for j in range(p):
                xtx[i][j] += row[i] * row[j]
    for i in range(p):
        xtx[i][i] += 1e-12
    return _solve_linear_system(xtx, xty)


def _apply_unary(op: str, x: float) -> float | None:
    try:
        if op == "neg":
            y = -x
        elif op == "abs":
            y = abs(x)
        elif op == "square":
            y = x * x
        elif op == "sqrt_abs":
            y = math.sqrt(abs(x))
        elif op == "log1p_abs":
            y = math.log1p(abs(x))
        elif op == "sat":
            y = x / (1.0 + abs(x))
        else:
            return None
    except (OverflowError, ValueError, ZeroDivisionError):
        return None
    return y if math.isfinite(y) else None


def _apply_binary(op: str, left: float, right: float) -> float | None:
    try:
        if op == "add":
            y = left + right
        elif op == "sub":
            y = left - right
        elif op == "mul":
            y = left * right
        elif op == "stable_div":
            y = left / (1.0 + abs(right))
        else:
            return None
    except (OverflowError, ValueError, ZeroDivisionError):
        return None
    return y if math.isfinite(y) else None


def evaluate_tree(tree: Mapping[str, Any], row: Mapping[str, float]) -> float:
    op = str(tree.get("op") or "")
    if op == "var":
        name = str(tree.get("name") or "")
        if name not in row:
            raise ExpressionTreeError("TREE_VARIABLE_MISSING:" + name)
        return _finite(row[name], name)
    if op in _UNARY:
        arg = evaluate_tree(tree.get("arg") or {}, row)
        value = _apply_unary(op, arg)
        if value is None:
            raise ExpressionTreeError("TREE_UNARY_NONFINITE:" + op)
        return value
    if op in _BINARY:
        left = evaluate_tree(tree.get("left") or {}, row)
        right = evaluate_tree(tree.get("right") or {}, row)
        value = _apply_binary(op, left, right)
        if value is None:
            raise ExpressionTreeError("TREE_BINARY_NONFINITE:" + op)
        return value
    raise ExpressionTreeError("TREE_OPERATOR_INVALID")


def _structural_signature(tree: Mapping[str, Any], names: Sequence[str]) -> str:
    op = str(tree.get("op") or "")
    if op == "var":
        name = str(tree.get("name") or "")
        if name not in names:
            raise ExpressionTreeError("TREE_VARIABLE_UNKNOWN:" + name)
        return "v" + str(names.index(name))
    if op in _UNARY:
        return op + "(" + _structural_signature(tree["arg"], names) + ")"
    if op in _BINARY:
        left = _structural_signature(tree["left"], names)
        right = _structural_signature(tree["right"], names)
        if op in _COMMUTATIVE and right < left:
            left, right = right, left
        return op + "(" + left + "," + right + ")"
    raise ExpressionTreeError("TREE_OPERATOR_INVALID")


def _tree_complexity(tree: Mapping[str, Any]) -> int:
    op = str(tree.get("op") or "")
    if op == "var":
        return 1
    if op in _UNARY:
        return 1 + _tree_complexity(tree["arg"])
    if op in _BINARY:
        return 1 + _tree_complexity(tree["left"]) + _tree_complexity(tree["right"])
    raise ExpressionTreeError("TREE_OPERATOR_INVALID")


def _feature_record(tree: Mapping[str, Any], *, names, data, train, valid, target):
    try:
        all_values = [evaluate_tree(tree, row) for row in data]
        train_values = [evaluate_tree(tree, row) for row in train]
        valid_values = [evaluate_tree(tree, row) for row in valid]
    except ExpressionTreeError:
        return None
    actual_train = [float(row[target]) for row in train]
    coeff = _fit_linear_features([train_values], actual_train)
    if coeff is None:
        return None
    actual_all = [float(row[target]) for row in data]
    actual_valid = [float(row[target]) for row in valid]
    predicted_all = [coeff[0] + coeff[1] * x for x in all_values]
    predicted_valid = [coeff[0] + coeff[1] * x for x in valid_values]
    validation_error = _nrmse(actual_valid, predicted_valid) if len(valid) >= 2 else _nrmse(actual_all, predicted_all)
    return {
        "tree": tree,
        "signature": _structural_signature(tree, names),
        "complexity": _tree_complexity(tree),
        "all_values": all_values,
        "train_values": train_values,
        "single_feature_validation_nrmse": validation_error,
    }


def _vector_key(values: Sequence[float]) -> tuple[float, ...]:
    scale = max(1.0, max(abs(x) for x in values))
    return tuple(round(float(x) / scale, 10) for x in values)


def _predict_combo(candidate: Mapping[str, Any], row: Mapping[str, float]) -> float:
    coefficients = [float(x) for x in candidate["coefficients"]]
    features = candidate["features"]
    if len(coefficients) != len(features) + 1:
        raise ExpressionTreeError("CANDIDATE_COEFFICIENT_COUNT_INVALID")
    value = coefficients[0]
    for coefficient, tree in zip(coefficients[1:], features):
        value += coefficient * evaluate_tree(tree, row)
    if not math.isfinite(value):
        raise ExpressionTreeError("CANDIDATE_PREDICTION_NONFINITE")
    return value


def predict(candidate: Mapping[str, Any], point: Mapping[str, Any]) -> float:
    row = {str(k): _finite(v, str(k)) for k, v in point.items()}
    return _predict_combo(candidate, row)


def discover(
    rows: Sequence[Mapping[str, Any]],
    *,
    target: str,
    inputs: Sequence[str] | None = None,
    max_depth: int = 3,
    beam_width: int = 32,
    pair_feature_pool: int = 24,
    exact_nrmse: float = 1e-8,
) -> dict[str, Any]:
    target, names, data = _normalize_rows(rows, target, inputs)
    for label, value, low, high in (
        ("max_depth", max_depth, 1, 4),
        ("beam_width", beam_width, 4, 64),
        ("pair_feature_pool", pair_feature_pool, 4, 48),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
            raise ExpressionTreeError(label.upper() + "_INVALID")
    exact_nrmse = _finite(exact_nrmse, "exact_nrmse")
    if exact_nrmse <= 0 or exact_nrmse > 1e-3:
        raise ExpressionTreeError("EXACT_NRMSE_INVALID")

    train = [row for i, row in enumerate(data) if i % 4 != 3]
    valid = [row for i, row in enumerate(data) if i % 4 == 3]
    if len(valid) < 2:
        valid = data[-2:]
        train = data[:-2]

    actual_train = [float(row[target]) for row in train]
    actual_all = [float(row[target]) for row in data]
    actual_valid = [float(row[target]) for row in valid]

    features: list[dict[str, Any]] = []
    seen_vectors: set[tuple[float, ...]] = set()

    def admit(tree: Mapping[str, Any]):
        rec = _feature_record(tree, names=names, data=data, train=train, valid=valid, target=target)
        if rec is None:
            return None
        key = _vector_key(rec["all_values"])
        if key in seen_vectors:
            return None
        seen_vectors.add(key)
        features.append(rec)
        return rec

    beam = []
    for name in names:
        rec = admit({"op": "var", "name": name})
        if rec is not None:
            beam.append(rec)
    beam.sort(key=lambda r: (r["single_feature_validation_nrmse"], r["complexity"], r["signature"]))

    generated_tree_count = len(beam)
    for _depth in range(1, max_depth + 1):
        best_global = sorted(
            features,
            key=lambda r: (r["single_feature_validation_nrmse"], r["complexity"], r["signature"]),
        )[:beam_width]
        binary_pool = []
        seen_sig = set()
        for rec in beam + best_global:
            if rec["signature"] in seen_sig:
                continue
            seen_sig.add(rec["signature"])
            binary_pool.append(rec)
            if len(binary_pool) >= 16:
                break

        proposed = []
        for rec in beam:
            for op in _UNARY:
                proposed.append({"op": op, "arg": rec["tree"]})
        for i, left in enumerate(binary_pool):
            for j, right in enumerate(binary_pool):
                for op in _BINARY:
                    if op in _COMMUTATIVE and j < i:
                        continue
                    proposed.append({"op": op, "left": left["tree"], "right": right["tree"]})
        generated_tree_count += len(proposed)

        new_features = []
        for tree in proposed:
            rec = admit(tree)
            if rec is not None:
                new_features.append(rec)
        new_features.sort(
            key=lambda r: (r["single_feature_validation_nrmse"], r["complexity"], r["signature"])
        )
        beam = new_features[:beam_width]
        if not beam:
            break

    primitive = [rec for rec in features if rec["complexity"] <= 3]
    scored = sorted(
        features,
        key=lambda r: (r["single_feature_validation_nrmse"], r["complexity"], r["signature"]),
    )[:pair_feature_pool]
    pair_candidates = []
    seen_signatures = set()
    for rec in sorted(primitive, key=lambda r: (r["complexity"], r["signature"])) + scored:
        if rec["signature"] in seen_signatures:
            continue
        seen_signatures.add(rec["signature"])
        pair_candidates.append(rec)
        if len(pair_candidates) >= 96:
            break

    combos = []

    def score_combo(combo: Sequence[dict[str, Any]]):
        train_features = [rec["train_values"] for rec in combo]
        coefficients = _fit_linear_features(train_features, actual_train)
        if coefficients is None:
            return
        candidate = {
            "features": [rec["tree"] for rec in combo],
            "feature_signatures": [rec["signature"] for rec in combo],
            "coefficients": coefficients,
        }
        try:
            pred_all = [_predict_combo(candidate, row) for row in data]
            pred_valid = [_predict_combo(candidate, row) for row in valid]
        except ExpressionTreeError:
            return
        all_error = _nrmse(actual_all, pred_all)
        valid_error = _nrmse(actual_valid, pred_valid)
        complexity = sum(rec["complexity"] for rec in combo) + len(combo)
        candidate.update({
            "nrmse": all_error,
            "validation_nrmse": valid_error,
            "complexity": complexity,
        })
        combos.append(candidate)

    for rec in pair_candidates:
        score_combo([rec])
    for i, left in enumerate(pair_candidates):
        for right in pair_candidates[i + 1:]:
            score_combo([left, right])

    combos.sort(
        key=lambda c: (
            max(float(c["nrmse"]), float(c["validation_nrmse"])),
            int(c["complexity"]),
            tuple(c["feature_signatures"]),
        )
    )
    best = combos[0] if combos else None
    exact = bool(
        best
        and float(best["nrmse"]) <= exact_nrmse
        and float(best["validation_nrmse"]) <= exact_nrmse
    )
    return {
        "schema": SCHEMA,
        "status": "EXACT_CANDIDATE_FOUND" if exact else "GRAMMAR_NOT_EXACT__EXPAND_OR_EXPERIMENT",
        "target": target,
        "input_variables": list(names),
        "row_count": len(data),
        "max_depth": max_depth,
        "generated_tree_count": generated_tree_count,
        "unique_feature_count": len(features),
        "candidate_count": len(combos),
        "exact_nrmse_threshold": exact_nrmse,
        "best_candidate": best,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "dynamic_code_execution": False,
        "random_search": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
