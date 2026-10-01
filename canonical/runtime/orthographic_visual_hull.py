"""Deterministic orthographic visual-hull reconstruction and acceptance primitives.

This module deliberately solves only the global-shape part of engineering-drawing
interpretation. It consumes normalized binary silhouettes for top/front/right
orthographic views and reconstructs the maximal voxel solid consistent with all three.

Coordinate convention:
    top[y][x]   -> XY occupancy observed from +Z
    front[z][x] -> XZ occupancy
    right[z][y] -> YZ occupancy

The reconstructed voxel grid is voxels[z][y][x]. A voxel is possible iff all three
orthographic silhouettes permit it. This is a visual hull: it is intentionally a
conservative geometric prior and cannot recover concavities invisible in every supplied
silhouette. That limitation is explicit so callers cannot mistake it for full CAD truth.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

Mask = Sequence[Sequence[bool | int]]
VoxelGrid = list[list[list[bool]]]


class VisualHullError(ValueError):
    pass


@dataclass(frozen=True)
class HullSignature:
    x_cells: int
    y_cells: int
    z_cells: int
    occupied_voxels: int
    exposed_faces: int
    connected_components: int
    bbox_cells: tuple[int, int, int] | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class MaskComparison:
    intersection: int
    union: int
    source_pixels: int
    candidate_pixels: int
    iou: float
    source_miss_rate: float
    candidate_overbuild_rate: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class OrthographicAcceptance:
    passed: bool
    top: MaskComparison
    front: MaskComparison
    right: MaskComparison
    source_hull: HullSignature
    candidate_hull: HullSignature
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "top": self.top.to_dict(),
            "front": self.front.to_dict(),
            "right": self.right.to_dict(),
            "source_hull": self.source_hull.to_dict(),
            "candidate_hull": self.candidate_hull.to_dict(),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class RepairRegion:
    operation: str
    voxel_count: int
    bbox_min: tuple[int, int, int]
    bbox_max_exclusive: tuple[int, int, int]
    bbox_volume: int
    fill_ratio: float
    rectangular: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _normalize_mask(mask: Mask, name: str) -> list[list[bool]]:
    rows = [list(map(bool, row)) for row in mask]
    if not rows or not rows[0]:
        raise VisualHullError(f"{name} mask must be non-empty")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise VisualHullError(f"{name} mask must be rectangular")
    return rows


def _validate_triplet(
    top: Mask, front: Mask, right: Mask
) -> tuple[list[list[bool]], list[list[bool]], list[list[bool]]]:
    t = _normalize_mask(top, "top")
    f = _normalize_mask(front, "front")
    r = _normalize_mask(right, "right")
    y_cells, x_cells = len(t), len(t[0])
    z_cells, front_x = len(f), len(f[0])
    right_z, right_y = len(r), len(r[0])
    if front_x != x_cells:
        raise VisualHullError(
            f"top/front x dimension mismatch: top={x_cells}, front={front_x}"
        )
    if right_z != z_cells:
        raise VisualHullError(
            f"front/right z dimension mismatch: front={z_cells}, right={right_z}"
        )
    if right_y != y_cells:
        raise VisualHullError(
            f"top/right y dimension mismatch: top={y_cells}, right={right_y}"
        )
    return t, f, r


def reconstruct_visual_hull(top: Mask, front: Mask, right: Mask) -> VoxelGrid:
    """Return the maximal voxel occupancy consistent with three silhouettes."""
    t, f, r = _validate_triplet(top, front, right)
    y_cells, x_cells = len(t), len(t[0])
    z_cells = len(f)
    return [
        [
            [bool(t[y][x] and f[z][x] and r[z][y]) for x in range(x_cells)]
            for y in range(y_cells)
        ]
        for z in range(z_cells)
    ]


def project_visual_hull(
    voxels: VoxelGrid,
) -> tuple[list[list[bool]], list[list[bool]], list[list[bool]]]:
    """Project voxels back to (top, front, right) binary silhouettes."""
    if not voxels or not voxels[0] or not voxels[0][0]:
        raise VisualHullError("voxel grid must be non-empty")
    z_cells = len(voxels)
    y_cells = len(voxels[0])
    x_cells = len(voxels[0][0])
    for slab in voxels:
        if len(slab) != y_cells or any(len(row) != x_cells for row in slab):
            raise VisualHullError("voxel grid must be rectangular")
    top = [
        [any(voxels[z][y][x] for z in range(z_cells)) for x in range(x_cells)]
        for y in range(y_cells)
    ]
    front = [
        [any(voxels[z][y][x] for y in range(y_cells)) for x in range(x_cells)]
        for z in range(z_cells)
    ]
    right = [
        [any(voxels[z][y][x] for x in range(x_cells)) for y in range(y_cells)]
        for z in range(z_cells)
    ]
    return top, front, right


def _occupied(voxels: VoxelGrid) -> Iterable[tuple[int, int, int]]:
    for z, slab in enumerate(voxels):
        for y, row in enumerate(slab):
            for x, value in enumerate(row):
                if value:
                    yield x, y, z


def hull_signature(voxels: VoxelGrid) -> HullSignature:
    if not voxels or not voxels[0] or not voxels[0][0]:
        raise VisualHullError("voxel grid must be non-empty")
    z_cells, y_cells, x_cells = len(voxels), len(voxels[0]), len(voxels[0][0])
    occ = set(_occupied(voxels))
    if not occ:
        return HullSignature(x_cells, y_cells, z_cells, 0, 0, 0, None)
    xs = [p[0] for p in occ]
    ys = [p[1] for p in occ]
    zs = [p[2] for p in occ]
    bbox = (
        max(xs) - min(xs) + 1,
        max(ys) - min(ys) + 1,
        max(zs) - min(zs) + 1,
    )
    nbrs = (
        (1, 0, 0),
        (-1, 0, 0),
        (0, 1, 0),
        (0, -1, 0),
        (0, 0, 1),
        (0, 0, -1),
    )
    exposed = 0
    for x, y, z in occ:
        for dx, dy, dz in nbrs:
            if (x + dx, y + dy, z + dz) not in occ:
                exposed += 1
    remaining = set(occ)
    components = 0
    while remaining:
        components += 1
        start = remaining.pop()
        queue = deque([start])
        while queue:
            x, y, z = queue.popleft()
            for dx, dy, dz in nbrs:
                nxt = (x + dx, y + dy, z + dz)
                if nxt in remaining:
                    remaining.remove(nxt)
                    queue.append(nxt)
    return HullSignature(
        x_cells=x_cells,
        y_cells=y_cells,
        z_cells=z_cells,
        occupied_voxels=len(occ),
        exposed_faces=exposed,
        connected_components=components,
        bbox_cells=bbox,
    )


def compare_masks(source: Mask, candidate: Mask, name: str = "mask") -> MaskComparison:
    s = _normalize_mask(source, f"source {name}")
    c = _normalize_mask(candidate, f"candidate {name}")
    if len(s) != len(c) or len(s[0]) != len(c[0]):
        raise VisualHullError(
            f"{name} dimensions differ: source={len(s)}x{len(s[0])}, "
            f"candidate={len(c)}x{len(c[0])}"
        )
    intersection = union = src_n = cand_n = 0
    missed = over = 0
    for sr, cr in zip(s, c):
        for sv, cv in zip(sr, cr):
            src_n += int(sv)
            cand_n += int(cv)
            intersection += int(sv and cv)
            union += int(sv or cv)
            missed += int(sv and not cv)
            over += int(cv and not sv)
    iou = 1.0 if union == 0 else intersection / union
    miss_rate = 0.0 if src_n == 0 else missed / src_n
    over_rate = 0.0 if cand_n == 0 else over / cand_n
    return MaskComparison(
        intersection,
        union,
        src_n,
        cand_n,
        iou,
        miss_rate,
        over_rate,
    )


def accept_candidate_orthographic_shape(
    source_top: Mask,
    source_front: Mask,
    source_right: Mask,
    candidate_top: Mask,
    candidate_front: Mask,
    candidate_right: Mask,
    *,
    min_iou: float = 0.97,
    max_miss_rate: float = 0.02,
    max_overbuild_rate: float = 0.02,
    max_hull_occupancy_rel_error: float = 0.03,
    max_hull_surface_rel_error: float = 0.05,
) -> OrthographicAcceptance:
    """Fail-closed comparison of a candidate's projections to drawing silhouettes."""
    for label, value in (
        ("min_iou", min_iou),
        ("max_miss_rate", max_miss_rate),
        ("max_overbuild_rate", max_overbuild_rate),
        ("max_hull_occupancy_rel_error", max_hull_occupancy_rel_error),
        ("max_hull_surface_rel_error", max_hull_surface_rel_error),
    ):
        if not 0.0 <= value <= 1.0:
            raise VisualHullError(f"{label} must be within [0,1]")
    st, sf, sr = _validate_triplet(source_top, source_front, source_right)
    ct, cf, cr = _validate_triplet(candidate_top, candidate_front, candidate_right)
    if (len(st), len(st[0]), len(sf)) != (len(ct), len(ct[0]), len(cf)):
        raise VisualHullError("source/candidate orthographic grids differ")
    top_cmp = compare_masks(st, ct, "top")
    front_cmp = compare_masks(sf, cf, "front")
    right_cmp = compare_masks(sr, cr, "right")
    source_sig = hull_signature(reconstruct_visual_hull(st, sf, sr))
    cand_sig = hull_signature(reconstruct_visual_hull(ct, cf, cr))
    reasons: list[str] = []
    for view_name, cmp in (
        ("top", top_cmp),
        ("front", front_cmp),
        ("right", right_cmp),
    ):
        if cmp.iou < min_iou:
            reasons.append(f"{view_name}_iou={cmp.iou:.6f}<{min_iou:.6f}")
        if cmp.source_miss_rate > max_miss_rate:
            reasons.append(
                f"{view_name}_miss_rate={cmp.source_miss_rate:.6f}>"
                f"{max_miss_rate:.6f}"
            )
        if cmp.candidate_overbuild_rate > max_overbuild_rate:
            reasons.append(
                f"{view_name}_overbuild_rate={cmp.candidate_overbuild_rate:.6f}>"
                f"{max_overbuild_rate:.6f}"
            )
    if source_sig.connected_components != cand_sig.connected_components:
        reasons.append(
            f"visual_hull_components={cand_sig.connected_components}!="
            f"{source_sig.connected_components}"
        )
    if source_sig.bbox_cells != cand_sig.bbox_cells:
        reasons.append(
            f"visual_hull_bbox={cand_sig.bbox_cells}!={source_sig.bbox_cells}"
        )

    def rel_error(actual: int, expected: int) -> float:
        if expected == 0:
            return 0.0 if actual == 0 else 1.0
        return abs(actual - expected) / expected

    occ_err = rel_error(cand_sig.occupied_voxels, source_sig.occupied_voxels)
    surf_err = rel_error(cand_sig.exposed_faces, source_sig.exposed_faces)
    if occ_err > max_hull_occupancy_rel_error:
        reasons.append(
            f"visual_hull_occupancy_rel_error={occ_err:.6f}>"
            f"{max_hull_occupancy_rel_error:.6f}"
        )
    if surf_err > max_hull_surface_rel_error:
        reasons.append(
            f"visual_hull_surface_rel_error={surf_err:.6f}>"
            f"{max_hull_surface_rel_error:.6f}"
        )
    return OrthographicAcceptance(
        passed=not reasons,
        top=top_cmp,
        front=front_cmp,
        right=right_cmp,
        source_hull=source_sig,
        candidate_hull=cand_sig,
        reasons=tuple(reasons),
    )


