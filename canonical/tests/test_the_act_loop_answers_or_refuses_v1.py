"""The act loop: it answers, it refuses, and it cannot be talked into a false success.

Split deliberately in two halves:

  * PURE -- no browser.  Proposal gating, the causal gate, the step budget, replay
    refusal.  These run anywhere and are what CI would run.
  * LIVE -- a real Chromium on :9222, skipped if there is none.  Proves the loop end to
    end, and proves the replay path works without a model.

The most important test in this file is `test_a_click_that_changed_nothing_is_caught`.
A loop that reports success when nothing moved is the failure mode that makes GUI agents
look good in demos and useless in practice.
"""
import json
import pathlib
import sqlite3
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import act_loop_v1 as L

ROOT = pathlib.Path(__file__).resolve().parents[2]
BEFORE = str(ROOT / "canonical/evaluation/the_loop/step1_before.png")
AFTER = str(ROOT / "canonical/evaluation/the_loop/step2_after.png")
REGION = [20, 30, 290, 210]          # the heading's box: changed when pressed
WRONG = [600, 600, 1200, 860]        # blank canvas: did not change


# ------------------------------------------------------------------ proposal gate

def test_an_action_outside_the_allowlist_never_reaches_the_browser():
    ok, why = L.validate_proposal({"action": "evaluate_js", "x": 1, "y": 1,
                                   "because": "faster"}, 1280, 900)
    assert not ok and why == "ACTION_NOT_ALLOWED__evaluate_js"


def test_a_proposal_without_a_reason_is_refused():
    ok, why = L.validate_proposal({"action": "click", "x": 1, "y": 1}, 1280, 900)
    assert not ok and why == "PROPOSAL_GIVES_NO_REASON"


def test_a_point_outside_the_viewport_is_refused():
    ok, why = L.validate_proposal({"action": "click", "x": 5000, "y": 1,
                                   "because": "r"}, 1280, 900)
    assert not ok and why.startswith("POINT_OUTSIDE_THE_VIEWPORT")


def test_a_claimed_region_that_is_not_a_box_is_refused():
    ok, why = L.validate_proposal({"action": "click", "x": 10, "y": 10, "because": "r",
                                   "expect_region": [10, 10, 5, 5]}, 1280, 900)
    assert not ok and why.startswith("EXPECT_REGION_NOT_A_BOX")


def test_type_and_key_need_something_to_do():
    assert not L.validate_proposal({"action": "type", "because": "r"}, 1280, 900)[0]
    assert L.validate_proposal({"action": "type", "text": "hi", "because": "r"},
                               1280, 900)[0]


# ------------------------------------------------------------------ causal gate

def test_a_change_where_claimed_and_nowhere_else_is_accepted():
    cc = L.causal_check(BEFORE, AFTER, REGION)
    assert cc["verdict"] == "CAUSAL_OK", cc
    assert cc["changed_fraction_inside"] > 0.02
    assert cc["changed_fraction_outside"] == 0.0


def test_a_click_that_changed_nothing_is_caught():
    """The failure mode that makes GUI agents look good in demos."""
    same = L.causal_check(BEFORE, BEFORE, REGION)
    assert same["verdict"] == "CAUSAL_VIOLATION"
    assert same["detail"] == "NOTHING_CHANGED_BUT_A_CHANGE_WAS_CLAIMED"


def test_a_change_somewhere_other_than_claimed_is_caught():
    """The click landed somewhere else, or the page navigated. Either way: not what was said."""
    cc = L.causal_check(BEFORE, AFTER, WRONG)
    assert cc["verdict"] == "CAUSAL_VIOLATION"
    assert cc["detail"].startswith("THE_CLAIMED_REGION_DID_NOT_CHANGE")


def test_a_wait_that_changed_the_screen_is_caught():
    """A no-op claim naming the blank canvas, while the heading changed: caught, because
    the page moved outside the widget that was named."""
    cc = L.causal_check(BEFORE, AFTER, WRONG, expect="none")
    assert cc["verdict"] == "CAUSAL_VIOLATION"
    assert "OUTSIDE_THE_NAMED_WIDGET" in cc["detail"]


def test_a_no_change_claim_with_no_place_is_refused():
    """Found live: focus rings and heading swaps differ by a factor of 1.7 in pixels, so
    no global threshold separates them. A "none" claim is only checkable as a claim about
    a PLACE."""
    assert not L.validate_proposal({"action": "click", "x": 1, "y": 1, "because": "r",
                                    "expect": "none", "why_no_change": "x"}, 1280, 900)[0]
    ok, why = L.validate_proposal({"action": "click", "x": 1, "y": 1, "because": "r",
                                   "expect": "none", "why_no_change": "x",
                                   "expect_region": [0, 0, 100, 100]}, 1280, 900)
    assert ok, why


def test_the_gate_fails_closed_when_it_cannot_compare(tmp_path):
    a = tmp_path / "a.png"; a.write_bytes(b"\x89PNG\r\n\x1a\nnot really")
    cc = L.causal_check(BEFORE, str(a), REGION)
    assert cc["verdict"] in {"CAUSAL_UNVERIFIABLE", "CAUSAL_VIOLATION"}
    assert cc["verdict"] != "CAUSAL_OK"


