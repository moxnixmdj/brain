"""ARC adapter for the generic finite visual program inventor V1.

This module exposes Brain-owned deterministic grid transforms already present in
the ARC V16 runtime as typed primitives. The invention engine remains benchmark-
agnostic; this adapter is only one consumer.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import arc_novelty_compiler_v1 as arc
from canonical.runtime.finite_visual_program_inventor_v1 import PrimitiveSpec, solve

SCHEMA = "PROJECT_BRAIN_ARC_VISUAL_PROGRAM_INVENTION_ADAPTER_V1"
SOURCE = {"path": "canonical/runtime/arc_novelty_compiler_v1.py", "frozen_baseline": "V16"}


def _p(pid: str, fn, cost: float = 1.0) -> PrimitiveSpec:
    return PrimitiveSpec(
        primitive_id=pid,
        input_type="GRID",
        output_type="GRID",
        cost=cost,
        source={**SOURCE, "primitive_id": pid},
        apply=fn,
    )


def primitive_library() -> list[PrimitiveSpec]:
    return [
        _p("ROTATE_90", arc._rot90),
        _p("ROTATE_180", arc._rot180),
        _p("ROTATE_270", arc._rot270),
        _p("FLIP_HORIZONTAL", arc._flip_h),
        _p("FLIP_VERTICAL", arc._flip_v),
        _p("TRANSPOSE", arc._transpose),
        _p("ANTI_TRANSPOSE", arc._anti_transpose),
        _p(
            "CROP_NON_BACKGROUND",
            lambda g: None
            if (bbox := arc._non_background_bbox(g)) is None
            else arc._crop_bbox(g, bbox),
        ),
        _p("DEDUPE_ADJACENT_LINES", arc._dedupe_adjacent_lines, 1.1),
        _p("REMOVE_ZERO_LINES", arc._remove_zero_lines, 1.1),
        _p("BBOX_TOP_LEFT_QUADRANT", arc._top_left_bbox_quadrant, 1.2),
        _p("SELECT_LARGEST_COMPONENT_CROP", lambda g: arc._component_crop(g, "LARGEST"), 1.2),
        _p("SELECT_SMALLEST_COMPONENT_CROP", lambda g: arc._component_crop(g, "SMALLEST"), 1.2),
        _p("FILL_EACH_COLOR_BBOX", arc._fill_each_color_bbox, 1.3),
        _p("CONNECT_SAME_COLOR_DIAGONALS", arc._connect_same_color_diagonals, 1.3),
        _p("CONNECT_ALIGNED_SAME_COLOR_BOTH_AXES", arc._connect_both_same_color, 1.3),
        _p("COMPLETE_SYMMETRY_VERTICAL", lambda g: arc._complete_symmetry(g, "VERTICAL"), 1.3),
        _p("COMPLETE_SYMMETRY_ROTATE_180", lambda g: arc._complete_symmetry(g, "ROTATE_180"), 1.3),
        _p("GRAVITY_LEFT", lambda g: arc._row_col_gravity(g, "LEFT"), 1.3),
        _p("GRAVITY_RIGHT", lambda g: arc._row_col_gravity(g, "RIGHT"), 1.3),
        _p("GRAVITY_UP", lambda g: arc._row_col_gravity(g, "UP"), 1.3),
        _p("GRAVITY_DOWN", lambda g: arc._row_col_gravity(g, "DOWN"), 1.3),
        _p("SELF_KRONECKER", arc._self_kronecker, 1.5),
        _p("ROTATIONAL_QUAD_COMPLETION", arc._rotational_quad, 1.5),
        _p("MIRROR_EXTEND_HORIZONTAL_RIGHT", lambda g: arc._hcat(g, arc._flip_h(g)), 1.5),
        _p("MIRROR_EXTEND_VERTICAL_DOWN", lambda g: arc._vcat(g, arc._flip_v(g)), 1.5),
    ]


def solve_task(
    task: Mapping[str, Any],
    *,
    max_depth: int = 3,
    attempts: int = 2,
    max_semantic_states_per_depth: int = 50000,
    max_equivalent_programs_per_semantics: int = 8,
    max_grid_cells: int = 10000,
) -> dict[str, Any]:
    train = task.get("train")
    test = task.get("test")
    if not isinstance(train, list) or not train or not isinstance(test, list) or not test:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "TASK_INVALID"}

    test_inputs = []
    for i, row in enumerate(test):
        if not isinstance(row, Mapping) or "input" not in row:
            return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": f"TEST_{i}_INVALID"}
        test_inputs.append(row["input"])

    result = solve(
        train,
        test_inputs,
        primitive_library(),
        max_depth=max_depth,
        attempts=attempts,
        max_semantic_states_per_depth=max_semantic_states_per_depth,
        max_equivalent_programs_per_semantics=max_equivalent_programs_per_semantics,
        max_grid_cells=max_grid_cells,
    )
    return {
        "schema": SCHEMA,
        "status": result.get("status"),
        "program_invention": result,
        "external_learned_capability_calls": 0,
        "donor_runtime_required": False,
        "benchmark_credit": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }


def score_public_task(
    task: Mapping[str, Any],
    *,
    max_depth: int = 3,
    attempts: int = 2,
    max_semantic_states_per_depth: int = 50000,
    max_equivalent_programs_per_semantics: int = 8,
    max_grid_cells: int = 10000,
) -> dict[str, Any]:
    result = solve_task(
        task,
        max_depth=max_depth,
        attempts=attempts,
        max_semantic_states_per_depth=max_semantic_states_per_depth,
        max_equivalent_programs_per_semantics=max_equivalent_programs_per_semantics,
        max_grid_cells=max_grid_cells,
    )
    test = task.get("test", [])
    if result.get("status") != "SOLVED_CANDIDATES":
        return {**result, "exact_task_solved": False}

    attempts_rows = result["program_invention"].get("attempts", [])
    if not attempts_rows:
        return {**result, "exact_task_solved": False}

    expected = [row.get("output") for row in test]
    exact = any(row.get("predictions") == expected for row in attempts_rows)
    return {**result, "exact_task_solved": bool(exact)}
