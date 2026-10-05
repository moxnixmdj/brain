"""Real-engine render oracle for Brain static SVG diagram mechanics.

A static structural parser cannot establish renderability. This oracle requires an
installed SVG rendering engine (librsvg or Inkscape), renders the exact compiled SVG
to PNG, and verifies the output dimensions. Missing engines fail closed.
"""
from __future__ import annotations

import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
from typing import Any, Mapping

from canonical.runtime import html_svg_diagram_mechanics_v1 as mechanics

RENDERER_CANDIDATES = ("rsvg-convert", "inkscape")


def find_renderer() -> tuple[str, str] | None:
    for name in RENDERER_CANDIDATES:
        path = shutil.which(name)
        if path:
            return name, path
    return None


def _png_dimensions(payload: bytes) -> tuple[int, int]:
    if len(payload) < 24 or payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[12:16] != b"IHDR":
        raise ValueError("NOT_PNG")
    return struct.unpack(">II", payload[16:24])


def render_smoke(svg: str, spec: Mapping[str, Any], renderer: tuple[str, str] | None = None) -> dict[str, Any]:
    expected = mechanics.normalize_spec(spec)
    renderer = renderer or find_renderer()
    if renderer is None:
        return {"pass": False, "reason": "SVG_RENDERER_RUNTIME_MISSING"}
    kind, executable = renderer
    width = int(math.ceil(expected["canvas"]["width"]))
    height = int(math.ceil(expected["canvas"]["height"]))
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        src = root / "diagram.svg"
        png = root / "diagram.png"
        src.write_text(svg, encoding="utf-8")
        if kind == "rsvg-convert":
            cmd = [executable, "-o", str(png), str(src)]
        elif kind == "inkscape":
            cmd = [executable, str(src), "--export-type=png", f"--export-filename={png}"]
        else:
            return {"pass": False, "reason": "UNKNOWN_RENDERER_KIND", "renderer": kind}
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=45)
        except Exception as exc:
            return {"pass": False, "reason": "SVG_RENDERER_EXCEPTION", "renderer": kind, "error": type(exc).__name__}
        if proc.returncode != 0 or not png.is_file():
            return {
                "pass": False,
                "reason": "SVG_RENDER_FAILED",
                "renderer": kind,
                "returncode": proc.returncode,
                "stderr_tail": (proc.stderr or "")[-500:],
            }
        payload = png.read_bytes()
        try:
            got_w, got_h = _png_dimensions(payload)
        except Exception as exc:
            return {"pass": False, "reason": "INVALID_RENDER_OUTPUT", "renderer": kind, "error": str(exc)}
        if got_w < width or got_h < height:
            return {
                "pass": False,
                "reason": "RENDER_DIMENSIONS_TOO_SMALL",
                "renderer": kind,
                "expected_min": [width, height],
                "actual": [got_w, got_h],
            }
        return {
            "pass": True,
            "reason": "PASS",
            "renderer": kind,
            "renderer_executable": Path(executable).name,
            "render_dimensions": [got_w, got_h],
            "render_bytes": len(payload),
        }


def verify(spec: Mapping[str, Any], renderer: tuple[str, str] | None = None) -> dict[str, Any]:
    try:
        svg = mechanics.compile_svg(spec)
    except Exception as exc:
        return {"pass": False, "reason": "COMPILE_FAILED", "error": type(exc).__name__ + ":" + str(exc)}
    structural = mechanics.validate_svg(svg, spec)
    if not structural.get("pass"):
        return {"pass": False, "reason": "STRUCTURAL_FAILED", "structural": structural}
    render = render_smoke(svg, spec, renderer=renderer)
    if not render.get("pass"):
        return {"pass": False, "reason": "RENDER_FAILED", "structural": structural, "render": render}
    return {
        "pass": True,
        "reason": "PASS",
        "structural": structural,
        "render": render,
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }
