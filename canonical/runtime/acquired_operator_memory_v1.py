"""An operator the creature INDUCED must outlive the process that induced it.

THE MEASUREMENT THAT STARTED THIS.

    acquire_from_examples("spreadish", examples=[[1,2,3]->3, [10,20,30]->30])
        acquired            True
        arithmetic          sum(v)-max(v)
        same process        "spreadish" in aggregate_names()   True
        FRESH PROCESS       "spreadish" in aggregate_names()   False

The creature can genuinely induce an operator from worked examples -- not look one up, not
take a name on trust, but narrow a generated family of composed primitives down to the one
function that reproduces what it was shown. That is the most impressive thing in this
repository and it was being thrown away.

It is the same defect as the answer cache, one layer deeper. `answer()` was a pure function
of (question, tree); now the decomposition law remembers. But `value_algebra_v1._AGGREGATES`
is a module-level dict populated from a literal, so every process starts with exactly the
vocabulary a human typed into that literal. Learning could not accumulate. A system that
learns and forgets is static code with an interesting moment in the middle.

WHY THIS DOES NOT STORE CODE.

The obvious implementation persists the candidate's `fn` and re-executes it. That would be
arbitrary code from a JSON file, and this repository already contains a guard that refuses
exactly that shape. It is also unnecessary, and the reason is worth stating because it is
the whole design:

    THE DEMONSTRATION IS THE OPERATOR.

A word's meaning, in this system, is *the set of candidate arithmetics that reproduce the
examples it was taught with*. `acquire_from_examples` refuses when the examples leave more
than one such candidate standing, so at the moment of acquisition the examples already pin
down exactly one function out of the generated family. Storing the examples therefore
stores everything needed to rebuild the operator -- and rebuilding is a RE-DERIVATION, not
a replay: the same gates run again (`_usable`, `induce_laws`, `_law_is_falsifiable`,
`indistinguishable_from`), so an operator whose arithmetic stopped satisfying its declared
law would be refused on load rather than trusted.

    Memorising an answer would let the system be wrong about something it was right about
    before. Re-deriving does not, because the thing re-derived is checked on the way in.

Memory removes the need to be TAUGHT again. It never removes the need for the teaching to
have been real. That is the same rule `experience_v1.teach_resolution` states for itself:
"memory removes the NEED TO ASK, never the need to check."

WHAT IS DELIBERATELY NOT HERE.

No word is ever mapped to a function because that word "usually means" it. `median` with one
example leaves three candidates and is refused; two examples still leave three (a four-point
form, an interpolating form, and a parity-split form all agree), and it is refused. A
hand-typed word table was rejected three times on this project and this module does not
smuggle one back in.

An operator is also never acquired from a word alone. `operator_acquisition_v1.acquire()`
exists and is deliberately useless: "the word alone does not say which one is meant."
"""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE = "canonical/runtime/state/acquired_operators_v1.json"

#: Nothing here is trusted for longer than it takes to re-check it, so this is a plain
#: cache of state rather than a cache of conclusions.
_STATE_CACHE: dict[str, dict] = {}


def _path(path=None) -> Path:
    return ROOT / (path or DEFAULT_STATE)


def _load(path=None) -> dict:
    key = str(path or DEFAULT_STATE)
    if key in _STATE_CACHE:
        return _STATE_CACHE[key]
    p = _path(path)
    try:
        state = json.loads(p.read_text())
    except (OSError, ValueError):
        state = {}
    if not isinstance(state, dict):
        state = {}
    state.setdefault("taught", {})
    _STATE_CACHE[key] = state
    return state


def _save(state: dict, path=None) -> None:
    p = _path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n")
    os.replace(tmp, p)
    _STATE_CACHE[str(path or DEFAULT_STATE)] = state


def _coerce_examples(examples) -> list[list]:
    """Examples are (values, answer) and both parts must survive a JSON round trip."""
    out = []
    for values, answer in examples:
        out.append([[float(v) for v in values], float(answer)])
    return out


def teach(kind: str, words, examples, path=None) -> dict:
    """Acquire an operator by example and REMEMBER the demonstration that acquired it.

    Returns the acquisition result, with `remembered` added. Nothing is remembered unless
    acquisition actually succeeded -- a refusal has no operator behind it to remember, and
    storing the failed attempt as though it were knowledge is how a cache becomes a lie.
    """
    from canonical.runtime import operator_acquisition_v1 as A

    pairs = [(tuple(v), a) for v, a in examples]
    result = dict(A.acquire_from_examples(kind, words, pairs))
    if not result.get("acquired"):
        return result

    state = _load(path)
    state["taught"][str(kind)] = {
        "words": sorted(str(w).strip().lower() for w in words),
        "examples": _coerce_examples(examples),
        "arithmetic": result.get("arithmetic"),
    }
    _save(state, path)
    result["remembered"] = True
    return result


def recall(path=None) -> list[dict]:
    """Everything that was ever taught, newest vocabulary included."""
    return [dict(kind=k, **v) for k, v in _load(path).get("taught", {}).items()]


def restore(path=None) -> dict:
    """Re-derive every taught operator into this process. Called once, on import by the door.

    A taught operator that no longer re-derives is REPORTED, not silently dropped and not
    trusted anyway: its demonstration no longer identifies a function, which means either
    the candidate family changed or the declaration stopped passing its own gates. Either
    way the creature is owed a truthful account of what it still knows.
    """
    from canonical.runtime import operator_acquisition_v1 as A
    from canonical.runtime import value_algebra_v1 as V

    restored, already, failed = [], [], []
    for row in recall(path=path):
        kind = row["kind"]
        if kind in V.aggregate_names():
            already.append(kind)
            continue
        pairs = [(tuple(v), a) for v, a in row.get("examples") or []]
        try:
            result = A.acquire_from_examples(kind, set(row.get("words") or ()), pairs)
        except Exception as exc:  # noqa: BLE001 -- one bad row must not stop the rest
            failed.append({"kind": kind, "why": f"{type(exc).__name__}: {exc}"})
            continue
        if result.get("acquired"):
            restored.append(kind)
        else:
            failed.append({"kind": kind, "why": result.get("reason"),
                           "detail": result.get("detail")})
    return {"restored": restored, "already_declared": already, "failed": failed}
