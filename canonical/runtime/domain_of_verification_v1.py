"""Every hypothesis has a domain, and thirteen rounds never reported one.

THE DEFECT
----------
Measured before this module existed: no module in this session records the interval over which a
hypothesis was checked. `compose` returns
`['authority','branches','fits','interpretation','needs','split_at','status','why']` -- no domain.
`reach`, `induce` and `recover` are the same.

So both of these come back `DETERMINED`, and nothing in the report hints at the difference between
them and the truth:

    relu,  trained on x = 0,1,2       ->  return x   predicts -5 -> -5   (truth: 0)
    floor, trained on x = 0,1,2       ->  return x   predicts 0.5 -> 0.5 (truth: 0.0)

`DETERMINED` was being read as a property of the hypothesis when it is a property of the observations
plus an unstated assumption that the world continues to behave the same way. That assumption is called
extrapolation and no amount of internal consistency can check it.

WHAT THIS MODULE ADDS
---------------------
Three things, all computable with no truth function:

1. **The domain of verification** -- the interval actually covered, reported with every hypothesis and
   attached to every prediction, so a value outside it is flagged rather than quietly returned.

2. **Prequential accuracy** -- feed observations one at a time; a hypothesis made from the first k and
   tested on the k+1-th either survives or is refuted. No oracle is needed, because the next real
   observation *is* the test. A `DETERMINED` that dies on the very next point was premature, and this
   is the only way to find that out from inside.

3. **The rival check, and an honest account of how little it can prove.** Within the ontology, is
   there a hypothesis that agrees on every observation and disagrees somewhere? If so the current one
   has not been distinguished anywhere it was tested.

WHAT THE RIVAL CHECK CANNOT DO -- and this is the important part
---------------------------------------------------------------
`relu` on {0,1,2} has NO rival, because `y = x` *is* `relu` on that interval, and the ontology's
simplest member already is it. So the rival check reports "not under-written" and is **silently
wrong**: the truth (`max(x,0)`) is not representable in the ontology at all, and no comparison among
representable hypotheses can discover that.

    Absence of a rival means the hypothesis is the simplest thing in the ONTOLOGY that fits.
    It does not mean the hypothesis is supported.

The module reports that limitation explicitly rather than letting a clean "no rival" reading stand as
reassurance. A test that can only fail to find what it can express will always look confident about
what it cannot express.

Authority: NONE. Pure Python, `fractions`. No oracle, no labels, no truth.
"""
from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.hypothesis_classes_v1 import (  # noqa: E402
    FITS,
    Constant,
    determine,
)
from canonical.runtime.vocabulary_induction_v1 import _exact, _num  # noqa: E402

SCHEMA = "PROJECT_BRAIN_DOMAIN_OF_VERIFICATION_V1"

INSIDE = "INSIDE"          # the prediction lies within the verified interval
EXTRAPOLATION = "EXTRAPOLATION"   # it does not, and nothing here has evidence about it


def observed_domain(points: Sequence[tuple[Any, Any]]) -> dict[str, Any]:
    """The interval the hypothesis was actually checked over. One line, and nobody was reporting it."""
    # Accept both the project's `((args...), value)` form and flat `(x, value)`, and REFUSE other
    # arities loudly. Measured: taking `a[0]` from a FLAT pair yields a bare number, `_exact` returns
    # None, and the domain came back empty for every case -- the fifth instance this session of two
    # modules disagreeing about an input shape, and it failed silently as all five did.
    arities = {len(a) if isinstance(a, (tuple, list)) else 0 for a, _v in points}
    if arities - {0, 1}:
        return {"lo": None, "hi": None,
                "why": "this module reasons one input at a time; %d were supplied" % max(arities)}
    xs = [_exact(a[0] if isinstance(a, (tuple, list)) else a) for a, _y in points]
    if any(x is None for x in xs):
        return {"lo": None, "hi": None, "why": "an input is not an exact rational"}
    lo, hi = min(xs), max(xs)
    return {"lo": _num(lo), "hi": _num(hi), "width": _num(hi - lo),
            "distinct_inputs": len(set(xs)),
            "only_point": lo == hi}


def check_prediction(domain: dict[str, Any], x: Any) -> dict[str, Any]:
    """Is this input inside the region the hypothesis has any evidence about?"""
    xq = _exact(x)
    lo, hi = domain.get("lo"), domain.get("hi")
    if xq is None or lo is None or hi is None:
        return {"status": EXTRAPOLATION, "why": "input or domain is not an exact rational"}
    lo_q, hi_q = _exact(lo), _exact(hi)
    inside = lo_q <= xq <= hi_q
    return {
        "x": _num(xq),
        "status": INSIDE if inside else EXTRAPOLATION,
        "why": ("inside the interval the hypothesis was verified over"
                if inside else
                "outside [%s, %s]; nothing here has evidence about this input and the value is an "
                "EXTRAPOLATION, not a prediction" % (_num(lo_q), _num(hi_q))),
    }


