"""Answers are BUILT OUT OF typed pieces, not looked up in a menu.

THE DEFECT THIS REPLACES
------------------------
`operation_trial_v1` moved dispatch from English phrasings to the tree, and that was
real progress: it resolved what a sentence names and tried the operations those things
permitted. But every operation it tried was a CLOSED FUNCTION with a hand-written name
(`_op_count_lines`, `_op_aggregate`, ...) and NO OPERATION'S INPUT COULD BE ANOTHER
OPERATION'S OUTPUT. Measured on five questions that need two steps:

    how many digits are in the total of the amounts      -> refused
    what is the average of the totals in a.csv and b.csv -> refused
    what is the largest amount doubled                   -> refused
    which region has the largest amount                  -> refused
    is the total of a.csv less than the total of b.csv   -> refused

0 of 5. Not because the door was wrong -- those refusals were honest -- but because
seven primitives can only ever answer seven shapes. Adding an eighth primitive for each
new question is the same defect as adding a ninth regex, displaced one layer up: the
answer space grows by ONE per unit of work.

WHAT REPLACES IT
----------------
Values have TYPES, and operators are typed. A number can be summed; a numeric column can
be summed into a number; a number can be counted, doubled, compared, or used to select a
row; a row can yield a cell; a cell is text. Because the operators COMPOSE, the set of
answerable questions is the PRODUCT of the primitives, not their sum. Ten primitives do
not answer ten questions; they answer the questions that can be built from ten typed
pieces, and nobody writes those down.

This is the difference between a menu and a grammar. It is also the difference the user
kept naming: a static program enumerates its answers, and a system that composes them
does not.

VERIFICATION, WHICH IS NOT OPTIONAL
-----------------------------------
Every node re-derives itself from the tree. A leaf re-reads the file and re-extracts the
values; an operator re-applies itself to its children's re-derived values. What is
returned is the value of a re-derived tree, or nothing. That is the same discipline the
counts always had, applied to the whole expression rather than to one step of it.

ACCOUNTING, WHICH IS ALSO NOT OPTIONAL
--------------------------------------
Every node declares which of the question's words it CONSUMES. The root's consumed set
must cover the question's subject. A composition that computes something perfectly and
leaves `digit` or `largest` or `region` unaccounted for is not an answer to the question
asked -- it is a correct answer to a different question. Measured before this rule:
`sum` won "how many digits are in the total", returned 500, verified, and was wrong.

The word lists below map words to PRIMITIVES. That mapping is irreducible -- a word has
to mean something -- but it is not a list of QUESTIONS: nothing here knows what any
particular sentence looks like.
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_VALUE_ALGEBRA_V1"

_MAX_STEPS = 3_000          # hard search bound, so a bad question cannot hang the door


# ---------------------------------------------------------------------------
# Types. A value knows what it is, and an operator says what it accepts and returns.
# This is what makes composition checkable instead of guessed.
# ---------------------------------------------------------------------------

NUMBER = "number"
NUMVEC = "numvec"          # several numbers, e.g. one total per file
TEXT = "text"
TEXTVEC = "textvec"        # lines, or the cells of a column
ROW = "row"
TABLE = "table"
BOOL = "bool"


# ---------------------------------------------------------------------------
# Leaves: values taken from the tree.
# ---------------------------------------------------------------------------

class Node:
    """One typed value, with what it consumes and how to re-derive it."""

    __slots__ = ("op", "args", "type", "consumes", "label")

    def __init__(self, op: str, args: tuple, type: str, consumes: frozenset, label: str):
        self.op = op
        self.args = args
        self.type = type
        self.consumes = consumes
        self.label = label

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{self.label}:{self.type}>"


def _n(op, args, type, consumes, label):
    return Node(op, args, type, frozenset(consumes), label)


def _fmt(v) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _eq_text(cell: str, wanted: str) -> bool:
    """Equality of a cell and a value the question named.

    Case and surrounding space are spelling. A plural is the same thing (`north` in a
    question against `north` in a cell). Nothing else is coerced: `north` does not match
    `northeast`, because a filter that matches more than it was told is a wrong answer
    wearing the right answer's clothes.
    """
    a, b = cell.strip().lower(), wanted.strip().lower()
    return a == b or _norm(a) == _norm(b)


# --- tree readers. Each one is the ONLY place that touches disk for its kind. ---

def _read_text(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw[:4096] or len(raw) > 2_000_000:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def _rows_of(path: Path) -> list[list[str]] | None:
    text = _read_text(path)
    if text is None or not text.strip():
        return None
    try:
        rows = [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]
    except Exception:
        return None
    return rows or None


def _to_float(cell) -> float | None:
    """A number from a cell, whether the cell is text or already a number.

    Tables read from a file hold text; tables built by an operator hold values. Every
    numeric reader goes through here, so accepting both is one decision in one place
    rather than a `.strip()` that works until the first computed table arrives.
    """
    if isinstance(cell, bool):
        return None
    if isinstance(cell, (int, float)):
        return float(cell)
    if not isinstance(cell, str):
        return None
    s = cell.strip().replace(",", "").replace("$", "").replace("%", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _norm(s: str) -> str:
    s = s.strip().lower()
    if len(s) > 3 and s.endswith("s") and not s.endswith("ss"):
        s = s[:-1]
    return s


# ---------------------------------------------------------------------------
# Operators. (accepted type, result type, apply, words that select it)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# AN OPERATOR IS ONE DECLARATION, NOT FIVE.
# ---------------------------------------------------------------------------
#
# An aggregate used to be stated in five places that had no way to check each other:
# its words in `_AGG_WORDS`, its arithmetic in a hardcoded dict here, its arity in the
# enumerator's `_OPERATORS`, its word-accounting in `_structural_words`, and its
# invariant in `_holds_invariants`. Every defect this project has found for several
# rounds has been two of those disagreeing, and there was no way to notice, because
# there was nothing that WAS the operator to compare them against.
#
# The cost is not tidiness. `_AGG_WORDS["median"] = {...}` alone produced an operator
# that ENUMERATED fine and raised KeyError when evaluated: the vocabulary grew and the
# arithmetic did not. And an operator added that way carried NO invariant, because
# `_holds_invariants` returned True for every aggregate except `sum`. A creature able to
# extend its own vocabulary while unable to check the extension would grow confident and
# wrong -- which is worse than not growing.
#
# So an aggregate is declared once and must supply all four parts. `laws` is not
# decoration: it is the function that says a value is a legitimate answer, and a
# declaration without one is REFUSED. The weakest law -- the value is one of the inputs,
# between the least and the greatest -- holds for every aggregate there is, so nothing
# may escape by claiming it has no property to check.

#: the weakest law: an aggregate of numbers is one of them, hence between min and max
_WITHIN_INPUTS = "within_inputs"


def _law_within_inputs(values, result, *_):
    """Every aggregate of a set of numbers lies between its least and greatest member.

    True of a sum only when there is one member, of a mean always, of a median always, of
    a count never in value but always in ORDER -- so this is stated only for aggregates
    that return a member-like value and the declaration says which law it claims.
    """
    vals = [v for v in values if v is not None]
    if not vals or result is None:
        return True
    try:
        return min(vals) - 1e-9 <= float(result) <= max(vals) + 1e-9
    except (TypeError, ValueError):
        return True


def _law_non_negative(values, result, *_):
    vals = [v for v in values if v is not None]
    if result is None:
        return True
    try:
        return float(result) >= 0
    except (TypeError, ValueError):
        return True


def _law_integral(values, result, *_):
    if result is None:
        return True
    try:
        return abs(float(result) - round(float(result))) < 1e-9
    except (TypeError, ValueError):
        return True


def _law_equals_row_count(values, result, *_):
    """A count of a table is its number of rows -- not merely non-negative or integral.

    `integral` and `non_negative` let 99 through for a three-row table. They were chosen
    because they are true of every count, which is exactly the problem: a law that is true
    of every value in a large set cannot reject the wrong ones. Where a stronger statement
    is true, the weaker one is not a check, it is a formality.
    """
    if result is None:
        return True
    try:
        return abs(float(result) - float(len(values))) < 1e-9
    except (TypeError, ValueError):
        return True


def _law_sum_between(values, result, *_):
    """A sum of n numbers lies between n*min and n*max, which follows from the definition.

    Lower bound: adding the others can only move the total toward them, and if they are
    all at least as large as the largest then the sum is at least n*max >= max. The
    honest, simple statement is: the sum is at least min and at most sum(|v|). Both hold
    for negative values, which "non_negative" did not.
    """
    vals = [float(v) for v in values if v is not None]
    if not vals or result is None:
        return True
    try:
        r = float(result)
    except (TypeError, ValueError):
        return True
    # A SUM IS BOUNDED BY n TIMES THE EXTREMES, and that is the tight statement.
    #
    # My first attempt said "at least min and at most sum(|v|)", which is false for
    # [-3, -1, -7]: the sum is -11, below the minimum of -7. The honest bound falls out
    # of the definition -- n numbers each at least min and at most max -- and it is tight
    # enough to reject a count wearing a sum's clothes, which is what it is for.
    n = len(vals)
    return (n * min(vals) - 1e-9) <= r <= (n * max(vals) + 1e-9)


_LAWS = {
    _WITHIN_INPUTS: _law_within_inputs,
    "non_negative": _law_non_negative,
    "integral": _law_integral,
}

_AGGREGATES: dict[str, dict] = {
    "sum": {
        "fn": lambda v: sum(v),
        # A SUM IS AT LEAST ITS LARGEST MEMBER AND AT MOST ITS TOTAL MAGNITUDE.
        #
        # The law used to be "non_negative", which is true of sums of positives and false
        # in general -- the falsifiability probe found it on [-3, -1, -7], where an honest
        # sum of -11 was reported as violating its own declaration. A law that only holds
        # for convenient data is not a law; it would have rejected correct answers the
        # first time a column held a negative.
        "laws": (_law_sum_between,),
    },
    "max": {"fn": lambda v: max(v), "laws": (_WITHIN_INPUTS,)},
    "min": {"fn": lambda v: min(v), "laws": (_WITHIN_INPUTS,)},
    "mean": {"fn": lambda v: sum(v) / len(v), "laws": (_WITHIN_INPUTS,)},
    "count": {"fn": lambda v: len(v), "laws": (_law_equals_row_count, "integral")},
}


#: Numbers chosen to be awkward: odd length, even length, negatives, zero, a repeat,
#: and one value. A law that survives all of these has not been tested, it has been
#: ignored -- there is nothing left for real data to break that these did not.
_PROBE_SETS = (
    [5.0, 15.0, 7.0],
    [2.0, 4.0, 6.0, 8.0],
    [-3.0, -1.0, -7.0],
    [0.0],
    [1.0, 1.0, 4.0],
    [0.5, 2.25, 9.0, 1.75],
)


def _law_is_falsifiable(kind: str, fn, laws) -> str | None:
    """Is there data on which this law REJECTS something? Returns a reason, or None.

    A LAW THAT CANNOT FAIL LICENSES ANYTHING.

    `declare_aggregate("liar", {"liar"}, lambda v: 999.0, (lambda values, result, *_: True,))`
    was accepted: the declaration had a law, the law was callable, and it passed every
    value -- so a median of [5, 15, 7] was licensed as 999 and "an operator cannot exist
    unchecked" was false in the most direct way. It existed, checked by nothing.

    So a law must be shown to DISCRIMINATE before it is accepted: over the probes below,
    at least one honest value must pass and at least one corrupt value must fail. That is
    the weakest standard that still means something, and it is the same standard the whole
    system applies to answers -- a check that cannot fail is not a check.
    """
    if kind in ("count",):
        # a count is a property of the ROWS, not of their values, so the value probes
        # below do not apply to it; it is falsified directly against table shapes.
        bad = [(3, -1), (0, 5), (2, 1.5)]
        good = [(3, 3), (0, 0), (2, 2)]
        passed = any(_run_laws(laws, [float(i) for i in range(n)], n) is not False
                     for n, _ in good)
        failed = any(_run_laws(laws, [float(i) for i in range(n)], v) is False
                     for n, v in bad)
        if not (passed and failed):
            return (f"{kind}: the law accepts every value it was shown, so it can never "
                    "say no -- a check that cannot fail is not a check")
        return None

    passed = failed = False
    for values in _PROBE_SETS:
        try:
            honest = fn(list(values))
        except Exception:
            return f"{kind}: the arithmetic raised on {values!r}"
        if _run_laws(laws, list(values), honest) is False:
            return (f"{kind}: the declaration's own arithmetic VIOLATES its own law on "
                    f"{values!r} -- it computed {honest!r}")
        passed = True
        for corrupt in (999.0, -999.0, max(values) + 1000.0, min(values) - 1000.0):
            if _run_laws(laws, list(values), corrupt) is False:
                failed = True
    if not passed:
        return f"{kind}: no probe produced an honest value, so nothing was tested"
    if not failed:
        return (f"{kind}: the law accepts every value it was shown, so it can never say "
                "no -- a check that cannot fail is not a check")
    return None


# ---------------------------------------------------------------------------
# DERIVING a law instead of writing one.
#
# The laws above were all written by hand: I decided a sum is bounded by n*min and
# n*max, that a mean stays inside its inputs, that a count equals its row count. That
# makes the vocabulary static in the way that matters -- the system can declare a new
# operator, but only a human can say what would make it wrong.
#
# So the laws are stated as FORMS that take the arithmetic and the data, not as
# sentences about a particular operator. Nothing here mentions sum, mean or count. The
# forms are candidates; which ones are true of a given arithmetic is MEASURED by running
# that arithmetic, and the strongest surviving form is the one admitted. A form that the
# arithmetic violates anywhere is discarded, which is also how the hand-written
# "non_negative" law for sum was found to be false.
#
# This is the difference between a checkable declaration and a declaration that merely
# contains a check: the check is a claim about the arithmetic, and the arithmetic decides
# whether the claim survives.
# ---------------------------------------------------------------------------


def _form_within_inputs(values, result):
    return min(values) - 1e-9 <= result <= max(values) + 1e-9


def _form_bounded_by_extremes(values, result):
    # A RESULT CANNOT EXCEED THE TOTAL MAGNITUDE OF ITS INPUTS.
    #
    # This was n*min <= result <= n*max, which is a false claim about differences and
    # ranges: max-min of [-3, -1, -7] is 6, but n*max is -3, so a correct answer was
    # reported as violating its own law. Caught by running the form against an arithmetic
    # rather than by reasoning about the form -- which is the point of measuring laws
    # instead of asserting them. The surviving bound is true of sums, means, ranges and
    # totals alike, and still rejects a value larger than any combination of the inputs.
    return abs(result) <= sum(abs(v) for v in values) + 1e-9


def _form_is_one_of_the_inputs(values, result):
    return any(abs(result - v) <= 1e-9 for v in values)


def _form_is_a_whole_number(values, result):
    return abs(result - round(result)) <= 1e-9


def _form_is_the_row_count(values, result):
    return abs(result - len(values)) <= 1e-9


#: Nothing in this table says which operator it is for. Each is a statement that either
#: does or does not hold of an arithmetic, and the arithmetic is what decides.
_LAW_FORMS = (
    ("within_inputs", _form_within_inputs),
    ("bounded_by_extremes", _form_bounded_by_extremes),
    ("is_one_of_the_inputs", _form_is_one_of_the_inputs),
    ("is_a_whole_number", _form_is_a_whole_number),
    ("is_the_row_count", _form_is_the_row_count),
)


def _holds_on(values, result, form):
    try:
        return bool(form([float(v) for v in values], float(result)))
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False


def induce_laws(fn, probes=None) -> tuple[str, ...]:
    """Derive the law forms this arithmetic actually satisfies, strongest first.

    A form survives if the arithmetic satisfies it on every probe. Surviving forms are
    then ranked by how many WRONG values they reject, because a form that is true and
    never says no is the vacuity this whole layer exists to refuse. Ties keep the earlier,
    tighter form.

    Returns names from `_LAW_FORMS`, or () if the arithmetic satisfies none of them --
    in which case a declaration has nothing checkable to say and must be refused.
    """
    probe_sets = probes or _PROBE_SETS
    tested = []
    for values in probe_sets:
        try:
            got = fn(list(values))
        except Exception:
            return ()
        if got is None:
            continue
        try:
            float(got)
        except (TypeError, ValueError):
            return ()
        tested.append((list(values), float(got)))
    if not tested:
        return ()

    # AN ARITHMETIC THAT DOES NOT DEPEND ON ITS DATA CANNOT BE CHECKED BY A LAW ABOUT
    # ITS DATA, and saying so is the fix for a liar that got through here.
    #
    # `lambda v: 0.0` passed the previous test: |0| is within the total magnitude, and the
    # form rejected an invented 1000, so it looked like a check. It was not -- the value it
    # would give for any input is the same, and no statement about a single input can
    # distinguish it from a correct answer. The test has to be CROSS-DATA: does the law
    # reject the honest answer computed from DIFFERENT rows?
    if len({round(r, 9) for _, r in tested}) < 2:
        return ()

    survivors = []
    for name, form in _LAW_FORMS:
        if not all(_holds_on(v, r, form) for v, r in tested):
            continue
        rejected = 0
        for i, (v_i, _) in enumerate(tested):
            for j, (_, r_j) in enumerate(tested):
                if i != j and not _holds_on(v_i, r_j, form):
                    rejected += 1
        if rejected:                           # it separates answers from other data
            survivors.append((-rejected, name))
    survivors.sort()
    return tuple(name for _, name in survivors)


def law_strength(fn, laws, probes=None) -> dict:
    """How much of the space of wrong answers does this law actually exclude?

    A LAW'S STRENGTH IS NOT ITS CONFIDENCE, IT IS ITS REACH, and a caller needs to be able
    to tell a check that catches 999 from one that would also catch a plausible mistake.
    An INDUCED law is weaker than a written one by construction -- it can only say what is
    true of every input the probes tried, and a median's induced law accepts the minimum
    and the maximum because both really are inputs.

    This reports the fraction of a dense range around the data that the law rejects, so a
    weak law is visible as weak instead of looking like a strong one that happened to pass.
    """
    tested = []
    for values in (probes or _PROBE_SETS):
        try:
            got = fn(list(values))
        except Exception:
            continue
        if got is None:
            continue
        tested.append((list(values), float(got)))
    if not tested:
        return {"probes": 0, "rejected_fraction": 0.0}
    rejected = considered = 0
    for values, honest in tested:
        span = max(abs(honest), max(abs(v) for v in values), 1.0)
        for k in range(-10, 11):
            candidate = honest + k * span / 5.0
            considered += 1
            if any(_run_laws(laws, values, candidate) is False for _ in (0,)):
                rejected += 1
    return {"probes": len(tested),
            "rejected_fraction": round(rejected / considered, 4) if considered else 0.0}


def law_from_name(name):
    """The callable behind a form name, so an induced law is a real law."""
    for n, form in _LAW_FORMS:
        if n == name:
            return form
    raise ValueError(f"unknown law form {name!r}")

def _run_laws(laws, values, result):
    """True/False from the laws, or None when no law could judge."""
    judged = False
    ok = True
    for law in laws:
        checker = _LAWS[law] if isinstance(law, str) else law
        try:
            verdict = checker(list(values), result)
        except Exception:
            continue
        if verdict is False:
            return False
        if verdict is True:
            judged = True
    return True if judged else None


def declare_aggregate(kind: str, words, fn, laws=()) -> None:
    """Add an aggregate as ONE declaration: its words, its arithmetic, and its check.

    `laws` may be omitted, in which case they are induced from the arithmetic itself.

    Refusing a declaration with no law is the point. An operator nobody can be wrong
    with is not a capability, it is a way to be confidently wrong, and this system's
    whole purpose is to not do that.

    But having a law is not enough -- the law has to be able to SAY NO, and the
    declaration's own arithmetic has to satisfy it. Both are checked here, before
    anything is registered, because a declaration that fails later has already been
    used.
    """
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("an aggregate needs a name")
    if not words:
        raise ValueError(f"{kind}: an aggregate needs at least one word or nothing can ask for it")
    if not callable(fn):
        raise ValueError(f"{kind}: an aggregate needs arithmetic")
    # A DECLARATION MAY SUPPLY ITS LAW OR HAVE ONE INDUCED FROM ITS ARITHMETIC.
    #
    # Requiring a hand-written law made the system's vocabulary static in the way that
    # matters: anyone could add an operator, but only a human could say what would make it
    # wrong. When no law is given, the arithmetic is measured against the law FORMS and the
    # strongest ones it satisfies become its law. If it satisfies none -- it is not tied to
    # its data in any way the system can express, like an arithmetic that always returns
    # 999 -- the declaration is refused. The operator does not get to exist unchecked
    # merely because its author chose not to say what would make it wrong.
    if not laws:
        induced = induce_laws(fn)
        if not induced:
            raise ValueError(
                f"{kind}: no law was given and none could be INDUCED from the arithmetic "
                "-- nothing this system can state would make an answer from it wrong, so "
                "a value nobody can check is a way to be confidently wrong")
        laws = tuple(law_from_name(n) for n in induced)
    for law in laws:
        if law not in _LAWS and not callable(law):
            raise ValueError(f"{kind}: unknown law {law!r}")
    reason = _law_is_falsifiable(kind, fn, tuple(laws))
    if reason is not None:
        raise ValueError(reason)
    _AGG_WORDS[kind] = {str(w).strip().lower() for w in words}
    _AGGREGATES[kind] = {"fn": fn, "laws": tuple(laws)}


def aggregate_names() -> tuple[str, ...]:
    """The aggregates that are really declared: words AND arithmetic AND a law."""
    return tuple(k for k, v in _AGGREGATES.items() if k in _AGG_WORDS and v.get("laws"))


def aggregate_holds(kind: str, values, result) -> bool | None:
    """Does `result` satisfy what was declared about `kind`? None if it cannot be judged."""
    spec = _AGGREGATES.get(kind)
    if not spec:
        return None
    if isinstance(values, dict) and "_body" in values:
        # A table's law is about its ROWS, and the row count is the value being judged.
        vals = [1.0] * len(values["_body"])
    else:
        vals = [v for v in values if v is not None] if isinstance(values, list) else None
    # "I COULD NOT JUDGE" IS NOT "FINE".
    #
    # This returned True whenever `values` was not a list -- including for every TABLE,
    # because a table is a dict -- so no law ran at all on table-valued aggregates and a
    # count of a table was licensed at any value. The return type already says `None`
    # means not-judged; the bug was that the caller could not tell True from None because
    # both looked like success. It still cannot, so the distinction is made here: an
    # aggregate whose law cannot be evaluated is reported None, and `holds` treats None
    # as "no verdict" rather than as a pass.
    if vals is None:
        return None
    verdict = _run_laws(spec.get("laws", ()), vals, result)
    if verdict is False:
        return False
    extra = spec.get("extra")
    if callable(extra):
        try:
            if extra(vals, result) is False:
                return False
        except (TypeError, ValueError):
            pass
    return verdict


def _aggregate(kind: str):
    fn = _AGGREGATES[kind]["fn"]

    def apply(values, *_):
        # A TABLE HAS ROWS, AND A COUNT OF THEM IS ITS ROW COUNT.
        #
        # `len()` on a table dict is the number of KEYS -- `_header` and `_body` -- so
        # `count(t@file)` was 2 for every file in the world, however many rows it had.
        # It never showed up because nothing built that expression until the enumerator
        # did, and it passed every invariant: 2 is a number, and no statement relates a
        # table's row count to anything else. The meaning of a count lives here, so this
        # is where a table's count is defined -- not in each operator that might count.
        if isinstance(values, dict) and "_body" in values:
            rows = values["_body"]
            return len(rows) if kind == "count" else None
        vals = list(values)
        if not vals:
            return None
        return fn(vals)

    return apply


def _digits(x, *_):
    """How many decimal digits the integer part has. A count, not a formatting choice."""
    n = abs(int(round(float(x))))
    return len(str(n)) if n else 1


def _double(x, *_):
    return float(x) * 2


def _half(x, *_):
    return float(x) / 2


def _negate(x, *_):
    return -float(x)


def _length(x, *_):
    return len(str(x))


def _cell_of(row, column):
    cells = row.get("_cells") or []
    idx = row.get("_index") or {}
    key = _norm(str(column))
    for name, i in idx.items():
        if _norm(name) == key and i < len(cells):
            return cells[i]
    return None


# words that select each operator. NOT a list of questions -- a lexicon of primitives.
_AGG_WORDS = {
    # "add up to", "how much", "in total" -- the particle of a phrasal verb and the
    # quantifier are part of saying WHICH aggregate, not a thing being asked about.
    "sum": {"total", "sum", "added", "altogether", "combined", "overall", "add",
            "up", "addup", "much", "altogether"},
    "max": {"largest", "biggest", "max", "maximum", "highest", "most", "greatest", "top"},
    "min": {"smallest", "least", "min", "minimum", "lowest", "fewest", "bottom"},
    "mean": {"average", "mean", "typical", "avg"},
    "count": {"how", "many", "number", "count"},
}
# The lexicon of UNARY PRIMITIVES. A word has to mean something; nothing here knows
# what any particular sentence looks like, and every operator composes with all the rest.
_MAP_WORDS = {
    "digits": {"digit", "digits"},
    "double": {"double", "doubled", "double", "twice", "two", "multiplied", "times",
               "tripled"},
    "half": {"half", "halved", "divided"},
    "negate": {"negated", "inverted", "negated"},
    "length": {"length", "characters", "chars"},
}
_CMP_WORDS = {
    "lt": {"less", "fewer", "below", "under", "smaller"},
    "gt": {"greater", "more", "above", "over", "bigger", "exceeds"},
    "eq": {"equal", "same", "equals"},
}
_SELECT_WORDS = {"which", "what", "whose", "row", "record", "entry"}
# "how many KINDS / DIFFERENT / UNIQUE things" is a cardinality question over the distinct
# values, not over the rows. Asked without these words, a plain count is right; asked with
# them, the row count is a true number that answers a different question.
_DISTINCT_WORDS = {"distinct", "different", "unique", "kinds", "kind", "types", "type"}
# "per <key>" asks for one answer PER group, so a single count cannot be it.
_PER_WORDS = {"per", "each", "every", "respectively"}
# Words whose whole job is to choose the SHAPE of the answer. They name nothing, so the
# search treats them as glue; but an answer that took that shape owes them its account.
_SHAPE_WORDS = {"per", "each", "every", "respectively", "distinct", "different", "unique"}
_VECTOR_WORDS = {"totals", "total", "sums", "sum", "amounts", "values", "averages"}
_ROW_WORDS = frozenset({"row", "rows", "record", "records", "entry", "entries",
                       "line", "lines", "*"})


# ---------------------------------------------------------------------------
# Building candidate expressions from the entities and the question's words.
# ---------------------------------------------------------------------------

class Lexicon:
    """The question's words, minus what the entities already are."""

    def __init__(self, words: list[str]):
        self.raw = [w.lower() for w in words]
        self.set = set(self.raw)

    def pick(self, table: dict[str, set[str]]) -> list[str]:
        return [k for k, ws in table.items() if self.set & ws]

    def without(self, used: frozenset) -> set[str]:
        return self.set - set(used)


