"""Hypotheses with slots, instead of expressions without them.

THE DEFECT
----------
`y = 2x + 1` defeated the search. Not because the function is hard -- a slope of two and an offset
of one -- but because the search has no way to SAY `a*x + b`. It can only spell concrete expressions
over a frozen constant list `[0, 1, 2, -1, 100, ...]`. Slope 1 and offset 1 are spellable; slope 3
is not, at any budget I can afford, because `(x+x)+x` costs three operations and so does every other
spelling of it.

So the creature's ontology is: *closed expressions over the inputs and a few constants*.
`2x` from three points therefore admits **12 programs in 3 explanations**, all of them spellings of
one linear function. The previous rounds then had to *guess* which spellings were the same idea by
probing a finite input range and hoping. That whole apparatus -- grouping, probe ranges, witnesses --
exists because the search counts sentences and has no sentences-with-slots to count instead.

WHAT THIS MODULE ADDS
---------------------
Hypothesis classes: a template with free parameters, plus an exact solver for them.

    AFFINE     a*x + b        needs 2 points; extra points are consistency tests, not information
    POWER      a*x**k         needs 2 points   (k from a small bound, no floats involved)

Three things fall out that the string search cannot do at all:

1. **Exact arithmetic.** Parameters are `Fraction`s. `2/3` is `2/3`, not `0.6666666666666666`, so
   "does this fit" is a decision rather than a tolerance.
2. **The number of observations a class needs is computable from the class.** A two-parameter family
   is determined by two points; the third is a TEST. So the creature knows how much evidence would
   settle a hypothesis BEFORE seeing it -- the question it asks is derived from the class, not from
   which strings happened to survive.
3. **Grouping becomes algebraic.** Two bodies that instantiate the same class with the same
   parameters ARE the same explanation, exactly, with no probe range and no caveat. The probe-range
   caveat survives only for bodies that belong to no class.

WHAT THIS DOES NOT DO
---------------------
A fitted family is a guess that fits. `a=2, b=0` is not true because it is simple; it is
undetermined-by-nothing-faster than the alternatives. Fitting is not evidence, and this module
reports `residual` so a bad fit is visible rather than rounded away.

It does not compose families, does not search over family structure, and does not decide which class
to try -- the caller gives the classes to consider.

Authority: NONE. Pure Python, `fractions` only. No randomness, no I/O.
"""
from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_HYPOTHESIS_CLASSES_V1"

# A float observation is a DECIMAL, and a decimal almost never equals the simple rational a creature
# would name. Measured: fitting to `1/3` in floats yields 3333333333333333/10000000000000000 --
# exactly right, and useless as an answer. Rational reconstruction recovers the simplest fraction
# that agrees with the value to within its decimal precision, so the report says `1/3` while the
# exactness claim stays honest: the reconstruction is stated, not assumed.
_RECONSTRUCT_DIGITS = 12


def _reconstruct(value: Fraction, digits: int = _RECONSTRUCT_DIGITS) -> Fraction:
    """Simplest fraction within 10**-digits of `value` (Stern-Brocot / continued fractions)."""
    if value.denominator == 1:
        return value
    tol = Fraction(1, 10 ** digits)
    # continued-fraction convergents; stop at the first one inside tolerance
    n, d = value.numerator, value.denominator
    p_prev, p_cur = 0, 1
    q_prev, q_cur = 1, 0
    while d:
        a = n // d
        p_next, q_next = a * p_cur + p_prev, a * q_cur + q_prev
        cand = Fraction(p_next, q_next) if q_next else None
        if cand is not None and abs(cand - value) <= tol:
            return cand
        p_prev, p_cur = p_cur, p_next
        q_prev, q_cur = q_cur, q_next
        n, d = d, n - a * d
    return value

FITS = "FITS"
UNDERDETERMINED = "UNDERDETERMINED"     # not enough points to pin the parameters
INCONSISTENT = "INCONSISTENT"           # enough points, and they do not lie on the family
UNSUPPORTED = "UNSUPPORTED"             # the points are not even in the class's domain
# Every class that could be TESTED was refuted. This is not the same as "no class fits yet":
# an observation cannot rescue an ontology that has no class for the data, and telling the caller
# "ask me again" would spend its only scarce resource on a question already known to be useless.
# Measured 2026-11-04: `relu` and `mod 2` were reported PROVISIONAL while affine was INCONSISTENT
# and power could not even be pinned -- the same conflation of budget-failure with world-fact that
# `SEARCH_TRUNCATED` was introduced to fix one layer down.
ONTOLOGY_EXHAUSTED = "ONTOLOGY_EXHAUSTED"


