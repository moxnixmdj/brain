"""Interrogate a real observation surface, and survive an answer that contradicts the model.

THE DEFECT THIS REPLACES
------------------------
The interrogation loop in `evidence_demand_v1.run()` ends with

    examples.append((tuple(probe), 2.0 * probe[0]))   # only the caller knows this

The *question* is computed honestly. The *answer* is a constant the harness already knew. So the
loop could only ever confirm the creature: every observation shaved the admissible set down, the
set never emptied, and the module had no vocabulary for the one thing a real world does all the
time -- return a value that no surviving explanation predicts.

WHAT THIS MODULE DOES
---------------------
Takes an actual callable as the oracle and drives the same loop through it. When an answer empties
the admissible set, the report is `REFUTED`, which is deliberately NOT `UNRESOLVED`:

    UNRESOLVED  zero admissible bodies and none were ever found. The grammar never fit the data.
                Nothing has been contradicted; something has simply not been described yet.
    REFUTED     bodies WERE found, and one observation is inconsistent with all of them. The model
                was sufficient for what it had seen and is now wrong. Something must be given up.

Collapsing these into one status is how a creature ends up either throwing away working ideas (it
treats "not yet described" as "wrong") or keeping broken ones (it treats "wrong" as "not yet
described"). The two call for opposite repairs, so the report must keep them apart.

WHO IS WRONG?
-------------
A refutation says the examples and the grammar cannot both be right. It does not say which example
lied. `accuse()` removes each example in turn and re-enumerates; every example whose removal
restores a non-empty admissible set is a suspect. This usually returns a SET, and a set is the
honest answer: with four points there is often more than one way to restore consistency, and
picking the observation that "looks wrong" would be guessing in the costume of diagnosis.

WHAT THIS CANNOT DO
-------------------
It cannot tell a lying sensor from a real regime change. An observation the grammar cannot fit is
indistinguishable, from the inside, from a true discontinuity in the world. Repairs are a separate
problem and are not attempted here. `REFUTED` does not mean an observation is false; it means the
observation and the descriptions cannot both be true.

Authority: NONE. Pure Python. No truth is claimed about any answer.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.evidence_demand_v1 import (  # noqa: E402
    PROVISIONAL,
    _normalise_body,
    demand_evidence,
    what_would_settle_it,
)

SCHEMA = "PROJECT_BRAIN_OBSERVATION_REFUTATION_V1"

REFUTED = "REFUTED"
UNRESOLVED = "UNRESOLVED"
DETERMINED = "DETERMINED"


def interrogate(
    params: Sequence[str],
    examples: Sequence[Any],
    oracle: Callable[..., Any],
    *,
    max_steps: int = 5,
    **demand_kwargs: Any,
) -> dict[str, Any]:
    """Ask until one explanation remains, or until the world says something impossible.

    `oracle` is called with the arguments of the question and returns the observed value. It is
    the only source of answers; nothing here computes what the answer "should" be.
    """
    current: list[tuple[tuple[Any, ...], Any]] = [(tuple(a), v) for a, v in examples]
    prior: dict[str, Any] | None = demand_evidence(list(params), list(current), **demand_kwargs)
    trajectory: list[dict[str, Any]] = [_summarise(0, prior, None)]

    for step in range(1, max_steps + 1):
        if prior is None or prior["status"] != PROVISIONAL:
            break
        asked = what_would_settle_it(list(params), prior["admissible"])
        if not asked["queries"]:
            trajectory[-1]["stopped"] = asked.get("residual") or "no question separates the bodies"
            break
        question = list(asked["queries"][0]["args"])
        try:
            answer = oracle(*question)
        except Exception as exc:  # noqa: BLE001
            trajectory[-1]["stopped"] = "the oracle refused the question: %r" % (exc,)
            break
        current.append((tuple(question), answer))

        after = demand_evidence(list(params), list(current), **demand_kwargs)
        entry = _summarise(step, after, question)
        entry["observed"] = answer
        entry["predicted_by_chosen"] = _predict(prior.get("chosen"), list(params), question)
        trajectory.append(entry)

        if after["admissible_count"] == 0:
            # The set was non-empty BEFORE this answer and is empty AFTER it. That is a
            # refutation, not an absence of description, and it must not be softened.
            entry["status"] = REFUTED
            entry["why"] = (
                "the answer is inconsistent with every explanation that was admissible before it "
                "was given; the model and this observation cannot both be true")
            entry["suspects"] = accuse(list(params), list(current),
                                       prior_programs=prior["admissible_count"], **demand_kwargs)
            prior, current = after, current
            break

        prior = after

    final = prior or {}
    refuted = any(row.get("status") == REFUTED for row in trajectory)
    # The status must be REFUTED, not whatever the last `demand_evidence` call returned. Measured:
    # the first version of this function reported `UNRESOLVED` for a contradicted model, because
    # `demand_evidence` sees only the CURRENT example set and an empty set looks identical whether
    # it was never populated or was just emptied. That distinction is HISTORICAL -- it is a fact
    # about what the creature used to believe -- so it cannot be recovered from the data alone and
    # has to be carried by whoever remembers the previous step. That is this function, and the
    # first draft forgot to carry it: the module reproduced the exact defect it was built to fix.
    status = REFUTED if refuted else final.get("status", UNRESOLVED)
    return {
        "schema": SCHEMA,
        "params": list(params),
        "examples": len(current),
        "status": status,
        "explanations": 0 if refuted else final.get("explanation_count", 0),
        "programs": 0 if refuted else final.get("admissible_count", 0),
        "chosen": "" if refuted else _normalise_body(final.get("chosen") or ""),
        "trajectory": trajectory,
        "questions_asked": sum(1 for row in trajectory if row.get("asked_at")),
        "authority": "NONE",
    }


def accuse(
    params: Sequence[str],
    examples: Sequence[Any],
    *,
    prior_programs: int | None = None,
    max_suspects: int = 8,
    **demand_kwargs: Any,
) -> dict[str, Any]:
    """Which observations are candidates for being the wrong one? Drop-one, re-enumerate.

    Returns a SET. With few examples, more than one removal will restore a non-empty admissible
    set, and a single culprit would be a fabrication. `decisive` is true only when exactly one
    example can be blamed.

    When `prior_programs` is given, each suspect is also marked `restores_prior`: removing it
    returns the model to exactly the size it had before the doubtful observation arrived. That is
    a sharper signal than "removal helps", and it is also BIASED -- see the module docstring.
    """
    rows = [(tuple(a), v) for a, v in examples]
    suspects: list[dict[str, Any]] = []
    for index in range(len(rows)):
        reduced = rows[:index] + rows[index + 1:]
        if not reduced:
            continue
        state = demand_evidence(list(params), reduced, **demand_kwargs)
        if state["admissible_count"] == 0:
            continue       # removing this one does not help; it is not a candidate
        suspects.append({
            "index": index,
            "example": [list(rows[index][0]), rows[index][1]],
            "without_it_programs": state["admissible_count"],
            "without_it_explanations": state["explanation_count"],
            "restores_prior": (state["admissible_count"] == prior_programs
                               if prior_programs is not None else None),
        })
    suspects = suspects[:max_suspects]
    restorers = [s for s in suspects if s["restores_prior"]]
    return {
        "suspects": suspects,
        "decisive": len(suspects) == 1,
        "restorers": [s["index"] for s in restorers],
        "why": ("exactly one observation can be blamed" if len(suspects) == 1 else
                "%d observations can each be blamed; naming one would be a guess" % len(suspects)),
        "authority": "NONE",
    }


def _predict(body: str | None, params: list[str], question: Sequence[Any]) -> Any:
    """What the creature's own answer would have predicted at the question's input.

    This is the value the answer is checked against -- so a refutation reports the disagreement,
    not merely that one exists.
    """
    if not body:
        return None
    from canonical.runtime.generalization_check_v1 import _compile_body

    try:
        fn = _compile_body(body, params)
        return fn(*question)
    except Exception:  # noqa: BLE001
        return None


def _summarise(step: int, state: dict[str, Any], question: Sequence[Any] | None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "step": step,
        "examples": state.get("examples"),
        "programs": state.get("admissible_count"),
        "explanations": state.get("explanation_count"),
        "status": state.get("status"),
        "chosen": _normalise_body(state.get("chosen") or ""),
    }
    if question is not None:
        row["asked_at"] = list(question)
    return row


def run() -> dict[str, Any]:
    """The pre-registered measurements in PREREG_OBSERVATION_REFUTATION_20261104_V1.md."""
    x_examples = [((1,), 2.0), ((2,), 4.0), ((3,), 6.0)]

    # R1: a truthful oracle is the same question the harness used to answer for itself.
    truthful = lambda x: 2.0 * x   # noqa: E731 - the world, not the model
    honest = interrogate(["x"], x_examples, truthful)

    # R2: an oracle that returns a value outside the grammar's reach. Not a slightly-off value --
    # one that no admissible body comes near.
    def liar(x: float) -> float:
        return 2.0 * x if x >= 0 else 99.0

    refuting = interrogate(["x"], x_examples, liar)

    # R3: UNRESOLVED without any prior success must stay UNRESOLVED, not REFUTED.
    never_fit = demand_evidence(["x"], [((1,), 5.0), ((0,), 5.0)])

    # R4/R5: who is to blame, and is it a set.
    blame = accuse(["x"], x_examples + [((-3.5,), 99.0)], prior_programs=12)

    # R6 -- the same machinery on a world where NOTHING is lying. The true function is piecewise:
    # 2x for x >= 0, 99 below. The creature saw only points on one branch, so the fourth (correct)
    # observation looks exactly like an error. Restoring the prior means deleting the only evidence
    # of the regime change.
    def piecewise(x: float) -> float:
        return 2.0 * x if x >= 0 else 99.0

    trap = accuse(["x"], x_examples + [((-3.5,), piecewise(-3.5))], prior_programs=12)

    # R6: the same drop-one machinery, but the "bad" observation is the only TRUE one. The world
    # is piecewise (2x for x >= 0, 99 below) and the creature was handed three points that all
    # happen to sit on one branch. Restoring the prior here means deleting the only evidence of the
    # regime change -- the mechanism cannot tell repair from confirmation bias, so this measures
    # that it cannot, rather than asserting that it can.

    findings = [
        {"id": "truthful_oracle_settles_in_one_question",
         "question": "with a truthful oracle does the loop reach DETERMINED in a single question?",
         "questions_asked": honest["questions_asked"], "status": honest["status"],
         "pass": bool(honest["questions_asked"] == 1 and honest["status"] == DETERMINED)},

        {"id": "impossible_answer_is_refuted_not_unresolved",
         "question": "is an answer no admissible body predicts reported as REFUTED?",
         "status": refuting["status"],
         "pass": refuting["status"] == REFUTED},

        {"id": "refutation_does_not_fall_back_to_the_cheapest_body",
         "question": "does a refuted loop keep handing back a body anyway?",
         "reported_chosen": refuting["chosen"],
         "pass": refuting["chosen"] == "" and refuting["programs"] == 0},

        {"id": "the_contradiction_is_located",
         "question": "does the report say what the creature predicted and what it saw?",
         "obs": [r for r in refuting["trajectory"] if r.get("status") == REFUTED][:1],
         "pass": any(r.get("status") == REFUTED
                     and r.get("observed") != r.get("predicted_by_chosen")
                     for r in refuting["trajectory"])},

        {"id": "never_described_stays_unresolved",
         "question": "is a grammar that never fit kept distinct from a contradicted one?",
         "status": never_fit["status"],
         "pass": never_fit["status"] == UNRESOLVED},

        {"id": "blame_is_a_set_not_a_culprit",
         "question": "does drop-one name several suspects rather than invent one?",
         "suspects": [s["index"] for s in blame["suspects"]],
         "decisive": blame["decisive"],
         "pass": len(blame["suspects"]) > 1 and not blame["decisive"]},

        {"id": "the_injected_observation_restores_the_prior_model",
         "question": "is the observation that actually broke the model the one whose removal restores it?",
         "restorers": blame["restorers"],
         "pass": blame["restorers"] == [3]},

        {"id": "restoring_the_prior_is_also_the_confirmation_bias",
         "question": ("when a true observation is the only one that disagrees with the model, does "
                      "the same test try to delete it?"),
         "trap_restorers": trap["restorers"],
         "pass": trap["restorers"] == [3]},

        {"id": "the_injected_observation_is_among_the_suspects",
         "question": "does the set of suspects contain the observation that was actually lying?",
         "suspects": [s["example"][0] for s in blame["suspects"]],
         "pass": any(s["example"][0] == [-3.5] for s in blame["suspects"])},
    ]
    passed = sum(1 for f in findings if f["pass"])
    return {
        "schema": SCHEMA,
        "passed": passed,
        "total": len(findings),
        "findings": findings,
        "runs": {"truthful": honest, "refuting": refuting, "blame": blame},
        "authority": "NONE",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = run()
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True, default=str))
        return 0
    for tri, label in ((doc["runs"]["truthful"], "truthful oracle"),
                       (doc["runs"]["refuting"], "lying oracle")):
        print("%s -> %s after %d question(s), %d explanation(s)" % (
            label, tri["status"], tri["questions_asked"], tri["explanations"]))
        for row in tri["trajectory"]:
            print("   step %d  %-11s programs=%2s explanations=%s%s" % (
                row["step"], row["status"], row["programs"], row["explanations"],
                ("   asked at %s -> saw %s, model said %s" % (
                    row["asked_at"], row.get("observed"), row.get("predicted_by_chosen")))
                if row.get("asked_at") else ""))
    blame = doc["runs"]["blame"]
    print("\nblame: %d suspect(s), decisive=%s -> %s" % (
        len(blame["suspects"]), blame["decisive"], blame["why"]))
    for s in blame["suspects"]:
        print("   candidate %d: %s (without it: %d programs, %d explanations)" % (
            s["index"], s["example"], s["without_it_programs"], s["without_it_explanations"]))
    print("\n%d/%d findings as predicted" % (doc["passed"], doc["total"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