_TABLE_SUFFIXES = (".csv", ".tsv")

def _columns(path: Path) -> tuple[list[str], list[list[str]]] | None:
    """A file read as a TABLE: first row is the header, the rest are records.

    WHETHER A FILE IS A TABLE IS A FACT ABOUT THE FILE, NOT AN ASSUMPTION.

    Every file was read this way, so `count(t@data.py)` on a four-line Python file
    counted its five "rows" minus the header and answered 2. It passed every invariant --
    the arithmetic was right about a table that does not exist -- and it REPLACED the
    correct answer of 4 that the door had already computed. A wrong answer delivered
    confidently over a right one is the worst outcome this system can produce.

    A delimiter that never appears is the giveaway: a real table has a header row with
    more than one field, or a suffix that says it is tabular. Everything else is text
    that happens to end in a dot and three letters.
    """
    rows = _rows_of(path)
    if not rows or len(rows) < 2:
        return None
    suffix = path.suffix.lower()
    header = rows[0]
    wide_header = len([c for c in header if c.strip()]) > 1
    if not (wide_header or suffix in _TABLE_SUFFIXES):
        return None
    return rows[0], rows[1:]


def _numeric_columns(header: list[str], rows: list[list[str]]) -> dict[str, list[float]]:
    """The columns that hold numbers, with missing cells left out.

    ONE MISSING CELL USED TO ERASE A WHOLE COLUMN.

    The test was all-or-nothing -- every cell had to parse -- so a single blank amount
    made `amount` stop being a quantity. `sum(amount)` then could not be built at all,
    and "the total amount" was answered by the only thing left: the row count, 5.0. The
    arithmetic was never wrong; the column had been discarded before the arithmetic was
    asked, and every later check reasoned about a quantity that was no longer there.

    An EMPTY cell and a NON-NUMERIC cell are different facts. Empty is absent data: a
    total over the column is the total of what is present, which is what `sum` already
    means everywhere else. A non-empty cell that does not parse ("n/a", "twelve") says
    this column is not a column of numbers, and that is still refused.
    """
    out: dict[str, list[float]] = {}
    for i, name in enumerate(header):
        vals: list[float] = []
        numeric = True
        for r in rows:
            cell = r[i] if i < len(r) else ""
            if cell is None or (isinstance(cell, str) and not cell.strip()):
                continue                      # missing, not wrong
            v = _to_float(cell)
            if v is None:
                numeric = False
                break                         # present and not a number: not numeric
            vals.append(v)
        if numeric and vals:
            out[name] = vals
    return out


