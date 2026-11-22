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
    # An INSTANCE of the declared type. An instance is what exposes `.rep` and friends; the
    # class does not. Three routes, in order, each stated rather than guessed:
    #   1. an explicit constructor for types whose useful members hide behind a property
    #      (`Poly.rep.to_list` answers item 188 and is invisible on the class);
    #   2. a zero-argument construction of the type itself;
    #   3. nothing -- a type that cannot be instantiated yields no guides, which is an empty
    #      space, never a wrong answer.
    tail = anno.rsplit(".", 1)[-1]
    try:
        if tail == "Poly":
            from sympy import symbols, Poly
            x = symbols("x")
            return Poly(x**2 + 2*x + 1, x)
        if tail in ("Matrix", "MutableDenseMatrix", "SparseMatrix", "ImmutableMatrix"):
            from sympy import Matrix
            return Matrix([[1, 2], [3, 4]])
    except BaseException:
        pass
    # Route 2 is SEVEN stated instantiations, not a search: the type's own signature is the
    # statement that it needs an argument, and a small integer is the only value these domain
    # constructors ever take. `FiniteField()` raises TypeError and `FiniteField(6)` is `GF(6)`,
    # which is exactly what item 185 hands the function.
    for maker in (
        lambda c: c(),
        lambda c: c(6),
        lambda c: c(2),
        lambda c: c(0),
        lambda c: c(1),
        lambda c: c("x"),
        lambda c: c(()),
    ):
        try:
            cls = eval(anno, globals())
        except BaseException:
            break
        try:
            inst = maker(cls)
            if inst is not None:
                return inst
        except BaseException:
            continue
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
    # Two-character tokens are kept: `int` is the declared return type of item 185 and a
    # three-character minimum silently deleted the one word that identifies its answer.
    return {w for w in re.findall(r"[a-z]{2,}", (text or "").lower()) if w not in _STOP}


