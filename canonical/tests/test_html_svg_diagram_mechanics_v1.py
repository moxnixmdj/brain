from __future__ import annotations

from types import SimpleNamespace
import struct

import pytest

from canonical.runtime import html_svg_diagram_mechanics_v1 as mech


def case():
    return {
        "schema": mech.SCHEMA,
        "canvas": {"width": 640, "height": 360},
        "nodes": [
            {"id": "input", "label": "Input <safe>", "shape": "rect", "x": 30, "y": 120, "width": 150, "height": 70},
            {"id": "output", "label": "Output & proof", "shape": "ellipse", "x": 420, "y": 120, "width": 170, "height": 70},
        ],
        "edges": [{"id": "verified", "source": "input", "target": "output", "label": "verified"}],
    }


def test_compile_and_structural_roundtrip_is_exact_and_escaped():
    spec = case()
    svg = mech.compile_svg(spec)
    assert "Input &lt;safe&gt;" in svg
    assert "Output &amp; proof" in svg
    out = mech.validate_svg(svg, spec)
    assert out["pass"] is True
    assert out["node_count"] == 2
    assert out["edge_count"] == 1


def test_unknown_edge_endpoint_fails_closed():
    spec = case()
    spec["edges"][0]["target"] = "missing"
    with pytest.raises(mech.DiagramMechanicsError, match="UNKNOWN_ENDPOINT"):
        mech.compile_svg(spec)


def test_duplicate_identity_fails_closed():
    spec = case()
    spec["nodes"].append(dict(spec["nodes"][0]))
    with pytest.raises(mech.DiagramMechanicsError, match="DUPLICATE"):
        mech.normalize_spec(spec)


def test_tampered_relation_is_detected():
    spec = case()
    svg = mech.compile_svg(spec).replace('data-target="output"', 'data-target="input"')
    out = mech.validate_svg(svg, spec)
    assert out == {"pass": False, "reason": "EDGE_RELATION_MISMATCH", "edge": "verified"}


def test_unresolved_fragment_reference_is_detected():
    spec = case()
    svg = mech.compile_svg(spec).replace("url(#brain-arrowhead)", "url(#missing-arrowhead)")
    out = mech.validate_svg(svg, spec)
    assert out["pass"] is False
    assert out["reason"] == "UNRESOLVED_FRAGMENT_REFERENCE"


def test_event_attribute_or_script_is_rejected():
    spec = case()
    svg = mech.compile_svg(spec).replace("<g id=\"brain-nodes\"", "<g onload=\"boom()\" id=\"brain-nodes\"")
    out = mech.validate_svg(svg, spec)
    assert out["pass"] is False
    assert out["reason"] == "EVENT_ATTRIBUTE"


def test_structural_only_mode_never_silently_claims_render_credit(monkeypatch):
    spec = case()
    def forbidden(*args, **kwargs):
        raise AssertionError("browser must not run")
    monkeypatch.setattr(mech, "browser_render_smoke", forbidden)
    out = mech.verify_mechanics(spec, require_browser=False)
    assert out["pass"] is True
    assert out["render"] == {"pass": None, "reason": "BROWSER_NOT_REQUESTED__NO_RENDER_CREDIT"}


def test_required_browser_absence_fails_closed(monkeypatch):
    spec = case()
    monkeypatch.setattr(mech, "find_browser", lambda: None)
    out = mech.verify_mechanics(spec, require_browser=True)
    assert out["pass"] is False
    assert out["reason"] == "RENDER_FAILED"
    assert out["render"]["reason"] == "BROWSER_RUNTIME_MISSING"


def test_browser_render_path_requires_real_png_dimensions(monkeypatch):
    spec = case()
    def fake_run(cmd, **kwargs):
        shot = next(x for x in cmd if x.startswith("--screenshot="))
        path = shot.split("=", 1)[1]
        payload = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", 640, 360) + b"x" * 32
        open(path, "wb").write(payload)
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(mech.subprocess, "run", fake_run)
    out = mech.browser_render_smoke(mech.compile_svg(spec), spec, browser="/fake/chromium")
    assert out["pass"] is True
    assert out["screenshot_dimensions"] == [640, 360]
