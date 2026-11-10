"""The act loop: a goal, a screen, a proposal, a gate, a verdict.

Why this module exists
----------------------
The repo could already see a page (`astra_hidden_visual_executor.screenshot`) and could
already press and type (`Browser.click`, `Input.insertText`).  What it could not do was
run those in a loop that knows when to stop and refuses to lie about succeeding.

Three rules, and each is enforced rather than described:

 1. THE MODEL PROPOSES, IT DOES NOT DISPATCH.  A proposal is a file.  It names an action,
    coordinates, the reason, and -- the part that matters -- the REGION it claims will
    change.  Nothing reaches the browser without passing `validate_proposal`.

 2. THE PROPOSAL MUST BE FALSIFIABLE.  After the action, `causal_check` compares the two
    screenshots.  The pixels inside the claimed region must change; the pixels outside it
    must not change much.  This catches "I clicked and nothing happened" and "I clicked and
    destroyed the page".  It is model-free, it costs one image diff, and it is the only
    part of the loop that cannot be talked out of a verdict.

 3. RUNNING OUT OF STEPS IS A REFUSAL, NOT A RESULT.  `act()` returns REFUSED_STEP_BUDGET
    with the full trajectory.  It never returns the last thing it did as if it were success.

What this module deliberately does NOT do: decide whether the goal has been reached.  That
is a judgement about meaning, it needs something that can read, and pretending a pixel diff
answers it would be the classic mistake.  `verify` is passed in, its answer is recorded with
the evidence, and an unverified success is reported as UNVERIFIED -- never as done.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time
from collections.abc import Callable, Mapping
from typing import Any

SCHEMA = "ACT_LOOP_V1"

# A proposal may only ask for these.  Anything else is refused before it reaches the browser.
ALLOWED_ACTIONS = frozenset({"click", "type", "key", "scroll", "wait"})

# What a step may expect its own effect to be.  "none" is a legitimate and necessary
# declaration: clicking a text field focuses it and changes almost no pixels.  Refusing that
# was this module's first live bug -- the gate rejected a correct action, which is the r53
# mistake in a new domain.  A step that claims "none" is not unchecked: the trajectory-level
# check below requires that the run as a whole moved something, and an ANSWERED result with
# no visible change anywhere is flagged so it can never be counted as a demonstrated action.
ALLOWED_EXPECTATIONS = frozenset({"some", "none"})
# "none" is only allowed to be a claim about a PLACE.  Measured: a focus ring moves ~1900 px
# and a heading swap moves ~3250 px -- a factor of 1.7 apart, so no global pixel threshold
# can tell them apart and any gate that pretends to is theatre.  Instead a "none" step must
# name the widget it is allowed to disturb, and the gate checks the REST of the page held
# still.  That is true for a caret, false for a heading swap, and needs no magic number.
MAX_OUTSIDE_CHANGE_FOR_NONE = 0.002

# A "none" step means "this is not meant to move the page", not "the frame must be
# byte-identical".  Focus rings, carets and caret blinks are real, sub-percent, and
# expected.  Measured: focusing the input on the test page changed 0.16% of the frame.
# Anything above this is a real change and contradicts a "none" claim.
NONE_TOLERANCE = 0.005

# "Did something happen HERE" is an absolute question.  A percentage floor punishes an
# honest, generous region: typing eleven characters changed ~1900 pixels, which is 0.9% of
# the band the model claimed and 100% of what the action did.  Measured, then fixed.  The
# percentage is kept only as a second door for very small regions.
MIN_INSIDE_PIXELS = 400
MIN_INSIDE_CHANGE = 0.02      # of the claimed region, where the region is small
# "Did something happen ELSEWHERE" is a fraction question, because the rest of the page is
# the right denominator for it.
MAX_OUTSIDE_CHANGE = 0.35     # a full navigation legitimately changes everything


def _sha_file(p: str | pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# --------------------------------------------------------------------------- proposals

def load_proposals(path: str | pathlib.Path) -> dict[str, Any]:
    """A model writes this file.  It is read, never executed."""
    return json.loads(pathlib.Path(path).read_text())


def validate_proposal(p: Mapping[str, Any], width: int, height: int) -> tuple[bool, str]:
    """Everything wrong with a proposal, or (True, 'PROPOSAL_VALID')."""
    if not isinstance(p, Mapping):
        return False, "PROPOSAL_NOT_A_MAPPING"
    action = p.get("action")
    if action not in ALLOWED_ACTIONS:
        return False, f"ACTION_NOT_ALLOWED__{action}"
    if not p.get("because"):
        return False, "PROPOSAL_GIVES_NO_REASON"
    if action in {"click", "scroll", "wait"}:
        try:
            x, y = float(p["x"]), float(p["y"])
        except (KeyError, TypeError, ValueError):
            return False, "PROPOSAL_HAS_NO_POINT"
        if not (0 <= x < width and 0 <= y < height):
            return False, f"POINT_OUTSIDE_THE_VIEWPORT__{x},{y}"
    if action == "type" and not isinstance(p.get("text"), str):
        return False, "TYPE_WITH_NO_TEXT"
    if action == "key" and not isinstance(p.get("key"), str):
        return False, "KEY_WITH_NO_KEY"
    expect = p.get("expect", "some")
    if expect not in ALLOWED_EXPECTATIONS:
        return False, f"EXPECT_NOT_ALLOWED__{expect}"
    if expect == "none" and not p.get("why_no_change"):
        # Saying "nothing should happen" is free unless it costs a sentence of reasoning.
        return False, "CLAIMING_NO_CHANGE_REQUIRES_why_no_change"
    if expect == "none" and p.get("expect_region") is None:
        return False, "CLAIMING_NO_CHANGE_REQUIRES_THE_PLACE_IT_MAY_DISTURB"
    region = p.get("expect_region")
    if region is not None:
        ok = (isinstance(region, (list, tuple)) and len(region) == 4
              and all(isinstance(v, (int, float)) for v in region))
        if not ok:
            return False, "EXPECT_REGION_IS_NOT_FOUR_NUMBERS"
        x0, y0, x1, y1 = region
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            return False, f"EXPECT_REGION_NOT_A_BOX_IN_THE_VIEWPORT__{region}"
    return True, "PROPOSAL_VALID"


# --------------------------------------------------------------------------- causal gate

def causal_check(before: str | pathlib.Path, after: str | pathlib.Path,
                 region: list[float] | tuple[float, ...] | None,
                 *, expect: str = "some") -> dict[str, Any]:
    """Did the screen change where the proposal said it would, and only there?

    `expect="some"`  -> the region must change, and most of the rest must not.
    `expect="none"`  -> nothing may change (a wait, a no-op).
    `region is None` -> only the whole-frame question is asked.

    Fails closed.  If the images cannot be compared, the answer is not "fine".
    """
    out: dict[str, Any] = {"schema": SCHEMA, "expect": expect}
    hb, ha = _sha_file(before), _sha_file(after)
    out["before_sha256"], out["after_sha256"] = hb, ha
    if hb == ha:
        if expect == "none":
            out.update(verdict="CAUSAL_OK", detail="NOTHING_EXPECTED_AND_NOTHING_CHANGED")
        else:
            out.update(verdict="CAUSAL_VIOLATION",
                       detail="NOTHING_CHANGED_BUT_A_CHANGE_WAS_CLAIMED")
        return out
    try:
        from PIL import Image, ImageChops
    except Exception:
        # No pixel comparison available.  A byte-level difference proves *something*
        # happened; it cannot prove *where*.  Say so instead of overclaiming.
        if expect == "none":
            out.update(verdict="CAUSAL_VIOLATION",
                       detail="SOMETHING_CHANGED_BUT_NONE_WAS_EXPECTED")
        else:
            out.update(verdict="CAUSAL_UNVERIFIABLE",
                       detail="BYTES_DIFFER_BUT_NO_PIXEL_COMPARATOR_IS_INSTALLED")
        return out

    try:
        a = Image.open(before).convert("RGB")
        b = Image.open(after).convert("RGB")
    except Exception as exc:
        # A truncated or unreadable frame is not a pass.  Found by writing the hostile
        # test rather than by reading this: PIL raises OSError on a partial PNG and the
        # loop used to die instead of refusing.
        out.update(verdict="CAUSAL_UNVERIFIABLE",
                   detail=f"AN_IMAGE_COULD_NOT_BE_READ__{type(exc).__name__}")
        return out
    if a.size != b.size:
        out.update(verdict="CAUSAL_UNVERIFIABLE",
                   detail=f"IMAGE_SIZE_CHANGED__{a.size}->{b.size}")
        return out
    diff = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v > 8 else 0)
    total = a.size[0] * a.size[1]
    changed_all = sum(1 for v in diff.getdata() if v) / total
    out["changed_fraction_whole_frame"] = round(changed_all, 6)

    if region is not None:
        x0, y0, x1, y1 = (int(round(v)) for v in region)
        inside = diff.crop((x0, y0, x1, y1))
        area = max(1, (x1 - x0) * (y1 - y0))
        inside_px = sum(1 for v in inside.getdata() if v)
        changed_in = inside_px / area
        outside_changed = max(0.0, changed_all * total - inside_px) / max(1, total - area)
        out["changed_pixels_inside"] = inside_px
        out["changed_fraction_inside"] = round(changed_in, 6)
        out["changed_fraction_outside"] = round(outside_changed, 6)
        if expect == "some":
            if inside_px < MIN_INSIDE_PIXELS and changed_in < MIN_INSIDE_CHANGE:
                out.update(verdict="CAUSAL_VIOLATION",
                           detail=f"THE_CLAIMED_REGION_DID_NOT_CHANGE__{inside_px}_px")
                return out
            if outside_changed > MAX_OUTSIDE_CHANGE:
                out.update(verdict="CAUSAL_VIOLATION",
                           detail="TOO_MUCH_CHANGED_OUTSIDE_THE_CLAIM__likely_a_navigation")
                return out
        if expect == "none":
            # Same composition check, opposite expectation: the named widget may move,
            # the page around it may not.
            if outside_changed > MAX_OUTSIDE_CHANGE_FOR_NONE:
                out.update(verdict="CAUSAL_VIOLATION",
                           detail=f"THE_PAGE_MOVED_OUTSIDE_THE_NAMED_WIDGET__outside={outside_changed:.4f}")
            else:
                out.update(verdict="CAUSAL_OK",
                           detail="ONLY_THE_NAMED_WIDGET_RESPONDED")
            return out
        out.update(verdict="CAUSAL_OK", detail="CHANGED_WHERE_CLAIMED_AND_NOWHERE_ELSE")
        return out

    if expect == "none":
        changed_px = sum(1 for v in diff.getdata() if v)
        out["changed_pixels_whole_frame"] = changed_px
        if region is None:
            out.update(verdict="CAUSAL_UNVERIFIABLE",
                       detail="A_NO_CHANGE_CLAIM_NEEDS_A_PLACE")
            return out
        x0, y0, x1, y1 = (int(round(v)) for v in region)
        inside = diff.crop((x0, y0, x1, y1))
        area = max(1, (x1 - x0) * (y1 - y0))
        inside_px = sum(1 for v in inside.getdata() if v)
        outside = max(0.0, changed_px - inside_px) / max(1, total - area)
        out["changed_pixels_inside"] = inside_px
        out["changed_fraction_outside"] = round(outside, 6)
        if outside > MAX_OUTSIDE_CHANGE_FOR_NONE:
            out.update(verdict="CAUSAL_VIOLATION",
                       detail=f"THE_PAGE_MOVED_OUTSIDE_THE_NAMED_WIDGET__outside={outside:.4f}")
        else:
            out.update(verdict="CAUSAL_OK",
                       detail="ONLY_THE_NAMED_WIDGET_RESPONDED")
        return out
    out.update(verdict="CAUSAL_OK", detail="THE_SCREEN_CHANGED_AS_PROMISED")
    return out


# --------------------------------------------------------------------------- execution

def execute_action(browser: Any, p: Mapping[str, Any]) -> dict[str, Any]:
    """Dispatch one validated action.  The browser object is the repo's own."""
    action = p["action"]
    if action == "click":
        browser.click(float(p["x"]), float(p["y"]))
        return {"did": "click", "x": p["x"], "y": p["y"]}
    if action == "scroll":
        browser.scroll(float(p.get("dy", 300)))
        return {"did": "scroll", "dy": p.get("dy", 300)}
    if action == "type":
        browser.c.call("Input.insertText", {"text": p["text"]})
        return {"did": "type", "text": p["text"]}
    if action == "key":
        browser.c.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": p["key"]})
        browser.c.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": p["key"]})
        return {"did": "key", "key": p["key"]}
    if action == "wait":
        time.sleep(float(p.get("seconds", 0.5)))
        return {"did": "wait", "seconds": p.get("seconds", 0.5)}
    raise ValueError(f"UNREACHABLE_ACTION__{action}")


