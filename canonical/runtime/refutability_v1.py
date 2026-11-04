#!/usr/bin/env python3
"""Is this claim testable from the evidence the creature already holds?

WHY THIS EXISTS
---------------
Round 25 measured `x*x + y` over three points being CRYSTALLISED as a law:

    def run(x0, x1):
        return ((4.5 * x0) + (-0.5 * x1) + -0.49999999999999994)

That body returns 34.5 where the truth is 120 at (10, 20). It is wrong on every input it was not
shown. It was admitted because it fits the evidence, and a fit is all that was ever asked for.

The reason is not that the search was weak. Three observations exactly determine the three parameters
of an affine fit, so the body has ZERO RESIDUAL ON ZERO LEFTOVER DATA. Zero residual with nothing left
over is not corroboration -- it is the definition of a curve drawn through three points. Any three
points, no matter what generated them, admit such a curve.

This is the same defect round 25 fixed one layer down, in a different costume:

    round 25   "no candidate" was spoken without proving the SEARCH FINISHED
    here       "crystallised" is spoken without proving anything TESTED IT

Both are the creature asserting a confidence its evidence has not earned. The first is about a budget;
this one is about degrees of freedom.

WHAT THIS MODULE COMPUTES
-------------------------
Not a score, and not another fit. A single question: **could the creature have been wrong?**

That is answerable from the evidence alone, with no oracle and no held-out set handed to it. Withhold
point `i`; fit the remaining points with the real candidate generator; if the fit still predicts the
withheld value, then that value was a PREDICTION and disagreement would have been a REFUTATION. A
claim that predicts nothing it was not shown cannot be refuted, and a claim that cannot be refuted is
not a claim about the world.

    REFUTABLE       at least one observation was predicted by a fit that did not use it
    NOT_REFUTABLE   every observation was available to every fit that "explained" it
    TOO_FEW_POINTS  no withheld fit could be over-determined, so the question is unanswerable

The third verdict matters as much as the first. With `n <= parameters + 1` the test cannot run, and
reporting that as either success or failure would be inventing an answer. That is exactly the
situation `x*x + y` over three points is in: the evidence is STRUCTURALLY INCAPABLE of testing the
claim, which is a fact the creature is entitled to know and to report.

WHAT THIS IS NOT
----------------
It does not say the claim is TRUE. REFUTABLE means "would have been caught if wrong", not "right". A
refutable claim can still be false on the next observation -- that risk is the point. It also does not
license refusal: TOO_FEW_POINTS is a statement about the evidence, and the caller decides whether to
buy more, ask an oracle, or answer under a stated provisionality.

Authority: NONE. Pure Python. $0. No truth is claimed about any body.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_REFUTABILITY_V1"

REFUTABLE = "REFUTABLE"
NOT_REFUTABLE = "NOT_REFUTABLE"
TOO_FEW_POINTS = "TOO_FEW_POINTS"


def _strip_header(src: str) -> str:
    """Drop a `def run(...)` header so `generalization_check` sees BODY lines, not a helper block.

    Measured 2026-11-04: `_split_body` treats a leading `def` as a helper and returns an EMPTY outer
    body, which compiles to NO_FUNCTION_BODY and is reported as OVERFIT. A correct organ was scored as
    overfit three separate times in this session for exactly this reason.
    """
    lines = src.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("def ") and ln.rstrip().endswith(":"):
            return "\n".join(lines[i + 1:])
    return src


class _SynthBody:
    """A synthesizer body presented as an organ-shaped object so `_fits` can treat both alike."""

    def __init__(self, body: str, names: Sequence[str]) -> None:
        self._body = body
        self._names = list(names)
        self.name = "observational_body"
        self.organ_id = "observational_body"
        self.source_code = f"def run({', '.join(self._names)}):\n" + "".join(
            "    " + ln + "\n" for ln in self._body.splitlines()
        )

    def invoke(self, *args: Any) -> Any:
        """Evaluate through the SAME exec path the organ graph uses.

        `generalization_check._compile_body` restricts builtins to abs/min/max/round/int/float/len, so
        `return sorted(x0)` raises NameError there and a correct body was scored as a failure -- twice
        in this session, once as OVERFIT and once as NOT_REFUTABLE. The crystallizer does not use that
        sandbox; it uses `_wrap_expr_into_source` plus exec, and an auditor that is stricter than the
        thing it audits refuses work that was actually valid.
        """
        from canonical.swe_kernel import meta_circular_organ_graph_v1 as M

        # `self._body` is a STATEMENT body (`return sorted(x0)`), not an expression, so it must not go
        # through `_wrap_expr_into_source`, which prefixes its own `return` and produced
        # `return return sorted(x0)` -- a SyntaxError swallowed as a prediction failure (measured
        # 2026-11-04). Build the function directly instead.
        lines = self._body.splitlines() or ["return None"]
        src = f"def run({', '.join(self._names)}):\n" + "".join(
            "    " + ln + "\n" for ln in lines
        )
        ns: dict[str, Any] = {}
        exec(compile(src, "<refutability>", "exec"), {"math": __import__("math")}, ns)  # noqa: S102
        return ns["run"](*args)


def _fits(examples: Sequence[tuple[tuple[Any, ...], Any]], arity: int) -> list[Any]:
    """Every candidate body the real generator can produce that reproduces `examples`.

    Deliberately the SAME generator the crystallizer uses, so this test cannot be easier than the
    thing it audits. A private, weaker fitter here would certify claims the crystallizer could not
    have made.
    """
    from canonical.swe_kernel import meta_circular_organ_graph_v1 as M

    # MEASURED, 2026-11-04, and this made the module WEAKER THAN THE THING IT AUDITS. Using only
    # `_generate_candidate_expressions` here (constant / projection / affine / table) meant `sorted(x)`
    # was invisible: withholding a point regenerated nothing that could predict it, so a perfectly
    # testable law was reported NOT_REFUTABLE and refused. An auditor must be at least as expressive
    # as the synthesizer or it certifies only what it happens to understand.
    #
    # So the observational synthesizer's bodies are included as well, at the budget rounds 22-25
    # established. That is the search that actually reaches `sorted(x0)`, `len(x0)` and `x*y+1`.
    out: list[Any] = []
    try:
        from canonical.runtime.swe_observational_program_synthesizer_v1 import (
            synthesize_python_function_body,
        )

        _names = [f"x{i}" for i in range(arity)]
        _consts: list[Any] = []
        for _inp, _out in examples:
            for _v in _inp:
                if isinstance(_v, (int, float)) and not isinstance(_v, bool) and _v not in _consts:
                    _consts.append(_v)
        _body = synthesize_python_function_body(
            _names, list(examples), extra_constants=_consts[:6],
            max_weight=3, max_bank_size=900,
        )
        if isinstance(_body, str) and _body.strip():
            # Validated by EXECUTION, not by `generalization_check.classify`. That module compiles
            # into a restricted builtin namespace (abs/min/max/round/int/float/len) which has no
            # `sorted`, so a correct `return sorted(x0)` raised NameError and was scored OVERFIT --
            # measured 2026-11-04, on the very case this branch was added for. The check here uses the
            # same evaluation path the crystallizer uses, so the auditor cannot disagree with the
            # thing it audits because of its own sandbox.
            _candidate = _SynthBody(_strip_header(_body), _names)
            if all(
                _safe_agrees(_candidate, _inp, _want) for _inp, _want in examples
            ):
                out.append(_candidate)
    except Exception:  # noqa: BLE001 - a failed second opinion must not certify anything
        pass

    # NOTE: `out` is NOT re-initialised here. It was, and that silently discarded every body the
    # synthesizer branch above had just validated -- `sorted(x)` was found, executed correctly, and
    # then thrown away by a shadowing assignment one line later (measured 2026-11-04). The function
    # reported NOT_REFUTABLE for a law whose own body it had just run successfully.
    seen: set[str] = set()
    for name, expr, helpers in M._generate_candidate_expressions(examples):
        if expr in seen:
            continue
        seen.add(expr)
        try:
            organ = M.make_organ(
                stratum=M.SKILL,
                name=name,
                task_signature="refutability::probe",
                entrypoint="run",
                source_code=M._wrap_expr_into_source(arity, expr, helpers),
            )
        except Exception:  # noqa: BLE001 - an unusable candidate cannot certify anything
            continue
        ok = True
        for inp, want in examples:
            hit, got = M._safe_eval_candidate(organ, inp)
            if not hit or not M._outputs_match(got, want):
                ok = False
                break
        if ok:
            out.append(organ)
    return out


def assess(
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    *,
    arity: int | None = None,
    agree: Callable[[Any, Any], bool] | None = None,
) -> dict[str, Any]:
    """Report whether the evidence COULD have refuted a claim it is being used to support.

    `examples` are `(input_tuple, output)`. Nothing else is needed: no oracle, no held-out set, no
    cooperation from the caller. That is the whole point -- a creature that needs to be handed the
    answer in order to know it should be unsure is not checking itself.
    """
    n = len(examples)
    if n == 0:
        return {
            "schema": SCHEMA,
            "verdict": TOO_FEW_POINTS,
            "why": "no evidence at all: nothing could have been predicted",
            "observations": 0,
            "withheld_predictions": 0,
            "withheld_attempts": 0,
            "authority": "NONE",
        }
    if arity is None:
        arity = len(examples[0][0])

    def _agrees(a: Any, b: Any) -> bool:
        if agree is not None:
            return bool(agree(a, b))
        from canonical.swe_kernel import meta_circular_organ_graph_v1 as M

        return bool(M._outputs_match(a, b))

    # How many training points a withheld fit needs before its prediction counts.
    #
    # MEASURED, 2026-11-04: this was `arity + 2`, on the assumption that a candidate is an affine fit
    # in `arity` inputs. That assumption is false about the generator -- `len(x0)` has ZERO free
    # parameters, a period table has one per residue, an affine fit has `arity + 1`. A single global
    # parameter count therefore rejected laws that were not fitted at all: `len(x)` over three lists
    # came back TOO_FEW_POINTS and was refused, when a body with no parameters needs no leftover data
    # to be trustworthy.
    #
    # The count below is the weakest honest bound: a fit must not have MORE parameters than training
    # points, which is `arity + 1`. Bodies with fewer parameters than that are strictly better off and
    # the leave-one-out test treats them on their merits -- `len(x0)` regenerates from any two
    # examples and predicts the third, which is a real prediction.
    need = arity + 1
    predicted: list[int] = []
    attempted = 0
    for i in range(n):
        train = [e for j, e in enumerate(examples) if j != i]
        if len(train) < need:
            continue
        attempted += 1
        probe_in, probe_out = examples[i]
        for organ in _fits(train, arity):
            hit, got = _safe_eval(organ, probe_in)
            if hit and _agrees(got, probe_out):
                predicted.append(i)
                break

    if attempted == 0:
        verdict = TOO_FEW_POINTS
        why = (
            f"{n} observation(s) cannot support a single over-determined fit "
            f"(needs at least {need + 1} for arity {arity}); the evidence is structurally incapable of "
            "testing a claim with this many parameters, so 'fits the evidence' is not corroboration"
        )
    elif predicted:
        verdict = REFUTABLE
        why = (
            f"{len(predicted)} of {n} observations were PREDICTED by a fit that did not use them, so "
            "disagreement there would have been a refutation"
        )
    else:
        verdict = NOT_REFUTABLE
        why = (
            f"all {attempted} withheld fits failed to predict the point they excluded, so every "
            "observation was available to every fit that explained it: the claim has absorbed its "
            "evidence without predicting anything beyond it"
        )

    return {
        "schema": SCHEMA,
        "verdict": verdict,
        "why": why,
        "observations": n,
        "arity": arity,
        "withheld_predictions": len(predicted),
        "withheld_attempts": attempted,
        "predicted_indices": predicted[:16],
        "authority": "NONE",
    }


def _safe_agrees(organ: Any, probe_in: Any, want: Any) -> bool:
    hit, got = _safe_eval(organ, probe_in)
    if not hit:
        return False
    from canonical.swe_kernel import meta_circular_organ_graph_v1 as M

    return bool(M._outputs_match(got, want))


def _safe_eval(organ: Any, probe_in: Any) -> tuple[bool, Any]:
    # `_SynthBody` is not an `ExecutableOrgan`, so `_safe_eval_candidate` cannot touch it and every
    # one of its predictions silently read as a failure -- which made `len(x)` look NOT_REFUTABLE when
    # a body predicting it was right there. Route each kind through the path that can evaluate it.
    if isinstance(organ, _SynthBody):
        try:
            args = tuple(probe_in) if isinstance(probe_in, (tuple, list)) else (probe_in,)
            return True, organ.invoke(*args)
        except Exception:  # noqa: BLE001
            return False, None
    from canonical.swe_kernel import meta_circular_organ_graph_v1 as M

    try:
        return M._safe_eval_candidate(organ, probe_in)
    except Exception:  # noqa: BLE001
        return False, None


def may_be_permanent(verdict: str) -> bool:
    """Only a REFUTABLE claim has earned permanence.

    NOT_REFUTABLE and TOO_FEW_POINTS are both statements that the evidence did not test the claim.
    They differ in what to do next -- buy more evidence, or say so and stop -- not in whether the
    claim has been corroborated. Neither one has.
    """
    return verdict == REFUTABLE


def plan_probes(
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    *,
    arity: int | None = None,
    candidates: Sequence[Any] = (),
    disagree: Callable[[Any, Any], bool] | None = None,
) -> dict[str, Any]:
    """Turn "this claim is untestable" into the smallest experiment that would test it.

    WHY THIS EXISTS
    ---------------
    A verdict is not a decision. `assess` can say TOO_FEW_POINTS, and until this function existed the
    only thing the creature did with that was refuse -- which is safe and useless. A refusal that does
    not say WHAT WOULD CHANGE ITS MIND is just a quieter way of not knowing.

    The deficit is COMPUTABLE, not a policy. An affine fit over `arity` inputs has `arity + 1`
    parameters and leave-one-out needs one more training point than parameters, so the evidence is
    testable at

        n >= arity + 2      observations

    measured: 3 points for a 2-input affine is one short, and the 4th point is exactly what makes the
    claim refutable. That is why Door 3's hardcoded "buy 2 probes" restored nothing -- with 3 seeds it
    left 4, which tests only if the withheld fit is over-determined, and it picked its probes from the
    derived space without asking how many were needed.

    Which probes is a second question, and it has a better answer than "the next integers". A probe is
    worth buying where the SURVIVING CANDIDATES DISAGREE: at a point they all agree on, the answer is
    already implied and the observation is free information about nothing. So when candidates and a
    disagreement predicate are supplied, probes are ranked by how many surviving pairs they separate.

    Returns the deficit, the probes, and an explicit statement of what the experiment buys.
    """
    if not examples:
        return {
            "schema": SCHEMA,
            "deficit": 0,
            "probes": [],
            "why": "no evidence at all; the first observation is not a question of design",
            "authority": "NONE",
        }
    if arity is None:
        arity = len(examples[0][0])
    need = int(arity) + 2
    deficit = max(0, need - len(examples))

    # Candidate probe inputs, from TWO sources, and the second one is not optional.
    #
    # (a) neighbours of what was observed; and
    # (b) the numbers the SURVIVING HYPOTHESES themselves mention.
    #
    # MEASURED, 2026-11-04, and this was a genuine false positive. Seeds 1..5 of `x // 7` are all 0,
    # so probes taken only near the evidence sat at x <= 7 where EVERY candidate returns 0. The
    # creature bought its tests there, learned nothing that separated `x // 7` from `x // 8`, and
    # crystallised `x // 8` -- wrong at 37 (4 for 5) and at 100 (12 for 14).
    #
    # Locality is the defect: tests near the evidence are worthless when the competing explanations
    # differ only far away. A hypothesis that mentions 8 can only be distinguished from one that
    # mentions 7 at points that straddle them, so those literals are where the experiment belongs.
    # This is the candidate's own model choosing its test -- not a frozen grid.
    numeric: list[int] = []
    for inp, _out in examples:
        for v in inp:
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                for delta in (1, -1, 2, -2):
                    cand = int(round(float(v))) + delta
                    if cand not in numeric:
                        numeric.append(cand)
    import re as _re

    for organ in candidates:
        body = getattr(organ, "source_code", "") or ""
        for lit in _re.findall(r"-?\d+", body):
            try:
                value = int(lit)
            except ValueError:
                continue
            for delta in (0, 1, -1, 2):
                cand = value + delta
                if cand not in numeric:
                    numeric.append(cand)



    def _probe_for(value: int) -> tuple[Any, ...]:
        return tuple([value] * int(arity))

    # (c) THE BOUNDARY OF THE EVIDENCE, and beyond it.
    #
    # A degrees-of-freedom deficit is not the only reason a claim is untested. Measured 2026-11-04:
    # seeds 1..5 of `x // 7` are all 0, everything fits, arity+2 <= 5 so the deficit was ZERO, one
    # probe was bought at x = -1 where nearly every candidate also returns 0, and `x // 8` was
    # crystallised -- wrong at 37, 100, 999. The ambiguity was never about parameters; it was about
    # WHERE the ramp breaks, and that can only be seen past the last observation.
    #
    # A structure that behaves one way on all the evidence is exactly a structure whose behaviour
    # changes next. So the region just outside the observed range is always probed, in both
    # directions, whatever the deficit says.
    observed_values = [
        int(round(float(v)))
        for inp, _out in examples
        for v in inp
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    ]
    if observed_values:
        lo, hi = min(observed_values), max(observed_values)
        span = max(1, hi - lo)
        for cand in (hi + 1, hi + 2, hi + span, lo - 1, lo - 2):
            if cand not in numeric:
                numeric.append(cand)

    # `fresh` is computed AFTER every source above has contributed, including the boundary probes.
    # It used to be computed here, before (c) was appended to `numeric`, so the boundary values never
    # reached the ranking -- the fix was invisible and the defect reproduced exactly (measured
    # 2026-11-04).
    seen = {tuple(repr(x) for x in inp) for inp, _ in examples}
    fresh = [v for v in numeric if tuple(repr(x) for x in (v,) * int(arity)) not in seen] or numeric

    ranked: list[tuple[int, tuple[Any, ...]]] = []
    for value in fresh:
        probe = _probe_for(value)
        score = 0
        if candidates and disagree is not None:
            for i, a in enumerate(candidates):
                for b in list(candidates)[i + 1:]:
                    try:
                        if disagree(a, b, probe):
                            score += 1
                    except Exception:  # noqa: BLE001 - an unusable pair separates nothing
                        continue
        ranked.append((score, probe))
    ranked.sort(key=lambda pair: (-pair[0], repr(pair[1])))
    # HOW MANY is not the degrees-of-freedom deficit. Measured 2026-11-04: for `x // 7` over seeds
    # 1..5 the deficit is ZERO (five points, arity 1, need three), so the old `max(deficit, 1)` bought
    # exactly ONE probe -- at x = -1, where `x // 7` and `x // 8` BOTH return -1. One question was
    # asked, nothing was separated, and `x // 8` was crystallised, wrong at 37, 100 and 999.
    #
    # A claim is untested when its SURVIVORS are still distinguishable, which is a different quantity
    # from whether an over-determined fit exists. So the plan returns enough probes to actually press
    # on the disagreement, and never fewer than a small floor: the cheapest possible experiment that
    # can still fail.
    separating = [p for s, p in ranked if s > 0]
    budget = max(deficit, 3)
    probes = (separating or [p for _s, p in ranked])[:budget]

    return {
        "schema": SCHEMA,
        "deficit": deficit,
        "need_observations": need,
        "have_observations": len(examples),
        "probes": probes,
        "separating_probes": sum(1 for s, _p in ranked if s > 0),
        "why": (
            f"{len(examples)} observation(s) cannot test an arity-{arity} fit, which needs {need}; "
            f"{deficit} more would make the claim refutable, and they are chosen where surviving "
            "candidates disagree so the answer is not already implied"
        ),
        "authority": "NONE",
    }