def _column_leaf(path: Path, rel: str, name: str, consumes: set[str]) -> Node | None:
    """A numeric column, resolved from the file's own header."""
    got = _columns(path)
    if got is None:
        return None
    header, rows = got
    nums = _numeric_columns(header, rows)
    idx = {_norm(h): h for h in header}
    target = None
    if _norm(name) in idx:
        target = idx[_norm(name)]
    else:
        for h in header:
            if _norm(h) and (_norm(h) in _norm(name) or _norm(name) in _norm(h)) and len(_norm(h)) > 2:
                target = h
                break
    if target is None or target not in nums:
        return None
    return _n("column", (str(path), target), NUMVEC, consumes, f"col:{target}@{rel}")


def _column_at(rel: str, name: str) -> list[float] | None:
    got = _columns(Path(rel))
    if got is None:
        return None
    header, rows = got
    return _numeric_columns(header, rows).get(name)


# ---------------------------------------------------------------------------
# Evaluation: re-derive from disk, top to bottom. Nothing is cached between runs.
# ---------------------------------------------------------------------------

class EvalError(Exception):
    pass


def _row_leaf(rel: str, column: str, index: int, header: list[str]) -> dict:
    rows = _rows_of(Path(rel))
    if rows is None or index >= len(rows) - 1:
        raise EvalError("row gone")
    cells = rows[index + 1]
    return {"_cells": cells, "_index": {h: i for i, h in enumerate(header)}}


def evaluate(node: Node, *, derived: dict | None = None) -> object:
    """The value of an expression, computed from the tree.

    Memoised per node identity for the duration of one question (`_reset_memo` clears it).
    A `Node` is immutable after construction and its value depends only on the files it
    names, so within one question the memo cannot return a stale answer -- and without it,
    asking a soundness question about sub-expressions the search has already built turned
    a single question into hundreds of full tree walks.
    """
    if derived is None:
        key = id(node)
        hit = _EVAL_MEMO.get(key)
        # THE CACHE HOLDS THE NODE, NOT ONLY ITS ID.
        #
        # Keying on `id()` alone is unsound on its own: a candidate that is dropped is
        # collected, and CPython hands its address to the next object -- so a later node
        # can inherit a dead node's id and be served that node's value. Storing the node
        # beside the value pins it for as long as the entry lives, which makes id reuse
        # impossible while the entry is live. The identity check catches anything else.
        if hit is not None and hit[0] is node:
            return hit[1]
        value = _evaluate(node, derived=None)
        _EVAL_MEMO[key] = (node, value)
        return value
    return _evaluate(node, derived=derived)