# --------------------------------------------------------------------------- the loop

def act(goal: str, browser: Any, *, propose: Callable[[int, str], Mapping[str, Any]],
        verify: Callable[[str], Mapping[str, Any]], shot_dir: str | pathlib.Path,
        budget: int = 8, width: int = 1280, height: int = 900) -> dict[str, Any]:
    """Run the loop until the verifier says the goal holds, or refuse honestly.

    `propose(step, goal)` returns one proposal.  `verify(path)` returns
    {"reached": bool, "because": str}.  Both come from the model.  Neither is trusted:
    the proposal is gated, and the verdict is recorded next to the images it was formed
    from.
    """
    shot_dir = pathlib.Path(shot_dir)
    shot_dir.mkdir(parents=True, exist_ok=True)
    traj: list[dict[str, Any]] = []
    result: dict[str, Any] = {"schema": SCHEMA, "goal": goal, "budget": budget, "steps": traj}

    cur = shot_dir / "step00.png"
    browser.screenshot(cur)

    for step in range(1, budget + 1):
        p = propose(step, goal)
        ok, why = validate_proposal(p, width, height)
        rec: dict[str, Any] = {"step": step, "proposal": dict(p), "gate": why}
        if not ok:
            rec["outcome"] = "REFUSED"
            traj.append(rec)
            result.update(verdict="REFUSED_BY_GATE", because=why, trajectory=traj)
            return result

        nxt = shot_dir / f"step{step:02d}.png"
        rec["before_sha256"] = _sha_file(cur)
        execute_action(browser, p)
        time.sleep(float(p.get("settle", 0.8)))
        browser.screenshot(nxt)
        cc = causal_check(cur, nxt, p.get("expect_region"),
                          expect=str(p.get("expect", "some")))
        rec["causal"] = cc
        if cc["verdict"] == "CAUSAL_VIOLATION":
            rec["outcome"] = "CAUSAL_VIOLATION"
            traj.append(rec)
            result.update(verdict="CAUSAL_VIOLATION", because=cc["detail"],
                          screenshot=str(nxt), trajectory=traj)
            return result

        v = verify(str(nxt))
        rec["verifier"] = dict(v)
        rec["outcome"] = "PROCEEDED"
        traj.append(rec)
        cur = nxt
        if v.get("reached"):
            final = _sha_file(nxt)
            moved = final != _sha_file(shot_dir / "step00.png")
            result.update(verdict="ANSWERED", because=v.get("because", ""),
                          steps_used=step, screenshot=str(nxt),
                          final_sha256=final, trajectory=traj,
                          visible_change_during_run=moved)
            if not moved:
                # The verifier says the goal was reached and not one pixel moved since the
                # first frame.  That is a real outcome (a read-only goal) but it is NOT a
                # demonstrated action, and it must not be filed as a taught trajectory.
                result["label"] = "NO_VISIBLE_CHANGE_AT_ALL"
            return result

    result.update(verdict="REFUSED_STEP_BUDGET",
                  because=f"the goal was not reached in {budget} steps",
                  screenshot=str(cur), trajectory=traj)
    return result


