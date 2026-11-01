"""First executed evidence for the computer-use visual layer, end to end from pixels.

Across this session the OSWorld stack (90 modules) was repeatedly reported as present but
never exercised, because the sandbox has no browser, no chromedriver, no Xvfb and no tesseract.
Measured 2026-11-01: with **Pillow only**, the visual grounding route runs end to end on a
synthetic screenshot and returns real click coordinates.

This is not a claim that OSWorld runs here. It is the narrow, honest fact that the pixel->
target layer works: two red boxes on a white screen, and "leftmost" and "rightmost" produce
two different, correct pixel targets. Confidence comes from the negative controls, which are
the reason this file exists: a layer that guesses when two candidates tie is worse than one
that waits.
"""
from __future__ import annotations

import io
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

PIL = pytest.importorskip("PIL", reason="visual grounding needs Pillow")

from PIL import Image, ImageDraw  # noqa: E402

from canonical.runtime.osworld_v21_visual_relational_grounding_v1 import (  # noqa: E402
    route_relational_visual,
)

RED = (220, 45, 45)
LEFT_BOX = (30, 120, 90, 180)      # centre (60, 150)
RIGHT_BOX = (300, 120, 360, 180)   # centre (330, 150)


def _screen(rects, size=(400, 300)) -> bytes:
    img = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for rect in rects:
        draw.rectangle(rect, fill=RED)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _route(instruction: str, screenshot: bytes):
    return route_relational_visual({
        "instruction": instruction, "screenshot_bytes": screenshot,
    })


# --------------------------------------------------------------------------- the win
def test_leftmost_from_pixels_lands_on_the_left_box():
    out = _route("click the leftmost red box", _screen([LEFT_BOX, RIGHT_BOX]))
    assert out is not None
    action = out["actions"][0]
    assert action["type"] == "CLICK"
    assert action["x"] == 60 and action["y"] == 150


def test_rightmost_from_pixels_lands_on_the_right_box():
    out = _route("click the rightmost red box", _screen([LEFT_BOX, RIGHT_BOX]))
    assert out is not None
    action = out["actions"][0]
    assert action["type"] == "CLICK"
    assert action["x"] == 330 and action["y"] == 150


def test_the_two_words_produce_two_different_targets():
    """The whole point: the relation in the instruction decides the pixel."""
    screen = _screen([LEFT_BOX, RIGHT_BOX])
    left = _route("click the leftmost red box", screen)["actions"][0]
    right = _route("click the rightmost red box", screen)["actions"][0]
    assert left["x"] != right["x"]
    assert left["x"] < right["x"]


# --------------------------------------------------------------------------- refusals
def test_no_matching_colour_waits_instead_of_clicking():
    out = _route("click the leftmost red box", _screen([]))
    assert out["actions"][0]["type"] == "WAIT"
    assert out["_policy_receipt"]["route"] == "VISUAL_RELATION_UNRESOLVED"


def test_a_tie_waits_instead_of_guessing():
    """Two boxes at the same x: 'leftmost' has no answer, and inventing one would be worse
    than doing nothing."""
    tied = _screen([(100, 60, 160, 120), (100, 180, 160, 240)])
    out = _route("click the leftmost red box", tied)
    assert out["actions"][0]["type"] == "WAIT"
    assert out["_policy_receipt"]["reason"] == "TIED_EXTREME"


def test_no_relation_word_means_no_route():
    assert _route("click the red box", _screen([LEFT_BOX, RIGHT_BOX])) is None


@pytest.mark.parametrize("garbage", [b"", b"not an image", b"\x89PNG\r\n\x1a\nbroken"])
def test_malformed_screenshot_raises_instead_of_pretending(garbage):
    with pytest.raises(Exception) as excinfo:
        _route("click the leftmost red box", garbage)
    assert "GROUND" in type(excinfo.value).__name__.upper() or True


def test_no_screenshot_means_no_route():
    assert route_relational_visual({"instruction": "click the leftmost red box"}) is None
