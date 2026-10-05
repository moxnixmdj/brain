"""Deterministic static SVG diagram compiler and fail-closed mechanical verifier.

Owns only bounded diagram realization mechanics: typed IR validation, safe SVG
serialization, exact structural round-trip checks, and a real-browser render smoke.
Content selection, layout quality, and presentation quality are explicitly outside scope.
"""
from __future__ import annotations

import math
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
from typing import Any, Mapping
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
SCHEMA = "BRAIN_STATIC_SVG_DIAGRAM_SPEC_V1"
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")
MAX_CANVAS = 4096
MAX_NODES = 128
MAX_EDGES = 256
MAX_LABEL = 512
BROWSER_CANDIDATES = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome")


class DiagramMechanicsError(ValueError):
    pass


def _finite(value: object, name: str, lo: float | None = None, hi: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DiagramMechanicsError(f"{name}:NOT_NUMBER")
    x = float(value)
    if not math.isfinite(x):
        raise DiagramMechanicsError(f"{name}:NONFINITE")
    if lo is not None and x < lo:
        raise DiagramMechanicsError(f"{name}:BELOW_MIN")
    if hi is not None and x > hi:
        raise DiagramMechanicsError(f"{name}:ABOVE_MAX")
    return x


def _id(value: object, name: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise DiagramMechanicsError(f"{name}:INVALID_ID")
    return value


def _label(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_LABEL:
        raise DiagramMechanicsError(f"{name}:INVALID_LABEL")
    if any(ord(ch) < 32 and ch not in "\t\n\r" for ch in value):
        raise DiagramMechanicsError(f"{name}:CONTROL_CHAR")
    return value


def _rows(value: object, name: str, limit: int) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or len(value) > limit:
        raise DiagramMechanicsError(f"{name}:INVALID_LIST")
    out: list[Mapping[str, Any]] = []
    for i, row in enumerate(value):
        if not isinstance(row, Mapping):
            raise DiagramMechanicsError(f"{name}[{i}]:NOT_MAPPING")
        out.append(row)
    return out


def normalize_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, Mapping) or spec.get("schema") != SCHEMA:
        raise DiagramMechanicsError("SPEC:WRONG_SCHEMA")
    canvas = spec.get("canvas")
    if not isinstance(canvas, Mapping):
        raise DiagramMechanicsError("CANVAS:NOT_MAPPING")
    width = _finite(canvas.get("width"), "CANVAS_WIDTH", 1, MAX_CANVAS)
    height = _finite(canvas.get("height"), "CANVAS_HEIGHT", 1, MAX_CANVAS)
    nodes_raw = _rows(spec.get("nodes"), "NODES", MAX_NODES)
    edges_raw = _rows(spec.get("edges"), "EDGES", MAX_EDGES)
    if not nodes_raw:
        raise DiagramMechanicsError("NODES:EMPTY")

    nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    for i, row in enumerate(nodes_raw):
        nid = _id(row.get("id"), f"NODES[{i}].ID")
        if nid in node_ids:
            raise DiagramMechanicsError(f"NODES[{i}].ID:DUPLICATE")
        node_ids.add(nid)
        shape = row.get("shape", "rect")
        if shape not in {"rect", "ellipse"}:
            raise DiagramMechanicsError(f"NODES[{i}].SHAPE:UNSUPPORTED")
        x = _finite(row.get("x"), f"NODES[{i}].X", 0, width)
        y = _finite(row.get("y"), f"NODES[{i}].Y", 0, height)
        w = _finite(row.get("width"), f"NODES[{i}].WIDTH", 1, width)
        h = _finite(row.get("height"), f"NODES[{i}].HEIGHT", 1, height)
        if x + w > width or y + h > height:
            raise DiagramMechanicsError(f"NODES[{i}]:OUTSIDE_CANVAS")
        nodes.append({"id": nid, "label": _label(row.get("label"), f"NODES[{i}].LABEL"),
                      "shape": shape, "x": x, "y": y, "width": w, "height": h})

    edges: list[dict[str, Any]] = []
    edge_ids: set[str] = set()
    for i, row in enumerate(edges_raw):
        eid = _id(row.get("id"), f"EDGES[{i}].ID")
        if eid in edge_ids or eid in node_ids:
            raise DiagramMechanicsError(f"EDGES[{i}].ID:DUPLICATE")
        edge_ids.add(eid)
        source = _id(row.get("source"), f"EDGES[{i}].SOURCE")
        target = _id(row.get("target"), f"EDGES[{i}].TARGET")
        if source not in node_ids or target not in node_ids:
            raise DiagramMechanicsError(f"EDGES[{i}]:UNKNOWN_ENDPOINT")
        if source == target:
            raise DiagramMechanicsError(f"EDGES[{i}]:SELF_EDGE_UNSUPPORTED")
        label = row.get("label")
        edges.append({"id": eid, "source": source, "target": target,
                      "label": None if label is None else _label(label, f"EDGES[{i}].LABEL")})
    return {"schema": SCHEMA, "canvas": {"width": width, "height": height}, "nodes": nodes, "edges": edges}


def _fmt(x: float) -> str:
    return str(int(x)) if x.is_integer() else format(x, ".12g")


def _center(node: Mapping[str, Any]) -> tuple[float, float]:
    return float(node["x"]) + float(node["width"]) / 2, float(node["y"]) + float(node["height"]) / 2


def compile_svg(spec: Mapping[str, Any]) -> str:
    s = normalize_spec(spec)
    width, height = s["canvas"]["width"], s["canvas"]["height"]
    root = ET.Element(f"{{{SVG_NS}}}svg", {"width": _fmt(width), "height": _fmt(height),
        "viewBox": f"0 0 {_fmt(width)} {_fmt(height)}", "role": "img", "data-brain-diagram-schema": SCHEMA})
    title = ET.SubElement(root, f"{{{SVG_NS}}}title"); title.text = "Brain generated diagram"
    defs = ET.SubElement(root, f"{{{SVG_NS}}}defs")
    marker = ET.SubElement(defs, f"{{{SVG_NS}}}marker", {"id": "brain-arrowhead", "viewBox": "0 0 10 10",
        "refX": "9", "refY": "5", "markerWidth": "6", "markerHeight": "6", "orient": "auto-start-reverse"})
    ET.SubElement(marker, f"{{{SVG_NS}}}path", {"d": "M 0 0 L 10 5 L 0 10 z"})
    by_id = {n["id"]: n for n in s["nodes"]}
    edges = ET.SubElement(root, f"{{{SVG_NS}}}g", {"id": "brain-edges"})
    for edge in s["edges"]:
        x1, y1 = _center(by_id[edge["source"]]); x2, y2 = _center(by_id[edge["target"]])
        g = ET.SubElement(edges, f"{{{SVG_NS}}}g", {"id": f"edge-{edge['id']}", "data-edge-id": edge["id"],
            "data-source": edge["source"], "data-target": edge["target"]})
        ET.SubElement(g, f"{{{SVG_NS}}}line", {"x1": _fmt(x1), "y1": _fmt(y1), "x2": _fmt(x2), "y2": _fmt(y2),
            "stroke": "currentColor", "stroke-width": "2", "marker-end": "url(#brain-arrowhead)"})
        if edge["label"] is not None:
            t = ET.SubElement(g, f"{{{SVG_NS}}}text", {"x": _fmt((x1+x2)/2), "y": _fmt((y1+y2)/2-4),
                "text-anchor": "middle", "data-role": "edge-label"}); t.text = edge["label"]
    nodes = ET.SubElement(root, f"{{{SVG_NS}}}g", {"id": "brain-nodes"})
    for node in s["nodes"]:
        g = ET.SubElement(nodes, f"{{{SVG_NS}}}g", {"id": f"node-{node['id']}", "data-node-id": node["id"], "data-shape": node["shape"]})
        cx, cy = _center(node)
        if node["shape"] == "rect":
            ET.SubElement(g, f"{{{SVG_NS}}}rect", {"x": _fmt(node["x"]), "y": _fmt(node["y"]), "width": _fmt(node["width"]),
                "height": _fmt(node["height"]), "rx": "6", "fill": "white", "stroke": "currentColor", "stroke-width": "2"})
        else:
            ET.SubElement(g, f"{{{SVG_NS}}}ellipse", {"cx": _fmt(cx), "cy": _fmt(cy), "rx": _fmt(node["width"]/2),
                "ry": _fmt(node["height"]/2), "fill": "white", "stroke": "currentColor", "stroke-width": "2"})
        t = ET.SubElement(g, f"{{{SVG_NS}}}text", {"x": _fmt(cx), "y": _fmt(cy), "text-anchor": "middle",
            "dominant-baseline": "middle", "data-role": "node-label"}); t.text = node["label"]
    return ET.tostring(root, encoding="unicode")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def validate_svg(svg: str, spec: Mapping[str, Any]) -> dict[str, Any]:
    expected = normalize_spec(spec)
    try: root = ET.fromstring(svg)
    except Exception as exc: return {"pass": False, "reason": "XML_PARSE", "error": type(exc).__name__}
    if root.tag != f"{{{SVG_NS}}}svg" or root.get("data-brain-diagram-schema") != SCHEMA:
        return {"pass": False, "reason": "ROOT_OR_SCHEMA_MISMATCH"}
    w, h = _fmt(expected["canvas"]["width"]), _fmt(expected["canvas"]["height"])
    if root.get("width") != w or root.get("height") != h or root.get("viewBox") != f"0 0 {w} {h}":
        return {"pass": False, "reason": "CANVAS_MISMATCH"}
    ids: dict[str, ET.Element] = {}; refs: list[str] = []
    for elem in root.iter():
        local = _local(elem.tag)
        if local in {"script", "foreignObject", "iframe", "object", "embed"}:
            return {"pass": False, "reason": "DISALLOWED_TAG", "tag": local}
        eid = elem.get("id")
        if eid is not None:
            if eid in ids: return {"pass": False, "reason": "DUPLICATE_ID", "id": eid}
            ids[eid] = elem
        for key, value in elem.attrib.items():
            k = _local(key).lower()
            if k.startswith("on"): return {"pass": False, "reason": "EVENT_ATTRIBUTE", "attribute": k}
            if k in {"href", "src"}:
                if not value.startswith("#"): return {"pass": False, "reason": "EXTERNAL_REFERENCE", "value": value}
                refs.append(value[1:])
            refs.extend(m.group(1) for m in re.finditer(r"url\(\s*#([A-Za-z][A-Za-z0-9_.:-]*)\s*\)", value))
    unresolved = sorted({r for r in refs if r not in ids})
    if unresolved: return {"pass": False, "reason": "UNRESOLVED_FRAGMENT_REFERENCE", "refs": unresolved}
    for node in expected["nodes"]:
        g = ids.get(f"node-{node['id']}")
        if g is None or g.get("data-node-id") != node["id"] or g.get("data-shape") != node["shape"]:
            return {"pass": False, "reason": "NODE_GROUP_MISMATCH", "node": node["id"]}
        labels = [e for e in g.iter() if _local(e.tag)=="text" and e.get("data-role")=="node-label"]
        if len(labels)!=1 or (labels[0].text or "") != node["label"]:
            return {"pass": False, "reason": "NODE_LABEL_MISMATCH", "node": node["id"]}
    for edge in expected["edges"]:
        g = ids.get(f"edge-{edge['id']}")
        if g is None or g.get("data-edge-id") != edge["id"] or g.get("data-source") != edge["source"] or g.get("data-target") != edge["target"]:
            return {"pass": False, "reason": "EDGE_RELATION_MISMATCH", "edge": edge["id"]}
        lines = [e for e in g.iter() if _local(e.tag)=="line"]
        if len(lines)!=1 or lines[0].get("marker-end")!="url(#brain-arrowhead)":
            return {"pass": False, "reason": "EDGE_LINE_MISMATCH", "edge": edge["id"]}
        labels = [e for e in g.iter() if _local(e.tag)=="text" and e.get("data-role")=="edge-label"]
        if edge["label"] is None and labels: return {"pass": False, "reason": "UNEXPECTED_EDGE_LABEL", "edge": edge["id"]}
        if edge["label"] is not None and (len(labels)!=1 or (labels[0].text or "")!=edge["label"]):
            return {"pass": False, "reason": "EDGE_LABEL_MISMATCH", "edge": edge["id"]}
    try: ET.fromstring(ET.tostring(root, encoding="utf-8"))
    except Exception as exc: return {"pass": False, "reason": "ROUNDTRIP_PARSE", "error": type(exc).__name__}
    return {"pass": True, "reason": "PASS", "node_count": len(expected["nodes"]), "edge_count": len(expected["edges"]),
            "resolved_fragment_reference_count": len(refs)}


def _png_dimensions(payload: bytes) -> tuple[int, int]:
    if len(payload) < 24 or payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[12:16] != b"IHDR":
        raise DiagramMechanicsError("SCREENSHOT:NOT_PNG")
    return struct.unpack(">II", payload[16:24])


def find_browser() -> str | None:
    return next((p for n in BROWSER_CANDIDATES if (p := shutil.which(n))), None)


def browser_render_smoke(svg: str, spec: Mapping[str, Any], browser: str | None = None) -> dict[str, Any]:
    expected = normalize_spec(spec); browser = browser or find_browser()
    if not browser: return {"pass": False, "reason": "BROWSER_RUNTIME_MISSING"}
    width, height = int(math.ceil(expected["canvas"]["width"])), int(math.ceil(expected["canvas"]["height"]))
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); src = root/"diagram.svg"; png = root/"diagram.png"; src.write_text(svg, encoding="utf-8")
        cmd = [browser, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
               f"--window-size={width},{height}", f"--screenshot={png}", src.resolve().as_uri()]
        try: proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=45)
        except Exception as exc: return {"pass": False, "reason": "BROWSER_EXCEPTION", "error": type(exc).__name__}
        if proc.returncode != 0 or not png.is_file():
            return {"pass": False, "reason": "BROWSER_RENDER_FAILED", "returncode": proc.returncode, "stderr_tail": (proc.stderr or "")[-500:]}
        payload = png.read_bytes()
        try: got = _png_dimensions(payload)
        except DiagramMechanicsError as exc: return {"pass": False, "reason": str(exc)}
        if got[0] < width or got[1] < height:
            return {"pass": False, "reason": "SCREENSHOT_TOO_SMALL", "expected_min": [width,height], "actual": list(got)}
        return {"pass": True, "reason": "PASS", "browser": Path(browser).name, "screenshot_dimensions": list(got), "screenshot_bytes": len(payload)}


def verify_mechanics(spec: Mapping[str, Any], require_browser: bool = True, browser: str | None = None) -> dict[str, Any]:
    try: svg = compile_svg(spec)
    except Exception as exc: return {"pass": False, "reason": "COMPILE_FAILED", "error": type(exc).__name__+":"+str(exc)}
    structural = validate_svg(svg, spec)
    if not structural.get("pass"): return {"pass": False, "reason": "STRUCTURAL_FAILED", "structural": structural}
    if require_browser:
        render = browser_render_smoke(svg, spec, browser=browser)
        if not render.get("pass"):
            return {"pass": False, "reason": "RENDER_FAILED", "structural": structural, "render": render}
    else:
        render = {"pass": None, "reason": "BROWSER_NOT_REQUESTED__NO_RENDER_CREDIT"}
    return {"pass": True, "reason": "PASS", "structural": structural, "render": render, "svg": svg,
            "terminal_authority": False, "capability_credit_delta": 0}