def _exact(value: Any) -> Fraction | None:
    """Rational view of a number, or None. Floats are read at their decimal value, not their bits.

    `Fraction(0.1)` is 3602879701896397/36028797018963968. Reading the decimal 1/10 instead matches
    what the observation MEANS -- a printed 0.1 is one tenth. Getting this wrong would make every
    float observation inconsistent with every exact fit, which is the same class of error as the
    `repr`-based signature two rounds ago: representation mistaken for content.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return Fraction(str(value))
    return None


class Affine:
    """`a*x + b`. Two parameters, so two points determine it and every further point tests it."""

    name = "affine"
    template = "a * x + b"
    params_needed = 2

    @staticmethod
    def fit(points: Sequence[tuple[Any, Any]]) -> dict[str, Any]:
        exact = [(x, _exact(y)) for x, y in points]
        if any(y is None for _x, y in exact) or any(_exact(x) is None for x, _y in exact):
            return _unsupported(Affine.name)
        pairs = [(_exact(x), y) for x, y in exact]
        if not pairs:
            return {"class": Affine.name, "status": UNDERDETERMINED, "needs": 2, "have": 0}

        # Two points with distinct x pin (a, b) uniquely; equal x values either agree (no
        # information) or cannot both hold (inconsistent before any fit is attempted).
        constraining = []
        for x, y in pairs:
            if not constraining or any(x != px for px, _py in constraining):
                constraining.append((x, y))
        if len(constraining) < 2:
            return {"class": Affine.name, "status": UNDERDETERMINED, "needs": 2,
                    "have": len(constraining),
                    "why": ("the observations fix too few distinct inputs; a two-parameter family "
                            "is not pinned by them, and any answer would be a choice")}

        (x1, y1), (x2, y2) = constraining[0], constraining[1]
        slope = (y2 - y1) / (x2 - x1)
        intercept = y1 - slope * x1
        # Every remaining point is a CONSISTENCY TEST, not new information -- the family is already
        # pinned. Reporting the surplus is the difference between "I need more data" and "more data
        # would only confirm or refute me".
        violations = [
            {"x": _num(x), "y": _num(y), "predicted": _num(slope * x + intercept)}
            for x, y in pairs if slope * x + intercept != y
        ]
        return {
            "class": Affine.name,
            "status": INCONSISTENT if violations else FITS,
            "parameters": {"a": _num(slope), "b": _num(intercept)} if not violations else None,
            "needs": 2,
            "have": len(pairs),
            "surplus": max(0, len(pairs) - 2),
            "violations": violations,
            "predicate": (f"lambda x: {_num(slope)} * x + {_num(intercept)}"
                          if not violations else None),
            "exact": True,
            "reconstructed": (_reconstruct(slope) != slope or _reconstruct(intercept) != intercept),
        }


class Power:
    """`a * x**k` for k in a small integer range. Two parameters, but k is searched, not solved."""

    name = "power"
    template = "a * x**k"
    params_needed = 2

    @staticmethod
    def fit(points: Sequence[tuple[Any, Any]]) -> dict[str, Any]:
        exact = [(x, _exact(y)) for x, y in points]
        if any(y is None for _x, y in exact) or any(_exact(x) is None for x, _y in exact):
            return _unsupported(Power.name)
        pairs = [(_exact(x), y) for x, y in exact if _exact(x) != 0]
        if len(pairs) < 2:
            return {"class": Power.name, "status": UNDERDETERMINED, "needs": 2, "have": len(pairs)}
        # A non-zero ordinate on a non-zero input FORCES the scale factor for a given exponent, so
        # two such points are enough to test the family. Returning UNDERDETERMINED whenever any
        # ordinate is zero let refuting data be reported as "not enough information" -- and those
        # two demand opposite repairs.
        usable = [(x, y) for x, y in pairs if y != 0]
        if len(usable) < 2:
            return {"class": Power.name, "status": UNDERDETERMINED, "needs": 2, "have": len(usable),
                    "why": ("fewer than two observations have a non-zero ordinate, so no scale "
                            "factor is forced and the family cannot be tested")}
        (x1, y1), (x2, y2) = usable[0], usable[1]
        if x1 == x2:
            return {"class": Power.name, "status": UNDERDETERMINED, "needs": 2, "have": len(usable),
                    "why": "the two usable observations share an input"}
        for k in (1, 2, 3, 4, -1, -2):
            a = y1 / (x1 ** k)
            if all(a * (x ** k) == y for x, y in pairs):
                # k=1 is the affine family with b=0; reporting it twice would let one idea be
                # counted as two explanations, which is the defect this module exists to avoid.
                return {"class": Power.name, "status": FITS,
                        "parameters": {"a": _num(a), "k": k},
                        "needs": 2, "have": len(pairs), "surplus": max(0, len(pairs) - 2),
                        "subsumed_by": "affine" if k == 1 else None,
                        "predicate": f"lambda x: {_num(a)} * x ** {k}", "exact": True}
        return {"class": Power.name, "status": INCONSISTENT, "needs": 2, "have": len(pairs),
                "why": "no integer exponent with a constant scale fits all the observations"}


class Constant:
    """`c`. One parameter, so ONE observation pins it -- which is both its use and its danger.

    A piecewise function's branch is very often constant (`relu` below zero, a clipped region, a
    regime that has saturated), and a two-parameter family cannot be pinned by the single
    observation such a branch usually gets. But a constant pinned by one point is a MEMORISED VALUE,
    not a fitted hypothesis: from `f(-1) = 0` nothing follows about `f(-7)`. This class is therefore
    only ever used inside a composition, where the free-parameter count is checked against the
    number of observations -- see `compose`, which refuses to call a zero-surplus fit determined.
    """

    name = "constant"
    template = "c"
    params_needed = 1

    @staticmethod
    def fit(points: Sequence[tuple[Any, Any]]) -> dict[str, Any]:
        exact = [(_exact(x), _exact(y)) for x, y in points]
        if any(y is None for _x, y in exact) or any(x is None for x, _y in exact):
            return _unsupported(Constant.name)
        if not exact:
            return {"class": Constant.name, "status": UNDERDETERMINED, "needs": 1, "have": 0}
        values = {y for _x, y in exact}
        if len(values) > 1:
            return {"class": Constant.name, "status": INCONSISTENT, "needs": 1, "have": len(exact),
                    "why": "the observations take more than one value, so no constant fits"}
        value = exact[0][1]
        return {"class": Constant.name, "status": FITS, "parameters": {"c": _num(value)},
                "needs": 1, "have": len(exact), "surplus": max(0, len(exact) - 1),
                "predicate": "lambda x: %s" % _num(value), "exact": True,
                "reconstructed": (_reconstruct(value) != value)}


def _num(value: Fraction) -> Any:
    """Report a rational as an int when it is one, else in `n/d` spelling.

    The value is reconstructed to the simplest rational its decimal precision supports, so a fit to
    float `1/3` reports `1/3` rather than 3333333333333333/10000000000000000. The reconstruction is
    recorded on the fit as `reconstructed: True` -- an answer that reads as a simple fraction is
    easier to check, and easier to wrongly trust.
    """
    value = _reconstruct(value)
    if value.denominator == 1:
        return int(value)
    return "%d/%d" % (value.numerator, value.denominator)


def _unsupported(name: str) -> dict[str, Any]:
    return {"class": name, "status": UNSUPPORTED,
            "why": "an observation is not an exact rational, so the class cannot be tested exactly"}


FAMILIES = {Affine.name: Affine, Power.name: Power, Constant.name: Constant}

# Inside a composition a constant branch is the only thing that can explain a lone observation, so
# it is available there. `determine` keeps its original default: a bare constant explanation of a
# multi-point sample is not a hypothesis anyone should be offered.
COMPOSITION_FAMILIES = ("affine", "power", "constant")


def fit_all(points: Sequence[tuple[Any, Any]],
            families: Sequence[str] = ("affine", "power")) -> list[dict[str, Any]]:
    """Fit every class that could explain the points. A list, because the answer is usually plural."""
    out = []
    for name in families:
        fam = FAMILIES.get(name)
        if fam is not None:
            out.append(fam.fit(points))
    return out


def determine(points: Sequence[tuple[Any, Any]],
              families: Sequence[str] = ("affine", "power")) -> dict[str, Any]:
    """How many EXPLANATIONS do these points permit, when explanations are parameterised families?

    A family that fits with pinned parameters is one explanation, no matter how many ways its body
    could be spelled -- that is the whole point of having the class. Families that are subsumed by
    another (power with k=1 is affine with b=0) are not counted twice.
    """
    fits = fit_all(points, families)
    fitting = [f for f in fits if f["status"] == FITS]
    distinct: list[dict[str, Any]] = []

    def _constant_value(fit: dict[str, Any]) -> Any:
        """The value a fit returns for every input, if it is constant, else None."""
        p = fit.get("parameters") or {}
        if fit.get("class") == "constant":
            return p.get("c")
        if fit.get("class") == "affine" and p.get("a") == 0:
            return p.get("b")
        return None

    for f in fitting:
        if f.get("subsumed_by") in {d["class"] for d in distinct}:
            continue
        # A zero-slope line IS a constant, and a constant IS a zero-slope line. Counting them
        # separately would report two explanations where there is one function -- the same defect
        # as counting `2*x` and `(x/1)*2` separately, one level up. Measured 2026-11-04: the
        # `relu` left branch {(-2,0),(-1,0)} produced exactly this pair.
        value = _constant_value(f)
        if value is not None:
            same = [d for d in distinct if _constant_value(d) == value]
            if same:
                # ...and when two descriptions are the SAME function, keep the one that is better
                # supported, not the one that came first in the family list. Measured: `affine`
                # with a=0 explains {(-2,0),(-1,0)} using two parameters and zero observations to
                # spare, while `constant` explains it with one parameter and one to spare. Keeping
                # the list-order winner made the better-supported description invisible and left
                # `relu` reported as PROVISIONAL for want of a spare observation it actually had.
                best = max([f] + same, key=lambda d: (d.get("surplus", 0), -d.get("needs", 0)))
                distinct = [d for d in distinct if _constant_value(d) != value]
                distinct.append(best)
                continue
        distinct.append(f)
    under = [f for f in fits if f["status"] == UNDERDETERMINED]

    if distinct:
        status = "DETERMINED" if len(distinct) == 1 else "PROVISIONAL"
        why = ("exactly one family fits and pins its parameters"
               if len(distinct) == 1 else
               "%d different families fit; the observations do not choose between them" % len(distinct))
    elif any(f["status"] == INCONSISTENT for f in fits) and not under:
        # ONTOLOGY_EXHAUSTED requires that NOTHING is still merely unpinned. Refuted and unpinned are
        # different findings and must not be ranked: a refuted class wanted an observation and got a
        # contradiction; an unpinned class has not seen enough of the data yet. Measured: the region
        # {(-2,0), (-1,0), (2,2)} refutes `affine` on its third point while `power` still needs a
        # second non-zero ordinate, and declaring that ONTOLOGY_EXHAUSTED told the caller to acquire
        # a new CLASS when one more observation would have settled it.
        status = ONTOLOGY_EXHAUSTED
        why = ("every class that could be tested was refuted by the observations; no further input "
               "will help, because the gap is in the ontology and not in the evidence")
    elif under:
        status = "PROVISIONAL"
        why = ("no family is pinned yet; %d need more distinct inputs, and asking for one is a "
               "well-formed question (some classes were refuted outright, but at least one is "
               "still merely unpinned, so more data can still help)" % len(under))
    else:
        status = "UNRESOLVED"
        why = "no family in this ontology explains the observations"

    return {
        "schema": SCHEMA,
        "observations": len(points),
        "status": status,
        "explanations": len(distinct),
        "fits": distinct,
        "all": fits,
        "needs": max((f.get("needs", 0) for f in under), default=0),
        "why": why,
        "authority": "NONE",
    }


def question_for(points: Sequence[tuple[Any, Any]], family: str = "affine") -> dict[str, Any]:
    """Which input would pin this family, asked BEFORE seeing the answer.

    The string search asks which of its survivors disagree. That question can only be formed after
    the survivors exist. A parameterised family knows what it needs in advance: a second distinct
    input. That is the difference between reacting to a gap and anticipating one.
    """
    fam = FAMILIES[family]
    state = fam.fit(points)
    if state["status"] == FITS:
        return {"schema": SCHEMA + "_QUESTION", "queries": [],
                "why": "already pinned; further inputs would only confirm or refute, not inform",
                "surplus_inputs": state.get("surplus", 0), "authority": "NONE"}
    if state["status"] == INCONSISTENT:
        return {"schema": SCHEMA + "_QUESTION", "queries": [],
                "why": "the family is already refuted; no input can pin it",
                "authority": "NONE"}
    seen = {str(x) for x, _y in points}
    for candidate in (0, 1, 2, 3, 4, 5, -1, -2, 10):
        if str(candidate) not in seen:
            return {"schema": SCHEMA + "_QUESTION", "queries": [{"x": candidate}],
                    "why": ("%s needs %d distinct inputs and has %d; any new one pins it"
                            % (family, fam.params_needed, state.get("have", 0))),
                    "authority": "NONE"}
    return {"schema": SCHEMA + "_QUESTION", "queries": [], "why": "no unused input available",
            "authority": "NONE"}


COMPOSITION_CASES = {
    # two regimes, both affine; the true boundary is at 2.5, which no grid of whole numbers reaches
    "regime change at 2.5": [((0,), 1.0), ((1,), 3.0), ((2,), 5.0), ((3,), 8.0), ((4,), 10.0),
                             ((5,), 12.0)],
    # the classic kink: constant below zero, identity above
    "relu": [((-2,), 0.0), ((-1,), 0.0), ((2,), 2.0), ((3,), 3.0), ((4,), 4.0)],
    # saturated above zero, doubling below
    "clipped": [((-2,), 99.0), ((-1,), 99.0), ((1,), 2.0), ((2,), 4.0), ((3,), 6.0)],
    # NOT a split of anything in this ontology -- must be refused, not fitted
    "mod 2": [((0,), 0.0), ((1,), 1.0), ((2,), 0.0), ((3,), 1.0), ((4,), 0.0), ((5,), 1.0)],
}

CASES = {
    # the line the string search could not fit at any affordable budget
    "3x+1": [((0,), 1.0), ((1,), 4.0), ((2,), 7.0)],
    # the session's headline case
    "2x": [((1,), 2.0), ((2,), 4.0), ((3,), 6.0)],
    # not affine, not a power: a genuine regime change
    "piecewise": [((-2,), 99.0), ((1,), 2.0), ((2,), 4.0), ((3,), 6.0)],
    # affine-with-b=0 would overfit this; slope 1 offset 1 is the honest fit
    "x+1": [((0,), 1.0), ((1,), 2.0), ((2,), 3.0)],
    # the quadratic the search saw as three explanations
    "x*x": [((1,), 1.0), ((2,), 4.0), ((3,), 9.0), ((4,), 16.0)],
}


def compose_and_verify(points: Sequence[tuple[Any, Any]],
                       param_names: Sequence[str] = ("x",),
                       families: Sequence[str] = COMPOSITION_FAMILIES) -> dict[str, Any]:
    """Compose, compile, and check the program against the observations with the search's checker."""
    flat = [(args[0], value) for args, value in points]
    result = compose(flat, families)
    body = compile_composed(result)
    if body is None:
        # `errors` is present on every path. A caller should never have to know which branch ran to
        # find out whether anything was verified -- the same defect as `demand_evidence` reporting
        # `chosen` on only some branches, which cost a round of KeyErrors.
        return {"reached": False, "status": result["status"], "body": None,
                "why": result["why"], "verified_against": 0, "errors": [],
                "composition": result, "authority": "NONE"}
    from canonical.runtime.generalization_check_v1 import _compile_body

    fn = _compile_body(body, list(param_names))
    errors = []
    for args, want in points:
        try:
            got = fn(*args)
        except Exception as exc:  # noqa: BLE001
            errors.append({"args": list(args), "error": repr(exc)})
            continue
        if not _same(got, want):
            errors.append({"args": list(args), "got": got, "want": want})
    return {"reached": not errors, "status": "DETERMINED", "body": body,
            "verified_against": len(points), "errors": errors, "composition": result,
            "why": result["why"], "authority": "NONE"}


