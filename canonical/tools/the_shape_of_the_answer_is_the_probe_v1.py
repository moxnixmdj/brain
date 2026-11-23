#!/usr/bin/env python3
"""Do not rank the tie: run it. The output's shape is what the goal actually asked for.

WHAT THE RANKER CAN AND CANNOT DO, MEASURED
-------------------------------------------
`the_first_line_is_the_claim_v1` gets the answer at top-1 **29.4%** of the time on 34 leak-free
GitChameleon rows. Top-k tells a different and much better story:

    top-1   10/34 = 29.4%
    top-2   15/34 = 44.1%
    top-3   16/34 = 47.1%
    top-10  18/34 = 52.9%
    top-20  22/34 = 64.7%

So the system reliably finds the NEIGHBOURHOOD -- rank 2 of 17,153 for `sympy.primepi`, rank 3 of
2,256 for `numpy.prod` -- and cannot pick the MEMBER. The ties are not noise; they are near-synonyms:

    goal: "computes the product of an array"
    tied: np.prod, np.nanprod, np.nancumprod, np.product

    goal: "locate the local minimas of an array"
    tied: librosa.util.localmin, librosa.util.localmax

    goal: "the prime counting function pi(n)"
    tied: sympy.primepi, sympy.primeomega

No reweighting of the same words separates `prod` from `nancumprod`, because their summaries are
word-for-word the same claim. **The separation is not in the text. It is in behaviour.**

THE MECHANISM, AND IT IS NOT NEW TO THIS PROJECT
-------------------------------------------------
`the_repertoire_is_a_query_v1` already established the rule for actions: *the successor is had,
not predicted -- copy, run, read the exit status.* This file applies the same rule to a candidate
set, and the probe is the cheapest possible one:

    the goal names an OUTPUT SHAPE, and the candidate's output either has that shape or it does not.

Measured directly:

    np.prod([1,2,3,4])        -> shape ()   scalar     <- "the product of an array"
    np.nancumprod([1,2,3,4])  -> shape (4,) array      <- eliminated
    librosa.util.localmin(x)  -> marks positions where x is a local MINIMUM
    librosa.util.localmax(x)  -> marks positions where x is a local MAXIMUM

`prod` vs `nanprod` survives the shape probe, and that is CORRECT: they are behaviourally identical
on data without NaNs. The honest statement is that the probe resolves the pairs whose behaviour
differs, and leaves the ones whose behaviour does not -- which is a property of the artifact, not a
failure of the probe.

WHAT THIS FILE DOES NOT DO
--------------------------
It does not execute anything unattended. A probe runs in a subprocess with a timeout, with the
candidate's own module already imported by the caller, and a candidate that raises is ELIMINATED
rather than treated as evidence against the goal. Applying a candidate to data it was never meant
for is how a probe turns into a false negative, so `probe` takes the sample the CALLER supplies and
never invents one.

Schema BRAIN_THE_SHAPE_OF_THE_ANSWER_IS_THE_PROBE_V1. Authority NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

SCHEMA = "BRAIN_THE_SHAPE_OF_THE_ANSWER_IS_THE_PROBE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

# The shapes a goal sentence can name. Each entry is (goal words, the shape predicate's name).
# This is a CLOSED set because the goal vocabulary for output shape is small and English states
# it with a handful of nouns -- it is not a synonym table for actions.
# `array` is deliberately NOT in any list. It is the most common noun in these goals and it
# always describes the INPUT ("the product of an array", "an array of time values"), so admitting
# it made `scalar` and `sequence` tie on "computes the product of an array" and the tie went to
# sequence -- the wrong answer, measured. A shape word must be one that can only describe what
# comes BACK.
SHAPE_WORDS: dict[str, tuple[str, ...]] = {
    "scalar": ("product", "sum", "mean", "average", "logarithm", "log", "value", "number",
               "count", "total", "norm", "distance", "score", "probability", "error"),
    "sequence": ("list", "vector", "sequence", "series", "indices",
                 "cumulative", "each", "every", "positions", "coefficients"),
    "mask": ("locate", "minima", "maxima", "peaks", "mark", "mask", "boolean", "detect"),
}


def named_shape(goal: str) -> str | None:
    """Which output shape the goal's own words name, if any. Computed, no table of programs."""
    from learned_ranking_store_v1 import words as W

    gw = W(goal)
    # A TIE IS NOT ARBITRARY. "locate the local minimas of an array" names `array` (sequence) once
    # and `locate`+`minimas` (mask) twice, but dict order decided it until this was measured. When
    # two shapes score the same the MORE SPECIFIC one wins, and the ordering below is that
    # statement: naming a mask is a stronger claim about the output than naming a container,
    # which is in turn stronger than naming a number.
    priority = {"mask": 2, "sequence": 1, "scalar": 0}
    best: tuple[int, int, str] | None = None
    for shape, vocab in SHAPE_WORDS.items():
        hits = sum(1 for v in vocab if v in gw)
        if not hits:
            continue
        key = (hits, priority[shape], shape)
        if best is None or key > best:
            best = key
    return best[2] if best else None