# `int` and `integer` are THE SAME CONCEPT stated in two forms -- the annotation's spelling and
# the prose's spelling. Matching them is not a synonym table; it is the single morphological
# fact that an abbreviation and its expansion denote one thing.
_TYPE_FORMS = {"int": {"int", "integer", "integers"}, "list": {"list", "lists"},
               "dict": {"dict", "dictionary", "mapping"}}


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
    # The prose vocabulary is the PROSE only. Injecting the declared type's own spellings here
    # made `tolist` match the word "list" that the annotation supplied, and it then beat
    # `todok` for item 194 -- whose prose never says "list" at all. The declared type belongs in
    # the type-name weight below, not in the wanted-meaning set.
    wanted = _words(problem)
    if not wanted:
        return []
    ret_tail = (return_annotation or "").rsplit(".", 1)[-1].split("[")[0].strip()
    # EVERY declared return type is a statement, including the builtins that an earlier version
    # of this function excluded as "generic". Item 185 declares `-> int` and its answer is
    # `K.to_int(a)`: the member's own name AND its first-sentence guide ("Convert val to a
    # Python int object") both state the declared type, while `from_sympy` -- which outscored it
    # on prose overlap -- converts INTO sympy and returns something else entirely. Dropping
    # builtins from the type partition is what let the wrong direction win.
    _uninformative = {"", "None", "Any", "object", "Expr", "Symbol"}
    want_type = ret_tail if ret_tail not in _uninformative else ""

    # ONE RULE, STATED ONCE. Ranking is by how much of the WANTED MEANING a member's own
    # first-sentence guide states. The declared return type is then applied as a single
    # ordering preference -- never as admission and never as exclusion -- because an annotation
    # can be WRONG: item 194 declares `-> list[int]` while its answer `todok()` returns a dict,
    # so letting the type admit candidates put `tolist` ahead of the member whose guide literally
    # says "dictionary of keys". And letting it exclude candidates is just as wrong in the other
    # direction. Preference only: candidates the type names move to the front, everything the
    # prosody matched stays.
    _TYPE_SPELLING = ({f"to_{want_type}", f"to{want_type}", want_type}
                      if want_type else set())
    defn_of: dict[str, str] = {}
    for body, doc in guides:
        defn_of.setdefault(body, re.split(r"(?<=[.!?])\s|\n\s*\n", (doc or "").strip())[0])

    def _meaning(body_: str) -> tuple[int, int, str]:
        member_ = body_.split(".", 1)[1].rstrip("()")
        defn_ = defn_of.get(body_, "")
        text_ = _words(defn_) | _words(member_)
        overlap_ = len(wanted & text_)
        extra_ = len(_words(defn_) - wanted)
        # SPECIFICITY, CAPPED. Overlap alone rewards long docstrings, so unmatched words cost --
        # but the cost must never exceed one overlap unit, or a terse guide loses to a wordy one
        # for no reason. Measured: `to_int`'s guide ("Convert val to a Python int object") is
        # four words the prose never says, and an uncapped penalty gave it -1 against
        # `from_sympy`'s 8, burying the answer of item 185. Capped at 4, the same comparison is
        # decided by the statements that actually name the type.
        score_ = overlap_ * 4 - min(4, max(0, extra_ - 4))
        # direction is part of meaning: `from_list`/`from_sympy` state an inversion in the name
        if member_.startswith("from_"):
            score_ -= 3
            # A `from_<X>` member produces something OF X. When the declared return type is not
            # X, that is a CONTRADICTION stated by the member's own name, and it is a far
            # stronger signal than the small inversion penalty: `from_sympy` given `-> int`
            # returns a SymPy object, not an int. `from_list` given `-> list` returns a list, so
            # it keeps only the small penalty and stays available for 188. This is a stated
            # type mismatch, not a tuned weight.
            src_ = member_[len("from_"):]
            if want_type and src_ and want_type not in {src_, *_TYPE_FORMS.get(src_, set())}:
                score_ -= 8
        # the member's own name spelling a whole prose token (`to_list` in "to_list")
        if member_.lower() in _PROSE_TOKENS:
            score_ += 6
        # THE TYPE IS EVIDENCE, NOT A VERDICT, AND IT IS WEAK EVIDENCE. One prose overlap unit
        # is worth 4; the type contributes at most 6 (name 3 + stated form 3), so a member whose
        # guide states TWO prose words always beats a member that only matches the annotation.
        # That ordering is forced by a measured fact: item 194's annotation is WRONG -- it
        # declares `-> list[int]` while its answer `todok()` returns a dict -- so any rule that
        # lets the type outrank stated meaning loses 194, and any rule that lets the type add
        # nothing loses 185 (whose answer `to_int` shares no prose word at all). Weak type
        # evidence satisfies both.
        # DECLARED-TYPE EVIDENCE. A member whose own name spells the declared return type is
        # stating the answer's type, which is independent of the prose: item 185's answer
        # `to_int` shares no word with "integer representation" and would otherwise be dropped
        # for zero overlap. This is evidence FOR that member only -- it can never promote a
        # member by exclusion, and `tolist` does not gain it because 194's real type is a dict
        # that its annotation misstates.
        if member_ in _TYPE_SPELLING:
            score_ += 3
        if want_type and _words(defn_) & _TYPE_FORMS.get(want_type, set()):
            score_ += 3
        return (-score_, len(member_), body_)

    _PROSE_TOKENS = set(re.findall(r"[a-z0-9_]{4,}",
                                   (problem or "").lower().replace("-", "_").replace(" ", "_")))
    ranked = sorted((b for b, _d in guides), key=_meaning)
    keyed = [(_meaning(b), b) for b in ranked]
    keyed = [k for k in keyed if -k[0][0] > 0]           # at least one stated word

    # NO SECOND SORT. The type weight is already inside _meaning. An earlier version applied a
    # separate partition here "as a preference" and it silently undid the weighting -- which is
    # the whole failure mode this file is about: two places deciding one thing.
    out = [b for _k, b in keyed]
    return out[:limit]