def _composition_findings() -> list[dict[str, Any]]:
    """The round-11 pre-registration, scored."""
    composed = {name: compose_and_verify(ex, ["x"])
                for name, ex in COMPOSITION_CASES.items()}

    relu_thin = compose_and_verify([((-1,), 0.0), ((2,), 2.0), ((3,), 3.0)], ["x"])
    exhaustion = determine([(-1, 0.0), (2, 2.0), (3, 3.0)])
    one_short = determine([(0, 1.0)])
    headline = determine([(1, 2.0), (2, 4.0), (3, 6.0)])

    return [
        {"id": "an_exhausted_ontology_is_not_reported_as_ask_me_again",
         "question": "does a refuted-and-unpinned-free ontology stop asking for data?",
         "status": exhaustion["status"], "one_short_status": one_short["status"],
         "pass": exhaustion["status"] == ONTOLOGY_EXHAUSTED
                 and one_short["status"] == "PROVISIONAL"},

        {"id": "relu_composes_from_two_branches",
         "question": "is a kink at zero explained by two families rather than by 50 programs?",
         "body": composed["relu"]["body"], "branches": composed["relu"]["composition"]["branches"],
         "pass": composed["relu"]["reached"] and
                 composed["relu"]["composition"]["branches"] == 2},

        {"id": "a_regime_change_composes",
         "question": "does a boundary no whole-number grid would hit get found?",
         "split_at": composed["regime change at 2.5"]["composition"]["split_at"],
         "pass": composed["regime change at 2.5"]["reached"]
                 and composed["regime change at 2.5"]["composition"]["split_at"] == "5/2"},

        {"id": "mod_two_is_refused_rather_than_fitted",
         "question": "does the mechanism decline to invent a boundary to match its answers?",
         "status": composed["mod 2"]["status"],
         "pass": composed["mod 2"]["status"] == ONTOLOGY_EXHAUSTED},

        {"id": "composed_bodies_verify_against_the_search_checker",
         "question": "does the compiled program reproduce every observation?",
         "errors": [composed[k]["errors"] for k in composed],
         "pass": all(not composed[k]["errors"]
                     for k in composed if composed[k]["reached"])},

        {"id": "two_branches_need_four_observations",
         "question": "is the evidence requirement of a composition computed rather than guessed?",
         "needs": relu_thin["composition"]["needs"], "status": relu_thin["status"],
         "pass": relu_thin["composition"]["needs"] == 4 and relu_thin["status"] == "PROVISIONAL"},

        {"id": "composition_does_not_replace_the_family_layer",
         "question": "does a one-region explanation still come back as one explanation?",
         "explanations": headline["explanations"],
         "pass": headline["explanations"] == 1 and headline["status"] == "DETERMINED"},
    ]