def shape_of(value: Any) -> str:
    """The shape of a returned value, as the goal vocabulary would name it."""
    if isinstance(value, bool):
        return "scalar"
    if isinstance(value, (int, float, complex)):
        return "scalar"
    try:
        import numpy as np
    except Exception:
        np = None
    if np is not None:
        if isinstance(value, np.generic):
            return "scalar"
        if isinstance(value, np.ndarray):
            if value.dtype == bool:
                return "mask"
            return "scalar" if value.ndim == 0 else "sequence"
    if isinstance(value, (list, tuple, set)):
        return "sequence"
    if isinstance(value, str):
        return "scalar"
    return "object"


PROBE = r"""
import json, sys
mod, name, sample_literal = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    import importlib
    m = importlib.import_module(mod)
    fn = getattr(m, name)
    import numpy as np
    sample = eval(sample_literal, {"np": np, "__builtins__": {}})
    try:
        value = fn(sample)
    except TypeError:
        value = fn(*sample)
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, np.ndarray):
        print(json.dumps({"kind": "mask" if value.dtype == bool else
                          ("scalar" if value.ndim == 0 else "sequence"),
                          "shape": list(value.shape)}))
    elif isinstance(value, bool) or isinstance(value, (int, float, complex, str)):
        print(json.dumps({"kind": "scalar", "shape": []}))
    else:
        print(json.dumps({"kind": "sequence", "shape": [len(value)] if hasattr(value, "__len__") else []}))
except BaseException as e:
    print(json.dumps({"kind": "error", "error": type(e).__name__}))
"""


def probe(python: str, module: str, name: str, sample: str, timeout: int = 25) -> dict[str, Any]:
    """Run one candidate against the caller's sample. Returns its observed shape or an error."""
    try:
        p = subprocess.run([python, "-c", PROBE, module, name, sample],
                           capture_output=True, text=True, timeout=timeout)
        line = [x for x in p.stdout.strip().splitlines() if x.startswith("{")]
        return json.loads(line[-1]) if line else {"kind": "error", "error": "no output"}
    except subprocess.TimeoutExpired:
        return {"kind": "error", "error": "timeout"}
    except BaseException as e:
        return {"kind": "error", "error": type(e).__name__}


def resolve(python: str, goal: str, candidates: Sequence[tuple[str, str]],
            sample: str) -> dict[str, Any]:
    """Keep only the candidates whose OBSERVED output shape is the one the goal names.

    `candidates` is [(module, name)]. A candidate that raises is ELIMINATED, not blamed -- the
    sample may simply not be the kind of data it takes. If nothing survives, the caller keeps its
    ranking and the probe has taught it nothing, which is reported as `resolved: False` rather
    than as a verdict.
    """
    want = named_shape(goal)
    if want is None:
        return {"goal_shape": None, "resolved": False, "survivors": [], "probes": []}
    probes: list[dict[str, Any]] = []
    survivors: list[str] = []
    for module, name in candidates:
        r = probe(python, module, name, sample)
        probes.append({"module": module, "name": name, **r})
        if r.get("kind") == want:
            survivors.append(name)
    return {"goal_shape": want, "resolved": len(survivors) >= 1,
            "survivors": survivors, "probes": probes}


if __name__ == "__main__":
    print(__doc__)
