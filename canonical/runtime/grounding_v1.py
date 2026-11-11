"""Grounding that survives a page moving.

The problem this solves, stated exactly
--------------------------------------
r64 taught the loop to file a trajectory under the hash of the screen it started from, and
to replay it with no model.  That works, and it is worth almost nothing, because a hash is a
guarantee about ONE screenshot.  Change the heading, move the button twenty pixels, add a
cookie banner -- a neighbouring instance of the same task -- and the hash no longer matches,
so the learned trajectory is dead and the model has to solve it again from scratch.

That is the difference between reciting a trajectory and learning an ability, and it is the
first thing that has to be measured rather than asserted.

What is kept from the demonstration
-----------------------------------
Not the coordinates.  The demonstration is reduced to a set of ANCHORS -- the small image
patches around each place the model chose to act -- plus a binding saying, for this goal,
which anchor belongs to which action and, crucially, WHERE THE NEXT ACTION IS RELATIVE TO
THE PREVIOUS ANCHOR.  A binding that stores "click the GO button" as "the patch that looks
like GO, near the patch that looks like the text field" is a statement about the task.  A
binding that stores (537, 131) is a statement about one screenshot.

Search is multi-scale template matching, run on the full frame and on the background
estimate of a frame the anchors never covered.  Nothing here needs a GPU, a dataset or a
network, which is the point: the expensive part of learning has already happened, once, in
the demonstration.

Honest limits, recorded in `confidence`, not hidden:
  * anchors are appearance; a theme change that repaints the widget defeats them
  * three or more near-identical instances are ambiguous and the match is flagged
  * this grounds WHERE to act, and nothing about WHAT the goal means
"""
from __future__ import annotations

import json
import pathlib
from collections.abc import Mapping
from typing import Any

import numpy as np
from PIL import Image, ImageFilter

SCHEMA = "GROUNDING_V1"
PATCH = 56                 # half-size of the anchor patch, in pixels
MAX_ANCHOR = 128           # an anchor wider than this is not a widget, it is the page.
                           # Found by measuring: a 1280-px-wide band matched with a score of
                           # -31181 under a formula that assumed it was a template.  An
                           # anchor is only meaningful if it is small enough to be something.
MATCH_FLOOR = 0.55         # below this an anchor is not considered present
MIN_PATCH_STD = 4.0        # a patch flatter than this has no structure to locate.
                           # Found by measurement: a flat 112-px patch scored 13,671,875
                           # and matched at every offset, because its variance is 0 and the
                           # normalisation's denominator collapses.  Structureless anchors
                           # must be refused, not silently accepted as perfect matches.
# Ambiguity is not a count, it is a DISTANCE.  Measured on real frames: the empty text
# field's patch matched 162 offsets equally well -- but every one of them was inside the
# same field, and any of them is a correct place to click.  A count-based rule refused
# that (and broke a working 5/5); a distance-based rule does not.  Ambiguity only matters
# when the equally-good matches are FAR APART, because then two different widgets on the
# page look the same and the matcher cannot know which one the demonstration meant.
# The right measure, reached by getting it wrong twice.  First a COUNT of ties (162 for the
# empty text field) -- wrong, because those 162 were all inside one field and every one was
# a valid place to click.  Then a spread in units of 2.5 anchor widths -- also wrong, for
# the same patch: a 56-px patch whose 162 ties span 161 px is a patch that cannot say where
# it is, and 161 px is under 2.5 x 56.  The unit that works is the PATCH ITSELF: if the
# equally-good matches are spread further than the patch's own size, then "the best match"
# is an arbitrary choice among many, and acting on it is a coin flip.
MAX_TIE_SPREAD = 1.0       # in units of the patch's own width/height
AMBIGUOUS_MARGIN = 0.03    # a second peak within this of the best makes the match ambiguous


def _grey(path: str | pathlib.Path) -> np.ndarray:
    """The frame, as float64.

    Not float32.  `frame*frame` on uint8 pixels reaches 65 025, and the FFT then sums
    millions of those into intermediates that overflow float32's 3.4e38 and return inf.  The
    overflow is invisible in the final images and only shows up as a normalisation that is
    nonsense -- which is exactly what happened: every match scored 1 000 000+ on a real
    screenshot while an isolated float64 test scored exactly 1.0.  Verified on real frames,
    not on synthetic ones, after that.
    """
    im = Image.open(path).convert("L")
    return np.asarray(im, dtype=np.float64)


