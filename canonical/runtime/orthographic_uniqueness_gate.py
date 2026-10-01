"""Exact orthographic uniqueness and ambiguity gate for voxelized 3-view geometry.

Given normalized top/front/right binary silhouettes, this module determines whether
their discrete 3D occupancy is uniquely determined by projection constraints.

The key fact is simple and exact:
- the visual hull is the set of all voxels that are *possible*;
- a possible voxel is *forced* if it is the sole remaining support for at least
  one required projection pixel;
- if every possible voxel is forced, the occupancy is unique;
- if any possible voxel is not forced, removing that voxel preserves all three
  silhouettes, which is an explicit alternative witness and therefore proves
  non-uniqueness.

This closes hidden-occupancy ambiguity for the normalized voxel silhouette subset.
It does not infer curved continuous geometry, OCR dimensions, or raw drawing semantics.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from canonical.runtime.orthographic_visual_hull import (
    Mask,
    VoxelGrid,
    VisualHullError,
    _validate_triplet,
    project_visual_hull,
    reconstruct_visual_hull,
)


@dataclass(frozen=True)
class OrthographicUniqueness:
    status: str
    unique: bool
    consistent: bool
    possible_voxels: int
    forced_voxels: int
    ambiguous_voxels: int
    unsupported_projection_pixels: tuple[str, ...]
    witness_removed_voxel: tuple[int, int, int] | None

    def to_dict(self) -> dict:
        return asdict(self)


def _occupied(voxels: VoxelGrid) -> set[tuple[int, int, int]]:
    out: set[tuple[int, int, int]] = set()
    for z, slab in enumerate(voxels):
        for y, row in enumerate(slab):
            for x, value in enumerate(row):
                if value:
                    out.add((x, y, z))
    return out


def _support_counts(
    occupied: set[tuple[int, int, int]],
    *,
    x_cells: int,
    y_cells: int,
    z_cells: int,
) -> tuple[list[list[int]], list[list[int]], list[list[int]]]:
    top = [[0 for _ in range(x_cells)] for _ in range(y_cells)]
    front = [[0 for _ in range(x_cells)] for _ in range(z_cells)]
    right = [[0 for _ in range(y_cells)] for _ in range(z_cells)]
    for x, y, z in occupied:
        top[y][x] += 1
        front[z][x] += 1
        right[z][y] += 1
    return top, front, right


def analyze_orthographic_uniqueness(
    top: Mask,
    front: Mask,
    right: Mask,
) -> OrthographicUniqueness:
    t, f, r = _validate_triplet(top, front, right)
    y_cells, x_cells = len(t), len(t[0])
    z_cells = len(f)

    hull = reconstruct_visual_hull(t, f, r)
    possible = _occupied(hull)
    tc, fc, rc = _support_counts(
        possible, x_cells=x_cells, y_cells=y_cells, z_cells=z_cells
    )

    unsupported: list[str] = []
    for y in range(y_cells):
        for x in range(x_cells):
            if t[y][x] and tc[y][x] == 0:
                unsupported.append(f"top:{y}:{x}")
    for z in range(z_cells):
        for x in range(x_cells):
            if f[z][x] and fc[z][x] == 0:
                unsupported.append(f"front:{z}:{x}")
    for z in range(z_cells):
        for y in range(y_cells):
            if r[z][y] and rc[z][y] == 0:
                unsupported.append(f"right:{z}:{y}")

    if unsupported:
        return OrthographicUniqueness(
            status="INCONSISTENT",
            unique=False,
            consistent=False,
            possible_voxels=len(possible),
            forced_voxels=0,
            ambiguous_voxels=len(possible),
            unsupported_projection_pixels=tuple(sorted(unsupported)),
            witness_removed_voxel=None,
        )

    forced: set[tuple[int, int, int]] = set()
    for x, y, z in possible:
        if tc[y][x] == 1 or fc[z][x] == 1 or rc[z][y] == 1:
            forced.add((x, y, z))

    ambiguous = sorted(possible - forced)
    witness = ambiguous[0] if ambiguous else None

    if witness is not None:
        # Constructively prove non-uniqueness: remove one non-forced voxel and
        # verify the three projections are exactly unchanged.
        alternative = [
            [
                [
                    bool(hull[z][y][x] and (x, y, z) != witness)
                    for x in range(x_cells)
                ]
                for y in range(y_cells)
            ]
            for z in range(z_cells)
        ]
        at, af, ar = project_visual_hull(alternative)
        if at != t or af != f or ar != r:
            raise AssertionError("non-forced voxel removal did not preserve projections")

    return OrthographicUniqueness(
        status="UNIQUE" if not ambiguous else "AMBIGUOUS",
        unique=not ambiguous,
        consistent=True,
        possible_voxels=len(possible),
        forced_voxels=len(forced),
        ambiguous_voxels=len(ambiguous),
        unsupported_projection_pixels=(),
        witness_removed_voxel=witness,
    )


def unique_voxel_solution(top: Mask, front: Mask, right: Mask) -> VoxelGrid:
    result = analyze_orthographic_uniqueness(top, front, right)
    if not result.consistent:
        raise VisualHullError(
            "orthographic silhouettes are inconsistent: "
            + ",".join(result.unsupported_projection_pixels)
        )
    if not result.unique:
        raise VisualHullError(
            f"orthographic occupancy is non-unique; ambiguous_voxels={result.ambiguous_voxels}; "
            f"witness_removed_voxel={result.witness_removed_voxel}"
        )
    return reconstruct_visual_hull(top, front, right)
