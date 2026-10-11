"""ARC adapter for the generic finite grid program inducer V1.

This module does not add ARC-specific answer logic. It exposes reusable,
deterministic grid transforms from the existing ARC novelty compiler through
the generic GridOperator protocol so bounded composition search can discover
programs automatically.
"""
from __future__ import annotations

from typing import Sequence

from canonical.runtime import arc_novelty_compiler_v1 as arc
from canonical.runtime.finite_grid_program_inducer_v1 import Grid, GridOperator, induce


def _crop_non_background(grid: Grid) -> Grid | None:
    bbox = arc._non_background_bbox(grid)
    return None if bbox is None else arc._crop_bbox(grid, bbox)


def _sym_vertical(grid: Grid) -> Grid | None:
    return arc._complete_symmetry(grid, "VERTICAL")


def _sym_rot180(grid: Grid) -> Grid | None:
    return arc._complete_symmetry(grid, "ROTATE_180")


def _grav_left(grid: Grid) -> Grid:
    return arc._row_col_gravity(grid, "LEFT")


def _grav_right(grid: Grid) -> Grid:
    return arc._row_col_gravity(grid, "RIGHT")


def _grav_up(grid: Grid) -> Grid:
    return arc._row_col_gravity(grid, "UP")


def _grav_down(grid: Grid) -> Grid:
    return arc._row_col_gravity(grid, "DOWN")


ARC_COMPOSABLE_OPERATORS_V1: tuple[GridOperator, ...] = (
    GridOperator("ROTATE_90", 1, arc._rot90),
    GridOperator("ROTATE_180", 1, arc._rot180),
    GridOperator("ROTATE_270", 1, arc._rot270),
    GridOperator("FLIP_HORIZONTAL", 1, arc._flip_h),
    GridOperator("FLIP_VERTICAL", 1, arc._flip_v),
    GridOperator("TRANSPOSE", 1, arc._transpose),
    GridOperator("ANTI_TRANSPOSE", 1, arc._anti_transpose),
    GridOperator("CROP_NON_BACKGROUND", 1, _crop_non_background),
    GridOperator("REMOVE_ZERO_LINES", 1, arc._remove_zero_lines),
    GridOperator("DEDUPE_ADJACENT_LINES", 1, arc._dedupe_adjacent_lines),
    GridOperator("CONNECT_ALIGNED_SAME_COLOR_BOTH_AXES", 1, arc._connect_both_same_color),
    GridOperator("FILL_EACH_COLOR_BBOX", 1, arc._fill_each_color_bbox),
    GridOperator("CONNECT_SAME_COLOR_DIAGONALS", 1, arc._connect_same_color_diagonals),
    GridOperator("COMPLETE_SYMMETRY_VERTICAL", 1, _sym_vertical),
    GridOperator("COMPLETE_SYMMETRY_ROTATE_180", 1, _sym_rot180),
    GridOperator("ROW_GRAVITY_LEFT", 1, _grav_left),
    GridOperator("ROW_GRAVITY_RIGHT", 1, _grav_right),
    GridOperator("COL_GRAVITY_UP", 1, _grav_up),
    GridOperator("COL_GRAVITY_DOWN", 1, _grav_down),
    GridOperator("SELECT_ODD_COLOR_COMPONENT_CROP", 1, arc._select_odd_color_component_crop),
    GridOperator("EXTRACT_LARGEST_MONOCHROME_FRAME_INTERIOR", 1, arc._select_largest_frame_interior),
)


def induce_arc_composition(
    training_pairs: Sequence[dict],
    *,
    max_depth: int = 3,
    max_programs: int = 20000,
) -> dict:
    result = induce(
        training_pairs,
        max_depth=max_depth,
        max_programs=max_programs,
        operators=ARC_COMPOSABLE_OPERATORS_V1,
    )
    result["adapter_schema"] = "PROJECT_BRAIN_ARC_PROGRAM_INDUCTION_ADAPTER_V1"
    result["benchmark_specific_answer_logic"] = False
    result["operator_source"] = "VERIFIED_OR_CURRENT_BRAIN_OWNED_ARC_GRID_PRIMITIVES"
    return result