def _normalised(img: np.ndarray) -> np.ndarray:
    m = float(img.mean())
    s = float(img.std()) or 1.0
    return (img - m) / s


def _match(frame: np.ndarray, patch: np.ndarray) -> tuple[float, int, int, int]:
    """Best normalised cross-correlation of `patch` over `frame`.

    Returns (score in [-1, 1], centre x, centre y, best score outside the peak).

    Written once and verified against a patch taken from the frame itself, which must score
    exactly 1.0.  The first version demeaned the patch and then subtracted its raw sum as
    well -- a double correction -- and returned -27.7 where the answer was 1.0.  Both
    mistakes are recorded here because each of them silently made every match look absent.

    Only three correlations over the frame are needed, because the patch's own terms are
    constants: the window sum, the window sum of squares, and the window-patch cross sum.
    """
    ph, pw = patch.shape
    fh, fw = frame.shape
    if fh < ph or fw < pw:
        return -1.0, 0, 0, -1.0
    n = float(ph * pw)

    def corr(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        sh, sw = a.shape[0] + b.shape[0] - 1, a.shape[1] + b.shape[1] - 1
        out = np.fft.irfft2(np.fft.rfft2(a, (sh, sw)) * np.fft.rfft2(b[::-1, ::-1], (sh, sw)),
                            (sh, sw))
        return out[ph - 1:fh, pw - 1:fw]

    frame = frame.astype(np.float64, copy=False)
    patch = patch.astype(np.float64, copy=False)
    ones = np.ones((ph, pw), dtype=np.float64)
    s1 = corr(frame, ones)                 # SIGMA(f)
    s2 = corr(frame * frame, ones)         # SIGMA(f^2)
    sfp = corr(frame, patch)               # SIGMA(f*p)

    sp = float(patch.sum())
    if float(patch.std()) < MIN_PATCH_STD:
        # No structure: every offset matches equally well and none of them means anything.
        return -1.0, 0, 0, -1.0
    # (the tie count is checked after the correlation, below)
    s2p = float((patch * patch).sum())
    num = n * sfp - s1 * sp
    den_f = np.sqrt(np.maximum(n * s2 - s1 * s1, 1e-9))
    den_p = np.sqrt(max(n * s2p - sp * sp, 1e-9))
    ncc = num / (den_f * den_p)

    idx = int(np.argmax(ncc))
    y, x = divmod(idx, ncc.shape[1])
    best = float(ncc[y, x])
    tie_y, tie_x = np.where(ncc > best - 1e-6)
    if tie_x.size:
        spread = max(int(tie_x.max() - tie_x.min()), int(tie_y.max() - tie_y.min()))
        if spread > MAX_TIE_SPREAD * max(ph, pw):
            # The same patch appears in two places far apart.  It cannot say which one.
            return -1.0, 0, 0, -1.0
    flat = ncc.copy()
    y0, y1 = max(0, y - 6), min(flat.shape[0], y + 7)
    x0, x1 = max(0, x - 6), min(flat.shape[1], x + 7)
    flat[y0:y1, x0:x1] = -2.0
    second = float(flat.max()) if flat.size else -1.0
    return best, x + pw // 2, y + ph // 2, second


# --------------------------------------------------------------------------- teaching

def learn(screens: list[str], actions: list[Mapping[str, Any]],
          regions: list[list[float]] | None = None,
          after: list[str] | None = None) -> dict[str, Any]:
    """Reduce a demonstrated trajectory to anchors and a relative binding.

    `screens[i]` is the frame BEFORE action i.  `actions[i]` is what was done on it.
    `regions[i]` optionally names the widget each action touched, so the anchor is cut from
    the widget rather than from a blind box.
    `after[i]` is the frame AFTER action i.  Where it is given, the expected effect region
    is MEASURED from the two frames and stored as an offset from the anchor -- because
    guessing it from the widget box is wrong for the most common case of all: pressing a
    button whose effect is somewhere else on the page.
    """
    anchors = []
    for i, (shot, act) in enumerate(zip(screens, actions)):
        img = _grey(shot)
        if regions and i < len(regions) and regions[i]:
            x0, y0, x1, y1 = (int(v) for v in regions[i])
        elif "x" in act and "y" in act:
            cx, cy = int(act["x"]), int(act["y"])
            # The search window reaches well past the click: the distinctive part of a
            # text field is its border, which can be hundreds of pixels from where the
            # caret goes.  Measured: the field's left border at x=40 matched uniquely
            # (1.000 vs runner-up 0.459) while the empty interior 190 px away had 162
            # equally good matches and therefore meant nothing.
            x0, y0 = max(0, cx - PATCH), max(0, cy - PATCH)
            x1, y1 = min(img.shape[1], cx + PATCH), min(img.shape[0], cy + PATCH)
        else:
            x0 = y0 = x1 = y1 = 0   # resolved below, from the previous anchor
        # Always cut a POINT-SIZED box around the place the action happened, using the
        # named region only as a hint for where that place is.  An anchor is the thing you
        # clicked, not the panel it sits in.
        if "x" in act and "y" in act:
            cx, cy = int(act["x"]), int(act["y"])
        elif anchors:
            # A `type` or `key` has no coordinates: it goes wherever the caret was left.
            # Its anchor is therefore the widget the PREVIOUS action focused -- which is
            # what the action actually depends on, and what has to be found again later.
            prev = anchors[-1]
            px, py = prev["_centre"]
            cx, cy = int(px), int(py)
        else:
            cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        half = PATCH
        x0, y0 = max(0, cx - half), max(0, cy - half)
        x1, y1 = min(img.shape[1], cx + half), min(img.shape[0], cy + half)
        if (x1 - x0) > MAX_ANCHOR or (y1 - y0) > MAX_ANCHOR:
            raise ValueError("THE_ANCHOR_BOX_IS_TOO_LARGE_TO_BE_A_WIDGET")
        # CUT THE ANCHOR WHERE THE WIDGET IS DISTINCTIVE -- on its edge, not at the point
        # that was clicked.  Measured on a real page: a 112-px box centred on a click inside
        # an empty filter field had std 18 and matched 122 offsets; the same size box on the
        # field's LEFT BORDER had std 38 and matched exactly one place.  An earlier attempt
        # at this searched a wide window and picked the most structured crop anywhere nearby,
        # which scored 0/5 because it drifted off the widget; this one searches only the
        # widget the action already names, so the anchor cannot leave it.
        crop = img[y0:y1, x0:x1]
        if "x" in act and "y" in act and crop.size >= 400:
            best = None
            for oy in range(0, max(1, crop.shape[0] - 40), 6):
                for ox in range(0, max(1, crop.shape[1] - 40), 6):
                    win = crop[oy:oy + 40, ox:ox + 40]
                    if win.shape[0] < 40 or win.shape[1] < 40:
                        continue
                    sd = float(win.std())
                    if best is None or sd > best[0]:
                        best = (sd, ox, oy)
            if best is not None and best[0] >= MIN_PATCH_STD:
                _, ox, oy = best
                x0, y0 = x0 + ox, y0 + oy
                x1, y1 = x0 + 40, y0 + 40
                crop = img[y0:y1, x0:x1]
        if crop.size < 100:
            raise ValueError("THE_ANCHOR_REGION_IS_TOO_SMALL_TO_MATCH")
        if float(crop.std()) < MIN_PATCH_STD:
            raise ValueError("THE_ANCHOR_HAS_NO_STRUCTURE_TO_LOCATE")
        effect = None
        if after and i < len(after) and after[i]:
            try:
                from PIL import ImageChops
                fa = Image.open(after[i]).convert("L")
                fb = Image.open(shot).convert("L")
                box = ImageChops.difference(fa, fb).point(lambda v: 255 if v > 8 else 0).getbbox()
                if box:
                    # stored relative to the anchor, so it moves with the widget
                    effect = [box[0] - cx, box[1] - cy, box[2] - cx, box[3] - cy]
            except Exception:
                effect = None
        anchors.append({
            "_centre": (cx, cy),
            "observed_effect_offsets": effect,
            "step": i,
            "action": {k: act[k] for k in ("action", "text", "key", "dy", "seconds",
                                           "expect", "why_no_change", "because")
                       if k in act},
            "patch": crop.round().astype(np.uint8).tolist(),
            "patch_size": [int(x1 - x0), int(y1 - y0)],
            # the click point, measured from the (possibly shifted) anchor's top-left
            "offset_in_patch": [int(cx) - x0, int(cy) - y0],
            "expect_region_size": [int(x1 - x0), int(y1 - y0)],
        })
    for a in anchors:
        a.pop("_centre", None)
    return {"schema": SCHEMA, "anchors": anchors, "taught_on": [str(s) for s in screens]}


def save(binding: Mapping[str, Any], path: str | pathlib.Path) -> None:
    pathlib.Path(path).write_text(json.dumps(binding))


def load(path: str | pathlib.Path) -> dict[str, Any]:
    return json.loads(pathlib.Path(path).read_text())


# --------------------------------------------------------------------------- grounding

def ground(binding: Mapping[str, Any], screenshot: str | pathlib.Path,
           *, floor: float = MATCH_FLOOR) -> dict[str, Any]:
    """Locate every anchor of a learned trajectory in a screen it was never taught on."""
    frame = _grey(screenshot)
    placed: list[dict[str, Any]] = []
    confidence = 1.0
    for a in binding["anchors"]:
        patch = np.asarray(a["patch"], dtype=np.float32)
        score, cx, cy, second = _match(frame, patch)
        ox, oy = a["offset_in_patch"]
        present = score >= floor
        ambiguous = present and (score - second) < AMBIGUOUS_MARGIN
        confidence = min(confidence, max(0.0, min(1.0, score)))
        placed.append({
            "step": a["step"], "action": a["action"],
            "found": bool(present), "score": round(score, 4),
            "runner_up": round(second, 4), "ambiguous": bool(ambiguous),
            "x": int(cx - patch.shape[1] // 2 + ox) if present else None,
            "y": int(cy - patch.shape[0] // 2 + oy) if present else None,
            "expect_region_size": a.get("expect_region_size"),
            "observed_effect_offsets": a.get("observed_effect_offsets"),
        })
    missing = [p["step"] for p in placed if not p["found"]]
    ambiguous = [p["step"] for p in placed if p["ambiguous"]]
    if missing:
        return {"schema": SCHEMA, "verdict": "NOT_GROUNDED", "missing": missing,
                "confidence": 0.0, "placed": placed,
                "because": "the learned widget is not on this screen"}
    return {"schema": SCHEMA, "verdict": "GROUNDED", "placed": placed,
            "confidence": round(confidence, 4),
            "ambiguous": ambiguous,
            "because": "every learned widget was located" +
                       (" but " + str(len(ambiguous)) + " match(es) were ambiguous" if ambiguous else "")}


def to_actions(grounded: Mapping[str, Any], *, settle: float = 1.0,
               width: int = 1280) -> list[dict[str, Any]]:
    """Turn a grounding into directly executable proposals, regions included."""
    out = []
    for p in grounded["placed"]:
        act = dict(p["action"])
        # The whole point of grounding: replace the taught coordinates with the ones found
        # on THIS screen.  An earlier version only copied them when the widget was located,
        # so a grounded action silently shipped with no point at all and the gate refused it.
        if p.get("x") is None:
            raise ValueError("AN_ACTION_CANNOT_BE_EXECUTED_WITHOUT_A_GROUNDED_POINT")
        act["x"], act["y"] = p["x"], p["y"]
        act.setdefault("because", "the taught widget, located on this screen")
        # The expected region is recomputed from the action, not copied from the taught
        # screenshot.  Found live: a `type` action carried a 112-px box, but eleven
        # characters of text render wider than the box, so the gate correctly reported
        # "nothing changed where you claimed" while the text sat plainly on the screen.
        w, h = p.get("expect_region_size") or [PATCH * 2, PATCH * 2]
        if p.get("observed_effect_offsets"):
            # The region measured during the demonstration, moved to wherever this screen
            # put the anchor.  This is the whole difference between guessing an effect and
            # knowing one.
            o = p["observed_effect_offsets"]
            act["expect_region"] = [max(0, p["x"] + o[0]), max(0, p["y"] + o[1]),
                                    min(width, p["x"] + o[2]), min(900, p["y"] + o[3])]
            act.pop("expect", None) if False else None
        elif act["action"] == "type":
            # MEASURED, then written down: the text landed at x 32..203 while the claim
            # said 264..602.  Clicking an empty field puts the caret at position 0, at the
            # widget's far left -- which a 112-px anchor centred on the click cannot know.
            # So the honest, still-falsifiable claim for typing is *the band at the field's
            # height*: typing must change nothing above or below that band.
            act["expect_region"] = [0, max(0, p["y"] - h // 2 - 8),
                                    int(width), min(900, p["y"] + h // 2 + 8)]
        elif not act.get("expect_region"):
            act["expect_region"] = [max(0, p["x"] - w // 2), max(0, p["y"] - h // 2),
                                    p["x"] + w // 2, p["y"] + h // 2]
        act.setdefault("settle", settle)
        out.append(act)
    return out