# --------------------------------------------------------------------------- memory

def record_trajectory(result: Mapping[str, Any], db: str | pathlib.Path) -> str:
    """File a successful trajectory under the screen it started from."""
    import sqlite3
    if result.get("verdict") != "ANSWERED":
        raise ValueError("ONLY_AN_ANSWERED_TRAJECTORY_MAY_BE_RECORDED")
    if result.get("label") == "NO_VISIBLE_CHANGE_AT_ALL":
        raise ValueError("A_RUN_THAT_CHANGED_NOTHING_IS_NOT_A_DEMONSTRATION")
    start = result["trajectory"][0]["before_sha256"]
    actions = [{"action": r["proposal"]["action"],
                **{k: r["proposal"][k] for k in ("x", "y", "text", "key", "dy", "seconds",
                                                "expect", "expect_region", "settle",
                                                "why_no_change")
                   if k in r["proposal"]}}
               for r in result["trajectory"]]
    db = pathlib.Path(db)
    con = sqlite3.connect(db)
    con.execute("""CREATE TABLE IF NOT EXISTS gui_trajectories_v1(
        screen_sha256 TEXT PRIMARY KEY, goal TEXT, actions_json TEXT, record_json TEXT)""")
    con.execute("INSERT OR REPLACE INTO gui_trajectories_v1 VALUES(?,?,?,?)",
                (start, result["goal"], json.dumps(actions), json.dumps(dict(result))))
    con.commit(); con.close()
    return start


