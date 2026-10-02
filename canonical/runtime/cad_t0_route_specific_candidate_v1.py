"""Route-specific Brain candidate for the frozen CAD T0 post-refreeze population.

Candidate-visible input is ONLY the public SVG drawing plus declared output schema.
This adapter parses the frozen visible drawing notation, constructs the exact typed
constraint graph, and materializes a CadQuery solid through already-owned M1B
compilers. Hidden reference contracts, geometry metrics, family labels, and oracle
state are never imported or received.

This file is preterminal infrastructure. It does not generate terminal cases.
"""
from __future__ import annotations

import html
import json
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CAD_T0_ROUTE_SPECIFIC_CANDIDATE_V1"


class CandidateError(ValueError):
    pass


def _attr_number(attrs: str, name: str) -> float | None:
    m = re.search(r"\b" + re.escape(name) + r"\s*=\s*[\"']\s*([-+]?[0-9]+(?:\.[0-9]+)?)", attrs, re.I)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _texts(svg: Any) -> list[str]:
    """Reconstruct rendered text lines independently of SVG source-node boundaries."""
    if not isinstance(svg, str) or not svg.strip():
        raise CandidateError("DRAWING_SVG_REQUIRED")

    groups: dict[tuple[str, float | int], list[tuple[float, int, str]]] = {}
    first_seen: dict[tuple[str, float | int], int] = {}
    count = 0
    for m in re.finditer(r"<text\b([^>]*)>(.*?)</text>", svg, flags=re.I | re.S):
        attrs, raw = m.group(1), m.group(2)
        text = html.unescape(re.sub(r"<[^>]+>", "", raw))
        if not text.strip():
            continue
        x = _attr_number(attrs, "x")
        y = _attr_number(attrs, "y")
        key: tuple[str, float | int]
        if y is None:
            key = ("node", count)
        else:
            key = ("y", round(y, 9))
        first_seen.setdefault(key, count)
        groups.setdefault(key, []).append((x if x is not None else float(count), count, text))
        count += 1

    rows: list[str] = []
    for key in sorted(groups, key=lambda k: first_seen[k]):
        fragments = sorted(groups[key], key=lambda row: (row[0], row[1]))
        rendered = "".join(fragment for _, _, fragment in fragments)
        rendered = re.sub(r"\s+", " ", rendered).strip()
        if rendered:
            rows.append(rendered)
    if not rows:
        raise CandidateError("DRAWING_TEXT_EMPTY")
    return rows

def _one(pattern: str, rows: list[str], label: str, flags: int = 0):
    hits = []
    rx = re.compile(pattern, flags)
    for row in rows:
        m = rx.search(row)
        if m:
            hits.append(m)
    if len(hits) != 1:
        raise CandidateError(f"{label}_MATCH_COUNT:{len(hits)}")
    return hits[0]


def _f(s: str) -> float:
    v = float(s)
    if not (v == v and abs(v) != float("inf")):
        raise CandidateError("NONFINITE_NUMBER")
    return v


def _rect_profile(w: float, h: float) -> dict[str, Any]:
    return {
        "kind": "profile_extrude",
        "start": [0.0, 0.0],
        "segments": [
            {"kind": "line", "end": [w, 0.0]},
            {"kind": "line", "end": [w, h]},
            {"kind": "line", "end": [0.0, h]},
            {"kind": "line", "end": [0.0, 0.0]},
        ],
    }


def _graph(family: str, dims: Mapping[str, float], features=None) -> dict[str, Any]:
    return {
        "geometry_family": family,
        "dimensions": {k: float(v) for k, v in sorted(dims.items())},
        "features": list(features or []),
    }


def _exec_source(source: str):
    ns: dict[str, Any] = {}
    exec(compile(source, "<cad-t0-candidate>", "exec"), ns)
    if "result" not in ns:
        raise CandidateError("CAD_SOURCE_DID_NOT_DEFINE_RESULT")
    return ns["result"]


def _build_result(contract: Mapping[str, Any]):
    kind = contract.get("kind")
    if kind in {"spline_revolve", "circle_loft", "polygon_loft"}:
        from canonical.runtime.m1b_smooth_surface_compiler import compile_source

        out = compile_source(contract)
        if out.get("status") != "COMPILED":
            raise CandidateError("SMOOTH_COMPILE_FAILED:" + repr(out.get("errors")))
        return _exec_source(out["source"])

    from canonical.runtime.m1b_continuous_geometry_compiler import compile_contract
    from canonical.runtime.cad_partspec_generator import generate_code

    out = compile_contract(contract)
    if out.get("status") != "COMPILED":
        raise CandidateError("CONTINUOUS_COMPILE_FAILED:" + repr(out.get("errors")))
    return _exec_source(generate_code(out["partspec"]))