def _evaluate(node: Node, *, derived: dict | None = None) -> object:
    op = node.op
    if op == "column":
        rel, name = node.args
        vals = _column_at(rel, name)
        if vals is None:
            raise EvalError(f"column {name!r} gone")
        return vals
    if op == "aggregate":
        kind, child = node.args
        return _aggregate(kind)(evaluate(child), kind)
    if op == "map":
        kind, child = node.args
        v = evaluate(child)
        fn = {"digits": _digits, "double": _double, "half": _half,
              "negate": _negate, "length": _length}[kind]
        return fn(v)
    if op == "compare":
        kind, left, right = node.args
        a, b = evaluate(left), evaluate(right)
        return {"lt": a < b, "gt": a > b, "eq": abs(float(a) - float(b)) < 1e-9}[kind]
    if op == "vector":
        return [evaluate(c) for c in node.args[0]]
    if op == "argmax":
        rel, column, by, extreme = node.args
        rows = _rows_of(Path(rel))
        if rows is None:
            raise EvalError("table gone")
        header, body = rows[0], rows[1:]
        idx = {h: i for i, h in enumerate(header)}
        if by not in idx:
            raise EvalError("column gone")
        better = (lambda v, best: v > best) if extreme == "max" \
            else (lambda v, best: v < best)
        best, best_i = None, None
        for i, r in enumerate(body):
            if idx[by] >= len(r):
                continue
            v = _to_float(r[idx[by]])
            if v is None:
                continue
            if best is None or better(v, best):
                best, best_i = v, i
        if best_i is None:
            raise EvalError("no numeric rows")
        return {"_cells": body[best_i], "_index": idx, "_row": best_i}
    if op == "cell":
        row, column = node.args
        v = _cell_of(evaluate(row), column)
        if v is None:
            raise EvalError("no such cell")
        # A CELL IS TEXT WHEN THE NODE SAYS SO, AND A NUMBER WHEN IT SAYS SO.
        #
        # Grouped tables now hold real numbers, so a cell taken from one arrived as a
        # float where the node had declared TEXT -- and the type the expression declared
        # stopped matching the value it produced. Converting here keeps the declaration
        # and the value in agreement; a number rendered as text is a decision about the
        # ANSWER, and `cell` is where the answer is taken.
        if node.type == TEXT and not isinstance(v, str):
            return str(_fmt(v))
        if node.type == NUMBER and isinstance(v, str):
            num = _to_float(v)
            if num is None:
                raise EvalError("cell is not numeric")
            return num
        return v
    if op == "table":
        rel = node.args[0]
        rows = _rows_of(Path(rel))
        if rows is None:
            raise EvalError("table gone")
        return {"_header": rows[0], "_body": rows[1:]}
    if op == "filter":
        # A TABLE IS THE CONDITION'S DOMAIN, NOT A DETOUR.
        # `filter` takes the table and a column/value pair, so a filtered aggregate is
        # the SAME arithmetic over a smaller table -- no second definition of sum.
        table = evaluate(node.args[0])
        column, wanted = node.args[1], node.args[2]
        header = table["_header"]
        if column not in header:
            raise EvalError("column gone")
        i = header.index(column)
        keep = [r for r in table["_body"]
                if i < len(r) and _eq_text(r[i], wanted)]
        return {"_header": header, "_body": keep}
    if op == "group":
        table = evaluate(node.args[0])
        key, valcol = node.args[1], node.args[2]
        header, body = table["_header"], table["_body"]
        for c in (key,):
            if c not in header:
                raise EvalError("column gone")
        ki = header.index(key)
        # "*" IS THE ROW ITSELF, NOT A COLUMN.
        #
        # "how many rows per region" has no column to count: the natural spelling is
        # count(amount), which silently counts only the rows where the amount parses --
        # a blank cell removes a row from the answer. Counting ROWS is a property of the
        # table, so the value column is allowed to name the row instead of a field. With
        # this, `count` over `*` is a row count and needs no operator of its own.
        vi = None if valcol == "*" else header.index(valcol)
        buckets: dict[str, list[float]] = {}
        order: list[str] = []
        for r in body:
            if ki >= len(r):
                continue
            if vi is None:
                v = 1.0                      # the row exists; no cell decides that
            else:
                if vi >= len(r):
                    continue
                v = _to_float(r[vi])
                if v is None:
                    continue
            k = r[ki].strip()
            if k not in buckets:
                buckets[k] = []
                order.append(k)
            buckets[k].append(v)
        if not buckets:
            raise EvalError("nothing to group")
        return {"_keys": order, "_buckets": buckets}
    if op == "groups":
        # A GROUPED RESULT IS A TABLE. Its rows are (key, aggregate), which is why the
        # same `cell`, `argmax` and `compare` operators work on it without knowing that
        # grouping ever happened. This is the property a menu cannot have.
        grouped = evaluate(node.args[0])
        kind = node.args[1]
        fn = _aggregate(kind)
        header = [node.args[2], f"{kind}({node.args[3]})"]
        # THE TABLE HOLDS NUMBERS; ONLY THE RENDERING TURNS THEM INTO TEXT.
        #
        # Storing `str(_fmt(...))` looked harmless and made a grouped table a table of
        # strings, so any later operator that treated its aggregate column as numbers --
        # `values_of`, a comparison, a second aggregate -- silently saw a different type
        # than the one the node declared. `_to_float` reads a numeric cell whether it was
        # stored as text or not, so holding the number is strictly more faithful.
        body = [[k, fn(v)] for k, v in zip(grouped["_keys"],
                                           grouped["_buckets"].values())]
        return {"_header": header, "_body": body}
    if op == "distinct":
        table = evaluate(node.args[0])
        column = node.args[1]
        header = table["_header"]
        if column not in header:
            raise EvalError("column gone")
        i = header.index(column)
        seen, out = set(), []
        for r in table["_body"]:
            if i < len(r):
                v = r[i].strip()
                if v and v.lower() not in seen:
                    seen.add(v.lower())
                    out.append(v)
        if not out:
            raise EvalError("no values")
        return out
    if op == "values_of":
        table = evaluate(node.args[0])
        column = node.args[1]
        header = table["_header"]
        if column not in header:
            raise EvalError("column gone")
        i = header.index(column)
        # A CELL MAY ALREADY BE A NUMBER: tables read from a file hold text, tables built
        # by an operator hold values. Reading a cell is the same operation either way.
        raw = [(r[i].strip() if isinstance(r[i], str) else r[i])
               for r in table["_body"] if i < len(r)]
        # A VALUE STAYS THE TYPE IT IS.
        #
        # This returned strings for every column, so a grouped NUMVEC re-derived as
        # numbers while its recorded value was text: the verification compared
        # ['150', '250'] with [150.0, 250.0], correctly refused, and "the total amount per
        # region" had no answer. Formatting a number as text is a RENDERING decision and
        # belongs at the edge, not in the value.
        if node.type == NUMVEC:
            nums = [_to_float(x) for x in raw]
            if any(v is None for v in nums):
                raise EvalError("not a numeric column")
            return [v for v in nums if v is not None]
        # AND A TEXTVEC HOLDS TEXT. `raw` is already text when the table came from a
        # file, but a COMPUTED table holds numbers, so reading them as text was returned
        # unformatted and the node's declared type disagreed with its value again -- the
        # same defect as `groups`, one operator over.
        return [x if isinstance(x, str) else str(_fmt(x)) for x in raw]
    if op == "column_from":
        # A COLUMN IS A PROJECTION OF A TABLE, not necessarily a whole file's.
        #
        # This is the same `count`/`sum`/`max` arithmetic applied to whatever rows are in
        # scope. Defining it here means a filtered aggregate never has a second
        # implementation that could drift from the unfiltered one.
        table = evaluate(node.args[0])
        column = node.args[1]
        header = table["_header"]
        if column not in header:
            raise EvalError("column gone")
        i = header.index(column)
        vals = [_to_float(r[i]) for r in table["_body"] if i < len(r)]
        vals = [v for v in vals if v is not None]
        if not vals:
            raise EvalError("no numeric values in scope")
        return vals
    if op == "argmax_table":
        grouped, column, extreme = node.args
        table = evaluate(grouped)
        header, body = table["_header"], table["_body"]
        if column not in header:
            raise EvalError("column gone")
        i = header.index(column)
        better = (lambda v, best: v > best) if extreme == "max" \
            else (lambda v, best: v < best)
        best, best_row = None, None
        for r in body:
            if i >= len(r):
                continue
            v = _to_float(r[i])
            if v is None:
                continue
            if best is None or better(v, best):
                best, best_row = v, r
        if best_row is None:
            raise EvalError("nothing to choose")
        return {"_cells": best_row, "_index": {h: j for j, h in enumerate(header)}}
    if op == "count":
        # ONE DEFINITION OF WHAT A COUNT IS.
        #
        # This was a second implementation, with its own `len(v)` -- so it counted the
        # KEYS of a table (2) while `_aggregate("count")` counted its rows, and "how many
        # rows are in sales.csv" returned 2 for a file of five. The same value had two
        # meanings depending on how it was spelled, which is the defect this file keeps
        # finding: a fact is only true if there is one place that says it.
        return _aggregate("count")(evaluate(node.args[0]), "count")
    if op == "contains_all":
        haystack, needle = evaluate(node.args[0]), evaluate(node.args[1])
        h = {str(x).strip().lower() for x in haystack}
        n = {str(x).strip().lower() for x in needle}
        return n <= h
    raise EvalError(f"unknown op {op}")


# ---------------------------------------------------------------------------
# The search. Typed, bounded, and driven by the question's own words.
# ---------------------------------------------------------------------------

def _candidate_columns(lex: Lexicon, header: list[str] | None,
                       numeric: list[str] | None = None) -> list[str]:
    """Which column the question is about, decided by the FILE'S header.

    When the question names no column and the file has exactly ONE numeric column, that
    column is the referent: the tree resolves it, and the question does not have to use
    the header's spelling. This was missing here after being added to the single-file
    aggregate, and it made every multi-file question unbuildable over columns called
    `x` -- the same fix, needed twice, which is why it now lives in one place.
    """
    if not header:
        return []
    wanted = {_norm(w) for w in lex.raw}
    named = [h for h in header if _norm(h) in wanted]
    if named:
        return named
    out = [h for h in header if any(
        _norm(h) and (_norm(h) in _norm(w) or _norm(w) in _norm(h)) and len(_norm(h)) > 2
        for w in lex.raw)]
    if out:
        return out
    if numeric and len(numeric) == 1:
        return list(numeric)
    return []


def _numeric_candidates(lex: Lexicon, header: list[str], numeric: list[str]) -> list[str]:
    """Which NUMERIC column the question's quantity refers to.

    A text column named in the question is the KEY of a group or a value to filter by,
    never the thing to sum. Offering `region` as a column to aggregate is how "the total
    amount per region" could try to total the region names.
    """
    return [c for c in _candidate_columns(lex, header, numeric) if c in numeric]


def _text_candidates(lex: Lexicon, header: list[str], numeric: list[str]) -> list[str]:
    """Which TEXT column the question names -- the key, or the filter's subject."""
    return [c for c in _candidate_columns(lex, header, numeric) if c not in numeric]


