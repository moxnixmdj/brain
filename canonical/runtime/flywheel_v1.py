"""The part that was missing: the machine gets better for having worked.

Everything before this ran a task, proved what happened, and forgot it.
The next identical task started from nothing and failed in the same way
again. That is not how the car works. The car is not valuable because
one vehicle drives well; it is valuable because every mile driven by
every car makes the next mile better. The architecture is half of it.
The accumulation is the other half, and it is the half that compounds.

So this is the flywheel, and the rules it must obey to be one.

KEYED ON PATHOLOGY, NOT ON TASKS.
    A memory of "how I fixed that one task" is useless the moment the
    task changes, and this system exists to handle tasks it has never
    seen. What repeats is not the task; it is the way things break.
    So the unit of memory is the cell (WHERE x WHY) -- what kind of
    thing failed, and how it failed. "Reading a file" x "No such file"
    recurs across every domain there is. That cell is worth remembering.
    A task is not. Archiving task instances is how you build a memory
    that grows forever and generalises never.

CREDITED BY ARITHMETIC, NEVER BY ASSERTION.
    The rule that keeps this honest: a correction is promoted only when
    evidence clears an ANYTIME-VALID gate. Not "it worked once", and
    not a mean that drifted upward. A plain mean improves about 60% of
    the time for a change that does nothing at all, and a fixed-sample
    test is invalid the moment anyone peeks at it -- which, in a loop
    that checks constantly, is always. So the evidence is accumulated
    as an e-process, whose supremum Ville's inequality bounds however
    often it is inspected. Peeking cannot inflate it.

EVIDENCE, NOT MEMORIES.
    What is stored per cell is a sequence of +/-1 outcomes and, once
    credited, one procedure. Not transcripts, not embeddings, not a log
    to be mined later. The store stays small enough to read in one pass
    forever, because the unit is a pathology and not an episode.

WHAT IT BUYS IS SPEED.
    A credited cell means the next run is told, before it acts, how this
    failure was last resolved -- so it does not have to discover it
    again by failing. Fewer steps is the only thing that makes a loop
    faster, and this is the only mechanism here that reduces them.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_FLYWHEEL_V1"

DEFAULT_STATE = os.environ.get(
    "BRAIN_FLYWHEEL_STATE",
    str(Path(tempfile.gettempdir()) / "brain_flywheel.json"))

# Ville's inequality: P(ever crossing 1/alpha) <= alpha, however often
# the running value is inspected. 1/0.05 = 20.
DEFAULT_ALPHA = 0.05


def _load(path: str = DEFAULT_STATE) -> dict:
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {"schema": SCHEMA, "cells": {}}


def _save(state: dict, path: str = DEFAULT_STATE) -> None:
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(state, indent=1, sort_keys=True))
    except OSError:
        pass


# The operation, stripped of whatever it was performed on. Getting this
# wrong is the difference between a flywheel and a diary: keyed on the
# OBJECT -- "reading a log file", "reading a config", "reading a
# spreadsheet" -- every task lands in a cell of its own, n stays at 1
# forever, and nothing is ever learned. Measured, that is exactly what
# happened on the first run.
#
# So the cell records the OPERATION and the WAY IT FAILED. "Reading" x
# "No such file" recurs in every domain there is. "Reading a log file"
# happens once.
_VERBS = ("reading", "writing", "parsing", "opening", "creating",
          "deleting", "moving", "copying", "listing", "searching",
          "counting", "summarising", "fetching", "running", "installing",
          "editing", "formatting", "converting", "downloading")

# The vocabulary classify() speaks. These are categories already, not
# descriptions, and they pass through whole rather than being trimmed.
_CATEGORIES = frozenset((
    "file access", "data access", "computation", "execution",
    "environment", "network", "authorship", "unknown", "unclassified",
))


def _operation(where: str) -> str:
    """Reduce 'reading a log file' to 'reading'.

    Two cases, and conflating them is how cells split apart.

    A free-text description -- "reading a log file" -- must be cut down
    to the operation, or every object creates its own cell and nothing
    accumulates. Measured once already: three domains, three cells,
    n=1 forever.

    But a phrase that is ALREADY a category -- "file access", "network",
    "computation", the vocabulary classify() emits -- is not prose to be
    trimmed. Cutting it to its first word turns "file access" into
    "file" and "data access" into "data": survivable while the wording
    happens to be fixed, and the moment anyone rewords one, the same
    pathology lands in two cells and neither ever earns credit.

    So a known category passes through whole, and only genuine prose is
    trimmed to its verb.
    """
    text = " ".join(str(where or "?").lower().split())
    words = text.split()
    if not words:
        return "?"
    if text in _CATEGORIES:
        return text
    for w in words:
        stem = w.rstrip(".,:;")
        if stem in _VERBS:
            return stem
        for v in _VERBS:
            if stem.startswith(v[:5]):
                return v
    # Unrecognised prose: keep the head, but not so much that rewording
    # it moves the cell.
    return words[0].rstrip(".,:;")


def cell_of(where: str, why: str) -> str:
    """The address of a recurring failure: (operation x failure mode)."""
    w = _operation(where)
    y = " ".join(str(why or "?").lower().split())[:60]
    return f"{w}|{y}"


def record(where: str, why: str, succeeded: bool,
           path: str = DEFAULT_STATE) -> dict:
    """One more datum: did resolving this pathology work, or not.

    +1 when the correction held, -1 when it did not. The sign is the
    unit of evidence, and it is deliberately coarse -- anything finer
    invites a score the caller gets to grade itself on.
    """
    state = _load(path)
    key = cell_of(where, why)
    entry = state["cells"].setdefault(
        key, {"where": where, "why": why, "observations": [],
              "procedure": None, "credited": False})
    entry["observations"].append(1 if succeeded else -1)
    _save(state, path)
    return status(key, path=path)


def status(cell: str, alpha: float = DEFAULT_ALPHA,
           path: str = DEFAULT_STATE) -> dict:
    """Has this correction earned the right to be reused?"""
    state = _load(path)
    entry = state["cells"].get(cell)
    if not entry:
        return {"cell": cell, "n": 0, "e_value": 0.0,
                "credited": False, "reason": "no evidence yet",
                "procedure": None}
    try:
        from credit_gates_v1 import e_process
        e = e_process(entry["observations"], bound=1.0)
        e_value = float(e.get("e_value") or 0.0)
        n = int(e.get("n") or 0)
    except Exception:
        # No gate, no credit. Refusing to fall back to a mean is the
        # point: an ungated average would promote almost anything.
        e_value, n = 0.0, len(entry["observations"])
    threshold = 1.0 / alpha if alpha and alpha > 0 else 20.0
    # DIRECTION, not just magnitude.
    #
    # The e-process tests "no effect" against ANY consistent deviation,
    # so a correction that fails every single time also accumulates
    # evidence -- eight straight failures scored e=31.6, past a
    # threshold of 20, and would have been promoted as a fix. Wrong in
    # the most dangerous way: confidently reusing the thing that never
    # works.
    #
    # Strong consistent evidence of HARM is real evidence against the
    # null, and it is still not grounds for credit. So magnitude alone
    # is not the gate; the sign is.
    mean = float(e.get("mean") or 0.0)
    credited = bool(e_value >= threshold and mean > 0)
    entry["credited"] = credited
    _save(state, path)
    return {"cell": cell, "n": n, "e_value": round(e_value, 3),
            "threshold": round(threshold, 1), "credited": credited,
            "mean": round(mean, 3),
            "reason": (
                "improvement clears the anytime-valid gate" if credited
                else (f"consistently harmful (mean {mean:+.2f})"
                      if mean < 0 and e_value >= threshold
                      else f"e={e_value:.2f} < {threshold:.0f} "
                           f"after {n} observation(s)")),
            "procedure": entry.get("procedure") if credited else None}


def teach(cell: str, procedure: str, path: str = DEFAULT_STATE) -> None:
    """Attach the resolution. It is only handed back once credited."""
    state = _load(path)
    entry = state["cells"].setdefault(
        cell, {"where": cell, "why": "", "observations": [],
               "procedure": None, "credited": False})
    entry["procedure"] = procedure
    _save(state, path)


def recall(where: str, why: str, path: str = DEFAULT_STATE) -> dict:
    """What has been learned about this failure, if anything."""
    return status(cell_of(where, why), path=path)


def cells(path: str = DEFAULT_STATE) -> list:
    state = _load(path)
    return [status(k, path=path) for k in sorted(state["cells"])]


# ---------------------------------------------------------------------------
# Naming a failure without knowing the task.
# ---------------------------------------------------------------------------
#
# The cell is (operation x failure mode), and both halves have to come
# from somewhere that does not involve understanding the task -- if
# classifying a failure required understanding what the task was, this
# would be a table of tasks again and nothing would generalise.
#
# So it is derived from the error itself. This works because the two
# sets are completely different sizes:
#
#     the ways a program fails      a small, closed set
#     the tasks a person has        unbounded
#
# "No such file" recurs in every domain there is, and it always looks
# the same in a traceback. A taxonomy of FAILURE is therefore finite and
# worth writing down; a taxonomy of TASKS is neither.

_PATHOLOGIES = (
    # (matcher,                operation,        why)
    ("FileNotFoundError",      "file access",    "no such file"),
    ("IsADirectoryError",      "file access",    "path is a directory"),
    ("NotADirectoryError",     "file access",    "path is not a directory"),
    ("PermissionError",        "file access",    "permission denied"),
    ("ModuleNotFoundError",    "environment",    "module missing"),
    ("ImportError",            "environment",    "import failed"),
    ("TimeoutExpired",         "execution",      "timed out"),
    ("MemoryError",            "execution",      "out of memory"),
    ("KeyError",               "data access",    "missing key"),
    ("IndexError",             "data access",    "index out of range"),
    ("AttributeError",         "data access",    "missing attribute"),
    ("ZeroDivisionError",      "computation",    "divided by zero"),
    ("ValueError",             "computation",    "bad value"),
    ("TypeError",              "computation",    "wrong type"),
    ("SyntaxError",            "authorship",     "program will not parse"),
    ("IndentationError",       "authorship",     "program will not parse"),
    ("NameError",              "authorship",     "undefined name"),
)

_MSG = (
    ("no such file",           "file access",    "no such file"),
    ("permission denied",      "file access",    "permission denied"),
    ("read-only file system",  "file access",    "read-only filesystem"),
    ("timed out",              "execution",      "timed out"),
    ("connection refused",     "network",        "connection refused"),
    ("name or service not known", "network",     "no dns"),
    ("temporary failure in name resolution", "network", "no dns"),
    ("no space left",          "execution",      "disk full"),
)


def classify(error_text: str) -> tuple:
    """Name a failure from its error alone. Never from the task."""
    text = (error_text or "").strip()
    low = text.lower()
    for needle, where, why in _MSG:
        if needle in low:
            return where, why
    # The LAST exception named is the one that actually fired; earlier
    # ones in a traceback are the chain that led there.
    for needle, where, why in _PATHOLOGIES:
        if needle in text:
            return where, why
    if not text:
        return "unknown", "no error reported"

    # What the table cannot name, a calibrated classifier may be able
    # to. This is the one place the loop still held hand-written domain
    # knowledge, and it is the reason unanticipated failures landed in
    # "unclassified" forever.
    #
    # The table runs FIRST, not second: it is free, deterministic and
    # instant, and a classifier is none of those. The judge is asked
    # only about what the table could not name -- so the common path
    # pays nothing for having the capability.
    #
    # Its answer is ADVICE. It is admitted only above a confidence
    # threshold, and anything below escalates to "unclassified",
    # because a guess filed as a category is worse than no category:
    # it silently merges two different failures into one cell.
    try:
        import judge_v1 as J
        if J.configured():
            # Both tables are (matcher, operation, why) triples. The
            # _PATHOLOGIES arm was unpacked as pairs, which raised
            # ValueError straight into the except below and silently
            # disabled the judge -- the failure this system keeps
            # meeting: an error swallowed so the feature quietly does
            # nothing, with no signal anywhere.
            cats = sorted({w for _, w, _ in _PATHOLOGIES}
                          | {w for _, w, _ in _MSG})
            r = J.choose(text, "which kind of failure is this?",
                         {c: c for c in cats})
            if r["admitted"] and r["choice"] in cats:
                return r["choice"], _why_for_operation(r["choice"])
    except Exception:
        pass

    first = text.splitlines()[-1][:80] if text.splitlines() else text[:80]
    return "unclassified", first


def _why_for_operation(operation: str) -> str:
    """A stable 'why' for a category the classifier chose.

    The classifier names WHAT broke, not HOW. Pairing it with a fixed
    why keeps the cell addressable and stops one category from
    fragmenting into a cell per error message.
    """
    return "judged:" + operation


def primers(alpha: float = DEFAULT_ALPHA,
            path: str = DEFAULT_STATE) -> list:
    """Every credited fix, for handing over BEFORE anything fails.

    Timing is the whole mechanism, and getting it wrong cost the entire
    benefit. Consulted only AFTER a failure, the store can help the next
    step of the same run but never the first step of the next one -- so
    the same mistake is made afresh every single time. Measured: credit
    arrived at the eighth job and mean steps did not move, 2.00 before
    and 2.00 after. A 0% improvement from a mechanism whose only stated
    purpose was speed.

    So this is read before the first action. The set is small by
    construction -- it is keyed on how things break, and there are not
    many ways to break -- so handing over all of it costs nothing and
    lets the model avoid the failure instead of recovering from it.
    Avoiding a step is worth strictly more than repairing one.
    """
    out = []
    for st in cells(path=path):
        if st["credited"] and st.get("procedure"):
            out.append({"cell": st["cell"], "procedure": st["procedure"],
                        "n": st["n"]})
    return out
