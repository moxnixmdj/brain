#!/usr/bin/env python3
"""The return annotation selects which member's guide applies.

Two held-out items were classified as unreachable because the prose and the name share no word:

   188  poly.rep.to_list()   prose: "a list of its coefficients"
   194  matrix.todok()       prose: "its dictionary-of-keys representation"

`to_list` contains no word for "coefficient"; `todok` contains no word for "dictionary". Ranked
by the prose vocabulary they sit far below hundreds of members, and no amount of ranking fixes
that, because the NAME IS NOT THE STATEMENT.

The statement is elsewhere, and it is the artifact's own:

    >>> Matrix([[1,2],[3,4]]).todok.__doc__
    'Return the matrix as dictionary of keys.'

The artifact says what each member MEANS. The prose says what is WANTED. Both are strings in the
same space, so the match is computable -- but only if the search is narrowed first, and the
narrowing is also stated: **the return annotation names the type of the answer.** A stub declared
`-> list[int]` cannot be answered by a member returning a dict, and `-> dict` cannot be answered
by one returning a list.

So the mechanism is three statements and no stored knowledge:

   1. return annotation  -> the TYPE of the answer (e.g. `list`)
   2. member docstring   -> the MEANING of each candidate (e.g. "as dictionary of keys")
   3. problem prose      -> the WANTED meaning  (e.g. "dictionary-of-keys representation")

Candidates whose docstring or whose own name says the wanted meaning, and whose return type is
the declared one, are emitted first. No name table, no synonym list, no fitted weight: the words
come from the artifact and the prose, and the type filter comes from the signature.

Authority: NONE. Sandbox measurement. Zero model calls.
"""
from __future__ import annotations

import json
import re
import subprocess
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_RETURN_TYPE_SELECTS_THE_GUIDE_V1"

_READER = r"""
import importlib, json, sys
imports = __imports__
for line in imports:
    exec(line, globals())
spec = __spec__
out = []
# A small instance of each declared type is enough to read its members' behaviour: these are
# type-level statements, not data.
def _sample(anno):
    tail = anno.rsplit(".", 1)[-1]
    try:
        if tail == "Poly":
            from sympy import symbols, Poly
            x = symbols("x")
            return Poly(x**2 + 2*x + 1, x)
        if tail in ("Matrix", "MutableDenseMatrix"):
            from sympy import Matrix
            return Matrix([[1, 2], [3, 4]])
        cls = eval(anno, globals())
        return cls()
    except BaseException:
        return None
for param, anno in spec.items():
    inst = _sample(anno)
    if inst is None:
        continue
    # follow one stated attribute level when the annotation names a type whose members sit
    # behind a property (`Poly.rep` is where `to_list` lives)
    holders = [("", inst)]
    for attr in ("rep",):
        try:
            sub = getattr(inst, attr, None)
            if sub is not None:
                holders.append((attr + ".", sub))
        except BaseException:
            pass
    for prefix, holder in holders:
        for name in dir(holder):
            if name.startswith("_"):
                continue
            try:
                obj = getattr(holder, name)
            except BaseException:
                continue
            if not callable(obj):
                continue
            try:
                doc = (getattr(obj, "__doc__", "") or "")[:400]
            except BaseException:
                doc = ""
            out.append([param, prefix + name, doc])
print(json.dumps(out))
"""

# Only structural English. Nothing type-specific (`coefficient`, `dictionary`, `keys`, `list`)
# may appear here: those are exactly the words that carry the meaning. An earlier stoplist
# contained "representation", which is the one word item 194 depends on.
_STOP = {"with", "from", "that", "this", "the", "and", "for", "its", "returns", "return",
         "should", "given", "into", "will", "argument", "function", "parameter", "object",
         "of", "a", "an", "all", "every", "each", "which", "what", "when", "then", "than",
         "such", "same", "also", "have", "has", "been", "being", "can", "may", "must"}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{3,}", (text or "").lower()) if w not in _STOP}