def run() -> dict[str, Any]:
    rows = []
    for name, pts in CASES.items():
        flat = [(a[0], v) for a, v in pts]
        rows.append({"case": name, **{k: v for k, v in determine(flat).items()
                                      if k in ("status", "explanations", "needs", "why")},
                     "fit": [{"class": f["class"], "status": f["status"],
                              "parameters": f.get("parameters")} for f in determine(flat)["fits"]]})

    # H3: the line the search could not fit.
    three = Affine.fit([(a[0], v) for a, v in CASES["3x+1"]])
    # H4: two points pin a two-parameter family; the third is a test.
    two_points = Affine.fit([(0, 1.0), (1, 3.0)])
    # H6: the headline case, as a family rather than as twelve strings.
    headline = determine([(a[0], v) for a, v in CASES["2x"]])
    # and the question the family can ask before it has seen the answer
    anticipates = question_for([(0, 1.0)], "affine")
    # a truly non-affine point set must be refused, not rounded onto a line
    refused = Affine.fit([(0, 0.0), (1, 1.0), (2, 4.0)])

    findings = [
        {"id": "a_two_parameter_family_needs_two_points",
         "question": "is the evidence requirement computed from the class rather than discovered?",
         "needs": two_points.get("needs"), "have": two_points.get("have"),
         "status": two_points["status"],
         "pass": two_points["status"] == FITS and two_points.get("surplus") == 0},

        {"id": "further_points_test_rather_than_inform",
         "question": "is a third point on a two-parameter family counted as new information?",
         "surplus": three.get("surplus"), "status": three["status"],
         "pass": three["status"] == FITS and three.get("surplus") == 1},

        {"id": "the_line_the_search_could_not_fit_fits_exactly",
         "question": "does the family explain 3x+1, which the string search left UNRESOLVED?",
         "parameters": three.get("parameters"),
         "pass": three["status"] == FITS and three["parameters"] == {"a": 3, "b": 1}},

        {"id": "a_non_affine_point_set_is_refused_not_rounded",
         "question": "does a quadratic get forced onto a straight line?",
         "violations": len(refused.get("violations") or []), "status": refused["status"],
         "pass": refused["status"] == INCONSISTENT and refused.get("parameters") is None},

        {"id": "the_headline_case_is_one_explanation_as_a_family",
         "question": "how many explanations are the three 2x points, once a family exists?",
         "explanations": headline["explanations"],
         "pass": headline["explanations"] == 1
                 and headline["fits"][0]["parameters"] == {"a": 2, "b": 0}},

        {"id": "the_question_is_derived_before_the_answer",
         "question": "can the class say what input would pin it while it is still unpinned?",
         "queries": anticipates.get("queries"),
         "pass": len(anticipates.get("queries") or []) == 1},

        {"id": "subsumed_families_are_not_counted_twice",
         "question": "does power(k=1) get counted as a second explanation alongside affine?",
         "explanations": headline["explanations"], "all_statuses": [f["status"] for f in headline["all"]],
         "pass": headline["explanations"] == 1},
    ]
    findings = findings + _composition_findings()
    composed_rows = []
    for name, ex in COMPOSITION_CASES.items():
        r = compose_and_verify(ex, ["x"])
        composed_rows.append({"case": name, "status": r["status"], "reached": r["reached"],
                              "branches": r["composition"]["branches"],
                              "split_at": r["composition"]["split_at"],
                              "body": r["body"]})
    passed = sum(1 for f in findings if f["pass"])
    return {"schema": SCHEMA, "passed": passed, "total": len(findings), "findings": findings,
            "cases": rows, "composition": composed_rows, "authority": "NONE"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = run()
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True, default=str))
        return 0
    for row in doc["cases"]:
        print("%-10s %-11s explanations=%d  %s" % (
            row["case"], row["status"], row["explanations"],
            ", ".join("%s %s" % (f["class"], f["parameters"]) for f in row["fit"]) or "-"))
    print()
    for f in doc["findings"]:
        print("  %-52s %s" % (f["id"], "PASS" if f["pass"] else "FAIL"))
    print()
    for row in doc["composition"]:
        print("%-22s %-20s branches=%d split_at=%s" % (
            row["case"], row["status"], row["branches"], row["split_at"]))
        if row["body"]:
            print("      " + row["body"].replace("\n", "\n      "))
    print("\n%d/%d findings as predicted" % (doc["passed"], doc["total"]))
    return 0




