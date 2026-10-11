"""Finite typed grid program inducer V1.

This is a Brain-owned bounded program synthesizer for deterministic grid-to-grid
transformations. It is intentionally benchmark-neutral: ARC can call it, but its
contract is "examples + typed operator registry -> all minimum-cost exact
programs within a declared finite search bound."

Key laws:
* no target-score beam pruning;
* search every well-typed program through max_depth;
* preserve equal-minimum ambiguity;
* select by declared description cost, never by hidden/test outcomes;
* fail closed on invalid grids or search-bound overflow;
* report completeness only relative to the frozen operator registry and bounds.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

Grid = tuple[tuple[int, ...], ...]
SCHEMA = "PROJECT_BRAIN_FINITE_GRID_PROGRAM_INDUCER_V1"


class GridProgramInducerError(ValueError):
    pass


def _grid(value: Sequence[Sequence[int]], label: str = "grid") -> Grid:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise GridProgramInducerError(label.upper() + "_INVALID")
    rows: list[tuple[int, ...]] = []
    width: int | None = None
    for raw_row in value:
        if not isinstance(raw_row, Sequence) or isinstance(raw_row, (str, bytes)) or not raw_row:
            raise GridProgramInducerError(label.upper() + "_ROW_INVALID")
        row: list[int] = []
        for cell in raw_row:
            if not isinstance(cell, int) or isinstance(cell, bool) or not 0 <= cell <= 9:
                raise GridProgramInducerError(label.upper() + "_CELL_INVALID")
            row.append(cell)
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise GridProgramInducerError(label.upper() + "_NON_RECTANGULAR")
        rows.append(tuple(row))
    return tuple(rows)


def _shape(grid: Grid) -> tuple[int, int]:
    return len(grid), len(grid[0])


def _rot90(grid: Grid) -> Grid:
    return tuple(tuple(row) for row in zip(*grid[::-1]))


def _rot180(grid: Grid) -> Grid:
    return tuple(tuple(reversed(row)) for row in reversed(grid))


def _rot270(grid: Grid) -> Grid:
    return tuple(tuple(row) for row in zip(*grid))[::-1]


def _flip_h(grid: Grid) -> Grid:
    return tuple(tuple(reversed(row)) for row in grid)


def _flip_v(grid: Grid) -> Grid:
    return tuple(reversed(grid))


def _transpose(grid: Grid) -> Grid:
    return tuple(tuple(row) for row in zip(*grid))


def _anti_transpose(grid: Grid) -> Grid:
    return _rot180(_transpose(grid))


def _crop_nonzero(grid: Grid) -> Grid | None:
    cells = [(r, c) for r, row in enumerate(grid) for c, value in enumerate(row) if value != 0]
    if not cells:
        return None
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    r0, r1 = min(rs), max(rs)
    c0, c1 = min(cs), max(cs)
    return tuple(tuple(grid[r][c0 : c1 + 1]) for r in range(r0, r1 + 1))


def _remove_zero_lines(grid: Grid) -> Grid | None:
    rows = [tuple(row) for row in grid if any(v != 0 for v in row)]
    if not rows:
        return None
    keep = [c for c in range(len(rows[0])) if any(row[c] != 0 for row in rows)]
    if not keep:
        return None
    return tuple(tuple(row[c] for c in keep) for row in rows)


def _dedupe_adjacent_lines(grid: Grid) -> Grid | None:
    rows: list[tuple[int, ...]] = []
    for row in grid:
        t = tuple(row)
        if not rows or t != rows[-1]:
            rows.append(t)
    if not rows:
        return None
    columns = list(zip(*rows))
    kept: list[tuple[int, ...]] = []
    for column in columns:
        t = tuple(column)
        if not kept or t != kept[-1]:
            kept.append(t)
    if not kept:
        return None
    return tuple(tuple(row) for row in zip(*kept))


@dataclass(frozen=True)
class GridOperator:
    operator_id: str
    cost: int
    fn: Callable[[Grid], Grid | None]


DEFAULT_OPERATORS: tuple[GridOperator, ...] = (
    GridOperator("ROTATE_90", 1, _rot90),
    GridOperator("ROTATE_180", 1, _rot180),
    GridOperator("ROTATE_270", 1, _rot270),
    GridOperator("FLIP_HORIZONTAL", 1, _flip_h),
    GridOperator("FLIP_VERTICAL", 1, _flip_v),
    GridOperator("TRANSPOSE", 1, _transpose),
    GridOperator("ANTI_TRANSPOSE", 1, _anti_transpose),
    GridOperator("CROP_NONZERO", 1, _crop_nonzero),
    GridOperator("REMOVE_ZERO_LINES", 1, _remove_zero_lines),
    GridOperator("DEDUPE_ADJACENT_LINES", 1, _dedupe_adjacent_lines),
)


def _apply_program(grid: Grid, program: Sequence[GridOperator]) -> Grid | None:
    current: Grid | None = grid
    for operator in program:
        if current is None:
            return None
        current = operator.fn(current)
    return current


def _program_signature(program: Sequence[GridOperator]) -> tuple[str, ...]:
    return tuple(operator.operator_id for operator in program)


def _program_cost(program: Sequence[GridOperator]) -> int:
    return sum(operator.cost for operator in program)


def induce(
    training_pairs: Sequence[Mapping[str, Sequence[Sequence[int]]]],
    *,
    max_depth: int = 3,
    max_programs: int = 100000,
    operators: Sequence[GridOperator] | None = None,
) -> dict[str, Any]:
    if max_depth < 1:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "MAX_DEPTH_INVALID"}
    if max_programs < 1:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "MAX_PROGRAMS_INVALID"}
    registry = tuple(operators or DEFAULT_OPERATORS)
    if not registry:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "EMPTY_OPERATOR_REGISTRY"}
    if len({o.operator_id for o in registry}) != len(registry):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "DUPLICATE_OPERATOR_ID"}
    if any(o.cost < 1 for o in registry):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "NONPOSITIVE_OPERATOR_COST"}

    pairs: list[tuple[Grid, Grid]] = []
    try:
        if not isinstance(training_pairs, Sequence) or isinstance(training_pairs, (str, bytes)) or not training_pairs:
            raise GridProgramInducerError("TRAINING_PAIRS_INVALID")
        for i, raw in enumerate(training_pairs):
            if not isinstance(raw, Mapping) or "input" not in raw or "output" not in raw:
                raise GridProgramInducerError(f"PAIR_{i}_INVALID")
            pairs.append((_grid(raw["input"], f"pair_{i}_input"), _grid(raw["output"], f"pair_{i}_output")))
    except GridProgramInducerError as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": str(exc)}

    candidates_evaluated = 0
    exact: list[tuple[int, tuple[str, ...]]] = []
    frontier: list[tuple[GridOperator, ...]] = [tuple()]
    overflow = False

    for depth in range(1, max_depth + 1):
        next_frontier: list[tuple[GridOperator, ...]] = []
        for prefix in frontier:
            for operator in registry:
                program = (*prefix, operator)
                candidates_evaluated += 1
                if candidates_evaluated > max_programs:
                    overflow = True
                    break
                outputs = [_apply_program(inp, program) for inp, _ in pairs]
                if all(actual is not None and actual == expected for actual, (_, expected) in zip(outputs, pairs)):
                    exact.append((_program_cost(program), _program_signature(program)))
                next_frontier.append(program)
            if overflow:
                break
        if overflow:
            break
        frontier = next_frontier

    if overflow:
        return {
            "schema": SCHEMA,
            "status": "SEARCH_BOUND_EXCEEDED",
            "candidates_evaluated": candidates_evaluated,
            "max_programs": max_programs,
            "max_depth": max_depth,
            "operator_ids": [o.operator_id for o in registry],
            "complete_within_declared_bound": False,
            "terminal_authority": False,
        }

    if not exact:
        return {
            "schema": SCHEMA,
            "status": "NO_EXACT_PROGRAM",
            "candidates_evaluated": candidates_evaluated,
            "max_depth": max_depth,
            "operator_ids": [o.operator_id for o in registry],
            "complete_within_declared_bound": True,
            "completeness_scope": "DECLARED_OPERATOR_REGISTRY_X_PROGRAM_DEPTH_ONLY",
            "terminal_authority": False,
        }

    minimum_cost = min(cost for cost, _ in exact)
    programs = sorted({sig for cost, sig in exact if cost == minimum_cost})
    return {
        "schema": SCHEMA,
        "status": "EXACT_PROGRAMS",
        "candidates_evaluated": candidates_evaluated,
        "max_depth": max_depth,
        "operator_ids": [o.operator_id for o in registry],
        "minimum_cost": minimum_cost,
        "programs": [list(sig) for sig in programs],
        "program_count": len(programs),
        "ambiguity_preserved": len(programs) > 1,
        "complete_within_declared_bound": True,
        "completeness_scope": "DECLARED_OPERATOR_REGISTRY_X_PROGRAM_DEPTH_ONLY",
        "ranking_rule": "MINIMUM_TOTAL_OPERATOR_COST_THEN_PRESERVE_ALL_EQUAL_MINIMUM_PROGRAMS",
        "terminal_authority": False,
        "promotion_authority": False,
    }


def predict(
    program: Sequence[str],
    grid: Sequence[Sequence[int]],
    *,
    operators: Sequence[GridOperator] | None = None,
) -> dict[str, Any]:
    registry = tuple(operators or DEFAULT_OPERATORS)
    by_id = {o.operator_id: o for o in registry}
    try:
        g = _grid(grid)
        ops = [by_id[x] for x in program]
    except (GridProgramInducerError, KeyError, TypeError) as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": type(exc).__name__ + ":" + str(exc)}
    out = _apply_program(g, ops)
    if out is None:
        return {"schema": SCHEMA, "status": "UNDEFINED_FOR_INPUT", "prediction": None}
    return {
        "schema": SCHEMA,
        "status": "PREDICTED",
        "prediction": [list(row) for row in out],
        "terminal_authority": False,
    }