def _table_rel_of(tables: dict, key: str, val: str) -> str | None:
    """The entity rel whose header has this key, so a filtered table re-reads the file."""
    for rel, (header, _rows) in tables.items():
        if key in header:
            return rel
    return None


def _literal_values(lex: Lexicon, tables: dict, key: str) -> list[str]:
    """Values that appear in the KEY column AND in the question.

    This is not a list of values -- it is the intersection of the question's words with
    what the tree actually contains. "the total amount in north" resolves `north` only
    because `north` is a value in that column. A word that names nothing in the tree
    cannot become a filter, which is what stops the door inventing a category.
    """
    out: list[str] = []
    seen: set[str] = set()
    for rel, (header, rows) in tables.items():
        if key not in header:
            continue
        i = header.index(key)
        present = {}
        for r in rows:
            if i < len(r) and r[i].strip():
                present.setdefault(_norm(r[i].strip()), r[i].strip())
        for w in lex.raw:
            nw = _norm(w)
            if nw in present and nw not in seen and len(w) > 2:
                seen.add(nw)
                out.append(present[nw])
    return out


def compose(question: str, root: str, ents, words: list[str]) -> dict | None:
    """Try to BUILD an answer out of typed pieces. None when nothing builds.

    (The memo is cleared on entry: one question, one set of values.)

    The search is bounded and typed, and it is not a table of question shapes: it
    enumerates operators that TYPE-CHECK against the values the tree provides, which is
    why a question nobody wrote down can still be answered.
    """
    _reset_memo()

    # ---- THE ENUMERATION RUNS FIRST ----------------------------------
    #
    # The rest of this function is a hand-written list: sixteen appends, one per operator
    # shape somebody thought of. Measured, it reaches FIVE distinct structures, and a
    # question needing a shape nobody appended is refused while its pieces sit in this
    # file unused. `value_enumeration_v1` builds the same expressions from the operator
    # table BY TYPE, to a fixed point, so adding an operator adds every composition of it
    # rather than one sentence.
    #
    # It runs FIRST and the list below is the fallback, so this can only help: if the
    # enumeration has nothing, the incumbent path behaves exactly as it did.
    # IT DEFERS TO THE LIST, IT DOES NOT DISPLACE IT.
    #
    # Trying this the other way round -- enumeration first -- broke six tests, and every
    # break was a rule the incumbent had already paid for: comparison operands follow the
    # SENTENCE's order; a row question wants a cell of the extreme row, not a count; a
    # grouped table's aggregate column is named by its aggregation; plural and singular
    # are one word; and the type asked for is read from what the question asks, not from
    # a superlative. The incumbent search records 314 lines of such rules, essentially
    # one per comment, and each is a defect that was measured and fixed.
    #
    # Re-deriving them inside a second implementation is not progress; it is doing the
    # same work twice with no guarantee of a second success. So the enumeration is used
    # as an EXTENSION, not a replacement: the list runs first, and only when it can build
    # NOTHING does the enumerator look. That is exactly the case it was written for -- an
    # operator nobody appended -- and it cannot regress an answer the list already gives.
    list_answer = _compose_from_list(question, root, ents, words)
    if list_answer is not None:
        return list_answer
    try:
        from canonical.runtime import value_enumeration_v1 as _EN
        return _EN.choose(question, root, ents, words)
    except Exception:
        return None