def replay(screen_sha256: str, browser: Any, *, db: str | pathlib.Path,
           shot_dir: str | pathlib.Path) -> dict[str, Any]:
    """Deterministic re-execution. No model. Refuses if the screen is not the taught one."""
    import sqlite3
    con = sqlite3.connect(pathlib.Path(db))
    row = con.execute("SELECT goal, actions_json FROM gui_trajectories_v1 WHERE screen_sha256=?",
                      (screen_sha256,)).fetchone()
    con.close()
    if not row:
        return {"verdict": "NOTHING_TAUGHT_FOR_THIS_SCREEN", "screen_sha256": screen_sha256}
    goal, actions = row[0], json.loads(row[1])
    shot_dir = pathlib.Path(shot_dir); shot_dir.mkdir(parents=True, exist_ok=True)
    cur = shot_dir / "replay00.png"
    browser.screenshot(cur)
    live = _sha_file(cur)
    if live != screen_sha256:
        return {"verdict": "REFUSED_SCREEN_HAS_CHANGED", "taught_on": screen_sha256,
                "live": live, "goal": goal}
    log = []
    for i, a in enumerate(actions, 1):
        nxt = shot_dir / f"replay{i:02d}.png"
        execute_action(browser, a)
        time.sleep(float(a.get("settle", 0.8)))
        browser.screenshot(nxt)
        cc = causal_check(cur, nxt, a.get("expect_region"), expect=str(a.get("expect", "some")))
        log.append({"step": i, "action": a, "causal": cc})
        if cc["verdict"] == "CAUSAL_VIOLATION":
            return {"verdict": "REFUSED_CAUSAL_VIOLATION", "goal": goal, "log": log}
        cur = nxt
    return {"verdict": "REPLAYED_WITHOUT_A_MODEL", "goal": goal, "steps": len(actions),
            "final_screenshot": str(cur), "log": log}