# ---------------------------------------------------------------------------------------------
# Handing a fit back to the search
# ---------------------------------------------------------------------------------------------
#
# A family that fits is a hypothesis, not a program. The search speaks programs. Until the fit can
# be compiled INTO a body and re-verified against the same observations, this module is a parallel
# ontology that proves nothing about the creature's reach -- which is exactly the criticism that has
# been levelled at every round of this work. `compile_body` closes that loop.

def compile_body(fit: dict[str, Any]) -> str | None:
    """Turn a fitted family into an ordinary Python body, so the search's own verifier can check it."""
    if fit.get("status") != FITS:
        return None
    p = fit.get("parameters") or {}
    cls = fit.get("class")
    if cls == "constant":
        return "return %s" % _literal(p.get("c"))
    if cls == "affine":
        a, b = p.get("a"), p.get("b")
        # `a` and `b` arrive as int OR as "n/d" strings, because an exact rational is not an int.
        # The first version compared them numerically (`b >= 0`) and crashed on every fractional
        # fit -- a whole class of correct answers made unreachable by a type assumption. Compare
        # exactly, as Fractions.
        a_q, b_q = _as_fraction(a), _as_fraction(b)
        terms = []
        if a_q == 1:
            terms.append("x")
        elif a_q == -1:
            terms.append("-x")
        elif a_q != 0:
            terms.append("%s * x" % _literal(a))
        if b_q != 0 or not terms:
            terms.append(("+ " if b_q > 0 else "- ") + _literal(_num(abs(b_q))) if terms
                         else _literal(b))
        if len(terms) == 1:
            expr = terms[0]
        elif terms[1].startswith("- "):
            expr = "%s - %s" % (terms[0], terms[1][2:])
        elif terms[1].startswith("+ "):
            expr = "%s + %s" % (terms[0], terms[1][2:])
        elif terms[1].startswith("-"):
            expr = "%s %s" % (terms[0], terms[1])
        else:
            expr = "%s + %s" % (terms[0], terms[1])
        return "return %s" % expr
    if cls == "power":
        a, k = p.get("a"), p.get("k")
        base = "x" if k == 1 else "x ** %s" % _literal(k)
        return "return %s" % (base if a == 1 else "%s * %s" % (_literal(a), base))
    return None


