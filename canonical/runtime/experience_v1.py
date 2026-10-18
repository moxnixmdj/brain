"""The machine gets better for having worked.

WHY THIS EXISTS, AND WHAT WAS MISSING WITHOUT IT.

Everything before this ran a job, proved what happened, and FORGOT IT. Ask
the same thing twice and the machine started from nothing, reached for the
same tool that cannot work on this box, and failed the same way. It had
perception and it had proof, and no memory at all.

That is not how the car works. The car is not valuable because one vehicle
drives one road well; it is valuable because every mile driven by every car
makes the next mile better. The action space never changed -- steering,
throttle, brake. What accumulated was the judgement about WHEN.

THE UNIT OF MEMORY IS THE PATHOLOGY, NOT THE TASK.

"How I did that one job" is worthless the moment the job changes, and this
system exists precisely to handle jobs it has never seen. What repeats is
not the task -- it is the WAY THINGS BREAK. `image.extract.ocr.tesseract`
x `BOUND_CAPABILITY_SOURCE_UNSUPPORTED` will be true on this machine
forever, for every goal that ever wants text out of an image. That cell is
worth remembering. A transcript of one job is not -- it grows forever and
generalises never.

THE GATE, AND THE TRAP IN IT.

Evidence accumulates as an e-process (credit_gates_v1, Ville's inequality):
P(ever crossing 1/alpha) <= alpha HOWEVER OFTEN you look. That matters
because this machine looks constantly -- a fixed-sample test is invalid the
moment anyone peeks, and a plain mean improves about 60% of the time for a
change that does nothing at all.

But magnitude alone is not the gate, and this is the subtle part:

    The e-process tests "no effect" against ANY consistent deviation, so
    a correction that fails every single time also accumulates evidence.
    Eight straight failures scored e=31.6, past a threshold of 20, and
    would have been promoted as a fix -- confidently reusing the thing
    that never works.

So strong consistent evidence of HARM is real evidence against the null,
and it is still not grounds for credit. THE SIGN IS THE GATE. That rule was
learned the hard way in flywheel_v1 and is carried here unchanged.

STRUCTURAL FACTS SKIP THE GATE, AND ONLY FACTS CAN UNDO THEM.

"There is no tesseract on this box" is not a statistical claim. It is a
fact about a machine, true on the first observation, and waiting for eight
repeats before believing it is stupidity dressed as rigour. So structural
reasons (no such adapter, unsupported source type, binary absent) suppress
immediately AND record a real -1. The suppression is not permanent: it
lifts only when genuine successes accumulate past the same gate going the
other way. A memory that cannot be revoked is a superstition.

WHAT MEMORY MAY NEVER DO.

It changes WHICH capability is proposed and WHETHER THE MACHINE HAS TO ASK.
It never changes whether the result is checked. Verification is never
outsourced to memory, and a remembered success is re-proved every time.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_EXPERIENCE_V1"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE = "canonical/runtime/state/experience_v1.json"
DEFAULT_ALPHA = 0.05           # Ville: promote at e >= 1/alpha = 20
THRESHOLD = 1.0 / DEFAULT_ALPHA
MAX_OBSERVATIONS = 500         # the unit is a pathology, so this is plenty
RECHECK_AFTER_S = 300.0        # see _probe_due: a memory must be re-testable

# Reasons that are FACTS ABOUT A MACHINE rather than statistical claims.
# One observation settles them. Everything else must earn its gate.
# DO NOT REMEMBER WHAT YOU CAN CHEAPLY RECOMPUTE, AND NEVER GENERALISE A
# FACT ABOUT ONE GOAL INTO A FACT ABOUT THE MACHINE.
#
# Both mistakes were made here and both were caught by running it:
#
#   * `INPUT_KIND_CONTRADICTS_GOAL_FILE` was remembered as permanent harm.
#     It is not: "this capability cannot take a .pdf" is true of the GOAL,
#     and the very next request ("ocr this .png") needs that capability
#     again. Remembering it turned one PDF into a machine that can never
#     do OCR. Worse, the check is deterministic and costs microseconds, so
#     memory bought nothing and cost correctness.
#
#   * `PRECONDITION_NOT_TRUE_OF_WORLD` is re-decided by perception on every
#     run, and the world changes -- a PDF appearing tomorrow makes
#     "pdf.file.available" true again. Suppressing it permanently would be
#     a memory that lies about a world that moved. It is still RECORDED,
#     because the trend is worth knowing; it just does not suppress.
#
# What genuinely earns permanent suppression is narrow: things that are
# TRUE OF THIS MACHINE FOREVER and EXPENSIVE TO REDISCOVER. An install
# that fails costs two thirds of a second every single time; that is worth
# never paying again.
STRUCTURAL_REASONS = frozenset({
    "BOUND_CAPABILITY_SOURCE_UNSUPPORTED",
    "BOUND_CAPABILITY_ADAPTER_MISSING",
    "BOUND_CAPABILITY_ADAPTER_INVALID",
    "BOUND_CAPABILITY_ENTRYPOINT_MISSING",
    "BOUND_PYPI_INSTALL_FAILED",
    "BOUND_NPM_INSTALL_FAILED",
    "BOUND_APT_INSTALL_FAILED",
    "NO_SUCH_EXECUTABLE",
    "PYTHON_ENVIRONMENT_EXTERNALLY_MANAGED",
})

_STATE_CACHE: dict[str, dict] = {}


def _path(path=None):
    return ROOT / (path or DEFAULT_STATE)


def _load(path=None):
    key = str(path or DEFAULT_STATE)
    cached = _STATE_CACHE.get(key)
    if cached is not None:
        return cached
    p = _path(path)
    try:
        state = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or not isinstance(state.get("cells"), dict):
            state = {"cells": {}, "resolutions": {}}
    except (OSError, ValueError):
        state = {"cells": {}, "resolutions": {}}
    state.setdefault("cells", {})
    state.setdefault("resolutions", {})
    _STATE_CACHE[key] = state
    return state


def _save(state, path=None):
    p = _path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, sort_keys=True, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def cell_of(where: str, why: str) -> str:
    """The address of a recurring fact: (what x how it failed)."""
    w = " ".join(str(where or "?").lower().split())[:80]
    y = " ".join(str(why or "?").lower().split())[:60]
    return w + "|" + y


def _e_value(observations):
    try:
        from canonical.runtime.credit_gates_v1 import e_process
        return e_process(observations, bound=1.0)
    except Exception:
        try:
            from credit_gates_v1 import e_process
            return e_process(observations, bound=1.0)
        except Exception:
            # No gate, no credit. Falling back to a mean would promote
            # almost anything, so we refuse to.
            return {"n": len(observations), "e_value": 0.0, "mean": 0.0}


def _probe_due(entry) -> bool:
    """A suppressed memory must be allowed to be wrong.

    THE DEADLOCK THIS BREAKS. Structural suppression fires on one
    observation and then skips the capability forever -- so it can never
    gather the successes that would lift it. Install the missing package
    and the machine would still refuse, permanently, for a reason that
    stopped being true. That is not memory; it is a grudge.

    So a suppression expires into a single forced retry. Retrying is cheap
    and being wrong forever is not. One success is enough to lift it,
    because suppression requires mean < 0 and a single +1 makes it zero.
    """
    last = float(entry.get("last_seen") or 0.0)
    if not last:
        return False
    return (time.time() - last) > RECHECK_AFTER_S


def status(cell: str, path=None) -> dict:
    state = _load(path)
    entry = state["cells"].get(cell)
    if not entry:
        return {"cell": cell, "n": 0, "e_value": 0.0, "mean": 0.0,
                "credited": False, "suppressed": False,
                "reason": "no evidence yet"}
    e = _e_value(entry["observations"])
    e_value = float(e.get("e_value") or 0.0)
    mean = float(e.get("mean") or 0.0)
    n = int(e.get("n") or 0)
    # DIRECTION, not just magnitude -- see the module docstring.
    credited = bool(e_value >= THRESHOLD and mean > 0)
    probe_due = _probe_due(entry)
    harmful = bool(entry.get("structural") and mean < 0) or bool(
        e_value >= THRESHOLD and mean < 0)
    suppressed = bool(harmful and not probe_due)
    return {"cell": cell, "n": n, "e_value": round(e_value, 3),
            "mean": round(mean, 3), "threshold": round(THRESHOLD, 1),
            "credited": credited, "suppressed": suppressed,
            "structural": bool(entry.get("structural")),
            "probe_due": probe_due,
            "last_seen": entry.get("last_seen"),
            "reason": ("consistent success clears the gate" if credited
                       else ("consistently harmful here" if suppressed
                             else "evidence below the gate after %d observation(s)" % n))}


def record(where: str, why: str, succeeded: bool, structural: bool = False,
           path=None) -> dict:
    """One more fact about how this machine behaves. +1 held, -1 did not."""
    state = _load(path)
    key = cell_of(where, why)
    entry = state["cells"].setdefault(
        key, {"where": str(where), "why": str(why), "observations": [],
              "structural": False, "first_seen": time.time()})
    entry["observations"].append(1 if succeeded else -1)
    if len(entry["observations"]) > MAX_OBSERVATIONS:
        # Keep the tail. The supremum is a running statistic, so the oldest
        # evidence is the least load-bearing part of it.
        entry["observations"] = entry["observations"][-MAX_OBSERVATIONS:]
    if structural:
        entry["structural"] = True
    entry["last_seen"] = time.time()
    _save(state, path)
    return status(key, path=path)


def is_suppressed(capability_id: str, why: str = "", path=None) -> bool:
    """Has this capability earned the right to be left alone on this box?"""
    if why:
        return status(cell_of(capability_id, why), path=path)["suppressed"]
    state = _load(path)
    prefix = " ".join(str(capability_id or "?").lower().split())[:80] + "|"
    return any(status(k, path=path)["suppressed"]
               for k in state["cells"] if k.startswith(prefix))


def signature_of(goal: str) -> str:
    """What makes this question THIS question, as a stable address.

    The distinctive words, not the literal sentence -- so "make a sqlite
    table from these records" and the same request with different file
    names land in the same place, while a genuinely different question
    does not borrow an answer it was never given.
    """
    from canonical.runtime.grounded_action_v1 import _distinctive_goal_tokens
    try:
        toks = _distinctive_goal_tokens(goal)
    except Exception:
        toks = {t for t in re.findall(r"[a-z0-9]+", str(goal or "").lower())
                if len(t) >= 4}
    return "|".join(sorted(toks))


def teach_resolution(goal: str, capability_id: str, path=None) -> dict:
    """Record that this question was settled this way.

    A human said so, and that is a fact rather than a statistic -- so it
    applies on the next occurrence. It is still re-verified every time:
    memory removes the NEED TO ASK, never the need to check.
    """
    state = _load(path)
    sig = signature_of(goal)
    entry = state["resolutions"].setdefault(
        sig, {"goal": str(goal), "capability_id": str(capability_id),
              "taught_at": time.time(), "uses": 0})
    entry["capability_id"] = str(capability_id)
    entry["last_used"] = time.time()
    _save(state, path)
    return dict(entry)


def recall_resolution(goal: str, path=None):
    """Has this question been answered before?"""
    state = _load(path)
    entry = state["resolutions"].get(signature_of(goal))
    if not entry:
        return None
    entry["uses"] = int(entry.get("uses") or 0) + 1
    entry["last_used"] = time.time()
    _save(state, path)
    return entry.get("capability_id")


def observe(goal: str, receipt: dict, path=None) -> dict:
    """Fold one finished action into memory.

    The receipt is the experience: every rejection is a fact about this
    machine, and the outcome is evidence about the capability that was
    used. Nothing here guesses.
    """
    learned = {"recorded": [], "resolution_available": False}

    for rej in (receipt.get("rejected") or []):
        cid = str(rej.get("capability_id") or "")
        why = str(rej.get("why") or "")
        if not cid:
            continue
        if why == "PRECONDITION_NOT_TRUE_OF_WORLD":
            # Recorded, never suppressed: perception re-decides this every
            # run and the world is allowed to change its mind. A memory
            # that outlives the fact it was made of is a lie.
            for blocked in (rej.get("blocked") or []):
                record(cid, str(blocked), False, structural=False, path=path)
                learned["recorded"].append([cid, str(blocked), -1, "noted"])
        # INPUT_KIND_CONTRADICTS_GOAL_FILE is deliberately NOT recorded.
        # It is a fact about this goal's file, recomputed in microseconds
        # by perception; storing it would only hurt the next goal.


    cid = receipt.get("capability_id")
    if cid:
        err = str(receipt.get("error") or "")
        hit = next((r for r in STRUCTURAL_REASONS if r in err), None)
        if hit:
            record(cid, hit, False, structural=True, path=path)
            learned["recorded"].append([cid, hit, -1])
        else:
            ok = bool(receipt.get("verified"))
            reason = "VERIFIED" if ok else (err.split(":")[0][:60] or "FAILED")
            record(cid, reason, ok, structural=False, path=path)
            learned["recorded"].append([cid, reason, 1 if ok else -1])

    learned["resolution_available"] = recall_resolution(goal, path=path) is not None
    return learned


def summary(path=None) -> dict:
    state = _load(path)
    cells = {k: status(k, path=path) for k in sorted(state["cells"])}
    return {
        "schema": SCHEMA,
        "threshold": THRESHOLD,
        "alpha": DEFAULT_ALPHA,
        "cell_count": len(cells),
        "suppressed": sorted(k for k, v in cells.items() if v["suppressed"]),
        "credited": sorted(k for k, v in cells.items() if v["credited"]),
        "resolution_count": len(state.get("resolutions") or {}),
        "cells": cells,
    }
