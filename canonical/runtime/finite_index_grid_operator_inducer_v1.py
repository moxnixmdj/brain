"""Finite index-expression grid operator inducer V1.

Synthesizes reusable grid-to-grid operators from demonstrations by searching a
finite grammar of output-shape rules and source-index expressions. This extends
the verified affine inducer to non-affine coordinate programs such as integer
scaling and tiling/repetition.

No task IDs, benchmark labels, learned weights, external models, random search,
or target/test outcomes participate in operator selection.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

Grid = tuple[tuple[int, ...], ...]
SCHEMA = "PROJECT_BRAIN_FINITE_INDEX_GRID_OPERATOR_INDUCER_V1"


class IndexGridOperatorError(ValueError):
    pass


def _grid(value: Sequence[Sequence[int]], label: str) -> Grid:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise IndexGridOperatorError(label.upper() + "_INVALID")
    rows: list[tuple[int, ...]] = []
    width: int | None = None
    for raw in value:
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
            raise IndexGridOperatorError(label.upper() + "_ROW_INVALID")
        row: list[int] = []
        for v in raw:
            if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 9:
                raise IndexGridOperatorError(label.upper() + "_CELL_INVALID")
            row.append(v)
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise IndexGridOperatorError(label.upper() + "_NON_RECTANGULAR")
        rows.append(tuple(row))
    return tuple(rows)


def _shape(g: Grid) -> tuple[int, int]:
    return len(g), len(g[0])


@dataclass(frozen=True)
class ShapeRule:
    swap: bool
    row_multiplier: int
    col_multiplier: int

    def signature(self) -> str:
        return f"{'SWAP' if self.swap else 'DIRECT'}_R{self.row_multiplier}_C{self.col_multiplier}"

    def apply(self, h: int, w: int) -> tuple[int, int]:
        base_h, base_w = (w, h) if self.swap else (h, w)
        return base_h * self.row_multiplier, base_w * self.col_multiplier


@dataclass(frozen=True)
class IndexOperator:
    shape_rule: ShapeRule
    source_row_expr: str
    source_col_expr: str

    def signature(self) -> tuple[str, str, str]:
        return (self.shape_rule.signature(), self.source_row_expr, self.source_col_expr)


def _expr_value(expr: str, *, r: int, c: int, h: int, w: int) -> int | None:
    if expr == "R":
        return r
    if expr == "C":
        return c
    for k in (2, 3, 4):
        if expr == f"R_DIV_{k}":
            return r // k
        if expr == f"C_DIV_{k}":
            return c // k
        if expr == f"H1_MINUS_R_DIV_{k}":
            return h - 1 - (r // k)
        if expr == f"H1_MINUS_C_DIV_{k}":
            return h - 1 - (c // k)
        if expr == f"W1_MINUS_R_DIV_{k}":
            return w - 1 - (r // k)
        if expr == f"W1_MINUS_C_DIV_{k}":
            return w - 1 - (c // k)
    if expr == "R_MOD_H":
        return r % h
    if expr == "C_MOD_H":
        return c % h
    if expr == "R_MOD_W":
        return r % w
    if expr == "C_MOD_W":
        return c % w
    if expr == "H1_MINUS_R_MOD_H":
        return h - 1 - (r % h)
    if expr == "H1_MINUS_C_MOD_H":
        return h - 1 - (c % h)
    if expr == "W1_MINUS_R_MOD_W":
        return w - 1 - (r % w)
    if expr == "W1_MINUS_C_MOD_W":
        return w - 1 - (c % w)
    return None


INDEX_EXPRESSIONS: tuple[str, ...] = (
    "R", "C",
    "R_DIV_2", "R_DIV_3", "R_DIV_4",
    "C_DIV_2", "C_DIV_3", "C_DIV_4",
    "R_MOD_H", "C_MOD_H", "R_MOD_W", "C_MOD_W",
    "H1_MINUS_R_DIV_2", "H1_MINUS_R_DIV_3", "H1_MINUS_R_DIV_4",
    "H1_MINUS_C_DIV_2", "H1_MINUS_C_DIV_3", "H1_MINUS_C_DIV_4",
    "W1_MINUS_R_DIV_2", "W1_MINUS_R_DIV_3", "W1_MINUS_R_DIV_4",
    "W1_MINUS_C_DIV_2", "W1_MINUS_C_DIV_3", "W1_MINUS_C_DIV_4",
    "H1_MINUS_R_MOD_H", "H1_MINUS_C_MOD_H",
    "W1_MINUS_R_MOD_W", "W1_MINUS_C_MOD_W",
)


def _shape_rules() -> tuple[ShapeRule, ...]:
    return tuple(
        ShapeRule(swap, rm, cm)
        for swap in (False, True)
        for rm in (1, 2, 3, 4)
        for cm in (1, 2, 3, 4)
    )


def _apply(g: Grid, op: IndexOperator) -> Grid | None:
    h, w = _shape(g)
    oh, ow = op.shape_rule.apply(h, w)
    out: list[tuple[int, ...]] = []
    for r in range(oh):
        row: list[int] = []
        for c in range(ow):
            sr = _expr_value(op.source_row_expr, r=r, c=c, h=h, w=w)
            sc = _expr_value(op.source_col_expr, r=r, c=c, h=h, w=w)
            if sr is None or sc is None or not (0 <= sr < h and 0 <= sc < w):
                return None
            row.append(g[sr][sc])
        out.append(tuple(row))
    return tuple(out)


def _expr_cost(expr: str) -> float:
    if expr in ("R", "C"):
        return 1.0
    if "_DIV_" in expr:
        return 2.0 if "MINUS" not in expr else 2.5
    if "_MOD_" in expr:
        return 2.0 if "MINUS" not in expr else 2.5
    raise IndexGridOperatorError("EXPR_COST_UNKNOWN")


def _operator_cost(op: IndexOperator) -> float:
    shape = op.shape_rule
    shape_cost = (
        (0.5 if shape.swap else 0.0)
        + (0.0 if shape.row_multiplier == 1 else 1.0)
        + (0.0 if shape.col_multiplier == 1 else 1.0)
    )
    return shape_cost + _expr_cost(op.source_row_expr) + _expr_cost(op.source_col_expr)


def induce(
    training_pairs: Sequence[Mapping[str, Sequence[Sequence[int]]]],
    *,
    max_candidates: int = 50000,
) -> dict[str, Any]:
    try:
        if not isinstance(training_pairs, Sequence) or isinstance(training_pairs, (str, bytes)) or not training_pairs:
            raise IndexGridOperatorError("TRAINING_PAIRS_INVALID")
        pairs: list[tuple[Grid, Grid]] = []
        for i, raw in enumerate(training_pairs):
            pairs.append((_grid(raw["input"], f"pair_{i}_input"), _grid(raw["output"], f"pair_{i}_output")))
    except (IndexGridOperatorError, KeyError, TypeError) as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": type(exc).__name__ + ":" + str(exc)}

    admissible_shapes = [
        rule for rule in _shape_rules()
        if all(rule.apply(*_shape(inp)) == _shape(out) for inp, out in pairs)
    ]
    if not admissible_shapes:
        return {
            "schema": SCHEMA,
            "status": "NO_OPERATOR",
            "reason": "NO_SUPPORTED_OUTPUT_SHAPE_RULE",
            "terminal_authority": False,
        }

    exact: list[IndexOperator] = []
    evaluated = 0
    for shape_rule in admissible_shapes:
        for row_expr in INDEX_EXPRESSIONS:
            for col_expr in INDEX_EXPRESSIONS:
                evaluated += 1
                if evaluated > max_candidates:
                    return {
                        "schema": SCHEMA,
                        "status": "SEARCH_BOUND_EXCEEDED",
                        "candidates_evaluated": evaluated,
                        "max_candidates": max_candidates,
                        "complete_within_declared_bound": False,
                        "terminal_authority": False,
                    }
                op = IndexOperator(shape_rule, row_expr, col_expr)
                if all(_apply(inp, op) == out for inp, out in pairs):
                    exact.append(op)

    if not exact:
        return {
            "schema": SCHEMA,
            "status": "NO_OPERATOR",
            "candidates_evaluated": evaluated,
            "complete_within_declared_bound": True,
            "completeness_scope": "DECLARED_INDEX_EXPRESSION_GRAMMAR_X_SWAP_AND_INTEGER_1_TO_4_OUTPUT_MULTIPLIERS",
            "terminal_authority": False,
        }

    minimum_cost = min(_operator_cost(op) for op in exact)
    selected = sorted(
        {op.signature(): op for op in exact if _operator_cost(op) == minimum_cost}.values(),
        key=lambda op: op.signature(),
    )
    return {
        "schema": SCHEMA,
        "status": "EXACT_OPERATORS",
        "operators": [
            {
                "shape_rule": {
                    "swap": op.shape_rule.swap,
                    "row_multiplier": op.shape_rule.row_multiplier,
                    "col_multiplier": op.shape_rule.col_multiplier,
                },
                "source_row_expr": op.source_row_expr,
                "source_col_expr": op.source_col_expr,
            }
            for op in selected
        ],
        "operator_count": len(selected),
        "minimum_description_cost": minimum_cost,
        "ambiguity_preserved": len(selected) > 1,
        "candidates_evaluated": evaluated,
        "complete_within_declared_bound": True,
        "completeness_scope": "DECLARED_INDEX_EXPRESSION_GRAMMAR_X_SWAP_AND_INTEGER_1_TO_4_OUTPUT_MULTIPLIERS",
        "selection_rule": "MINIMUM_DESCRIPTION_COST__PRESERVE_ALL_EQUAL_MINIMUM_EXACT_OPERATORS",
        "terminal_authority": False,
        "promotion_authority": False,
    }


def predict(result: Mapping[str, Any], grid: Sequence[Sequence[int]]) -> dict[str, Any]:
    try:
        g = _grid(grid, "grid")
        outputs: set[Grid] = set()
        for raw in result["operators"]:
            shape = raw["shape_rule"]
            op = IndexOperator(
                ShapeRule(bool(shape["swap"]), int(shape["row_multiplier"]), int(shape["col_multiplier"])),
                str(raw["source_row_expr"]),
                str(raw["source_col_expr"]),
            )
            out = _apply(g, op)
            if out is not None:
                outputs.add(out)
    except (IndexGridOperatorError, KeyError, TypeError, ValueError) as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": type(exc).__name__ + ":" + str(exc)}

    if not outputs:
        return {"schema": SCHEMA, "status": "UNDEFINED_FOR_INPUT", "prediction": None}
    if len(outputs) > 1:
        return {"schema": SCHEMA, "status": "AMBIGUOUS_PREDICTION", "prediction": None}
    out = next(iter(outputs))
    return {
        "schema": SCHEMA,
        "status": "PREDICTED",
        "prediction": [list(row) for row in out],
        "terminal_authority": False,
    }
