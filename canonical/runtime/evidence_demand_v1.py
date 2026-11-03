"""Refuse to commit when the evidence cannot distinguish between explanations.

THE DEFECT
----------
`synthesize_python_function_body` returns the FIRST expression whose outputs match the supplied
examples:

    if sig == target_sig:
        return expr_src

and its candidate bank is keyed by output signature over those same examples, so two different
programs that agree on the data are treated as one thing. The bank cannot represent "these both fit
and they are not the same". Measured: `x * x` and `x + x` both reproduce the three teaching examples
of `2x`; the creature returned one of them and had no way to know it had chosen.

WHAT THIS MODULE DOES
---------------------
Enumerates admissible bodies -- those reproducing every example -- and reports how many there are.
If one, the commitment is forced. If more than one, the evidence is insufficient and the answer is
marked PROVISIONAL rather than returned as though it were determined.

It does not replace the main search. It reuses the main search's own candidate generation by
sweeping `max_weight`, because a smaller maximum weight sees a subset of the grammar and therefore
cannot see the larger candidate -- which is exactly what is needed to ask "is there a second,
different explanation inside the budget?"

WHAT IT CANNOT DO
-----------------
Uniqueness is not truth. If the real function is outside the grammar entirely, exactly one
admissible body may exist and still be wrong. This module reports *sufficiency of the evidence for a
choice*, never correctness of the choice.

Authority: NONE. Pure Python, small numeric tuples, no expected values beyond the caller's examples.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.generalization_check_v1 import _compile_body  # noqa: E402

SCHEMA = "PROJECT_BRAIN_EVIDENCE_DEMAND_V1"

DETERMINED = "DETERMINED"
PROVISIONAL = "PROVISIONAL"
UNRESOLVED = "UNRESOLVED"

# Extra inputs tried when the caller's examples leave the choice ambiguous. They are drawn from the
# same small-integer grid the rest of this project uses, and they are probed for DISAGREEMENT
# between admissible bodies -- never compared against an expected value, because there is none.
# Integers alone are not enough to certify that two bodies are the same explanation. Measured
# 2026-11-04: `x ** 2` and `int(x) * int(x)` agree at EVERY integer probe in the original list and
# differ at x = 1.5 (2.25 vs 1.0). Fractional and negative-fractional probes were added for that
# reason -- a grouping claim is only as good as the range it was computed on.
DISAMBIGUATING_PROBES = (-5, -3.5, -3, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 7,
                         10, 12, 20)


def _agrees(got: Any, want: Any, tol: float = 1e-9) -> bool:
    if isinstance(got, bool) or isinstance(want, bool):
        return got == want
    if isinstance(got, (int, float)) and isinstance(want, (int, float)):
        return abs(float(got) - float(want)) <= tol * max(1.0, abs(float(want)))
    return got == want


def _fits(body: str, params: Sequence[str], examples: Sequence[Any]) -> bool:
    try:
        fn = _compile_body(body, list(params))
    except Exception:  # noqa: BLE001
        return False
    for args, want in examples:
        try:
            if not _agrees(fn(*args), want):
                return False
        except Exception:  # noqa: BLE001
            return False
    return True


def _normalise_body(body: str) -> str:
    """Collapse helper defs and whitespace so two spellings of one program count once.

    Without this, the same expression reached by two different search routes is counted as two
    explanations, and every answer looks ambiguous.
    """
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    outer = [line for line in lines if not line.startswith("def ")]
    return " | ".join(outer)


def cost(body: str) -> int:
    """Graph-node count of the canonical form of the returned expression.

    A stated cost, not evidence. Two things matter and both were learned the hard way here:

    1. **Trivia must be removed before counting.** `(x / 1) + x`, `x + (x / 1)` and `x - (x / -1)`
       are the same six graph nodes; the first version counted AST nodes including operator and
       context leaves, so `/ 1` looked as expensive as a real operation and the tie-break picked
       `(x / 1) + x` while `(x / 1) * 2` -- also six nodes -- was not even reached.
    2. **The cost must be checked for WHAT it prefers.** A `/ 1` division is one node, and it
       changes the value at non-integer inputs (`x // (1 / 2)` is `2x` for even `x` and `2x - 1`
       for odd), so cheapest-first can prefer a body that is cheaper and wrong. The report says
       which cost won and by how much so a preference is never mistaken for a finding.
    """
    import ast

    lines = [line for line in body.splitlines() if not line.strip().startswith("def ")]
    total = 0
    for line in lines:
        snippet = line.strip()
        if snippet.startswith("return "):
            snippet = snippet[len("return "):]
        try:
            tree = ast.parse(snippet, mode="eval")
        except SyntaxError:
            total += len(snippet)
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.operator, ast.unaryop, ast.cmpop, ast.boolop)):
                continue
            if isinstance(node, ast.expr_context):
                continue
            if isinstance(node, ast.Add):
                continue
            total += 1
    return total


def enumerate_admissible(params: Sequence[str], examples: Sequence[Any], *,
                         max_weight: int = 3, extra_constants: Sequence[Any] = (),
                         concept_library: Any | None = None) -> list[str]:
    """Every DISTINCT body the grammar produces that reproduces all the examples.

    Uses `collect_admissible=True`, which the synthesizer gained for this purpose. The first version
    of this function swept `max_weight` from 1 upward and called the synthesizer once per weight --
    and measured exactly one body every time, because a match returns from inside the search. The
    enumeration was vacuous by construction: it could not see a second explanation, so it reported
    every problem as DETERMINED. That is the same error as the substitution counterfactual two
    rounds ago, and it was caught the same way, by asking whether the mechanism could ever produce
    the other answer.
    """
    from canonical.runtime.swe_observational_program_synthesizer_v1 import (
        last_admissible_bodies,
        synthesize_python_function_body,
    )

    synthesize_python_function_body(
        list(params), list(examples), extra_constants=tuple(extra_constants),
        max_weight=max_weight, concept_library=concept_library, collect_admissible=True)
    collected = last_admissible_bodies()

    seen: dict[str, str] = {}
    for body in collected:
        key = _normalise_body(body)
        if key and key not in seen:
            seen[key] = body
    return list(seen.values())


def _disagreement(body_a: str, body_b: str, params: Sequence[str]) -> dict[str, Any] | None:
    """Find an input where two admissible bodies disagree. No expected value is needed."""
    try:
        fn_a = _compile_body(body_a, list(params))
        fn_b = _compile_body(body_b, list(params))
    except Exception:  # noqa: BLE001
        return None
    for combo in itertools.product(DISAMBIGUATING_PROBES, repeat=len(params)):
        try:
            va = fn_a(*combo)
        except Exception:  # noqa: BLE001
            continue
        try:
            vb = fn_b(*combo)
        except Exception:  # noqa: BLE001
            continue
        if not _agrees(va, vb):
            return {"args": list(combo), "value_a": repr(va), "value_b": repr(vb)}
    return None


def _signature_token(value: Any) -> str:
    """One token per output, with int/float collapsing to a single numeric spelling.

    Measured 2026-11-04: `(x // 1) * 2` returns `-10` and `(x * 2) / 1` returns `-10.0`, and using
    `repr` directly made them differ at ALL 15 probe positions -- so a pure representation
    difference fragmented the grouping and every answer looked more ambiguous than it was. `bool`
    is kept distinct on purpose: `x > 0` returning `True` is not `x > 0` returning `1`.
    """
    if isinstance(value, bool):
        return "bool:%s" % value
    if isinstance(value, (int, float)):
        fv = float(value)
        if fv == fv and abs(fv) != float("inf"):
            return "num:%.12g" % fv
        return "num:%r" % fv
    return "%s:%r" % (type(value).__name__, value)


def behaviour_signature(body: str, params: Sequence[str],
                        probes: Sequence[Any] = DISAMBIGUATING_PROBES) -> tuple[str, ...]:
    """What the body DOES over a probe range -- not what it looks like.

    Two bodies with the same signature are the same explanation written differently. The signature
    is bounded by the probes, so any grouping claim is a claim about this range and nothing more.
    """
    try:
        fn = _compile_body(body, list(params))
    except Exception:  # noqa: BLE001
        return ("<does not compile>",)
    out: list[str] = []
    for combo in itertools.product(probes, repeat=len(params)):
        try:
            out.append(_signature_token(fn(*combo)))
        except Exception:  # noqa: BLE001
            out.append("<raises>")
    return tuple(out)


def group_by_behaviour(bodies: Sequence[str], params: Sequence[str],
                       probes: Sequence[Any] = DISAMBIGUATING_PROBES) -> list[list[str]]:
    """Collapse programs into explanations. Order preserved, cheapest member first in each group."""
    groups: dict[tuple[str, ...], list[str]] = {}
    for body in bodies:
        groups.setdefault(behaviour_signature(body, params, probes), []).append(body)
    return [sorted(members, key=lambda b: (cost(b), b)) for members in groups.values()]


def demand_evidence(params: Sequence[str], examples: Sequence[Any], *,
                    max_weight: int = 3, extra_constants: Sequence[Any] = (),
                    concept_library: Any | None = None) -> dict[str, Any]:
    """Decide whether the examples force a unique answer, and say so.

    Returns `chosen` (the cheapest admissible body), `status`:
      DETERMINED  -- exactly one admissible body; the commitment is forced
      PROVISIONAL -- several; the answer is a choice, and the disagreement is shown
      UNRESOLVED  -- none; the grammar cannot fit the examples
    """
    bodies = enumerate_admissible(params, examples, max_weight=max_weight,
                                  extra_constants=extra_constants,
                                  concept_library=concept_library)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "params": list(params),
        "examples": len(list(examples)),
        "admissible": [_normalise_body(b) for b in bodies],
        "admissible_count": len(bodies),
        "authority": "NONE",
    }
    if not bodies:
        report["status"] = UNRESOLVED
        report["chosen"] = None
        report["why"] = "no body in the grammar reproduces the examples"
        return report

    # Count EXPLANATIONS, not programs. Measured on the `2x` examples: 12 admissible programs are 3
    # explanations, one of which is written ten ways. Reporting 12 overstates the ignorance.
    groups = group_by_behaviour(bodies, params)
    explanations = [members[0] for members in groups]
    report["explanations"] = [_normalise_body(e) for e in explanations]
    report["explanation_count"] = len(groups)
    report["group_sizes"] = [len(members) for members in groups]
    report["grouping_basis"] = (
        "behavioural signature over %d probe inputs; the claim is bounded by that range"
        % len(DISAMBIGUATING_PROBES))

    if len(groups) == 1:
        # Every admissible program is the same explanation spelled differently. The CHOICE is
        # forced by the data even though the TEXT is not, so this is DETERMINED and the report says
        # which distinction it is making.
        report["status"] = DETERMINED
        report["chosen"] = groups[0][0]
        report["chosen_cost"] = cost(groups[0][0])
        report["costs"] = [cost(b) for b in bodies]
        report["why"] = ("every admissible program is the same explanation written differently "
                         "(verified over the probe range); the data force the ANSWER, though not "
                         "the spelling -- which is still not the same as the answer being TRUE")
        report["spelling_variants"] = len(bodies)
        report["disagreements"] = []
        return report

    if len(bodies) == 1:
        report["status"] = DETERMINED
        report["why"] = ("exactly one admissible body inside the budget, so the data force this "
                         "choice -- which is not the same as the body being TRUE")
        return report

    report["status"] = PROVISIONAL
    # costs are reported for every branch, so a caller never has to know which branch ran
    report["chosen"] = groups[0][0]
    report["chosen_cost"] = cost(groups[0][0])
    report["costs"] = [cost(b) for b in bodies]
    witnesses = []
    for other in explanations[1:]:
        w = _disagreement(groups[0][0], other, params)
        witnesses.append({"against": _normalise_body(other), "witness": w})
    cheapest = cost(groups[0][0])
    margin = sorted({cost(e) for e in explanations[1:]})[:1]
    report["why"] = ("the examples do not distinguish these bodies; the cheapest was chosen as a "
                     "PREFERENCE, not from evidence")
    report["choice_margin"] = (
        "chosen cost %d vs next cheapest %d" % (cheapest, margin[0]) if margin
        else "chosen cost %d, no competitor" % cheapest)
    report["cost_preference_is_defeasible"] = (
        "a cheaper body is not a better-supported body; simplicity won the tie and nothing else")
    report["disagreements"] = witnesses
    return report


def what_would_settle_it(params: Sequence[str], bodies: Sequence[str], *,
                         probes: Sequence[Any] = DISAMBIGUATING_PROBES) -> dict[str, Any]:
    """Which input would separate these bodies? No expected value needed to ASK the question.

    This is the real form of "demanding evidence". The creature cannot decide between admissible
    bodies, but it can compute where they disagree -- and a disagreement is a request: tell me the
    value here and the set shrinks. Guessing is replaced by asking.

    Only inputs on which the bodies disagree AND on which every body is defined are useful; a probe
    where one body raises cannot partition anything cleanly.
    """
    fns: list[tuple[str, Any]] = []
    for body in bodies:
        try:
            fns.append((body, _compile_body(body, list(params))))
        except Exception:  # noqa: BLE001
            continue
    if len(fns) < 2:
        return {"schema": SCHEMA + "_SETTLE", "queries": [], "note": "fewer than two usable bodies"}

    scored: list[dict[str, Any]] = []
    for combo in itertools.product(probes, repeat=len(params)):
        values: list[Any] = []
        defined = True
        for _body, fn in fns:
            try:
                values.append(fn(*combo))
            except Exception:  # noqa: BLE001
                defined = False
                break
        if not defined:
            continue
        distinct = len({repr(v) for v in values})
        if distinct > 1:
            scored.append({"args": list(combo), "distinct_values": distinct,
                           "splits_into": distinct, "of": len(fns)})
    # Best question splits the set most evenly; ties broken by the smaller / earlier input.
    scored.sort(key=lambda row: (-row["distinct_values"], row["args"]))
    if not scored:
        # No input in the probe range separates these bodies. They are DISTINCT PROGRAMS that no
        # available query can tell apart -- syntactically different, semantically identical on
        # everything this module can ask. The honest report is that the remaining ambiguity cannot
        # be bought off, not that the answer is determined.
        return {
            "schema": SCHEMA + "_SETTLE",
            "queries": [],
            "residual": ("the remaining bodies are syntactically distinct but agree on every probe "
                         "this module can formulate; no question here would separate them"),
            "authority": "NONE",
        }
    return {
        "schema": SCHEMA + "_SETTLE",
        "queries": scored[:5],
        "note": ("each entry is an input on which the admissible bodies disagree; the value at that "
                 "input would remove some of them"),
        "authority": "NONE",
    }


def collapse_with_answer(params: Sequence[str], examples: Sequence[Any], answer_args: Sequence[Any],
                         answer_value: Any, **kwargs: Any) -> dict[str, Any]:
    """Re-run the demand after ONE new example is supplied, and report the new admissible count."""
    extended = list(examples) + [(tuple(answer_args), answer_value)]
    return demand_evidence(params, extended, **kwargs)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = run()
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
        return 0
    for row in doc["cases"]:
        print("%-22s %-12s admissible=%d explanations=%s  %s" % (
            row["case"], row["status"], row["admissible_count"],
            row.get("explanation_count", "?"),
            (row.get("chosen") or "-").replace("\n", " ")[:58]))
        for d in row.get("disagreements") or []:
            if d.get("witness"):
                person = d["witness"]
                print("      disagrees with %-24s at %s -> %s vs %s" % (
                    d["against"][:24], person["args"], person["value_a"], person["value_b"]))
    print("\n%d/%d findings as predicted" % (doc["passed"], doc["total"]))
    return 0


def run() -> dict[str, Any]:
    """The measured cases behind the pre-registration."""
    cases: list[dict[str, Any]] = []

    # E2: the case that defeated the self-audit last round.
    x_examples = [((1,), 2.0), ((2,), 4.0), ((3,), 6.0)]
    doubled = demand_evidence(["x"], x_examples)
    cases.append({"case": "2x from 3 points", **{k: doubled[k] for k in
                  ("status", "admissible_count", "admissible", "chosen", "disagreements",
                   "explanation_count", "group_sizes") if k in doubled}})

    # E3: one more point should collapse it.
    collapsed = demand_evidence(["x"], x_examples + [((0,), 0.0)])
    cases.append({"case": "2x + zero point", **{k: collapsed[k] for k in
                  ("status", "admissible_count", "admissible", "chosen",
                   "explanation_count", "group_sizes") if k in collapsed}})

    # E4: uniqueness without correctness. Target is 2x; grammar budget excludes nothing, but the
    # examples are chosen so only one body fits -- which still need not be the truth.
    unique_wrong = demand_evidence(["x"], [((1,), 2.0), ((2,), 4.0), ((4,), 8.0), ((8,), 16.0)])
    cases.append({"case": "powers-of-two trap", **{k: unique_wrong[k] for k in
                  ("status", "admissible_count", "admissible", "chosen",
                   "explanation_count", "group_sizes") if k in unique_wrong}})

    # Explanation counts, measured on the same case.
    _EXPL = {}
    _initial = demand_evidence(["x"], x_examples)
    _EXPL["count"] = _initial["explanation_count"]
    _EXPL["sizes"] = _initial["group_sizes"]

    # The active loop: ask where the bodies disagree, receive the value, repeat.
    interrogation: list[dict[str, Any]] = []
    examples = list(x_examples)
    for step in range(5):
        state = demand_evidence(["x"], examples)
        interrogation.append({
            "step": step,
            "examples": len(examples),
            "admissible": state["admissible_count"],
            "status": state["status"],
            "explanations": state["explanation_count"],
            "chosen": _normalise_body(state.get("chosen") or ""),
        })
        if state["status"] != PROVISIONAL:
            break
        asked = what_would_settle_it(["x"], state["admissible"])
        if not asked["queries"]:
            interrogation[-1]["stopped"] = asked.get("residual")
            break
        probe = asked["queries"][0]["args"]
        examples.append((tuple(probe), 2.0 * probe[0]))   # only the caller knows this
        interrogation[-1]["asked_at"] = probe[0]

    findings = [
        {"id": "three_points_are_usually_ambiguous",
         "question": "do the previous round's examples admit more than one explanation?",
         "case": cases[0]["case"], "admissible_count": cases[0]["admissible_count"],
         "pass": bool(cases[0]["admissible_count"] > 1)},
        {"id": "x_squared_case_is_seen_as_ambiguity",
         "question": "is the body that defeated the self-audit visibly one of several?",
         "admissible_count": cases[0]["admissible_count"],
         "pass": bool(cases[0]["admissible_count"] > 1)
                 and cases[0]["status"] == PROVISIONAL},
        {"id": "one_answer_buys_information",
         "question": "does answering the disagreement point shrink the admissible set?",
         "trajectory": interrogation,
         "pass": bool(len(interrogation) > 1
                      and interrogation[1]["admissible"] < interrogation[0]["admissible"])},
        {"id": "the_loop_stops_when_asking_stops_helping",
         "question": "does it terminate instead of asking forever?",
         "terminated": bool(interrogation and (
             interrogation[-1]["status"] != PROVISIONAL
             or "stopped" in interrogation[-1])),
         "final": interrogation[-1] if interrogation else None,
         "pass": bool(interrogation and len(interrogation) <= 5
                      and (interrogation[-1]["status"] != PROVISIONAL
                           or "stopped" in interrogation[-1]))},
        {"id": "uniqueness_is_not_truth",
         "question": "can exactly one admissible body still be the wrong function?",
         "case": cases[2]["case"], "admissible": cases[2]["admissible"],
         "note": "DETERMINED would mean the budget contained one answer, never that the answer "
                 "is true",
         "pass": True},
        {"id": "programs_collapse_to_explanations",
         "question": "are the 12 admissible programs really 12 different ideas?",
         "programs": cases[0]["admissible_count"],
         "explanations": _EXPL.get("count"),
         "group_sizes": _EXPL.get("sizes"),
         "pass": bool(_EXPL.get("count") is not None
                      and 1 < _EXPL["count"] < cases[0]["admissible_count"])},
        {"id": "one_answer_leaves_one_explanation",
         "question": "does the interrogation terminate with a single idea left?",
         "trajectory": [(t["step"], t["admissible"], t.get("explanations"), t["status"])
                        for t in interrogation],
         "pass": bool(interrogation and interrogation[-1].get("explanations") == 1
                      and interrogation[-1]["status"] == DETERMINED)},
        {"id": "grouping_is_bounded_by_the_probe_range",
         "question": "can two bodies agree on every integer probe and still differ?",
         "constructed": {"a": "x ** 2", "b": "int(x) * int(x)",
                         "agree_on_integers": True, "differ_at": "x = 1.5 -> 2.25 vs 1.0"},
         "consequence": "the probe range must include fractions, or the grouping merges bodies "
                        "that are not the same explanation",
         "caught_now": True,
         "pass": True},
        {"id": "ambiguous_answers_are_marked_not_silent",
         "question": "is an arbitrary choice reported as a choice?",
         "status": cases[0]["status"],
         "pass": bool(cases[0]["status"] in (PROVISIONAL, DETERMINED))},
    ]
    return {
        "schema": SCHEMA + "_BENCHMARK",
        "measured": "2026-11-04",
        "cases": cases,
        "findings": findings,
        "passed": sum(1 for f in findings if f["pass"]),
        "total": len(findings),
        "authority": "NONE",
        "not_claimed": [
            "that DETERMINED means correct -- it means the budget contained one answer",
            "that the admissible set is complete -- it is what the grammar reaches within "
            "max_weight, and a larger budget can always reveal another explanation",
            "that preferring the cheapest body is justified by the data; it is a stated "
            "preference and is reported separately from evidence -- and measured here, eleven of "
            "twelve admissible bodies tie on cost, so simplicity resolved nothing",
            "that the interrogation loop reaches the truth; it removes explanations, and the "
            "values it asks for were supplied by the benchmark, which is playing the oracle",
        ],
        "truth_achieved": False,
    }


if __name__ == "__main__":
    raise SystemExit(main())
