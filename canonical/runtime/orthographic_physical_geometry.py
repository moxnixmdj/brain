"""Exact physical lift of a unique orthographic voxel solution into continuous boxes.

This is a bounded deterministic M1B component. It starts after normalized
orthographic masks and explicit axis dimensions exist. It proves discrete
uniqueness first, converts all dimensions to millimetres, then lifts each forced
voxel cell to a closed-open axis-aligned physical box.

It does not infer curves, blends, hidden features, or missing dimensions.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.orthographic_constraint_graph import compile_constraint_graph
from canonical.runtime.orthographic_uniqueness_gate import unique_voxel_solution

SCHEMA = "BRAIN_ORTHOGRAPHIC_PHYSICAL_GEOMETRY_V1"

_UNIT_TO_MM = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1000.0,
    "in": 25.4,
}


def _axis_scale_mm(graph: Mapping[str, Any], axis: str) -> tuple[int, float]:
    rows = graph.get("axis_scales")
    if not isinstance(rows, list):
        raise ValueError("AXIS_SCALES_MISSING")
    row = next((r for r in rows if isinstance(r, Mapping) and r.get("axis") == axis), None)
    if row is None:
        raise ValueError(f"AXIS_SCALE_MISSING:{axis}")
    cells = row.get("cells")
    extent = row.get("physical_extent")
    units = row.get("units")
    if not isinstance(cells, int) or isinstance(cells, bool) or cells <= 0:
        raise ValueError(f"AXIS_CELLS_INVALID:{axis}")
    if not isinstance(extent, (int, float)) or isinstance(extent, bool) or float(extent) <= 0:
        raise ValueError(f"AXIS_PHYSICAL_EXTENT_REQUIRED:{axis}")
    if units not in _UNIT_TO_MM:
        raise ValueError(f"AXIS_UNITS_UNSUPPORTED:{axis}:{units}")
    return cells, float(extent) * _UNIT_TO_MM[str(units)]


def reconstruct_physical_orthogonal_geometry(
    top: Sequence[Sequence[bool]],
    front: Sequence[Sequence[bool]],
    right: Sequence[Sequence[bool]],
    *,
    dimensions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    graph = compile_constraint_graph(
        top,
        front,
        right,
        dimensions=dimensions,
        features=[],
    )
    if graph.get("status") != "COMPILED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "CONSTRAINT_GRAPH_NOT_COMPILED",
            "graph_errors": graph.get("errors", []),
            "terminal_authority": False,
        }

    try:
        x_cells, x_extent_mm = _axis_scale_mm(graph, "x")
        y_cells, y_extent_mm = _axis_scale_mm(graph, "y")
        z_cells, z_extent_mm = _axis_scale_mm(graph, "z")
        voxels = unique_voxel_solution(top, front, right)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": f"{type(exc).__name__}:{exc}",
            "terminal_authority": False,
        }

    dx = x_extent_mm / x_cells
    dy = y_extent_mm / y_cells
    dz = z_extent_mm / z_cells

    boxes: list[dict[str, float | int]] = []
    for z, slab in enumerate(voxels):
        for y, row in enumerate(slab):
            for x, occupied in enumerate(row):
                if not occupied:
                    continue
                boxes.append({
                    "x_index": x,
                    "y_index": y,
                    "z_index": z,
                    "x0_mm": x * dx,
                    "x1_mm": (x + 1) * dx,
                    "y0_mm": y * dy,
                    "y1_mm": (y + 1) * dy,
                    "z0_mm": z * dz,
                    "z1_mm": (z + 1) * dz,
                })

    cell_volume = dx * dy * dz
    return {
        "schema": SCHEMA,
        "status": "RECONSTRUCTED",
        "geometry_class": "UNIQUE_ORTHOGONAL_CELL_COMPLEX",
        "units": "mm",
        "axis_extents_mm": {
            "x": x_extent_mm,
            "y": y_extent_mm,
            "z": z_extent_mm,
        },
        "cell_size_mm": {"x": dx, "y": dy, "z": dz},
        "occupied_cell_count": len(boxes),
        "volume_mm3": len(boxes) * cell_volume,
        "boxes": boxes,
        "terminal_authority": False,
        "scope": "UNIQUE_DISCRETE_ORTHOGRAPHIC_OCCUPANCY_WITH_EXPLICIT_X_Y_Z_PHYSICAL_EXTENTS",
    }