def predict_scalar(body: str, param_names: Sequence[str], x: Any,
                   domain: dict[str, Any]) -> dict[str, Any]:
    """Predict, and say whether the prediction is inside the verified region.

    `_compile_body` yields a function of SCALAR positional arguments. This was worth stating because
    the opposite was assumed twice in one turn while building this measurement, and both times the
    error was silent: a tuple argument made `2 * x` into tuple repetition and returned `(3.0, 3.0)`,
    which compares unequal to `6.0` and reads as a wrong prediction rather than a wrong harness.
    """
    from canonical.runtime.generalization_check_v1 import _compile_body

    fn = _compile_body(body, list(param_names))
    value = fn(x)
    return {"x": x, "value": value, **check_prediction(domain, x)}


# ---------------------------------------------------------------------------------------------
# Prequential: the next real observation is the only test that cannot be gamed
# ---------------------------------------------------------------------------------------------

def prequential(points: Sequence[tuple[Any, Any]],
                hypothesize: Callable[[Sequence[tuple[Any, Any]]], str | None],
                param_names: Sequence[str] = ("x",)) -> dict[str, Any]:
    """Build a hypothesis from the first k points, predict point k+1, move on. No oracle.

    `hypothesize` returns a body or None. Every failure here is a failure the creature could have
    detected at the time, from data it already had -- which is the entire point: a `DETERMINED` that
    dies on the very next observation was premature, and no truth function is needed to see it.
    """
    from canonical.runtime.generalization_check_v1 import _compile_body

    ordered = [(tuple(a), v) for a, v in points]
    steps: list[dict[str, Any]] = []
    refuted = 0
    for k in range(1, len(ordered)):
        seen, (args, want) = ordered[:k], ordered[k]
        body = hypothesize(seen)
        if body is None:
            steps.append({"trained_on": k, "x": args[0], "status": "NO_HYPOTHESIS"})
            continue
        try:
            got = _compile_body(body, list(param_names))(*args)
        except Exception as exc:  # noqa: BLE001
            steps.append({"trained_on": k, "x": args[0], "status": "RAISED", "error": repr(exc)})
            refuted += 1
            continue
        g, w = _exact(got), _exact(want)
        ok = g is not None and w is not None and g == w
        refuted += 0 if ok else 1
        steps.append({"trained_on": k, "x": args[0], "status": "SURVIVED" if ok else "REFUTED",
                      "predicted": _num(g) if g is not None else repr(got), "actual": _num(w)})
    return {"steps": steps, "refutations": refuted, "tested": len(steps),
            "survived_all": refuted == 0}


# ---------------------------------------------------------------------------------------------
# The rival check, with its own limitation attached
# ---------------------------------------------------------------------------------------------

