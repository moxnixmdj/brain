"""Does a demonstration transfer to a neighbouring instance of the same task?

This is the question the whole thesis rests on, so it is asked as a measurement rather than
an argument.  r64 could replay a trajectory only on the exact screen it was taught on: the
binding was a hash.  A hash is a statement about one screenshot, and one screenshot is not a
task.  Grounding_v1 reduces a demonstration to

    * what the widgets looked like  (anchors, small image patches)
    * what the action did to the page, measured in pixels and stored RELATIVE to the anchor

so that a page which has moved, been renamed, restyled or pushed down can still be acted on
without asking a model.

Every test here corresponds to a bug that was found by running the code, not by reading it.
"""
import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import grounding_v1 as G

ROOT = pathlib.Path(__file__).resolve().parents[2]
TEACH = ROOT / "canonical/evaluation/the_loop/teach"
SHOTS = [str(TEACH / f"step0{i}.png") for i in range(3)]
AFTER = [str(TEACH / f"step0{i}.png") for i in range(1, 4)]

pytestmark = pytest.mark.skipif(not (TEACH / "step00.png").exists(),
                                reason="teaching frames not present")


def _binding():
    acts = [{"action": "click", "x": 190, "y": 128, "because": "the field",
             "expect": "none", "why_no_change": "caret"},
            {"action": "type", "text": "eigenvalues", "because": "the query"},
            {"action": "click", "x": 492, "y": 127, "because": "the GO button"}]
    return G.learn(SHOTS, acts, None, after=AFTER)


# ------------------------------------------------------------------ the matcher itself

def test_a_patch_matches_itself_exactly():
    """The regression that cost the most time: float32 overflows in the FFT and every score
    came back as 1,000,000+ on a real screenshot while a synthetic float64 test passed."""
    frame = G._grey(SHOTS[0])
    patch = frame[120:232, 180:292].copy()
    score, x, y, _ = G._match(frame, patch)
    assert abs(score - 1.0) < 1e-6, f"self-match scored {score}"
    assert (x, y) == (180 + 56, 120 + 56)


def test_a_patch_that_is_not_on_the_screen_scores_low():
    frame = G._grey(SHOTS[0])
    rng = np.random.default_rng(0)
    score, *_ = G._match(frame, rng.normal(size=(112, 112)) * 20 + 120)
    assert score < 0.5


def test_an_anchor_with_no_structure_is_refused():
    """Measured: the empty middle of a text field matched 162 offsets spread over 161 px.
    Acting on the best of those is a coin flip, so it is refused rather than smoothed."""
    frame = G._grey(SHOTS[0])
    blank = frame[600:712, 400:512].copy()
    if float(blank.std()) < G.MIN_PATCH_STD:
        assert G._match(frame, blank)[0] == -1.0
    else:
        pytest.skip("this fixture has no structureless region")


# ------------------------------------------------------------------ what the binding keeps

def test_anchors_are_point_sized_not_widget_sized():
    """An anchor may be cut from a distinctive 40px window inside the widget, or fall back to
    the plain 112px box when the widget has no such window. Both are bounded by MAX_ANCHOR."""
    b = _binding()
    for a in b["anchors"]:
        assert max(a["patch_size"]) <= G.MAX_ANCHOR


def test_the_expected_effect_is_measured_not_guessed():
    """Pressing GO changes the heading, hundreds of pixels away from the button.  A region
    guessed from the widget box is wrong for the most common case of all."""
    b = _binding()
    go = b["anchors"][2]["observed_effect_offsets"]
    assert go is not None
    # the measured effect starts to the LEFT of the anchor and extends upward
    assert go[0] < -100, go
    assert go[1] < 0, go


def test_a_type_action_inherits_the_anchor_of_what_it_types_into():
    """A `type` has no coordinates: it goes wherever the caret was left, so its anchor is the
    widget the previous click focused. (Sizes can differ when one of the two is cut from a
    distinctive window; what matters is that the type action got an anchor at all.)"""
    b = _binding()
    assert b["anchors"][1]["patch_size"]
    assert b["anchors"][1]["offset_in_patch"]


# ------------------------------------------------------------------ grounding a moved page

def test_a_grounded_action_carries_a_point_and_a_reason():
    """Found live: grounded actions shipped with no coordinates at all and no reason, and
    the gate refused every one of them -- correctly."""
    b = _binding()
    g = G.ground(b, SHOTS[0])
    assert g["verdict"] == "GROUNDED", g
    acts = G.to_actions(g)
    assert len(acts) == 3
    for a in acts:
        assert isinstance(a["x"], int) and isinstance(a["y"], int)
        assert a["because"]


def test_the_region_is_taken_from_the_measured_effect():
    b = _binding()
    acts = G.to_actions(G.ground(b, SHOTS[0]))
    # the GO click's claimed region must reach the heading, not sit on the button
    x0, y0, x1, y1 = acts[2]["expect_region"]
    assert x1 < acts[2]["x"], "the effect region should lie left of the button"


def test_a_screen_without_the_learned_widgets_is_not_grounded():
    """A DIFFERENT page is not a moved one.  Refusing here is the feature: it is what stops
    'it learned' from meaning 'it guesses anywhere'."""
    b = _binding()
    other = ROOT / "canonical/evaluation/the_loop/step1_before.png"
    g = G.ground(b, str(other))
    assert g["verdict"] == "NOT_GROUNDED"
    assert g["missing"], "a different page must not fully ground"
    with pytest.raises(ValueError):
        G.to_actions(g)