# ------------------------------------------------------------------ loop control
class FakeBrowser:
    """Enough browser for the pure tests: it does what it is told and nothing more."""
    def __init__(self, shots):
        self.shots = list(shots)
        self.calls = []
    def screenshot(self, path):
        pathlib.Path(path).write_bytes(pathlib.Path(self.shots.pop(0)).read_bytes())
    def click(self, x, y): self.calls.append(("click", x, y))
    def scroll(self, dy): self.calls.append(("scroll", dy))
    class c:  # noqa: N801 - stands in for the CDP client
        @staticmethod
        def call(m, p=None): FakeBrowser.calls.append((m, p))


def test_running_out_of_steps_is_a_refusal_not_a_result(tmp_path):
    b = FakeBrowser([BEFORE, AFTER] * 10)
    res = L.act("press it", b,
                propose=lambda s, g: {"action": "click", "x": 157, "y": 162,
                                      "because": "the button is here",
                                      "expect_region": REGION},
                verify=lambda p: {"reached": False, "because": "heading still says BEFORE"},
                shot_dir=tmp_path, budget=3)
    assert res["verdict"] == "REFUSED_STEP_BUDGET"
    assert res["trajectory"][0]["outcome"] == "PROCEEDED"
    # and it did not report the last thing it did as success
    assert "steps_used" not in res


def test_a_bad_proposal_stops_the_loop_before_dispatch(tmp_path):
    b = FakeBrowser([BEFORE, AFTER] * 10)
    res = L.act("press it", b,
                propose=lambda s, g: {"action": "click", "x": 157, "y": 162},
                verify=lambda p: {"reached": True}, shot_dir=tmp_path, budget=3)
    assert res["verdict"] == "REFUSED_BY_GATE"
    assert b.calls == []


def test_a_causally_wrong_step_stops_the_loop(tmp_path):
    b = FakeBrowser([BEFORE, AFTER, AFTER] * 6)
    res = L.act("press it", b,
                propose=lambda s, g: {"action": "click", "x": 157, "y": 162,
                                      "because": "here", "expect_region": WRONG},
                verify=lambda p: {"reached": True}, shot_dir=tmp_path, budget=3)
    assert res["verdict"] == "CAUSAL_VIOLATION"


def test_the_verifier_never_gets_to_say_done_on_its_own(tmp_path):
    """The verifier says reached on step 1; the causal gate still ran first and the
    verdict is recorded next to the images it was formed from."""
    b = FakeBrowser([BEFORE, AFTER] * 6)
    res = L.act("press it", b,
                propose=lambda s, g: {"action": "click", "x": 157, "y": 162,
                                      "because": "here", "expect_region": REGION},
                verify=lambda p: {"reached": True, "because": "reads AFTER"},
                shot_dir=tmp_path, budget=3)
    assert res["verdict"] == "ANSWERED"
    assert res["trajectory"][0]["causal"]["verdict"] == "CAUSAL_OK"
    assert res["final_sha256"]


# ------------------------------------------------------------------ memory + replay

def _answered(tmp_path):
    b = FakeBrowser([BEFORE, AFTER] * 6)
    return L.act("press it", b,
                 propose=lambda s, g: {"action": "click", "x": 157, "y": 162,
                                       "because": "here", "expect_region": REGION},
                 verify=lambda p: {"reached": True, "because": "reads AFTER"},
                 shot_dir=tmp_path / "shots", budget=3)


def test_only_an_answered_trajectory_may_be_recorded(tmp_path):
    b = FakeBrowser([BEFORE, AFTER] * 10)
    res = L.act("press it", b,
                propose=lambda s, g: {"action": "click", "x": 157, "y": 162,
                                      "because": "here", "expect_region": REGION},
                verify=lambda p: {"reached": False}, shot_dir=tmp_path, budget=2)
    with pytest.raises(ValueError):
        L.record_trajectory(res, tmp_path / "db.sqlite")


def test_a_taught_trajectory_replays_without_a_model(tmp_path):
    res = _answered(tmp_path)
    db = tmp_path / "db.sqlite"
    key = L.record_trajectory(res, db)
    b = FakeBrowser([BEFORE, AFTER, AFTER] * 6)
    out = L.replay(key, b, db=db, shot_dir=tmp_path / "r")
    assert out["verdict"] == "REPLAYED_WITHOUT_A_MODEL", out
    assert out["steps"] == 1


def test_replay_refuses_a_screen_it_was_not_taught_on(tmp_path):
    res = _answered(tmp_path)
    db = tmp_path / "db.sqlite"
    L.record_trajectory(res, db)
    b = FakeBrowser([AFTER, AFTER] * 6)      # live screen is not the taught one
    out = L.replay("00" * 32, b, db=db, shot_dir=tmp_path / "r")
    assert out["verdict"] == "NOTHING_TAUGHT_FOR_THIS_SCREEN"