def _compose_from_list(question: str, root: str, ents, words: list[str]):
    lex = Lexicon(words)
    steps = 0
    files = [e for e in ents if e.kind == "file"]

    aggs = lex.pick(_AGG_WORDS)
    maps = lex.pick(_MAP_WORDS)
    cmps = lex.pick(_CMP_WORDS)
    # ASKING FOR A ROW IS ASKING FOR ONE OF ITS CELLS.
    #
    # "which region has ...", "which item has ...", "whose amount is highest" all ask
    # for a cell of the extreme row. The trigger is not a list of column names -- it is
    # whether the question names a column the row can yield, OR uses a word that asks
    # for one. `item` was only in the latter, which is where it failed.
    _selection_headers: set[str] = set()
    for _e in files:
        _got = _columns(_e.path)
        if _got is not None:
            _h, _r = _got
            _selection_headers |= {_norm(h) for h in _h}
    # "PER <key>" IS NOT A ROW-SELECTION QUESTION.
    #
    # `_selection_headers` holds EVERY column name, so naming the quantity ("the total
    # AMOUNT per region") made `wants_select` true, narrowed the accepted types to
    # {text, number}, and excluded the vector-of-totals the question actually wanted. It
    # answered "which <key> has the most", which is a different question that happens to
    # share every one of its words.
    wants_select = (bool(lex.set & _PER_WORDS) is False) and (
        bool(lex.set & _SELECT_WORDS)
        or bool({_norm(w) for w in lex.set} & _selection_headers)
        or bool(lex.set & {"region", "name", "label", "item"}))

    # ---- leaf columns ----------------------------------------------------
    # Every (entity, column) pair the words point at, with the words it consumes.

    column_leaves: list[Node] = []
    tables: dict[str, tuple[list[str], list[list[str]]]] = {}
    for ent in files:
        got = _columns(ent.path)
        if got is None:
            continue
        header, rows = got
        tables[ent.rel] = got
        numeric_names = list(_numeric_columns(header, rows))
        for name in _candidate_columns(lex, header, numeric_names):
            steps += 1
            if steps > _MAX_STEPS:
                return None
            consumed = {w for w in lex.set if _norm(w) == _norm(name)
                        or (_norm(name) and _norm(name) in _norm(w))}
            node = _column_leaf(ent.path, ent.rel, name, consumed)
            if node is not None:
                column_leaves.append(node)

    # A TABLE WITH NO NUMERIC COLUMN IS NOT AN UNANSWERABLE TABLE.
    #
    # This returned early when no numeric column was found, so a text-only table never
    # reached the branches that COUNT its values -- "how many names are in names.csv" was
    # refused by a guard written before text columns existed. The guard's real job is to
    # skip the ARITHMETIC branches, so it now says that instead of ending the search.
    has_tables = bool(tables)
    if not column_leaves and not has_tables:
        return None

    # ---- build: aggregate over column, or over per-file aggregates --------

    def per_file_aggregates(kind: str) -> Node | None:
        """`mean` over one total from each file -- "the average of the totals"."""
        wanted = {w for w in lex.set if _norm(w) in {_norm(x) for x in _VECTOR_WORDS}}
        parts: list[Node] = []
        used = set()
        for ent in files:
            got = tables.get(ent.rel)
            if got is None:
                continue
            header, rows = got
            nums = _numeric_columns(header, rows)
            if len(nums) != 1:
                continue
            (colname, _vals), = nums.items()
            leaf = _column_leaf(ent.path, ent.rel, colname,
                                {x for x in lex.set if _norm(x) == _norm(colname)})
            if leaf is None:
                continue
            inner = _n("aggregate", ("sum", leaf), NUMBER, set(), f"sum({leaf.label})")
            parts.append(inner)
            used |= {w for w in lex.set if _norm(w) == _norm(colname)}
        if len(parts) < 2:
            return None
        # THE LABEL MUST SHOW THE STRUCTURE.
        #
        # This said `mean(totals)`, which is true and hides that the mean is over TWO
        # separately computed sums -- a reader could not tell a one-step average of a
        # column from a two-step average of totals. An answer's expression is the
        # evidence that it was built, so it has to be legible.
        vec = _n("vector", (tuple(parts),), NUMVEC, wanted | used,
                 "vector(" + ",".join(part.label for part in parts) + ")")
        return _n("aggregate", (kind, vec), NUMBER, wanted,
                  f"{kind}({vec.label})")

    candidates: list[Node] = []

    for kind in aggs:
        for leaf in column_leaves:
            candidates.append(_n("aggregate", (kind, leaf), NUMBER,
                                 lex.set & _AGG_WORDS[kind], f"{kind}({leaf.label})"))
        pv = per_file_aggregates(kind)
        if pv is not None:
            candidates.append(pv)

    # ---- map: digits / double / half over a number -----------------------
    if maps:
        bases = list(candidates) + [_n("aggregate", (a, l), NUMBER, lex.set & _AGG_WORDS[a],
                                       f"{a}({l.label})")
                                    for a in aggs for l in column_leaves]
        for m in maps:
            for b in bases:
                candidates.append(_n("map", (m, b), NUMBER,
                                     lex.set & _MAP_WORDS[m], f"{m}({b.label})"))

    # ---- select a row by an extreme, then take a cell --------------------
    if wants_select and aggs and tables:
        for by_kind in ("max", "min"):
            if by_kind not in aggs:
                continue
            for ent in files:
                got = tables.get(ent.rel)
                if got is None:
                    continue
                header, rows = got
                nums = _numeric_columns(header, rows)
                for by_col in nums:
                    row = _n("argmax", (ent.path, ent.rel, by_col, by_kind), ROW,
                             lex.set & _AGG_WORDS[by_kind] | {_norm(by_col)}
                             | {w for w in lex.set if _norm(w) == _norm(by_col)},
                             f"argmax:{by_col}@{ent.rel}")
                    candidates.append(row)
                    # A CELL IS TEXT ONLY IF THAT COLUMN HOLDS TEXT.
                    #
                    # This offered every column, so "which item has the biggest price"
                    # could return a PRICE -- a number presented as the name of the
                    # thing. The type has to be decided by the data, not by the word
                    # `which`: a cell is text when the column it comes from is text.
                    for h in header:
                        if h == by_col or h in nums:
                            continue
                        candidates.append(_n("cell", (row, h), TEXT,
                                             {_norm(h)}, f"cell[{h}]({row.label})"))

    # ---- compare two numbers --------------------------------------------
    if cmps:
        # A comparison needs one number from each of two files -- not an aggregate word in
        # the question. "is the total of a.csv less than the total of b.csv" names `total`;
        # "is a.csv bigger than b.csv" does not, and both are comparisons.
        #
        # WHICH COLUMN is resolved the way every other column is: the question's own word
        # when it names one ("the total UNITS in ..."), and only when it names none does
        # the file have to have exactly one numeric column. Requiring the count to be one
        # made a comparison impossible on any file with two numeric columns, even when the
        # question said which one it meant.
        sums: dict[str, Node] = {}
        for ent in files:
            got = tables.get(ent.rel)
            if got is None:
                continue
            header, rows = got
            nums = _numeric_columns(header, rows)
            if not nums:
                continue
            chosen = _candidate_columns(lex, header, list(nums))
            chosen = [c for c in chosen if c in nums]
            if len(chosen) != 1:
                continue
            # THE COLUMN WORD IS PART OF THE ACCOUNT, even when it was resolved by the
            # file rather than by the question. Building this leaf with an empty
            # `consumes` left `units` unaccounted for and rejected the whole comparison
            # -- the door refusing a question it had already worked out: True, and the
            # true answer was False. An answer that is not accounted for is not shown,
            # so an under-accounted CORRECT computation reads as a refusal.
            col_consumed = {x for x in lex.set
                            if _norm(x) == _norm(chosen[0])
                            or (_norm(chosen[0]) and _norm(chosen[0]) in _norm(x))}
            leaf = _column_leaf(ent.path, ent.rel, chosen[0], col_consumed)
            if leaf is not None:
                sums[ent.rel] = _n("aggregate", ("sum", leaf), NUMBER, set(),
                                   f"sum({leaf.label})")
        if len(sums) == 2:
            # OPERAND ORDER IS THE SENTENCE'S ORDER, NOT THE RESOLVER'S.
            #
            # Entities come back in resolution order, which is neither reading order nor
            # meaningful. `lt(a, b)` means a < b, so taking the dict's order literally
            # made "is the total units in returns.csv less than the total units in
            # inventory.csv" answer `False` -- the reverse of the truth, verified, and
            # rendered as an answer. A relation is between its operands AS WRITTEN.
            ordered = sorted(sums.items(), key=lambda kv: question.find(kv[0]))
            (ra, a), (rb, b) = ordered
            for kind in cmps:
                candidates.append(_n("compare", (kind, a, b), BOOL,
                                     lex.set & _CMP_WORDS[kind], f"{kind}({ra},{rb})"))

    # ---- grouping: a table, then an aggregate over its groups ----------
    #
    # This is where the answer space stops being a list. `groups(...)` produces a TABLE
    # whose rows are (key, aggregate), so `argmax`, `cell`, `count` and `compare` work on
    # it without knowing grouping exists -- the same operators, a new domain. One node
    # opens "per region", "for each region", "which region has the most", "how many rows
    # per region" and every composition that can be built on top of them.

    # ---- counting values in a text column -----------------------------
    #
    # A table with no numeric column is not unanswerable: "how many names are in
    # names.csv" is a COUNT of the values in a column, and the same `count` operator
    # that counts rows counts them. This was skipped because every branch above required
    # a numeric column to get started.
    for ent in files:
        got = tables.get(ent.rel)
        if got is None:
            continue
        header, rows = got
        nums = list(_numeric_columns(header, rows))
        table = _n("table", (str(ent.path),), TABLE, set(), f"t@{ent.rel}")
        for col in _text_candidates(lex, header, nums)[:2]:
            vals = _n("values_of", (table, col), TEXTVEC, {_norm(col)},
                      f"values({col})@{ent.rel}")
            # VALUES, NOT ROWS.
            #
            # "how many regions are in sales.csv" was answered with the row count, 4,
            # when there are three regions and `north` appears twice. A question about how
            # many DISTINCT things there are is not a question about how many rows there
            # are; both are honest counts of different sets, and offering only the first
            # is how the door returns a true number to a different question.
            candidates.append(_n("count", (vals,), NUMBER,
                                 lex.set & {"many", "count", "number"},
                                 f"count(values({col}))"))
            candidates.append(_n("count",
                                 (_n("distinct", (table, col), TEXTVEC, {_norm(col)},
                                     f"distinct({col})@{ent.rel}"),), NUMBER,
                                 lex.set & {"many", "count", "number", "distinct", "different", "unique"},
                                 f"count(distinct({col}))"))

    # ---- filtering: the same arithmetic over fewer rows ---------------
    #
    # A filter does not need a group. "the total amount in north" names a column and a
    # VALUE that occurs in it, and the tree supplies both. This was reachable only from
    # inside the grouping loop, which never runs when the question names no key -- so the
    # simplest useful composition in the language was unreachable.
    if tables:
        for ent in files:
            got = tables.get(ent.rel)
            if got is None:
                continue
            header, rows = got
            nums = _numeric_columns(header, rows)
            if not nums:
                continue
            # THE KEY NEED NOT BE NAMED; THE VALUE CAN IDENTIFY ITS OWN COLUMN.
            #
            # "the total amount in north" names no column -- it names a VALUE. Requiring
            # the key to match a header word made the filter unreachable for exactly the
            # questions it exists for. Which column holds `north` is a fact about the
            # tree, so the tree answers it.
            keys_here = _text_candidates(lex, header, list(nums))
            for h in header:
                if h in nums or h in keys_here:
                    continue
                if _literal_values(lex, {ent.rel: (header, rows)}, h):
                    keys_here.append(h)
            for key in keys_here[:3]:
                for key_val in _literal_values(lex, tables, key)[:4]:
                    filtered = _n("filter",
                                  (_n("table", (str(ent.path),), TABLE, set(), f"t@{ent.rel}"),
                                   key, key_val), TABLE, {_norm(key_val)},
                                  f"where {key}={key_val}")
                    for val in _numeric_candidates(lex, header, list(nums))[:2]:
                        leaf = _n("column_from", (filtered, val), NUMVEC, {_norm(val)},
                                  f"{val} where {key}={key_val}")
                        for kind in (aggs or ["count"]):
                            candidates.append(_n("aggregate", (kind, leaf), NUMBER,
                                                 lex.set & _AGG_WORDS[kind],
                                                 f"{kind}({leaf.label})"))

    grouped_tables: list[Node] = []
    if tables:
        for ent in files:
            got = tables.get(ent.rel)
            if got is None:
                continue
            header, rows = got
            nums = _numeric_columns(header, rows)
            if not nums:
                continue
            keys = _text_candidates(lex, header, list(nums))
            vals = _numeric_candidates(lex, header, list(nums))
            if not vals and len(nums) == 1:
                vals = list(nums)
            for key in keys[:2]:
                for val in vals[:2]:
                    for kind in (aggs or ["count"]):
                        inner = _n("group", (_n("table", (str(ent.path),), TABLE, set(),
                                               f"table@{ent.rel}"), key, val),
                                   "grouped", set(), f"group[{key}]@{ent.rel}")
                        grouped_tables.append(
                            _n("groups", (inner, kind, key, val), TABLE, set(),
                               f"{kind}({val}) by {key}"))

    for g in grouped_tables:
        gkey, gval = g.args[2], g.args[3]
        gcol = f"{g.args[1]}({gval})"
        # the aggregate value of one named group: "the total amount in north"
        for key_val in _literal_values(lex, tables, gkey):
            filtered = _n("filter",
                          (_n("table", (_table_rel_of(tables, gkey, gval) or "",), TABLE, set(), "t"),
                           gkey, key_val),
                          TABLE, {_norm(key_val)}, f"where {gkey}={key_val}")
            for kind in (aggs or ["count"]):
                for val in ([gval] if gval else []):
                    leaf = _n("column_from", (filtered, val), NUMVEC, {_norm(val)},
                              f"{val} where {gkey}={key_val}")
                    candidates.append(_n("aggregate", (kind, leaf), NUMBER,
                                         lex.set & _AGG_WORDS[kind],
                                         f"{kind}({leaf.label})"))
        # a whole grouped table as a set of values
        # "PER REGION" ASKS FOR THE WHOLE GROUPING, not one number out of it.
        #
        # Returning the first aggregate would be a true fragment answering a question
        # about all of them. The grouped table IS the answer, and `values_of` reads its
        # aggregate column in key order.
        # A GROUPED COLUMN OF NUMBERS IS THE ANSWER TO "per <key>": the totals, one per
        # group, not one number out of them. Declaring it NUMVEC is what lets the type
        # system accept it instead of the search concluding that a question about all the
        # groups has no answer because no single number is one.
        candidates.append(_n("values_of", (g, gcol), NUMVEC, set(), f"{gcol}s by {gkey}"))
        candidates.append(_n("values_of", (g, gkey), TEXTVEC, set(), f"{gkey}s"))
        # "how many rows per region" counts GROUPS, not rows: there are three, not four,
        # and the row count is already the answer to a question that did not say "per".
        candidates.append(_n("count",
                             (_n("values_of", (g, gcol), TEXTVEC, set(),
                                 f"{gcol}s by {gkey}"),), NUMBER,
                             lex.set & {"many", "count", "number", "rows", "row", "records"}
                             | {_norm(gkey)},
                             f"count(groups by {gkey})"))
        candidates.append(_n("count", (_n("table", (_table_rel_of(tables, gkey, gval) or "",),
                                        TABLE, set(), "t"),), NUMBER,
                             lex.set & {"rows", "row", "many", "count", "number", "records"},
                             "count(rows)"))
        # which key has the largest / smallest group
        for extreme in ("max", "min"):
            if aggs and extreme not in aggs:
                continue
            row = _n("argmax_table", (g, gcol, extreme), ROW,
                     lex.set & _AGG_WORDS[extreme], f"argmax_{extreme}({gcol})")
            candidates.append(_n("cell", (row, gkey), TEXT, {_norm(gkey)},
                                 f"cell[{gkey}]({row.label})"))
            candidates.append(
                _n("cell", (row, gcol), NUMBER, {_norm(gval)}, f"cell[{gcol}]({row.label})"))

    # ---- choose: right type, accounts for the question, verifies ---------
    # THE TYPE OF THE ANSWER IS WHAT WAS ASKED FOR.
    #
    # This became TEXT whenever any column was named, so "what is the total of the
    # amounts in sales.csv" -- which names the column `amount` -- stopped accepting a
    # NUMBER and the question went unbuilt. Select only when a row is asked for AND no
    # aggregate was: an aggregate over a named column is still a number.
    if cmps:
        want_types = {BOOL}
    elif lex.set & _PER_WORDS:
        # "per <key>" wants one answer per group, and that is a vector -- never the single
        # number that some other branch of this chain would have accepted.
        want_types = {NUMVEC, TEXTVEC, NUMBER}
    elif wants_select and not aggs:
        want_types = {TEXT}
    elif wants_select and aggs:
        want_types = {TEXT, NUMBER}
    else:
        want_types = {NUMBER}

    best = None
    # PREFER THE EXPRESSION THAT EXPLAINS THE MOST OF THE QUESTION.
    #
    # Several candidates account for every word and verify, and the one tried first won:
    # "how many regions" got the ROW count because it was appended earlier, and "the total
    # amount per region" got three groups when it asked for their totals. Order of
    # construction is not a reason to prefer an answer; the operator that consumes MORE
    # of the question is the more specific one. Ties keep the earlier candidate, so the
    # simple questions are unaffected.
    # FILTER BY TYPE FIRST, THEN ORDER.
    #
    # Ordering the whole list and skipping the wrong-typed entries inside the loop looked
    # equivalent and was not: two candidates with equal specificity, one the right type and
    # one not, were ranked by construction order, so the wrong-typed twin could decide that
    # "the total amount per region" had no answer. A sort is only a preference among
    # things that are ANSWERS.
    usable = [(i, c) for i, c in enumerate(candidates) if c.type in want_types]
    ordered = sorted(
        usable,
        key=lambda pair: (-len({_norm(w) for w in
                                (pair[1].consumes | _structural_words(pair[1]))}),
                          pair[0]),
    )
    for _idx, cand in ordered:
        steps += 1
        if steps > _MAX_STEPS:
            break
        # A MORE SPECIFIC OPERATOR BEATS A MORE GENERAL ONE.
        #
        # `count(values(region))` is 4 and `count(distinct(region))` is 3; both verify, and
        # the general one was tried first, so "how many regions" came back 4. When the
        # question asked for distinct things -- or said "per" -- only the expression that
        # actually makes that distinction can answer it.
        if lex.set & _DISTINCT_WORDS and cand.op in ("count", "aggregate"):
            child = cand.args[1] if cand.op == "aggregate" else cand.args[0]
            if isinstance(child, Node) and child.op == "values_of":
                continue
        # ...AND "per" IS NOT A CARDINALITY WORD.
        #
        # `per` was in `_DISTINCT_WORDS`, so "the total amount per region" -- which asks
        # for ALL the totals, not how many there are -- was rejected by a rule meant for
        # "how many different regions". A word that changes what the answer IS must not be
        # the same word that changes how many answers there are.
        if cand.op == "count" and lex.set & _PER_WORDS:
            continue
        # THE ROOT MUST ACCOUNT FOR THE QUESTION'S WORDS.
        # A correct answer to a different question is not an answer.
        # BOTH SIDES OF THE COMPARISON ARE NORMALISED, OR NEITHER IS.
        #
        # The expression's account is normalised (`name`), the question's remaining words
        # were not (`names`), so a question was refused for a word it had dealt with. The
        # account and the check have to agree on what "the same word" means -- this is the
        # singular/plural rule `_norm` already owns.
        # THE SUBTRACTION HAPPENS IN NORMALISED SPACE, ON BOTH SIDES.
        #
        # Normalising each side separately is not enough: `without` removes RAW words, so
        # an account holding `name` could never cancel a question that said `names`, and
        # the door refused an expression whose value it had already computed. Whatever
        # "the same word" means for column matching, it has to mean here.
        consumed = {_norm(w) for w in (cand.consumes | _structural_words(cand))}
        left = {_norm(w) for w in lex.raw} - consumed - {_norm(w) for w in _noise}
        if left:
            continue
        try:
            value = evaluate(cand)
        except (EvalError, TypeError, ValueError, ZeroDivisionError,
                AttributeError, KeyError, IndexError):
            # A CANDIDATE THAT CRASHES IS A CANDIDATE THAT DID NOT WORK.
            #
            # The search builds many combinations; one of them raising is normal and must
            # skip, not abort the question. `AttributeError` was missing here, so a cell
            # that happened not to be text took the whole door down instead of being
            # discarded -- a crash where a refusal belongs.
            continue
        if value is None:
            continue
        # THE CHECK IS PART OF THE CHOICE, NOT A GATE AFTER IT.
        #
        # `verify()` re-derived the quantity from the partition and could reject a wrong
        # answer -- but nothing consulted it while choosing, so it ran after the decision
        # had already been made. Measured: with `groups` silently dropping one group, the
        # search returned [150.0, 150.0] (west's 250 missing) and `verify()` said False on
        # exactly that result. The machinery to reject it existed and was NOT IN THE LOOP.
        #
        # A candidate whose value violates its own operator's invariant is not a weaker
        # answer to fall back on; it is a wrong one, and the search must keep looking.
        if holds(cand, value) is False:
            # AN UNSOUND CANDIDATE ABORTS THE QUESTION; IT DOES NOT HAND OVER TO A WEAKER ONE.
            #
            # The first version `continue`d, and that was wrong in a way worth recording:
            # with `groups` lossy, the totals were correctly refused and the search then
            # answered a DIFFERENT question from the leftovers -- the key vector
            # ['north','south'] for a question about amounts, and the row count 4 for
            # "how many regions". Seeing the violation and then quietly substituting
            # another question is the defect this project exists to catch, one layer up.
            #
            # `holds` is not a preference; it is a contradiction between the expression
            # and the data. When it fires, nothing built from that data here is an answer.
            return None
        best = (cand, value)
        break

    if best is None:
        return None
    cand, value = best
    # WORDS THAT CHANGED THE SHAPE OF THE ANSWER WERE CONSUMED BY IT.
    #
    # `per` is glue to the SEARCH -- it does not name a column, so the vocabulary treats
    # it as noise -- but it is the reason this answer is all the group totals instead of
    # one of them. Leaving it out of the account made the door report a word unanswered
    # on the answer that word had just chosen the form of, and the refusal was correct
    # about its own bookkeeping and wrong about the question.
    shape_words = {w for w in lex.raw if _norm(w) in _SHAPE_WORDS}
    return {"node": cand, "value": value,
            # WHAT THE EXPRESSION CONSUMED, stated by the expression. Reconstructing this
            # from the operation's name is what reported `digits` as an unanswered word
            # of a question that had just been answered with the digits.
            "accounted": sorted(cand.consumes | _structural_words(cand) | shape_words)}