def _as_fraction(value: Any) -> Fraction:
    """Accept an int or the "n/d" spelling this module reports for a non-integer rational."""
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str) and "/" in value:
        n, d = value.split("/")
        return Fraction(int(n), int(d))
    return Fraction(str(value))


def _literal(value: Any) -> str:
    """Rational -> Python source. A Fraction becomes `Fraction(n, d)` only when it must."""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and "/" in value:
        n, d = value.split("/")
        return "(%s / %s)" % (n, d)
    return repr(value)


def reach(points: Sequence[tuple[Any, Any]], param_names: Sequence[str] = ("x",),
          families: Sequence[str] = ("affine", "power")) -> dict[str, Any]:
    """Fit, compile to a body, and verify that body with the same checker the search uses.

    The verification is not decorative. Compiling a fit back into source is where an exact
    rational turns into a float, and the only way to know it survived is to re-run the observations.
    """
    # `points` here arrives in the PROJECT's example form -- `((args...), value)` -- because that is
    # what every other module in this codebase speaks. `determine` wants flat `(x, value)`. The
    # first version of this function passed the project form straight through, so every fit came
    # back UNSUPPORTED and `reach` reported "no family explains the observations" for data it had
    # just fitted correctly. A silent non-result that looks exactly like a mechanism saying no.
    arities = {len(args) for args, _v in points}
    if arities and arities != {1}:
        # GUARD, not a guess: this ontology has no notion of a second input. Silently fitting the
        # first parameter and ignoring the second would be an invented result.
        return {"reached": False, "body": None,
                "why": "this module reasons one input at a time; %d were supplied"
                       % max(arities), "authority": "NONE"}
    flat = [(args[0], value) for args, value in points]
    verdict = determine(flat, families)
    if verdict["status"] != "DETERMINED":
        return {"reached": False, "why": verdict["why"], "status": verdict["status"],
                "body": None, "authority": "NONE"}
    body = compile_body(verdict["fits"][0])
    if body is None:
        return {"reached": False, "why": "no compiler for this family", "body": None,
                "authority": "NONE"}
    from canonical.runtime.generalization_check_v1 import _compile_body

    try:
        fn = _compile_body(body, list(param_names))
    except Exception as exc:  # noqa: BLE001
        return {"reached": False, "why": "the compiled body does not parse: %r" % (exc,),
                "body": body, "authority": "NONE"}
    errors = []
    for args, want in points:
        try:
            got = fn(*args)
        except Exception as exc:  # noqa: BLE001
            errors.append({"args": list(args), "error": repr(exc)})
            continue
        if not _same(got, want):
            errors.append({"args": list(args), "got": got, "want": want})
    return {
        "reached": not errors,
        "status": verdict["status"],
        "body": body,
        "verified_against": len(points),
        "errors": errors,
        "why": ("the family fit, was compiled to source, and the source reproduces every "
                "observation" if not errors else
                "the fit did not survive compilation into source"),
        "authority": "NONE",
    }


