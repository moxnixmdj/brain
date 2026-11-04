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
        (x1, y1), (x2, y2) = pairs[0], pairs[1]
        if x1 == x2 or y1 == 0 or y2 == 0:
            return {"class": Power.name, "status": UNDERDETERMINED, "needs": 2, "have": len(pairs),
                    "why": "a zero ordinate cannot pin a scale factor"}
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


FAMILIES = {Affine.name: Affine, Power.name: Power}


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
    for f in fitting:
        if f.get("subsumed_by") in {d["class"] for d in distinct}:
            continue
        distinct.append(f)
    under = [f for f in fits if f["status"] == UNDERDETERMINED]

    if distinct:
        status = "DETERMINED" if len(distinct) == 1 else "PROVISIONAL"
        why = ("exactly one family fits and pins its parameters"
               if len(distinct) == 1 else
               "%d different families fit; the observations do not choose between them" % len(distinct))
    elif under:
        status = "PROVISIONAL"
        why = ("no family is pinned yet; %d need more distinct inputs, and asking for one is a "
               "well-formed question" % len(under))
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
    passed = sum(1 for f in findings if f["pass"])
    return {"schema": SCHEMA, "passed": passed, "total": len(findings), "findings": findings,
            "cases": rows, "authority": "NONE"}


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
    print("\n%d/%d findings as predicted" % (doc["passed"], doc["total"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


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