# Words that describe the ACT of asking rather than the thing asked about.
_noise = {
    "how", "many", "what", "which", "is", "are", "the", "of", "in", "a", "an", "and",
    "do", "does", "it", "that", "this", "there", "for", "to", "than", "then", "be",
    "tell", "me", "give", "show", "please", "from", "on", "at", "by", "with", "value",
    "result", "answer", "per", "each", "every", "for", "respectively", "all",
    "across", "by", "grouped", "also", "both", "same", "value", "row", "rows",
}


def _structural_words(node: Node) -> frozenset:
    """Every word an expression consumes, at any depth.

    This must start from the node's OWN `consumes` and union the children, not rebuild
    the set from the operators alone. Rebuilding dropped what each leaf had already
    accounted for -- the column leaf consumed `amounts`, this function did not know it,
    and every composition was rejected with `amounts` unaccounted. Two derivations of
    one fact, disagreeing: the same defect as the three phrasing lists, one layer down
    inside the replacement for them.
    """
    out: set[str] = set(node.consumes)
    if node.op == "aggregate":
        out |= _AGG_WORDS.get(node.args[0], set())
        out |= _structural_words(node.args[1])
    elif node.op == "map":
        out |= _MAP_WORDS.get(node.args[0], set())
        out |= _structural_words(node.args[1])
    elif node.op == "compare":
        out |= _CMP_WORDS.get(node.args[0], set())
        out |= _structural_words(node.args[1]) | _structural_words(node.args[2])
    elif node.op == "vector":
        for c in node.args[0]:
            out |= _structural_words(c)
        out |= _VECTOR_WORDS
    elif node.op == "cell":
        out |= _structural_words(node.args[0])
    elif node.op == "argmax":
        out |= _SELECT_WORDS | {"row", "record", "entry"}
    elif node.op == "argmax_table":
        out |= _SELECT_WORDS | {"row", "record", "entry"}
        out |= _structural_words(node.args[0])
    elif node.op in ("groups", "group"):
        # A grouped node's own words are its aggregate and its columns. Leaving them out
        # of the account is what rejected "the total amount per region": the expression
        # computed 250 and the door could not see that `total`, `amount` or `per` had
        # been dealt with.
        if node.op == "groups":
            out |= _AGG_WORDS.get(node.args[1], set())
            # "*" is not a word of the question. Accounting for it adds a token no
            # sentence contains, and an expression that accounts for `*` is not thereby
            # answering "rows" -- the ROW is what the question already said.
            if node.args[3] != "*":
                out.add(_norm(node.args[3]))
        out.add(_norm(node.args[2]))
        out |= _structural_words(node.args[0])
    elif node.op == "filter":
        out.add(_norm(node.args[1]))
        out |= _structural_words(node.args[0])
    elif node.op == "column_from":
        out.add(_norm(node.args[1]))
        out |= _structural_words(node.args[0])
    elif node.op == "values_of":
        out |= _structural_words(node.args[0])
    elif node.op == "count":
        out |= _structural_words(node.args[0])
        if isinstance(node.args[0], Node) and node.args[0].op == "table":
            # counting a TABLE's rows is the question "how many rows", and `rows` is
            # exactly what it accounts for.
            out |= _ROW_WORDS
    # SINGULAR AND PLURAL ARE THE SAME WORD.
    #
    # The account held `name`, the question said `names`, and the expression was rejected
    # as ignoring a word it had plainly dealt with. `_norm` is the one place that decides
    # this for column matching; the account has to agree with it or the door refuses
    # answers it has already computed.
    if node.op in ("table", "groups", "group", "filter", "column_from",
                   "values_of", "count", "distinct", "contains_all"):
        # EVERY BRANCH THAT HAS CHILDREN MUST DESCEND INTO THEM.
        #
        # Adding an operator and forgetting this line is the third time the same defect
        # appeared: the node computes the right value, its own words are accounted for,
        # and the words its CHILDREN consumed are invisible -- so the whole expression is
        # rejected as not answering the question. The check is written as a completion
        # rather than another `elif` so a new operator is one list entry away from being
        # correct instead of silently wrong.
        for a in node.args:
            if isinstance(a, Node):
                out |= _structural_words(a)
            elif isinstance(a, (list, tuple)):
                for x in a:
                    if isinstance(x, Node):
                        out |= _structural_words(x)
    # NORMALISE LAST, not first.
    #
    # This ran before the child descent, so a word contributed by a CHILD arrived raw --
    # the account held `name`, the question said `names`, and the expression was refused
    # as ignoring a word it had dealt with. It is the final statement now, because it is
    # a statement about the whole set.
    out = {w for w in out if w} | {_norm(w) for w in out if w}
    return frozenset(out)


# ---------------------------------------------------------------------------
# Re-derivation. The expression is rebuilt from the tree and re-evaluated; only the
# re-derived value is ever reported.
# ---------------------------------------------------------------------------

def verify(question: str, root: str, result: dict) -> bool:
    """Is the recorded answer TRUE, not merely reproducible?

    WHAT THIS WAS. It called `evaluate(node)` a second time and compared. Same
    interpreter, same file, same ordering -- so it proved DETERMINISM and was read as
    CORRECTNESS. Every wrong answer this algebra ever produced passed it: the row count
    of 4 offered for "how many regions", a cardinality of 3 offered for "the total per
    region", and 550 offered for "the amounts in west". The check could not fail on a
    wrong answer, because a wrong answer is perfectly reproducible.

    WHAT IT IS. A quantity is re-derived INDEPENDENTLY of the expression that produced
    it -- from the partition itself, not by re-running the expression -- and the
    structural invariants of the operator are asserted at the same time. A grouping
    whose parts do not sum to the whole is wrong whether or not it re-runs.
    """
    node = result.get("node")
    if node is None:
        return False

    # (1) Reproducible. Necessary, not sufficient; kept because a nondeterministic
    #     answer is definitely wrong.
    #
    # THE CHECK MUST NOT READ THE ANSWER OUT OF THE CACHE IT IS CHECKING.
    #
    # `evaluate` is memoised, and the memo is populated by the very search that produced
    # this value -- so calling `evaluate(node)` here would return the sitting answer and
    # compare it with itself, which is exactly the tautology this function was rewritten
    # to stop being. `_evaluate` is the uncached body: a second real computation.
    try:
        again = _evaluate(node)
    except (EvalError, TypeError, ValueError, ZeroDivisionError,
            AttributeError, KeyError, IndexError):
        return False
    if not _same_value(again, result.get("value")):
        return False

    # (2) Consistent with the partition it came from, computed independently of it.
    #     A failure here is a failure of the ANSWER, which the old check could never see.
    return holds(node, result.get("value"))