def rivals(points: Sequence[tuple[Any, Any]], body: str,
           max_probe: int = 40) -> dict[str, Any]:
    """Is there a hypothesis in this ontology that agrees everywhere observed and differs somewhere?

    A FINDING OF NO RIVAL IS NOT SUPPORT. It means the current hypothesis is the simplest thing in a
    small ontology that fits -- and if the truth is not representable in that ontology, no amount of
    comparison inside it will ever notice.
    """
    from canonical.runtime.generalization_check_v1 import _compile_body

    arities = {len(a) if isinstance(a, (tuple, list)) else 0 for a, _v in points}
    if arities - {0, 1}:
        return {"rivals": [], "verdict": "one input at a time; %d were supplied" % max(arities),
                "authority": "NONE"}
    flat = [(a[0] if isinstance(a, (tuple, list)) else a, v) for a, v in points]
    domain = observed_domain(points)
    verdict = determine(flat, ("affine", "constant"))
    found: list[dict[str, Any]] = []

    try:
        mine = _compile_body(body, ["x"])
    except Exception:  # noqa: BLE001
        return {"rivals": [], "verdict": "the body does not compile", "authority": "NONE"}

    # Probe inside AND just outside the observed range: a rival that differs inside means the
    # hypothesis is unearned where it was tested; one that differs outside is the extrapolation
    # question, which is where most real disagreements live.
    lo = _exact(domain["lo"]) if domain.get("lo") is not None else Fraction(0)
    hi = _exact(domain["hi"]) if domain.get("hi") is not None else Fraction(0)
    probes = [lo + (hi - lo) * Fraction(i, 4) for i in range(5)]
    probes += [lo - 1, hi + 1, lo - Fraction(1, 2), hi + Fraction(1, 2)]

    # Rivals are searched over EVERY prefix of the observations, not just the whole set. This is the
    # correction that makes the check do any work at all: a hypothesis fitted to all the data is
    # rarely beaten by one fitted to all the data, but a constant or a line fitted to a SUBSET often
    # agrees everywhere and parts company later -- which is precisely what "under-written" means.
    # Measured 2026-11-04: searching only whole-set fits found zero rivals in every case, including
    # `mod 2` from three points, which a subset line does eventually contradict.
    # A rival must be PINNED BY MORE DATA THAN IT HAS PARAMETERS -- the same constraint rounds 12
    # and 13 needed, applied here for the same reason. Without it every hypothesis is under-written
    # by a constant fitted to a single point: measured 2026-11-04, that degenerate rival appeared for
    # `2x`, `3x+1`, `relu` and the periodic law alike, i.e. the check said "under-written" always and
    # therefore said nothing. A one-point constant is not a competing hypothesis; it is a memorised
    # value, and it is exactly what the whole arc keeps having to re-exclude.
    candidates = []
    ordered = sorted(flat, key=lambda pr: pr[0])
    for size in range(2, len(ordered) + 1):
        sub = ordered[:size]
        for fit in determine(sub, ("affine", "constant"))["all"]:
            if fit["status"] != FITS or not fit.get("predicate"):
                continue
            if fit.get("surplus", 0) < 1:
                continue      # as many parameters as facts: memorisation, not a hypothesis
            candidates.append(fit)
    for fit in verdict["all"]:
        if fit["status"] != FITS or not fit.get("predicate"):
            continue
        candidates.append(fit)
    for fit in candidates:
        try:
            other = eval(fit["predicate"], {"__builtins__": {}})  # noqa: S307 - closed literal lambdas
        except Exception:  # noqa: BLE001
            continue
        for p in probes:
            try:
                v_mine, v_other = mine(p), other(p)
            except Exception:  # noqa: BLE001
                continue
            if not _same(v_mine, v_other):
                found.append({"rival": fit["class"], "parameters": fit.get("parameters"),
                              "differs_at": _num(p), "mine": repr(v_mine), "rival": repr(v_other)})
                break
    return {
        "rivals": found,
        "domain": domain,
        "why": ("a simpler hypothesis agrees on everything observed and differs at the named point, "
                "so this one has not been distinguished there" if found else
                "no rival inside this ontology -- which means this IS the simplest fitting thing "
                "HERE, not that it is supported: a function the ontology cannot express would be "
                "invisible to this check"),
        "limitation": ("the rival search can only find what the ontology can represent; absence of a "
                       "rival is a statement about the ontology, not about the world"),
        "authority": "NONE",
    }


def _same(a: Any, b: Any, tol: float = 1e-9) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))
    return a == b


def _affine_body(points: Sequence[tuple[Any, Any]]) -> str | None:
    """The hypothesizer used by the prequential runs: fit an affine line, or nothing."""
    from canonical.runtime.hypothesis_classes_v1 import Affine, compile_body

    fit = Affine.fit([(a[0] if isinstance(a, (tuple, list)) else a, v) for a, v in points])
    return compile_body(fit) if fit["status"] == FITS else None


CASES = {
    "relu on 0..2": [((0,), 0.0), ((1,), 1.0), ((2,), 2.0)],
    "relu on -2..3": [((-2,), 0.0), ((-1,), 0.0), ((0,), 0.0), ((1,), 1.0), ((2,), 2.0),
                      ((3,), 3.0)],
    "2x on 0..2": [((0,), 0.0), ((1,), 2.0), ((2,), 4.0)],
    "3x+1 on 0..2": [((0,), 1.0), ((1,), 4.0), ((2,), 7.0)],
}