def _parse_visible(rows: list[str]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    # Nonidentifiable rectangle must be recognized before ordinary box extrusion.
    if any("DEPTH DIMENSION AND SIDE VIEW INTENTIONALLY ABSENT" in x for x in rows):
        m = _one(
            r"FRONT:\s*rectangle\s+([0-9.]+)\s*mm\s*x\s*([0-9.]+)\s*mm",
            rows,
            "NONIDENT_RECT",
            re.I,
        )
        w, h = map(_f, m.groups())
        candidate = {
            "status": "NONIDENTIFIABLE",
            "constraint_graph": _graph("NONIDENTIFIABLE_DEPTH", {"width": w, "height": h}),
            "ambiguity_witness": {"parameter": "depth_mm", "alternatives": [1.0, 2.0]},
            "terminal_authority": False,
        }
        return candidate, None

    plate_hits = [x for x in rows if x.startswith("PLATE:")]
    if plate_hits:
        m = _one(
            r"PLATE:\s*([0-9.]+)\s*x\s*([0-9.]+)\s*x\s*([0-9.]+)\s*mm",
            rows,
            "PLATE",
            re.I,
        )
        hm = _one(
            r"CENTER THROUGH HOLE:\s*diameter\s*([0-9.]+)\s*mm",
            rows,
            "THROUGH_HOLE",
            re.I,
        )
        w, h, d = map(_f, m.groups())
        dia = _f(hm.group(1))
        x = round(w / 2, 3)
        y = round(h / 2, 3)
        contract = {
            "units": "mm",
            "geometry": {**_rect_profile(w, h), "depth": d},
            "holes": [{"x": x, "y": y, "diameter": dia, "hole_type": "through"}],
            "dimensions": [
                {"name": "overall_width", "nominal": w},
                {"name": "overall_height", "nominal": h},
                {"name": "overall_depth", "nominal": d},
            ],
        }
        graph = _graph(
            "BOX_THROUGH_HOLE",
            {"width": w, "height": h, "depth": d, "hole_diameter": dia},
            [{"kind": "through_hole", "x": x, "y": y, "diameter": dia}],
        )
        return {"status": "SOLID", "constraint_graph": graph, "terminal_authority": False}, contract

    if any(x.startswith("REVOLVE PROFILE:") for x in rows):
        m1 = _one(
            r"REVOLVE PROFILE:\s*segment 1 L=([0-9.]+)\s*mm OD=([0-9.]+)\s*mm",
            rows,
            "REVOLVE_SEGMENT1",
            re.I,
        )
        m2 = _one(
            r"segment 2 ends at Z=([0-9.]+)\s*mm OD=([0-9.]+)\s*mm",
            rows,
            "REVOLVE_SEGMENT2",
            re.I,
        )
        z1, od1 = map(_f, m1.groups())
        z2, od2 = map(_f, m2.groups())
        contract = {
            "units": "mm",
            "geometry": {
                "kind": "revolved_steps",
                "segments": [
                    {"z_start": 0.0, "z_end": z1, "outer_diameter": od1, "inner_diameter": 0.0},
                    {"z_start": z1, "z_end": z2, "outer_diameter": od2, "inner_diameter": 0.0},
                ],
            },
        }
        graph = _graph(
            "REVOLVED_STEPS",
            {"length_1": z1, "length_total": z2, "diameter_1": od1, "diameter_2": od2},
        )
        return {"status": "SOLID", "constraint_graph": graph, "terminal_authority": False}, contract

    if any(x.startswith("SMOOTH REVOLVED PROFILE") for x in rows):
        m = _one(
            r"SMOOTH REVOLVED PROFILE control points \(radius,z\), mm:\s*(\[.*\])$",
            rows,
            "SPLINE_POINTS",
        )
        points = json.loads(m.group(1))
        if not isinstance(points, list) or len(points) < 3:
            raise CandidateError("SPLINE_POINTS_INVALID")
        clean = [[_f(str(p[0])), _f(str(p[1]))] for p in points]
        z_end = clean[-1][1]
        contract = {"kind": "spline_revolve", "radial_axial_points": clean}
        graph = _graph(
            "SPLINE_REVOLVE",
            {"z_end": z_end},
            [{"kind": "spline_revolve_profile", "points": clean}],
        )
        return {"status": "SOLID", "constraint_graph": graph, "terminal_authority": False}, contract

    if any(x.startswith("SMOOTH CIRCULAR LOFT sections") for x in rows):
        m = _one(
            r"SMOOTH CIRCULAR LOFT sections \(z,radius\), mm:\s*(\[.*\])$",
            rows,
            "CIRCLE_LOFT_SECTIONS",
        )
        sections = json.loads(m.group(1))
        clean = [{"z": _f(str(s["z"])), "radius": _f(str(s["radius"]))} for s in sections]
        z_end = clean[-1]["z"]
        contract = {"kind": "circle_loft", "sections": clean}
        graph = _graph(
            "CIRCLE_LOFT",
            {"z_end": z_end},
            [{"kind": "circle_sections", "sections": clean}],
        )
        return {"status": "SOLID", "constraint_graph": graph, "terminal_authority": False}, contract

    if any(x.startswith("POLYGON LOFT section Z=0:") for x in rows):
        m0 = _one(r"POLYGON LOFT section Z=0:\s*(\[.*\])$", rows, "POLYGON_LOFT_Z0")
        m1 = _one(r"^section Z=([0-9.]+):\s*(\[.*\])$", rows, "POLYGON_LOFT_Z1")
        p0 = json.loads(m0.group(1))
        z1 = _f(m1.group(1))
        p1 = json.loads(m1.group(2))
        cp0 = [[_f(str(x)), _f(str(y))] for x, y in p0]
        cp1 = [[_f(str(x)), _f(str(y))] for x, y in p1]
        sections = [{"z": 0.0, "points": cp0}, {"z": z1, "points": cp1}]
        contract = {"kind": "polygon_loft", "sections": sections}
        graph = _graph(
            "POLYGON_LOFT",
            {"z_end": z1},
            [{"kind": "polygon_sections", "sections": sections}],
        )
        return {"status": "SOLID", "constraint_graph": graph, "terminal_authority": False}, contract

    if any(re.search(r"FRONT:\s*circle diameter", x, re.I) for x in rows):
        dm = _one(r"FRONT:\s*circle diameter\s*([0-9.]+)\s*mm", rows, "CIRCLE_DIAMETER", re.I)
        zm = _one(r"DEPTH:\s*([0-9.]+)\s*mm", rows, "CIRCLE_DEPTH", re.I)
        dia, d = _f(dm.group(1)), _f(zm.group(1))
        contract = {
            "units": "mm",
            "geometry": {"kind": "circle_extrude", "diameter": dia, "depth": d},
            "dimensions": [
                {"name": "overall_diameter", "nominal": dia},
                {"name": "overall_depth", "nominal": d},
            ],
        }
        graph = _graph("CIRCLE_EXTRUDE", {"diameter": dia, "depth": d})
        return {"status": "SOLID", "constraint_graph": graph, "terminal_authority": False}, contract

    if any(re.search(r"FRONT:\s*rectangle", x, re.I) for x in rows):
        rm = _one(
            r"FRONT:\s*rectangle\s+([0-9.]+)\s*mm\s*x\s*([0-9.]+)\s*mm",
            rows,
            "BOX_RECT",
            re.I,
        )
        dm = _one(r"DEPTH:\s*([0-9.]+)\s*mm", rows, "BOX_DEPTH", re.I)
        w, h = map(_f, rm.groups())
        d = _f(dm.group(1))
        contract = {
            "units": "mm",
            "geometry": {**_rect_profile(w, h), "depth": d},
            "dimensions": [
                {"name": "overall_width", "nominal": w},
                {"name": "overall_height", "nominal": h},
                {"name": "overall_depth", "nominal": d},
            ],
        }
        graph = _graph("BOX_EXTRUDE", {"width": w, "height": h, "depth": d})
        return {"status": "SOLID", "constraint_graph": graph, "terminal_authority": False}, contract

    raise CandidateError("VISIBLE_DRAWING_PATTERN_UNSUPPORTED")


def solve_with_result(public_case: Mapping[str, Any]):
    if not isinstance(public_case, Mapping):
        raise CandidateError("PUBLIC_CASE_NOT_MAPPING")
    allowed = {"schema", "case_id", "drawing_svg", "declared_output_schema"}
    if "_oracle" in public_case or any(k not in allowed for k in public_case):
        raise CandidateError("NONPUBLIC_FIELD_PRESENT")
    rows = _texts(public_case.get("drawing_svg"))
    candidate, contract = _parse_visible(rows)
    if contract is None:
        return candidate, None
    result = _build_result(contract)
    return candidate, result


def solve(public_case: Mapping[str, Any]) -> dict[str, Any]:
    candidate, _ = solve_with_result(public_case)
    return candidate
