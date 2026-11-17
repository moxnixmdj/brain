"""The ceiling of "learn it once": what fraction of real work experience can own.

THE CLAIM, AND WHY IT NEEDS A CEILING RATHER THAN AN OPINION
------------------------------------------------------------
The claim under test, for the ninth session in a row:

    "Give the model the most advanced actions, let it experience each once, and it learns them
     permanently -- therefore all computer use and advanced software engineering are solved."

Every part of that has been measured here. Nobody has ever multiplied the parts, and the product is
the only number that answers the question, because the claim is a claim about a fraction of work.

WHAT THE THREE TERMS ARE, AND WHERE EACH WAS MEASURED
-----------------------------------------------------
The program's yield is bounded by three independent measured quantities:

  1. SUPPLY / RECURRENCE -- does the work come back in a form memory can serve?
     `LEARN_ONCE_KEEP_FOREVER_SERVES_A_TWENTIETH_OF_REAL_EDITS_20261116_V1.md`
     691 real changed sites, 5 public repositories, pinned corpus sha256 b47d9c9c.
       loose recurrence 0.2764 -> determinant replay 0.3039  =>  0.0481 end to end
       multi-line (advanced) edits: 0 of 14
       cross-repository, multi-line, strict: 0.021

  2. DETERMINACY -- when a demonstration exists, does it determine the edit?
     `ONE_DEMONSTRATION_AMORTISES_A_SIXTH_OF_REAL_WORK_20261116_V1.md`
     245 sibling pairs: 42.0% verbatim, 12.7% forced, 19.2% lucky, 26.1% wrong.
     On the 142 pairs that genuinely need induction: 54.9% reproduced.

  3. COMPOSITION -- do verified pieces compose into verified work?
     `SKILLS_DONT_COMPOSE_20261112_V1.md`, reproduced live below: two individually crystallised
     skills, each accepted, produce a sequence whose net change is NOTHING.

A ceiling is a product, and a product of measured terms is falsifiable in a way prose is not. If
someone raises recurrence, the ceiling rises by exactly the measured amount; that is the point.

WHAT IS NEW HERE
----------------
Not the terms -- every one is cited from a merged receipt and none is re-measured.
NEW: the product, stated as the ceiling of the whole program; the three-way split of real work into
MEMORISE / SYNTHESISE / REFUSE, derived from the measured terms rather than asserted; and two checks
this session actually ran -- the exact minimal demonstration count (verified against an exact cover
solver, no smaller cover exists) and the composition defect reproduced on the tree's own store.

Authority: NONE. $0. Zero model calls. Arithmetic over receipts that are already on main.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys
import tempfile
from fractions import Fraction
from typing import Any

sys.path.insert(0, "/home/user/brain")

SCHEMA = "THE_CEILING_OF_LEARN_ONCE_20261116_V1"
AUTHORITY = "NONE__PRODUCER_RUN_ARITHMETIC_OVER_MERGED_RECEIPTS"

#: Every term, as the exact fraction the receipt recorded. Fractions, never floats, because a
#: ceiling that has been rounded is not a ceiling.
TERMS: dict[str, dict[str, Any]] = {
    "recurrence_loose": {
        "value": Fraction(191, 691), "as_recorded": "191/691",
        "unit": "share of 691 real changed sites with an earlier same-signature site",
        "receipt": "LEARN_ONCE_KEEP_FOREVER_SERVES_A_TWENTIETH_OF_REAL_EDITS_20261116_V1.md"},
    "recurrence_strict": {
        "value": Fraction(102, 644), "as_recorded": "102/644",
        "unit": "share with one context line on BOTH sides",
        "receipt": "LEARN_ONCE_KEEP_FOREVER_SERVES_A_TWENTIETH_OF_REAL_EDITS_20261116_V1.md"},
    "replay_determinacy_strict": {
        "value": Fraction(31, 102), "as_recorded": "31/102",
        "unit": "share of recurring sites replaying EXACTLY across time",
        "receipt": "LEARN_ONCE_KEEP_FOREVER_SERVES_A_TWENTIETH_OF_REAL_EDITS_20261116_V1.md"},
    "end_to_end_exact": {
        "value": Fraction(31, 644), "as_recorded": "31/644",
        "unit": "sites served exactly by permanent memory, end to end",
        "receipt": "LEARN_ONCE_KEEP_FOREVER_SERVES_A_TWENTIETH_OF_REAL_EDITS_20261116_V1.md"},
    "multi_line_strict_served": {
        "value": Fraction(0, 14), "as_recorded": "0/14",
        "unit": "MULTI-LINE (advanced) edits served exactly by memory",
        "receipt": "LEARN_ONCE_KEEP_FOREVER_SERVES_A_TWENTIETH_OF_REAL_EDITS_20261116_V1.md"},
    "cross_repo_multi_line_strict": {
        "value": Fraction(21, 1000), "as_recorded": "2.1%",
        "unit": "a brand-new repository, multi-line edits, strict context",
        "receipt": "LEARN_ONCE_KEEP_FOREVER_SERVES_A_TWENTIETH_OF_REAL_EDITS_20261116_V1.md"},
    "induction_determinacy": {
        "value": Fraction(78, 142), "as_recorded": "78/142",
        "unit": "pairs that genuinely need induction and are reproduced",
        "receipt": "ONE_DEMONSTRATION_AMORTISES_A_SIXTH_OF_REAL_WORK_20261116_V1.md"},
    "verbatim_share_of_correct": {
        "value": Fraction(103, 245), "as_recorded": "103/245",
        "unit": "share of sibling pairs that are copy-paste, not induction",
        "receipt": "ONE_DEMONSTRATION_AMORTISES_A_SIXTH_OF_REAL_WORK_20261116_V1.md"},
}


def compose_defect() -> dict[str, Any]:
    """Reproduce the composition defect on the tree's own store, live.

    Two rules, each accepted by the crystalliser on its own demonstration. Applied in order they
    return the source text unchanged. A store of N verified skills is therefore not evidence about a
    sequence of two -- and real coding work is a sequence.
    """
    from canonical.swe_kernel import skill_sequence_verify_v1 as S
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

    before = "def f(x):\n    return x <= 10\n"
    forward = "def f(x):\n    return x < 10\n"
    backward_before = "def f(x):\n    return x < 10\n"
    backward = "def f(x):\n    return x <= 10\n"

    scratch = pathlib.Path(tempfile.mkdtemp(prefix="brain_ceiling_")) / "skills.sqlite"
    store = VerifiedSkillStore(db_path=scratch, seed=False)
    accepted = []
    for b, a, err in ((before, forward, "A"), (backward_before, backward, "B")):
        result = store.crystallize_code_fix(before_snippet=b, after_snippet=a,
                                            language="python", error_class=err)
        accepted.append(bool(result.get("crystallized")))
    conn = sqlite3.connect(str(scratch))
    try:
        rules = [json.loads(row[0]) for row in
                 conn.execute("SELECT pattern_json FROM crystallized_skills")]
    finally:
        conn.close()
    outcome = S.verify_sequence(before, rules)
    return {
        "each_rule_accepted_individually": accepted,
        "both_accepted": all(accepted) and len(accepted) == 2,
        "sequence_verdict": outcome["verdict"],
        "sequence_reason": outcome["reason"],
        "net_change_is_nothing": outcome["result"] == outcome["source"],
        "steps": [step["outcome"] for step in outcome["steps"]],
        "reading": ("each rule is verified by the demonstration that taught it; the check is LOCAL, "
                    "so a local check cannot see a global revert. 'N verified skills' is not "
                    "evidence about a sequence of two, and real coding work is a sequence."),
    }


def minimal_demonstration_count() -> dict[str, Any]:
    """The exact minimum number of demonstrations, verified in an earlier action of this session.

    The shipped figures (4 for task A, 1 for task C) came from a GREEDY cover. They are nonetheless
    exact: the tree's own `minimum_policy_cover` enumerates combinations in increasing size, and an
    independent exhaustive search found no smaller cover. That check is recorded, not re-run here,
    because it costs a real git exploration (~55 s) and its result is arithmetic.
    """
    return {
        "task_A": {"greedy": 4, "exact": 4, "smaller_cover_exists": False},
        "task_C": {"greedy": 1, "exact": 1, "smaller_cover_exists": False},
        "uncoverable_task_C": 28,
        "method": ("k6_minimum_adequate_policy_cover_v1.minimum_policy_cover, exact, checked "
                   "against an independent exhaustive search; validity confirmed by mapping the "
                   "returned labels back to plans because _normalize returns reprs, not plans"),
        "reading": ("acquisition is not the constraint. Four experiences, exactly, licence every "
                    "distinguishable situation for task A -- and one for task C. The number of "
                    "experiences needed was never the open question."),
    }


def compute() -> dict[str, Any]:
    end_to_end = TERMS["end_to_end_exact"]["value"]
    served = end_to_end
    rest = 1 - served

    # What the remainder is NOT: it is not "learn more". Multi-line work was served 0 of 14.
    # It is synthesis against a mechanical check -- and where no check exists, refusal.
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "kind": "receipt",
        "incremental_spend_usd": 0,
        "model_calls": 0,
        "network_calls": 0,
        "producer_cognition_model_dependency_count": 0,
        # `str(Fraction(0, 14))` is "0", which silently drops the denominator and would let a
        # "0 of 14" term read back as a bare zero. The exact ratio is carried separately so the
        # denominator survives the round trip.
        "terms": {name: {"value": term["as_recorded"],
                         "exact_ratio": [term["value"].numerator, term["value"].denominator],
                         "approx": round(float(term["value"]), 6),
                         "as_recorded": term["as_recorded"],
                         "unit": term["unit"],
                         "receipt": term["receipt"]} for name, term in TERMS.items()},
        "the_ceiling": {
            "learn_once_serves": str(served),
            "learn_once_serves_approx": round(float(served), 6),
            "percent_of_real_edits": round(float(served) * 100, 3),
            "remainder": str(rest),
            "one_in": round(1 / float(served), 1),
            "the_rest_is": ("synthesis plus a mechanical check, and where no check exists, refusal "
                            "-- not more experience"),
            "advanced_edits_ceiling": "0 of 14 multi-line edits served exactly; 2.1% cross-repository",
        },
        "three_way_split_of_real_work": {
            "MEMORISE": {"share": str(served), "why": "it recurs in a form replay reproduces exactly"},
            "SYNTHESISE": {"share": str(rest - Fraction(0)),
                           "why": ("novel or needs a value the demonstration cannot supply; 31 of 64 "
                                   "wrong predictions were exactly this constant_differs class")},
            "REFUSE": {"share": "unmeasured, and the least honest number in this tree",
                       "why": ("where no mechanical postcondition exists, the correct output is a "
                               "refusal, and this tree has not measured how much real work that is")},
        },
        "whether_learning_rate_is_the_bottleneck": {
            "answer": "NO",
            "why": ("learning rate multiplies a term that is already small. Making acquisition "
                    "infinitely fast leaves the fraction of work that memory can serve unchanged at "
                    "4.81%, because that fraction is a property of the WORK, not of the learner."),
            "what_would_move_it": [
                "raising recurrence (it rises with time in one repository: 0.149 -> 0.394 by "
                "chronological quarter, and saturates under 40% of gross)",
                "raising determinacy on the inductive remainder (54.9% today)",
                "measuring the REFUSE share, which nobody has",
            ],
        },
        "composition_is_a_separate_wall": compose_defect(),
        "acquisition_is_solved": minimal_demonstration_count(),
        "conclusion": (
            "The claim is right about acquisition and wrong about yield. Acquisition is exact: four "
            "experiences licence every distinguishable situation on the measured environment, and "
            "no fewer will do. But one-experience memory serves 4.81% of real edits end to end -- "
            "one in twenty-one -- and 0 of 14 multi-line edits. On top of that, verified pieces do "
            "not compose: two individually accepted skills produce a sequence whose net change is "
            "nothing, and every local check passes both steps. So 'learn each once and everything "
            "is solved' is false by two measured factors, neither of which is learning speed. The "
            "single bottleneck is not how fast the system learns; it is that real work is mostly "
            "not repetition, and that the correctness of a sequence is not implied by the "
            "correctness of its steps."),
        "reused_not_rebuilt": [
            "LEARN_ONCE_KEEP_FOREVER_SERVES_A_TWENTIETH_OF_REAL_EDITS_20261116_V1.md",
            "ONE_DEMONSTRATION_AMORTISES_A_SIXTH_OF_REAL_WORK_20261116_V1.md",
            "SKILLS_DONT_COMPOSE_20261112_V1.md",
            "ONE_DEMONSTRATION_BASIN_20261116_V1.md",
            "canonical/swe_kernel/skill_sequence_verify_v1.py -- verify_sequence, unchanged",
            "canonical/swe_kernel/verified_skill_crystallizer_v1.py -- VerifiedSkillStore, unchanged",
            "canonical/runtime/k6_minimum_adequate_policy_cover_v1.py -- exact cover, unchanged",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    result = compute()
    text = json.dumps(result, indent=1, sort_keys=True)
    if argv:
        pathlib.Path(argv[0]).write_text(text + "\n")
        print("written", argv[0])
    ceiling = result["the_ceiling"]
    print(f"learn-once serves {ceiling['percent_of_real_edits']}% of real edits "
          f"(1 in {ceiling['one_in']})")
    print(f"advanced edits: {ceiling['advanced_edits_ceiling']}")
    comp = result["composition_is_a_separate_wall"]
    print(f"composition: both accepted={comp['both_accepted']} "
          f"verdict={comp['sequence_verdict']} net-nothing={comp['net_change_is_nothing']}")
    acq = result["acquisition_is_solved"]
    print(f"acquisition: task A exact {acq['task_A']['exact']} demos, "
          f"task C exact {acq['task_C']['exact']} demo")
    print("bottleneck: " + result["whether_learning_rate_is_the_bottleneck"]["answer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
