"""Compile normalized orthographic views and explicit callouts into a typed constraint graph.

This module deliberately starts *after* raw drawing recognition/OCR. It removes a
deterministic slice of M1A by turning already-normalized silhouettes and explicit
dimension/feature callouts into a machine-checkable graph with cross-view consistency
and fail-closed conflict handling.

It does not claim raw image understanding or hidden-geometry inference.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from canonical.runtime.orthographic_visual_hull import Mask, _validate_triplet

SCHEMA = "BRAIN_ORTHOGRAPHIC_CONSTRAINT_GRAPH_V1"


@dataclass(frozen=True)
class AxisScale:
    axis: str
    cells: int
    physical_extent: float | None
    units: str | None
    cell_size: float | None


@dataclass(frozen=True)
class ConstraintGraph:
    schema: str
    status: str
    x_cells: int
    y_cells: int
    z_cells: int
    axis_scales: tuple[AxisScale, ...]
    silhouette_constraints: tuple[dict[str, Any], ...]
    explicit_features: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["axis_scales"] = [asdict(x) for x in self.axis_scales]
        out["silhouette_constraints"] = list(self.silhouette_constraints)
        out["explicit_features"] = list(self.explicit_features)
        out["errors"] = list(self.errors)
        return out


def _normalize_dimensions(
    dimensions: Sequence[Mapping[str, Any]] | None,
    counts: dict[str, int],
) -> tuple[tuple[AxisScale, ...], list[str]]:
    rows = list(dimensions or [])
    errors: list[str] = []
    by_axis: dict[str, tuple[float, str]] = {}

    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"DIMENSION_NOT_OBJECT:{i}")
            continue
        axis = row.get("axis")
        value = row.get("value")
        units = row.get("units", "mm")
        if axis not in {"x", "y", "z"}:
            errors.append(f"DIMENSION_AXIS_INVALID:{i}")
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            errors.append(f"DIMENSION_VALUE_INVALID:{i}:{axis}")
            continue
        if not isinstance(units, str) or not units.strip():
            errors.append(f"DIMENSION_UNITS_INVALID:{i}:{axis}")
            continue
        pair = (float(value), units.strip())
        prior = by_axis.get(axis)
        if prior is not None and prior != pair:
            errors.append(f"DIMENSION_CONFLICT:{axis}:{prior[0]}:{pair[0]}")
            continue
        by_axis[axis] = pair

    scales: list[AxisScale] = []
    for axis in ("x", "y", "z"):
        if axis in by_axis:
            extent, units = by_axis[axis]
            scales.append(
                AxisScale(
                    axis=axis,
                    cells=counts[axis],
                    physical_extent=extent,
                    units=units,
                    cell_size=extent / counts[axis],
                )
            )
        else:
            scales.append(
                AxisScale(
                    axis=axis,
                    cells=counts[axis],
                    physical_extent=None,
                    units=None,
                    cell_size=None,
                )
            )
    return tuple(scales), errors


def _normalize_features(
    features: Sequence[Mapping[str, Any]] | None,
) -> tuple[tuple[dict[str, Any], ...], list[str]]:
    rows = list(features or [])
    out: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"FEATURE_NOT_OBJECT:{i}")
            continue
        fid = row.get("id")
        kind = row.get("kind")
        if not isinstance(fid, str) or not fid.strip():
            errors.append(f"FEATURE_ID_INVALID:{i}")
            continue
        if fid in seen:
            errors.append(f"FEATURE_ID_DUPLICATE:{fid}")
            continue
        seen.add(fid)
        if kind not in {"hole", "slot", "cut", "boss", "fillet", "chamfer", "thread", "generic"}:
            errors.append(f"FEATURE_KIND_UNSUPPORTED:{fid}:{kind}")
            continue
        normalized = {"id": fid, "kind": kind}
        for key, value in sorted(row.items()):
            if key in {"id", "kind"}:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                normalized[key] = value
            else:
                errors.append(f"FEATURE_FIELD_UNSUPPORTED:{fid}:{key}")
        out.append(normalized)
    return tuple(out), errors


def compile_constraint_graph(
    top: Mask,
    front: Mask,
    right: Mask,
    *,
    dimensions: Sequence[Mapping[str, Any]] | None = None,
    features: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    try:
        t, f, r = _validate_triplet(top, front, right)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [f"VIEW_TRIPLET_INVALID:{type(exc).__name__}:{exc}"],
        }

    y_cells, x_cells = len(t), len(t[0])
    z_cells = len(f)
    counts = {"x": x_cells, "y": y_cells, "z": z_cells}

    scales, dim_errors = _normalize_dimensions(dimensions, counts)
    feats, feature_errors = _normalize_features(features)
    errors = dim_errors + feature_errors

    constraints: list[dict[str, Any]] = []
    for y, row in enumerate(t):
        for x, occupied in enumerate(row):
            constraints.append({
                "view": "top",
                "coordinates": {"x": x, "y": y},
                "ray_axis": "z",
                "occupied": bool(occupied),
            })
    for z, row in enumerate(f):
        for x, occupied in enumerate(row):
            constraints.append({
                "view": "front",
                "coordinates": {"x": x, "z": z},
                "ray_axis": "y",
                "occupied": bool(occupied),
            })
    for z, row in enumerate(r):
        for y, occupied in enumerate(row):
            constraints.append({
                "view": "right",
                "coordinates": {"y": y, "z": z},
                "ray_axis": "x",
                "occupied": bool(occupied),
            })

    if errors:
        return ConstraintGraph(
            schema=SCHEMA,
            status="FAIL_CLOSED",
            x_cells=x_cells,
            y_cells=y_cells,
            z_cells=z_cells,
            axis_scales=scales,
            silhouette_constraints=tuple(constraints),
            explicit_features=feats,
            errors=tuple(sorted(set(errors))),
        ).to_dict()

    return ConstraintGraph(
        schema=SCHEMA,
        status="COMPILED",
        x_cells=x_cells,
        y_cells=y_cells,
        z_cells=z_cells,
        axis_scales=scales,
        silhouette_constraints=tuple(constraints),
        explicit_features=feats,
        errors=(),
    ).to_dict()