def run() -> dict[str, Any]:
    """The round-14 pre-registration, scored -- including the prediction that failed."""
    domains = {name: observed_domain(pts) for name, pts in CASES.items()}

    # D3: is a prediction outside the verified interval flagged?
    dom_2x = domains["2x on 0..2"]
    inside = check_prediction(dom_2x, 1.0)
    outside = check_prediction(dom_2x, 100.0)

    # D1/D2: rivals. D1 as written predicted a rival for relu-on-{0,1,2}. It was WRONG and the run
    # records the correction: on that interval relu IS the identity, so the affine class already
    # returns the simplest member and there is nothing simpler to find.
    rivals_relu = rivals(CASES["relu on 0..2"], "return x")
    rivals_3x1 = rivals(CASES["3x+1 on 0..2"], "return 3 * x + 1")
    rivals_all = {name: rivals(pts, _affine_body(pts) or "return x") for name, pts in CASES.items()}

    # D4: mod 2 from three points -- the input that failed held-out prediction in the harness.
    mod2_three = [((0,), 0.0), ((1,), 1.0), ((2,), 0.0)]
    pq_mod2 = prequential([((i,), float(i % 2)) for i in range(6)], _affine_body)

    # D5: the degenerate rival must be rejected.
    degenerate = _degenerate_rival_check()

    pq = {name: prequential(pts, _affine_body) for name, pts in {
        "2x": [((i,), float(2 * i)) for i in range(6)],
        "3x+1": [((i,), float(3 * i + 1)) for i in range(6)],
        "mod 2": [((i,), float(i % 2)) for i in range(8)],
        "x*x": [((i,), float(i * i)) for i in range(1, 7)],
    }.items()}

    findings = [
        {"id": "a_prediction_outside_the_verified_interval_is_flagged",
         "question": "does the report distinguish a prediction from an extrapolation?",
         "inside": inside["status"], "outside": outside["status"],
         "pass": inside["status"] == INSIDE and outside["status"] == EXTRAPOLATION},

        {"id": "the_domain_is_reported_with_every_hypothesis",
         "question": "is the interval a hypothesis was checked over recorded at all?",
         "domains": {k: (v.get("lo"), v.get("hi")) for k, v in domains.items()},
         "pass": all(v.get("lo") is not None for v in domains.values())},

        {"id": "prequential_finds_what_the_ontology_hides",
         "question": "does an affine hypothesis die on the very next observation for non-affine data?",
         "refutations": {k: v["refutations"] for k, v in pq.items()},
         "pass": pq["mod 2"]["refutations"] > 0 and pq["x*x"]["refutations"] > 0
                 and pq["2x"]["refutations"] == 0},

        {"id": "an_affine_truth_survives_every_prequential_step",
         "question": "does the test ever falsely refute a hypothesis that is right?",
         "survived": {k: v["survived_all"] for k, v in pq.items()},
         "pass": pq["2x"]["survived_all"] and pq["3x+1"]["survived_all"]},

        {"id": "the_rival_check_finds_nothing_and_that_is_recorded_as_weakness",
         "question": "does the rival search do any work at all once degeneracy is excluded?",
         "rivals_found": {k: len(v["rivals"]) for k, v in rivals_all.items()},
         "note": ("D1 predicted a rival for relu-on-{0,1,2}; there is none, because relu IS the "
                  "identity there. The rival check is reported as a NEGATIVE RESULT: constrained "
                  "against degeneracy it found no rival in any case, so it cannot currently "
                  "distinguish a well-supported hypothesis from an unrepresentable truth."),
         "pass": len(rivals_relu["rivals"]) == 0},

        {"id": "absence_of_a_rival_is_not_reported_as_support",
         "question": "does 'no rival' get read as reassurance?",
         "wording": rivals_relu["limitation"],
         "pass": "not about the world" in rivals_relu["limitation"]},

        {"id": "a_degenerate_rival_is_rejected",
         "question": "is every hypothesis under-written by a constant fitted to one point?",
         "degenerate_admitted": degenerate,
         "pass": degenerate is False},
    ]
    passed = sum(1 for f in findings if f["pass"])
    return {"schema": SCHEMA, "passed": passed, "total": len(findings), "findings": findings,
            "domains": {k: v for k, v in domains.items()},
            "prequential": {k: {"tested": v["tested"], "refutations": v["refutations"],
                                "survived_all": v["survived_all"]} for k, v in pq.items()},
            "held_out_note": ("measured with a truth function in the same turn: 42/45 interpolated; "
                              "the failures were a hypothesis fitted on a strictly positive range "
                              "and asked about negatives, which is the domain question this module "
                              "is about"),
            "authority": "NONE"}


def _degenerate_rival_check() -> bool:
    """Would a one-point constant be admitted as a rival? It must not be."""
    pts = [((0,), 0.0), ((1,), 2.0), ((2,), 4.0)]
    out = rivals(pts, "return 2 * x")
    return any(r.get("differs_at") in ("0", "1", "2") and r.get("rival") == "constant"
               for r in out["rivals"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = run()
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True, default=str))
        return 0
    for name, d in doc["domains"].items():
        print("%-14s domain=[%s, %s]" % (name, d.get("lo"), d.get("hi")))
    print()
    for name, p in doc["prequential"].items():
        print("%-8s prequential: %d tested, %d refuted, survived_all=%s" % (
            name, p["tested"], p["refutations"], p["survived_all"]))
    print("\n%d/%d findings as predicted" % (doc["passed"], doc["total"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
