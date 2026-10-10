from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_EXACT_RATIONAL_SYMBOLIC_FEATURE_V1"

SUPPORTED_UNARY = {
    "neg",
    "abs",
    "square",
    "sat",
    "reciprocal",
}
SUPPORTED_BINARY = {
    "add",
    "sub",
    "mul",
    "stable_div",
    "safe_div",
}
SUPPORTED_LEAVES = {"one", "var"}

MAX_TREES = 8
MAX_ROWS = 32
MAX_QUERY_POINTS = 256
MAX_TREE_NODES = 63
MAX_TREE_DEPTH = 12


class ExactFeatureError(ValueError):
    pass


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
    if isinstance(value, bool):
        raise ExactFeatureError(label + "_BOOL_INVALID")
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str) and value.strip():
        try:
            return Fraction(value.strip())
        except (ValueError, ZeroDivisionError) as exc:
            raise ExactFeatureError(label + "_RATIONAL_INVALID") from exc
    raise ExactFeatureError(label + "_EXACT_RATIONAL_STRING_OR_INT_REQUIRED")


def _fstr(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _canonical_tree(tree: Mapping[str, Any]) -> str:
    return json.dumps(tree, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _tree_metrics(tree: Mapping[str, Any], depth: int = 1) -> tuple[int, int]:
    if not isinstance(tree, Mapping):
        raise ExactFeatureError("TREE_NODE_NOT_OBJECT")
    if depth > MAX_TREE_DEPTH:
        raise ExactFeatureError("TREE_DEPTH_LIMIT_EXCEEDED")
    op = str(tree.get("op") or "")
    if op in SUPPORTED_LEAVES:
        if op == "one":
            if set(tree) != {"op"}:
                raise ExactFeatureError("ONE_TREE_EXTRA_FIELDS")
        else:
            name = tree.get("name")
            if not isinstance(name, str) or not name:
                raise ExactFeatureError("VAR_NAME_INVALID")
            if set(tree) != {"op", "name"}:
                raise ExactFeatureError("VAR_TREE_EXTRA_FIELDS")
        return 1, depth
    if op in SUPPORTED_UNARY:
        if set(tree) != {"op", "arg"}:
            raise ExactFeatureError("UNARY_TREE_SHAPE_INVALID:" + op)
        nodes, max_depth = _tree_metrics(tree["arg"], depth + 1)
        total = 1 + nodes
        if total > MAX_TREE_NODES:
            raise ExactFeatureError("TREE_NODE_LIMIT_EXCEEDED")
        return total, max_depth
    if op in SUPPORTED_BINARY:
        if set(tree) != {"op", "left", "right"}:
            raise ExactFeatureError("BINARY_TREE_SHAPE_INVALID:" + op)
        ln, ld = _tree_metrics(tree["left"], depth + 1)
        rn, rd = _tree_metrics(tree["right"], depth + 1)
        total = 1 + ln + rn
        if total > MAX_TREE_NODES:
            raise ExactFeatureError("TREE_NODE_LIMIT_EXCEEDED")
        return total, max(ld, rd)
    raise ExactFeatureError("UNSUPPORTED_OR_INVALID_OPERATOR:" + op)


def _collect_variables(tree: Mapping[str, Any], out: set[str]) -> None:
    op = str(tree.get("op") or "")
    if op == "var":
        out.add(str(tree["name"]))
        return
    if op in SUPPORTED_UNARY:
        _collect_variables(tree["arg"], out)
        return
    if op in SUPPORTED_BINARY:
        _collect_variables(tree["left"], out)
        _collect_variables(tree["right"], out)


def _point(raw: Any, required: set[str], label: str) -> dict[str, Fraction]:
    if not isinstance(raw, Mapping):
        raise ExactFeatureError(label + "_POINT_REQUIRED")
    missing = sorted(required - set(raw))
    if missing:
        raise ExactFeatureError(label + "_MISSING_VARIABLES:" + ",".join(missing))
    return {
        name: _fraction(raw[name], f"{label}_{name}")
        for name in sorted(required)
    }


def evaluate(tree: Mapping[str, Any], point: Mapping[str, Fraction]) -> Fraction:
    op = str(tree.get("op") or "")
    if op == "one":
        return Fraction(1, 1)
    if op == "var":
        name = str(tree["name"])
        if name not in point:
            raise ExactFeatureError("TREE_VARIABLE_MISSING:" + name)
        return point[name]

    if op in SUPPORTED_UNARY:
        value = evaluate(tree["arg"], point)
        if op == "neg":
            return -value
        if op == "abs":
            return abs(value)
        if op == "square":
            return value * value
        if op == "sat":
            return value / (Fraction(1, 1) + abs(value))
        if op == "reciprocal":
            if value == 0:
                raise ExactFeatureError("RECIPROCAL_ZERO")
            return Fraction(1, 1) / value

    if op in SUPPORTED_BINARY:
        left = evaluate(tree["left"], point)
        right = evaluate(tree["right"], point)
        if op == "add":
            return left + right
        if op == "sub":
            return left - right
        if op == "mul":
            return left * right
        if op == "stable_div":
            return left / (Fraction(1, 1) + abs(right))
        if op == "safe_div":
            if right == 0:
                raise ExactFeatureError("SAFE_DIV_ZERO")
            return left / right

    raise ExactFeatureError("UNSUPPORTED_OR_INVALID_OPERATOR:" + op)


def compile_basis(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    Compile a declared exact symbolic feature basis to rational feature rows.

    This is deliberately a strict subgrammar of MysteryMechanism V2. It covers
    only operations whose real-number semantics are exactly representable using
    Fraction for rational inputs. Unsupported operators such as sqrt_abs,
    fractional powers, log1p_abs, exp, sin and cos fail closed.

    The output is shaped to feed exact_linear_parameter_polytope_v1 directly:
    an optional intercept column followed by exact feature values.
    """
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_REQUIRED")
    trees_raw = payload.get("trees")
    if (
        not isinstance(trees_raw, Sequence)
        or isinstance(trees_raw, (str, bytes))
        or not trees_raw
        or len(trees_raw) > MAX_TREES
    ):
        return _fail("TREES_INVALID_OR_TOO_MANY")

    trees: list[Mapping[str, Any]] = []
    tree_records: list[dict[str, Any]] = []
    variables: set[str] = set()
    try:
        for index, raw in enumerate(trees_raw):
            if not isinstance(raw, Mapping):
                return _fail(f"TREE_NOT_OBJECT:{index}")
            nodes, depth = _tree_metrics(raw)
            _collect_variables(raw, variables)
            canonical = _canonical_tree(raw)
            tree_records.append(
                {
                    "tree_index": index,
                    "nodes": nodes,
                    "depth": depth,
                    "tree_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
                    "canonical_tree": canonical,
                }
            )
            trees.append(raw)
    except ExactFeatureError as exc:
        return _fail("TREE_BINDING_FAILED", detail=str(exc))

    include_intercept = payload.get("include_intercept", True)
    if not isinstance(include_intercept, bool):
        return _fail("INCLUDE_INTERCEPT_INVALID")

    rows_raw = payload.get("rows", [])
    queries_raw = payload.get("queries", [])
    if (
        not isinstance(rows_raw, Sequence)
        or isinstance(rows_raw, (str, bytes))
        or len(rows_raw) > MAX_ROWS
    ):
        return _fail("ROWS_INVALID_OR_TOO_MANY")
    if (
        not isinstance(queries_raw, Sequence)
        or isinstance(queries_raw, (str, bytes))
        or len(queries_raw) > MAX_QUERY_POINTS
    ):
        return _fail("QUERIES_INVALID_OR_TOO_MANY")

    def compile_point(raw_point: Any, label: str) -> list[str]:
        point = _point(raw_point, variables, label)
        values = [evaluate(tree, point) for tree in trees]
        if include_intercept:
            values = [Fraction(1, 1)] + values
        return [_fstr(value) for value in values]

    compiled_rows: list[list[str]] = []
    compiled_queries: list[dict[str, Any]] = []
    seen_query_ids: set[str] = set()
    try:
        for index, raw in enumerate(rows_raw):
            compiled_rows.append(compile_point(raw, f"ROW_{index}"))
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
            compiled_queries.append(
                {
                    "query_id": query_id,
                    "features": compile_point(raw.get("point"), f"QUERY_{query_id}"),
                }
            )
    except ExactFeatureError as exc:
        return _fail("EXACT_FEATURE_EVALUATION_FAILED", detail=str(exc))

    basis_manifest = {
        "semantics_id": "EXACT_RATIONAL_SYMBOLIC_FEATURE_SUBGRAMMAR_V1",
        "supported_leaves": sorted(SUPPORTED_LEAVES),
        "supported_unary": sorted(SUPPORTED_UNARY),
        "supported_binary": sorted(SUPPORTED_BINARY),
        "include_intercept": include_intercept,
        "variables": sorted(variables),
        "tree_sha256": [record["tree_sha256"] for record in tree_records],
    }
    basis_sha256 = hashlib.sha256(
        json.dumps(
            basis_manifest,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__EXACT_RATIONAL_SYMBOLIC_FEATURE_BASIS",
        "basis_semantics_id": basis_manifest["semantics_id"],
        "basis_sha256": basis_sha256,
        "include_intercept": include_intercept,
        "feature_dimension": len(trees) + (1 if include_intercept else 0),
        "variables": sorted(variables),
        "trees": tree_records,
        "feature_rows": compiled_rows,
        "query_features": compiled_queries,
        "unsupported_v2_operators_intentionally_excluded": [
            "sqrt_abs",
            "pow_abs_1_3",
            "pow_abs_2_3",
            "pow_abs_1_4",
            "pow_abs_5_8",
            "pow_abs_4_5",
            "log1p_abs",
            "exp",
            "sin",
            "cos",
        ],
        "hard_boundary": (
            "EXACT_ONLY_FOR_RATIONAL_INPUTS_AND_DECLARED_SUPPORTED_SUBGRAMMAR;"
            "NO_CLAIM_THIS_SUBGRAMMAR_COVERS_PRIVATE_MYSTERYMECHANISM;"
            "NO_EQUIVALENCE_CLAIM_FOR_UNSUPPORTED_V2_OPERATORS"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