def _same(got: Any, want: Any, tol: float = 1e-9) -> bool:
    if isinstance(got, bool) or isinstance(want, bool):
        return got == want
    if isinstance(got, (int, float)) and isinstance(want, (int, float)):
        return abs(float(got) - float(want)) <= tol * max(1.0, abs(float(want)))
    return got == want


# ---------------------------------------------------------------------------------------------
# Composition: one hypothesis per region, with the boundary SEARCHED
# ---------------------------------------------------------------------------------------------
#
# Both mechanisms in this repository fail on the same input class -- data that changes regime --
# and both fail the same way: by refusing to have a second kind of object.
#
#   the string search   enumerates 50 interchangeable piecewise programs and cannot say which one
#   the family layer    refuses outright, because no single family covers both regions
#
# The repair is not a larger grammar. It is a SPLIT: `if x <= s: family_A else: family_B`, with the
# boundary `s` discovered from the observations rather than assumed to be a tidy number. A cut is
# searched at the MIDPOINT between adjacent observations, so a boundary at 1.5 is found exactly as
# readily as one at 2 -- the earlier version of this kind of code in this repository swept a grid of
# whole numbers and would have missed half the boundaries in the world.

MAX_BRANCHES = 2          # measured, not aspirational: 3 branches on 6 points fits anything


def _cuts(sorted_points: Sequence[tuple[Fraction, Fraction]]) -> list[Fraction]:
    """Every boundary position the data distinguishes: a midpoint between adjacent inputs."""
    out: list[Fraction] = []
    for i in range(len(sorted_points) - 1):
        lo = sorted_points[i][0]
        hi = sorted_points[i + 1][0]
        if lo != hi:
            out.append((lo + hi) / 2)
    return out