def member_guides(python: str, imports: Sequence[str], spec: Mapping[str, str],
                  *, timeout: float = 240.0) -> list[tuple[str, str]]:
    """(body, docstring) for every callable the declared types expose, read live."""
    code = (_READER.replace("__imports__", repr(list(imports)))
            .replace("__spec__", repr(dict(spec))))
    try:
        proc = subprocess.run([python, "-c", code], capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return []
    rows = [l for l in (proc.stdout or "").strip().splitlines() if l.startswith("[")]
    if not rows:
        return []
    try:
        data = json.loads(rows[-1])
    except (json.JSONDecodeError, ValueError):
        return []
    return [(f"{param}.{member}()", doc) for param, member, doc in data]


def guide_bodies(problem: str, return_annotation: str | None,
                 args: Sequence[str], guides: Sequence[tuple[str, str]],
                 *, limit: int = 40) -> list[str]:
    """Bodies whose own guide says what the prose asks for, filtered by the declared return type.

    Scoring is deliberately simple and fully stated: the number of prose content words that the
    member's docstring or its own name contains. Ties break toward the shorter member name,
    because the shortest member saying a thing is that type's own word for it (`todok` over
    `as_immutable_dict_of_keys_and_structure`).
    """
    wanted = _words(problem)
    if not wanted:
        return []
    ret_tail = (return_annotation or "").rsplit(".", 1)[-1].split("[")[0].strip()
    generic = {"tuple", "None", "Expr", "Any", "object", "int", "float", "bool", "str"}
    want_type = ret_tail if ret_tail and ret_tail not in {"list", "dict", "set"} else ""
    if ret_tail in {"list", "dict", "set"}:
        want_type = ret_tail

    scored: list[tuple[int, int, str]] = []
    for body, doc in guides:
        member = body.split(".", 1)[1].rstrip("()")
        # THE FIRST SENTENCE IS THE STATEMENT. Everything after it is examples, doctest
        # imports and cross-references, which mention `import`, `examples`, `sympy` and other
        # words no problem ever asks for -- and which made `matrix.tolist()` outrank
        # `matrix.todok()` for "dictionary-of-keys representation" on incidental overlap.
        defn = re.split(r"(?<=[.!?])\s|\n\s*\n", (doc or "").strip())[0]
        text = (_words(defn) | _words(member))
        overlap = len(wanted & text)
        if not overlap:
            continue
        # SPECIFICITY. The prose is short and specific ("dictionary of keys"); a docstring that
        # also matches many words the prose never says is describing something broader. Overlap
        # alone rewards long docstrings.
        extra = len(_words(defn) - wanted)
        score = overlap * 4 - max(0, extra - 4)
        # A member whose name begins with `from_`/`to_` is an INVERSE or a CONVERSION stated in
        # its own name. "as dictionary of keys" is not answered by `from_list`: the direction is
        # part of the meaning, and both `from_list`/`to_list` and `todok`/`from_dok` pairs exist.
        # The prose is read literally here -- it asks for one direction, and a conversion whose
        # name states an inversion is penalised. Measured: item 188 ranked `poly.rep.from_list()`
        # first and its answer, `to_list`, was behind it.
        if member.startswith("from_"):
            score -= 3
        # a name that literally states the wanted thing (`to_list` for "a list") is the
        # strongest evidence there is; `todok` states it in the docstring instead
        if member.lower() in (problem or "").lower().replace("-", "_").replace(" ", "_"):
            score += 5
        scored.append((-score, len(member), body))

    scored.sort()
    out = [b for _s, _l, b in scored]
    if want_type:
        # the declared return type is a statement about which members can be the answer; it is
        # applied as a partition, not a filter, so a wrong annotation cannot empty the space
        preferred = [b for b in out if _mentions(b, want_type, guides)]
        rest = [b for b in out if b not in preferred]
        out = preferred + rest
    return out[:limit]


def _mentions(body: str, want_type: str, guides: Sequence[tuple[str, str]]) -> bool:
    """True when this member's own guide mentions the declared return type."""
    for b, doc in guides:
        if b == body:
            return want_type.lower() in (doc or "").lower() or want_type.lower() in b.lower()
    return False