def test_replay_refuses_when_the_screen_has_moved(tmp_path):
    res = _answered(tmp_path)
    db = tmp_path / "db.sqlite"
    key = L.record_trajectory(res, db)
    b = FakeBrowser([AFTER, AFTER] * 6)      # same goal, different starting screen
    out = L.replay(key, b, db=db, shot_dir=tmp_path / "r")
    assert out["verdict"] == "REFUSED_SCREEN_HAS_CHANGED"


# ------------------------------------------------------------------ live
def _live_browser():
    import importlib.util
    import urllib.request
    try:
        pages = [x for x in json.loads(urllib.request.urlopen(
            "http://127.0.0.1:9222/json/list", timeout=3).read()) if x["type"] == "page"]
    except Exception:
        pytest.skip("no Chromium on :9222")
    if not pages:
        pytest.skip("no page target")
    spec = importlib.util.spec_from_file_location(
        "hv", ROOT / "canonical/runtime/astra_hidden_visual_executor.py")
    hv = importlib.util.module_from_spec(spec); spec.loader.exec_module(hv)
    c = hv.CDP(pages[0]["webSocketDebuggerUrl"])
    b = hv.Browser(c); b.enable()
    return b


def test_live_the_whole_loop_runs_and_the_gate_holds(tmp_path):
    b = _live_browser()
    import time
    # A live test must start from a known state.  Found the hard way: the page had been
    # pressed by an earlier demo, so the button was already spent and clicking it again
    # changed nothing -- the gate refused, correctly, and the test blamed the loop.
    b.navigate("http://127.0.0.1:8899/")
    time.sleep(1.2)
    res = L.act("press the button", b,
                propose=lambda s, g: {"action": "click", "x": 157, "y": 162,
                                      "because": "the button is at the top left",
                                      "expect_region": REGION, "settle": 1.0},
                verify=lambda p: {"reached": True, "because": "the heading reads AFTER"},
                shot_dir=tmp_path, budget=2)
    assert res["verdict"] == "ANSWERED", res
    assert res["trajectory"][0]["causal"]["verdict"] == "CAUSAL_OK"
    # the executor's own allowlist still refuses to reach through the page
    with pytest.raises(Exception):
        b.c.call("Runtime.evaluate", {"expression": "1+1"})
    b.c.close()


# ------------------------------------------------------------------ regressions found live
# Each of these failed on a real page before it passed here.  They are the price of the
# loop, paid once.

def test_a_step_that_changes_almost_nothing_may_say_so():
    """Focusing a text field is a correct action that moves ~0.16% of the screen.
    The gate used to refuse it, rejecting correct behaviour -- r53's mistake again."""
    ok, why = L.validate_proposal(
        {"action": "click", "x": 230, "y": 130, "because": "the field",
         "expect": "none", "why_no_change": "only moves the caret",
         "expect_region": [20, 100, 440, 160]}, 1280, 900)
    assert ok, why


def test_claiming_no_change_costs_a_reason():
    ok, why = L.validate_proposal({"action": "click", "x": 230, "y": 130,
                                   "because": "the field", "expect": "none"}, 1280, 900)
    assert not ok and why == "CLAIMING_NO_CHANGE_REQUIRES_why_no_change"


def test_a_none_step_tolerates_focus_noise_but_not_a_real_change():
    import shutil
    a = ROOT / "canonical/evaluation/the_loop/step1_before.png"
    b = ROOT / "canonical/evaluation/the_loop/step2_after.png"
    # same frame: fine
    assert L.causal_check(str(a), str(a), REGION, expect="none")["verdict"] == "CAUSAL_OK"
    # a real change inside the named widget is tolerated (that is what "none" permits)...
    assert L.causal_check(str(a), str(b), REGION, expect="none")["verdict"] == "CAUSAL_OK"
    # ...but the same change with the widget named elsewhere moved the page: caught.
    assert L.causal_check(str(a), str(b), WRONG, expect="none")["verdict"] == "CAUSAL_VIOLATION"


def test_a_small_but_real_change_inside_a_generous_region_is_accepted():
    """Typing eleven characters changed ~1900 px = 0.9% of the band the model claimed.
    A pure percentage floor called that nothing.  Absolute pixels is the right unit for
    "did something happen here"."""
    cc = L.causal_check(BEFORE, AFTER, REGION)
    assert cc["verdict"] == "CAUSAL_OK"
    assert cc["changed_pixels_inside"] > L.MIN_INSIDE_PIXELS


def test_a_run_that_moved_no_pixels_is_not_a_demonstration(tmp_path):
    b = FakeBrowser([BEFORE, BEFORE] * 6)
    res = L.act("read the heading", b,
                propose=lambda s, g: {"action": "click", "x": 157, "y": 162,
                                      "because": "here", "expect": "none",
                                      "why_no_change": "reading only",
                                      "expect_region": REGION},
                verify=lambda p: {"reached": True, "because": "I read it"},
                shot_dir=tmp_path, budget=2)
    assert res["verdict"] == "ANSWERED"
    assert res["visible_change_during_run"] is False
    assert res["label"] == "NO_VISIBLE_CHANGE_AT_ALL"
    with pytest.raises(ValueError):
        L.record_trajectory(res, tmp_path / "db.sqlite")