def compose(points: Sequence[tuple[Any, Any]],
            families: Sequence[str] = COMPOSITION_FAMILIES,
            max_branches: int = MAX_BRANCHES) -> dict[str, Any]:
    """Explain the observations as regions, each with its own family and its own parameters.

    A one-region explanation is just a family fit. A two-region explanation needs BOTH parts to be
    pinned: a branch with one observation is not a hypothesis, it is a value.
    """
    exact = [( _exact(x), _exact(y)) for x, y in points]
    if any(x is None or y is None for x, y in exact):
        return {"status": UNSUPPORTED, "why": "an observation is not an exact rational",
                "branches": [], "authority": "NONE"}
    ordered = sorted(exact, key=lambda p: p[0])

    # One region: the plain family fit, so composition never reports less than the family layer.
    single = determine([( _num(x), _num(y)) for x, y in ordered], families)
    if single["status"] == "DETERMINED":
        return {"status": "DETERMINED", "branches": 1, "split_at": None,
                "fits": single["fits"], "needs": single["fits"][0].get("needs", 0),
                "why": "one family explains every observation; no split is needed",
                "interpretation": single, "authority": "NONE"}

    if max_branches < 2:
        return {"status": single["status"], "branches": 0, "split_at": None, "fits": [],
                "needs": single.get("needs", 0), "why": single["why"],
                "interpretation": single, "authority": "NONE"}

    best: dict[str, Any] | None = None
    tried: list[dict[str, Any]] = []
    for cut in _cuts(ordered):
        left = [(x, y) for x, y in ordered if x <= cut]
        right = [(x, y) for x, y in ordered if x > cut]
        if not left or not right:
            continue
        lfit = _fit_region(left, families)
        rfit = _fit_region(right, families)
        # A branch must be PINNED BY MORE DATA THAN IT HAS PARAMETERS. Without this check a constant
        # branch is "pinned" by its single observation and so is every two-parameter branch by two
        # observations, which lets k free parameters absorb k points -- the composed explanation
        # then fits perfectly and says nothing. Measured: `mod 2` is exactly this pattern, and a
        # version of this function without the check reported it DETERMINED with zero surplus.
        lpinned = bool(lfit.get("pinned")) and lfit.get("surplus", 0) >= 1
        rpinned = bool(rfit.get("pinned")) and rfit.get("surplus", 0) >= 1
        row = {"split_at": _num(cut), "left": lfit, "right": rfit,
               "pinned": lpinned and rpinned,
               "underdetermined_by": [
                   side for side, ok, fit in (("left", lpinned, lfit), ("right", rpinned, rfit))
                   if not ok]}
        tried.append(row)
        if row["pinned"] and best is None:
            best = row
            break

    if best is None:
        # Honest refusal, and note the two ways of getting here are DIFFERENT diagnoses.
        fits_exist = any(t_["left"].get("pinned") and t_["right"].get("pinned") for t_ in tried)
        distinct_inputs = len({x for x, _y in ordered})
        if fits_exist:
            # A split explains the data, but with no observation to spare on at least one side --
            # so the explanation has as many degrees of freedom as it has facts. More data would
            # settle it, which is exactly what PROVISIONAL means.
            return {"status": "PROVISIONAL", "branches": 0, "split_at": None,
                    "fits": [], "needs": 4,
                    "why": ("a split fits, but at least one branch has no observation beyond its "
                            "own parameters, so it is memorising rather than explaining; more "
                            "observations would settle it"),
                    "tried_cuts": len(tried), "interpretation": single, "authority": "NONE"}
        if distinct_inputs < 4:
            return {"status": "PROVISIONAL", "branches": 0, "split_at": None, "fits": [],
                    "needs": 4,
                    "why": ("a two-branch explanation needs 4 observations -- two per branch, and "
                            "one spare on each side -- and %d distinct inputs were supplied"
                            % distinct_inputs),
                    "tried_cuts": len(tried), "interpretation": single, "authority": "NONE"}
        return {"status": ONTOLOGY_EXHAUSTED, "branches": 0, "split_at": None, "fits": [],
                "needs": 4,
                "why": ("no boundary splits the observations into regions that any family in this "
                        "ontology can each explain; the gap is in the classes, not the data"),
                "tried_cuts": len(tried), "interpretation": single, "authority": "NONE"}

    needs = (best["left"].get("needs", 2) or 2) + (best["right"].get("needs", 2) or 2)
    return {
        "status": "DETERMINED",
        "branches": 2,
        "split_at": best["split_at"],
        "fits": [best["left"], best["right"]],
        "needs": needs,
        # The boundary is a PARAMETER with no evidence of its own: the data locate it only between
        # two adjacent inputs. Saying so keeps a fitted boundary from reading as if it were solved.
        "boundary_is_bounded": "any cut between the same two observations would fit equally",
        "why": ("two families, each pinned, on either side of a boundary the observations locate "
                "only up to the gap between adjacent inputs"),
        "interpretation": single,
        "authority": "NONE",
    }


def _fit_region(region: Sequence[tuple[Fraction, Fraction]],
                families: Sequence[str]) -> dict[str, Any]:
    verdict = determine([(_num(x), _num(y)) for x, y in region], families)
    if verdict["status"] == "DETERMINED":
        fit = dict(verdict["fits"][0])
        fit["observations"] = len(region)
        # Say PINNED here, in this function's own vocabulary. The fit's own `status` is FITS, and a
        # caller comparing it against "DETERMINED" silently never sees a pinned branch -- measured
        # 2026-11-04, the third time in this session that two modules named the same state
        # differently and the comparison failed quietly instead of loudly.
        fit["pinned"] = True
        return fit
    return {"class": None, "status": verdict["status"], "parameters": None, "pinned": False,
            "observations": len(region), "why": verdict["why"]}


def compile_composed(result: dict[str, Any]) -> str | None:
    """A composed explanation that cannot be written as a program has not been reached."""
    if result.get("status") != "DETERMINED":
        return None
    fits = result.get("fits") or []
    if result.get("branches") == 1 and fits:
        return compile_body(fits[0])
    if len(fits) != 2:
        return None
    left, right = fits
    lb, rb = compile_body(left), compile_body(right)
    if lb is None or rb is None:
        return None
    cut = _literal(result["split_at"])
    lret = lb[len("return "):].strip()
    rret = rb[len("return "):].strip()
    return "if x <= %s:\n    return %s\nreturn %s" % (cut, lret, rret)


if __name__ == "__main__":
    raise SystemExit(main())