def _component_regions(
    points: set[tuple[int, int, int]], operation: str
) -> list[RepairRegion]:
    nbrs = (
        (1, 0, 0),
        (-1, 0, 0),
        (0, 1, 0),
        (0, -1, 0),
        (0, 0, 1),
        (0, 0, -1),
    )
    remaining = set(points)
    regions: list[RepairRegion] = []
    while remaining:
        start = remaining.pop()
        comp = {start}
        queue = deque([start])
        while queue:
            x, y, z = queue.popleft()
            for dx, dy, dz in nbrs:
                nxt = (x + dx, y + dy, z + dz)
                if nxt in remaining:
                    remaining.remove(nxt)
                    comp.add(nxt)
                    queue.append(nxt)
        xs = [p[0] for p in comp]
        ys = [p[1] for p in comp]
        zs = [p[2] for p in comp]
        lo = (min(xs), min(ys), min(zs))
        hi = (max(xs) + 1, max(ys) + 1, max(zs) + 1)
        bbox_volume = (
            (hi[0] - lo[0])
            * (hi[1] - lo[1])
            * (hi[2] - lo[2])
        )
        fill = len(comp) / bbox_volume
        regions.append(
            RepairRegion(
                operation=operation,
                voxel_count=len(comp),
                bbox_min=lo,
                bbox_max_exclusive=hi,
                bbox_volume=bbox_volume,
                fill_ratio=fill,
                rectangular=(len(comp) == bbox_volume),
            )
        )
    regions.sort(key=lambda r: (-r.voxel_count, r.operation, r.bbox_min))
    return regions


