"""Zero-learned-state ARC-AGI solver V1.

The solver is frozen before held-out task exposure. It searches a fixed,
solver-independent hypothesis language with the generic MDL program-induction
kernel. Task demonstrations may instantiate a consistent color mapping, but no
held-out output is visible to the solver.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.mdl_program_induction_v1 import (
    Primitive,
    execute,
    synthesize,
)

Grid = list[list[int]]


class ARCZeroLearnedError(ValueError):
    pass


def _grid(value: Any) -> Grid:
    if not isinstance(value, list) or not value or any(not isinstance(r, list) or not r for r in value):
        raise ARCZeroLearnedError("GRID_INVALID")
    width = len(value[0])
    if width < 1 or any(len(r) != width for r in value):
        raise ARCZeroLearnedError("GRID_NOT_RECTANGULAR")
    out: Grid = []
    for row in value:
        nr = []
        for cell in row:
            if isinstance(cell, bool) or not isinstance(cell, int) or not 0 <= cell <= 9:
                raise ARCZeroLearnedError("GRID_CELL_INVALID")
            nr.append(cell)
        out.append(nr)
    return out


def _shape(g: Grid) -> tuple[int, int]:
    return len(g), len(g[0])


def identity(g: Grid) -> Grid:
    return [row[:] for row in g]


def rot90(g: Grid) -> Grid:
    return [list(row) for row in zip(*g[::-1])]


def rot180(g: Grid) -> Grid:
    return [row[::-1] for row in g[::-1]]


def rot270(g: Grid) -> Grid:
    return [list(row) for row in zip(*g)][::-1]


def flip_h(g: Grid) -> Grid:
    return [row[::-1] for row in g]


def flip_v(g: Grid) -> Grid:
    return [row[:] for row in g[::-1]]


def transpose(g: Grid) -> Grid:
    return [list(row) for row in zip(*g)]


def repeat_rows(g: Grid, factor: int) -> Grid:
    return [row[:] for row in g for _ in range(factor)]


def repeat_cols(g: Grid, factor: int) -> Grid:
    return [[cell for cell in row for _ in range(factor)] for row in g]


def upscale(g: Grid, factor: int) -> Grid:
    return repeat_rows(repeat_cols(g, factor), factor)


def tile(g: Grid, row_factor: int, col_factor: int) -> Grid:
    row_block = [row * col_factor for row in g]
    return [row[:] for _ in range(row_factor) for row in row_block]


def crop_non_background(g: Grid) -> Grid:
    counts = Counter(cell for row in g for cell in row)
    background = max(sorted(counts), key=lambda c: (counts[c], -c))
    points = [
        (r, c)
        for r, row in enumerate(g)
        for c, value in enumerate(row)
        if value != background
    ]
    if not points:
        return identity(g)
    r0 = min(r for r, _ in points)
    r1 = max(r for r, _ in points)
    c0 = min(c for _, c in points)
    c1 = max(c for _, c in points)
    return [row[c0:c1 + 1] for row in g[r0:r1 + 1]]


def _base_primitives() -> list[Primitive]:
    rows = [
        Primitive("IDENTITY", 1, identity),
        Primitive("ROT90", 1, rot90),
        Primitive("ROT180", 1, rot180),
        Primitive("ROT270", 1, rot270),
        Primitive("FLIP_H", 1, flip_h),
        Primitive("FLIP_V", 1, flip_v),
        Primitive("TRANSPOSE", 1, transpose),
        Primitive("CROP_NON_BACKGROUND", 2, crop_non_background),
    ]
    for factor in (2, 3, 4):
        rows.extend([
            Primitive(f"REPEAT_ROWS_{factor}", 2, lambda g, f=factor: repeat_rows(g, f)),
            Primitive(f"REPEAT_COLS_{factor}", 2, lambda g, f=factor: repeat_cols(g, f)),
            Primitive(f"UPSCALE_{factor}", 2, lambda g, f=factor: upscale(g, f)),
        ])
    for rf in (2, 3):
        for cf in (2, 3):
            rows.append(
                Primitive(
                    f"TILE_{rf}X{cf}",
                    2,
                    lambda g, r=rf, c=cf: tile(g, r, c),
                )
            )
    return rows


def _infer_color_map(
    train_pairs: Sequence[Mapping[str, Any]],
    transform: Callable[[Grid], Grid],
) -> dict[int, int] | None:
    mapping: dict[int, int] = {}
    for pair in train_pairs:
        inp = _grid(pair.get("input"))
        out = _grid(pair.get("output"))
        try:
            candidate = transform(inp)
        except Exception:
            return None
        if _shape(candidate) != _shape(out):
            return None
        for source_row, target_row in zip(candidate, out):
            for source, target in zip(source_row, target_row):
                prior = mapping.get(source)
                if prior is not None and prior != target:
                    return None
                mapping[source] = target
    if not mapping or all(k == v for k, v in mapping.items()):
        return None
    return mapping


def _apply_map(g: Grid, mapping: Mapping[int, int]) -> Grid:
    return [[mapping.get(cell, cell) for cell in row] for row in g]


def _task_primitives(train_pairs: Sequence[Mapping[str, Any]]) -> list[Primitive]:
    base = _base_primitives()
    out = list(base)

    # Create only hypotheses inferable from demonstrations. Each composite
    # hypothesis remains explicit and deterministic; no test output participates.
    for primitive in base:
        mapping = _infer_color_map(train_pairs, primitive.fn)
        if mapping is None:
            continue
        frozen_map = dict(mapping)
        frozen_fn = primitive.fn

        def mapped(g: Grid, fn=frozen_fn, cmap=frozen_map) -> Grid:
            return _apply_map(fn(g), cmap)

        map_id = "_".join(f"{k}TO{v}" for k, v in sorted(frozen_map.items()))
        out.append(
            Primitive(
                f"{primitive.primitive_id}__COLORMAP__{map_id}",
                primitive.cost + 1,
                mapped,
            )
        )
    return out


def solve_with_trace(
    train_pairs: Sequence[Mapping[str, Any]],
    test_input: Any,
    *,
    max_description_length: int = 4,
    max_programs_evaluated: int = 100000,
) -> dict[str, Any]:
    if not isinstance(train_pairs, Sequence) or not train_pairs:
        raise ARCZeroLearnedError("TRAIN_PAIRS_REQUIRED")
    examples = []
    for pair in train_pairs:
        if not isinstance(pair, Mapping):
            raise ARCZeroLearnedError("TRAIN_PAIR_INVALID")
        examples.append((_grid(pair.get("input")), _grid(pair.get("output"))))

    test = _grid(test_input)
    primitives = _task_primitives(train_pairs)
    result = synthesize(
        examples=examples,
        primitives=primitives,
        max_description_length=max_description_length,
        max_programs_evaluated=max_programs_evaluated,
    )
    if result["status"] != "EXACT_PROGRAM_FOUND":
        return {
            "schema": "PROJECT_BRAIN_ARC_ZERO_LEARNED_SOLVER_RESULT_V1",
            "status": "NO_SOLUTION",
            "prediction": None,
            "program": None,
            "programs_evaluated": result["programs_evaluated"],
            "semantic_states_pruned": result["semantic_states_pruned"],
            "primitive_count": len(primitives),
            "persistent_learned_state_bytes": 0,
        }

    registry = {p.primitive_id: p for p in primitives}
    prediction = execute(result["program"], test, registry)
    return {
        "schema": "PROJECT_BRAIN_ARC_ZERO_LEARNED_SOLVER_RESULT_V1",
        "status": "PREDICTION",
        "prediction": prediction,
        "program": result["program"],
        "description_length": result["description_length"],
        "programs_evaluated": result["programs_evaluated"],
        "semantic_states_pruned": result["semantic_states_pruned"],
        "primitive_count": len(primitives),
        "persistent_learned_state_bytes": 0,
    }


def solve(train_pairs: Sequence[Mapping[str, Any]], test_input: Any) -> Grid | None:
    return solve_with_trace(train_pairs, test_input)["prediction"]
