from __future__ import annotations

from types import SimpleNamespace
import struct

import pytest

from canonical.runtime import html_svg_diagram_mechanics_v1 as mechanics
from canonical.runtime import svg_diagram_render_oracle_v1 as oracle


def case():
    return {
        "schema": mechanics.SCHEMA,
        "canvas": {"width": 640, "height": 360},
        "nodes": [
            {"id": "a", "label": "A", "shape": "rect", "x": 20, "y": 100, "width": 120, "height": 60},
            {"id": "b", "label": "B", "shape": "ellipse", "x": 450, "y": 100, "width": 120, "height": 60},
        ],
        "edges": [{"id": "e", "source": "a", "target": "b", "label": "causes"}],
    }


def test_missing_renderer_fails_closed(monkeypatch):
    monkeypatch.setattr(oracle, "find_renderer", lambda: None)
    out = oracle.verify(case())
    assert out["pass"] is False
    assert out["render"]["reason"] == "SVG_RENDERER_RUNTIME_MISSING"


def test_fake_renderer_must_emit_valid_png(monkeypatch):
    def fake_run(cmd, **kwargs):
        out_path = next((x.split("=", 1)[1] for x in cmd if x.startswith("--export-filename=")), None)
        assert out_path
        open(out_path, "wb").write(b"not png")
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(oracle.subprocess, "run", fake_run)
    out = oracle.render_smoke(mechanics.compile_svg(case()), case(), renderer=("inkscape", "/fake/inkscape"))
    assert out["pass"] is False
    assert out["reason"] == "INVALID_RENDER_OUTPUT"


def test_fake_renderer_dimension_regression_is_rejected(monkeypatch):
    def fake_run(cmd, **kwargs):
        out_path = next(x.split("=", 1)[1] for x in cmd if x.startswith("--export-filename="))
        payload = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", 320, 180) + b"x" * 32
        open(out_path, "wb").write(payload)
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(oracle.subprocess, "run", fake_run)
    out = oracle.render_smoke(mechanics.compile_svg(case()), case(), renderer=("inkscape", "/fake/inkscape"))
    assert out["pass"] is False
    assert out["reason"] == "RENDER_DIMENSIONS_TOO_SMALL"


def test_real_renderer_passes_when_available():
    renderer = oracle.find_renderer()
    if renderer is None:
        pytest.skip("no real SVG renderer")
    out = oracle.verify(case(), renderer=renderer)
    assert out["pass"] is True
    assert out["render"]["render_dimensions"][0] >= 640
    assert out["render"]["render_dimensions"][1] >= 360