def infer_visual_hull_repairs(
    source_top: Mask,
    source_front: Mask,
    source_right: Mask,
    candidate_top: Mask,
    candidate_front: Mask,
    candidate_right: Mask,
) -> list[RepairRegion]:
    """Infer coarse 3D add/cut regions from source-vs-candidate visual hulls."""
    st, sf, sr = _validate_triplet(source_top, source_front, source_right)
    ct, cf, cr = _validate_triplet(candidate_top, candidate_front, candidate_right)
    if (len(st), len(st[0]), len(sf)) != (len(ct), len(ct[0]), len(cf)):
        raise VisualHullError("source/candidate orthographic grids differ")
    source = set(_occupied(reconstruct_visual_hull(st, sf, sr)))
    candidate = set(_occupied(reconstruct_visual_hull(ct, cf, cr)))
    underbuilt = source - candidate
    overbuilt = candidate - source
    return _component_regions(underbuilt, "add") + _component_regions(
        overbuilt, "cut"
    )


def compile_rectangular_repairs_to_body_payloads(
    regions: Sequence[RepairRegion],
    *,
    cell_size: tuple[float, float, float],
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> tuple[list[dict], list[dict]]:
    """Compile proven-full rectangular repair regions to cad_partspec.Body payloads.

    Non-rectangular regions remain unresolved rather than being approximated by their
    bounding boxes. This prevents the repair compiler from inventing material/voids that
    were not justified by the visual-hull difference.
    """
    sx, sy, sz = cell_size
    if sx <= 0 or sy <= 0 or sz <= 0:
        raise VisualHullError("cell_size components must be positive")
    ox, oy, oz = origin
    bodies: list[dict] = []
    unresolved: list[dict] = []
    for region in regions:
        if region.operation not in ("add", "cut"):
            raise VisualHullError(f"unknown repair operation: {region.operation}")
        if not region.rectangular:
            unresolved.append({
                "reason": "NON_RECTANGULAR_REPAIR_REGION",
                "region": region.to_dict(),
            })
            continue
        x0, y0, z0 = region.bbox_min
        x1, y1, z1 = region.bbox_max_exclusive
        bodies.append({
            "shape": "box",
            "operation": region.operation,
            "x": ox + x0 * sx,
            "y": oy + y0 * sy,
            "z": oz + z0 * sz,
            "dx": (x1 - x0) * sx,
            "dy": (y1 - y0) * sy,
            "dz": (z1 - z0) * sz,
        })
    return bodies, unresolved