# EVALUATION MEMO, SCOPED TO ONE QUESTION.
#
# Checking soundness asks about sub-expressions the search has already evaluated, and
# candidates SHARE subtrees -- one `groups` node sits under a dozen of them. Without a
# memo, putting the check in the loop re-evaluated whole trees once per candidate: the
# trace showed hundreds of identical `count(amount)s by region` evaluations for a single
# question. Nodes are immutable after construction, so a node's value cannot change
# inside one question and caching it is exactly a memo.
_EVAL_MEMO: dict = {}


def _reset_memo() -> None:
    _EVAL_MEMO.clear()


def holds(node: Node, value) -> bool:
    """Is `value` a correct value FOR THIS NODE, checked without trusting the evaluation?

    This is the half of `verify` that can fail. It is separate from reproducibility
    because the SEARCH needs it: a candidate has just been evaluated, so re-running the
    evaluation would only confirm determinism, and the invariants are exactly the part
    that can say "this expression produced a value it should not have been able to".

    `verify` is `reproducible AND holds`. The search uses `holds`.
    """
    try:
        # JUDGE THE VALUE GIVEN, NOT ONE RE-DERIVED FROM THE SAME EXPRESSION.
        #
        # This call dropped `value` on the floor: `_holds_invariants(node)` re-evaluated the
        # node and compared the expression with ITSELF. `holds(node, 1027)` for a sum that
        # is 27 checked 27 and returned True. Every law declared on an operator was
        # therefore a tautology -- the one thing an invariant exists to catch, a value the
        # expression *should not* have been able to produce, was the one thing it could not
        # see, because it never looked at the value.
        #
        # An invariant is only worth stating if it derives the expected value by a route
        # the expression did not take. Passing the value in is what makes the routes
        # different: the expression computed it once, and the law asks whether that number
        # is possible.
        return _holds_invariants(node, value)
    except (EvalError, TypeError, ValueError, ZeroDivisionError,
            AttributeError, KeyError, IndexError):
        return True


def _same_value(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) < 1e-9
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same_value(x, y) for x, y in zip(a, b))
    return a == b


def _child_nodes(node: Node):
    """The sub-expressions of `node`, for a check that must hold at every depth."""
    for arg in getattr(node, "args", ()) or ():
        if isinstance(arg, Node):
            yield arg
        elif isinstance(arg, (list, tuple)):
            for item in arg:
                if isinstance(item, Node):
                    yield item


_NO_VALUE = object()


def _holds_invariants(node: Node, value=_NO_VALUE) -> bool:
    """The statements about a partition that must be true of any correct answer.

    These are asserted against the DATA, by a route the expression did not take: the
    parts are re-derived from the rows and compared with the whole. They catch the class
    of error the reproducibility check structurally cannot -- an expression that is
    faithfully evaluated and answers the wrong question about the right table.
    """
    # AN INVARIANT IS A PROPERTY OF THE EXPRESSION, NOT OF ITS ROOT.
    #
    # This checked only the node it was handed, so a violation one level down was
    # invisible: `cell[region](argmax(groups))` was judged on the `cell`, whose own
    # statement is vacuous, and the lossy `groups` underneath was never examined --
    # "which region has the largest total" returned `north` with west's 250 missing. Every
    # judgement about a value here is really a judgement about the whole expression that
    # produced it, so the walk descends before it answers.
    for child in _child_nodes(node):
        # a child is judged on its own value, which is a different route from the parent's
        if not _holds_invariants(child):
            return False

    # EVERY AGGREGATE ANSWERS TO ITS OWN DECLARED LAW.
    #
    # Until now `_holds_invariants` returned True for every aggregate except `sum`, so a
    # newly declared operator -- `median`, say -- was a word nothing could check. The law
    # lives in the operator's declaration, so a declaration cannot exist without one and
    # an operator cannot be added that the system is unable to be wrong with.
    if node.op == "aggregate":
        kind, child = node.args[0], node.args[1]
        try:
            values = evaluate(child)
        except (EvalError, TypeError, ValueError, ZeroDivisionError, KeyError, IndexError):
            return True
        if value is _NO_VALUE:
            # reached from an invariant walk that has no value to judge: nothing to check
            try:
                got = evaluate(node)
            except (EvalError, TypeError, ValueError, ZeroDivisionError, KeyError, IndexError):
                return True
        else:
            got = value
        # PASS THE TABLE THROUGH; DO NOT FLATTEN IT TO "NOT JUDGED".
        #
        # `values if isinstance(values, list) else None` discarded every table before the
        # law could see it, so `count(t@file)` was never checked at all -- and a count of a
        # table is exactly the operator that returned 2 for every file in the world. The
        # law for a count is about rows, and rows are what the table has.
        verdict = aggregate_holds(kind, values, got)
        if verdict is False:
            return False

    # A GROUPING'S KEYS ARE THE DISTINCT KEYS IN THE ROWS IT SUMMARISES.
    #
    # This was stated separately for every READER of a grouping -- `count(values_of(...))`,
    # `values_of(groups)`, `column_from(groups)`, `argmax_table(groups)` -- and the fourth
    # reader, `distinct(groups)`, had no check at all: with a lossy `groups` it returned
    # ['north','south'] for a question about amounts and passed. One statement about the
    # grouping covers every reader that will ever exist, including ones not written yet;
    # one statement per reader covers only the readers somebody remembered.
    if node.op == "groups" and isinstance(node.args[0], Node) and node.args[0].op == "group":
        inner = node.args[0]
        # `group` is (table, key, value) and `groups` is (grouped, agg, key, value).
        # Using the wrong slot here compares the DISTINCT VALUES of a column against the
        # distinct KEYS of a grouping, which never agree -- so the check said every
        # grouping was broken and the enumerator refused three questions it had answered
        # a minute earlier. An invariant that fires on correct data is worse than none.
        key = inner.args[1]
        try:
            source = evaluate(inner.args[0])
            index = source["_header"].index(key)
            expected = {r[index] for r in source["_body"] if index < len(r)}
            got = evaluate(node)
            keys = {r[0] for r in got["_body"]}
        except (EvalError, KeyError, IndexError, TypeError, ValueError):
            return True
        if keys != expected:
            return False

    if node.op == "count":
        inner = node.args[0]
        # A COUNT OVER DISTINCT VALUES CANNOT EXCEED THE VALUES IT DISTINGUISHES.
        # `count(distinct(region))` = 3 and `count(values(region))` = 4 are both true of
        # `sales.csv`; the invariant says the first can never exceed the second, which is
        # exactly the relationship that makes them answers to different questions.
        if inner.op == "distinct" and isinstance(inner.args[0], Node) and inner.args[0].op == "table":
            table = evaluate(inner.args[0])
            column = inner.args[1]
            index = table["_header"].index(column)
            cells = [r[index] for r in table["_body"] if index < len(r)]
            distinct = {_norm(c) if isinstance(c, str) else c for c in cells}
            # EXACT, NOT A BOUND. `<=` would accept the row count as a "distinct count"
            # whenever it happened to be an upper bound, which is the original bug.
            return int(evaluate(node)) == len(distinct)
        # THE PARTS OF A GROUPING COUNT TO THE DISTINCT KEYS IN THE ROWS.
        #
        # This compared against the grouping's OWN `_keys`, so a `groups` that dropped a
        # bucket dropped the key with it and the count agreed with itself: "how many
        # regions" would have answered 2, and the search -- seeing nothing wrong -- fell
        # through to the row count of 4. The keys have to be counted from the ROWS, which
        # is the route the grouping did not take.
        if inner.op == "values_of" and isinstance(inner.args[0], Node) and inner.args[0].op == "groups":
            grouped = inner.args[0]
            table = evaluate(grouped.args[0].args[0])
            key = grouped.args[2]
            index = table["_header"].index(key)
            groups = {r[index] for r in table["_body"] if index < len(r)}
            return int(evaluate(node)) == len(groups)
        return True

    # A TOTAL OVER GROUPS EQUALS THE TOTAL OVER THE ROWS THEY PARTITION.
    #
    # This is stated for EVERY operator that reads a grouping's aggregate column, not
    # just `values_of`. `column_from(groups(...))` -- the enumerator's favourite way to
    # read the same thing -- returned [150.0, 150.0] from a grouping that had lost west,
    # and `holds` passed it because the invariant only knew the `values_of` spelling. An
    # invariant that holds for one spelling of an operation and not another is not an
    # invariant; it is a fact about a string.
    if node.op in ("values_of", "column_from") and isinstance(node.args[0], Node) and node.args[0].op == "groups":
        grouped = node.args[0]
        kind, with_ = grouped.args[1], grouped.args[3]
        if kind != "sum":
            return True
        parts = evaluate(node)
        whole = _sum_of_column(grouped.args[0].args[0], with_)
        if whole is None or not parts:
            return True
        return abs(sum(parts) - whole) < 1e-6

    # A CHOICE AMONG GROUPS IS ONLY AS GOOD AS THE GROUPS.
    #
    # `argmax_table` over a grouping that lost a key returns the largest of what is left
    # and looks exactly like an answer -- with `groups` lossy, "which region has the
    # largest total" returned `north`, because west's 250 was not in the table. The
    # invariant is the same one the totals use: the groups must partition the rows.
    if node.op == "argmax_table":
        grouped = node.args[0]
        if isinstance(grouped, Node) and grouped.op == "groups" and grouped.args[1] == "sum":
            whole = _sum_of_column(grouped.args[0].args[0], grouped.args[3])
            parts = evaluate(_n("values_of", (grouped, f"{grouped.args[1]}({grouped.args[3]})"),
                                 NUMVEC, set(), "parts"))
            if whole is not None and parts:
                return abs(sum(parts) - whole) < 1e-6

    # EVERY GROUP EXISTED BEFORE IT WAS COUNTED.
    if node.op == "values_of" and isinstance(node.args[0], Node) and node.args[0].op == "groups":
        return True

    return True


def _sum_of_column(table_node: Node, column: str):
    """The total of `column` over ALL rows -- the independent check for a grouping."""
    table = evaluate(table_node)
    if column not in table["_header"]:
        return None
    index = table["_header"].index(column)
    total = 0.0
    seen = False
    for row in table["_body"]:
        if index >= len(row):
            continue
        number = _to_float(row[index])
        if number is None:
            return None
        total += number
        seen = True
    return total if seen else None


def describe(node: Node) -> str:
    return node.label


def render(result: dict) -> str:
    node = result["node"]
    value = result["value"]
    if isinstance(value, bool):
        text = "yes" if value else "no"
    elif isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = str(value)
    return f"{text}   [built: {node.label}]"
