#!/usr/bin/env python3
"""ONE EXPERIENCE BUYS ONE BIT OF IDENTIFICATION. THE PRICE OF A TASK DOES NOT FALL.

The question, in the owner's words: "after he does them at least once, he would learn all of those
permanently... so we solve everything on a computer?"

Every previous answer in this tree measured RATES: one success generalises to ~60-70% of unseen
instances, replay scores ~14-26%, instruction change kills the skill, new task *kind* is 0/10. Rates
answer "how good is the skill". They cannot answer the question that decides the strategy, which is
about COST:

    does experience make the NEXT task cheaper to identify, and if so, does the cost fall?

This module answers it out of numbers the tree already recorded, without a single new episode. The
recorded one-success run (`MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V5.json`) keeps, for every
step of every learned program, `descriptions_left` -- how many descriptions of that element still fit
the one success. That number IS the price of identifying that step, in bits.

MEASURED 2026-11-16 over the 78 tasks that produced a program (175 recorded steps):

    descriptions_left          min 1   median 51   max 255
    mean bits to identify ONE step        5.43
    steps needing more than ONE bit       174 of 175   (99.4%)

So one demonstration buys about one bit. A step costs 5.43. That is the whole claim, and it is not a
judgement about how clever the learner is -- it is the count of what was left undecided.

THE COMPOUNDING QUESTION, AND THE ANSWER THAT SURPRISED THIS ROUND
------------------------------------------------------------------
The obvious hope is that the descriptions are shared, so experience builds a vocabulary and the next
task is cheap. They are shared in part: 149 step-descriptions collapse to 96 distinct (1.55x reuse),
and 28 of those 96 are used by more than one task -- "the button whose text is the quoted word" serves
5 tasks, the submit class serves 6.

But the vocabulary does NOT saturate. Measured as experience accumulates in task order:

    first 39 tasks  -> 43 distinct descriptions
    last  39 tasks  -> 53 MORE (55% of the final 96)

Cost per task stays flat at 1.23 new descriptions. So experience lowers the *price* of a description
it has already paid for, and does not lower the *number* of descriptions a new task needs. The reuse
is real and it is worth 1.55x, and 1.55x is not a mechanism that compounds to zero.

What that means, in one line: **the unit of permanent memory is one bit, a page needs about six of
them, and most of those bits are private to the shape of that page.** That is why no amount of
one-shot experience totals computer use, and it is also why the bits are worth storing -- they are
cheap, permanent, and each one is a real observation rather than a guess.

WHAT THIS MODULE REFUSES
------------------------
It does not claim the 5.43 bits are irreducible: a better description language would lower it, and
that is a separate, real lever (a smaller language is a smaller hypothesis space). It does not treat
the recorded run as its own experiment -- it reads a receipt and says which file and which number.
It refuses to report a compounding claim unless a held-out task's vocabulary is measured BEFORE the
experience that would have helped it, which is why `compounding()` walks the tasks in order and
reports the curve rather than one ratio.

AUTHORITY NONE. No model, no parameters, no reward, $0, no new episodes.
"""
from __future__ import annotations

import json
import math
import pathlib
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_WHAT_ONE_EXPERIENCE_BUYS_V1"
REPO = pathlib.Path(__file__).resolve().parents[2]
RECORDED = REPO / "canonical/verification/MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V5.json"


@dataclass(frozen=True)
class Price:
    """What one step of one task costs to identify, and what one experience pays."""
    steps: int
    descriptions_left: tuple[int, ...]

    @property
    def bits_per_step(self) -> float:
        if not self.steps:
            return 0.0
        return sum(math.log2(d) for d in self.descriptions_left if d > 0) / self.steps

    @property
    def median_left(self) -> int:
        values = sorted(self.descriptions_left)
        return values[len(values) // 2] if values else 0

    @property
    def steps_needing_more_than_one_bit(self) -> int:
        return sum(1 for d in self.descriptions_left if d > 1)

    def as_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "steps": self.steps,
                "bits_per_step": round(self.bits_per_step, 3),
                "median_descriptions_left": self.median_left,
                "max_descriptions_left": max(self.descriptions_left) if self.descriptions_left else 0,
                "steps_needing_more_than_one_bit": self.steps_needing_more_than_one_bit,
                "of_which_share": (round(self.steps_needing_more_than_one_bit / self.steps, 4)
                                   if self.steps else None)}


def _programs(record: Mapping[str, Any]) -> Iterable[tuple[str, list[str]]]:
    """(task, the description chosen for each step) from a recorded run. Order is recorded order."""
    for task in record.get("tasks") or []:
        arms = task.get("arms")
        if not isinstance(arms, Mapping):
            continue
        learning = (arms.get("version_space") or {}).get("learning") or {}
        skills = learning.get("skills") or {}
        for program in skills.get("per_program") or []:
            chosen = [str(step.get("first")) for step in program.get("steps") or []
                      if step.get("first")]
            if chosen:
                yield str(task.get("task")), chosen


def price(record: Mapping[str, Any]) -> Price:
    """The bits one demonstration leaves undecided, over every recorded step."""
    left: list[int] = []
    for task in record.get("tasks") or []:
        arms = task.get("arms")
        if not isinstance(arms, Mapping):
            continue
        learning = (arms.get("version_space") or {}).get("learning") or {}
        for program in (learning.get("skills") or {}).get("per_program") or []:
            for step in program.get("steps") or []:
                value = step.get("descriptions_left")
                if isinstance(value, int) and value > 0:
                    left.append(value)
    return Price(steps=len(left), descriptions_left=tuple(left))


def compounding(record: Mapping[str, Any]) -> dict[str, Any]:
    """Does a task get cheaper as experience accumulates? Measured on the curve, not a ratio.

    A task's OWN descriptions are never counted as available to it -- that would let every task
    pay for itself. What is counted is the vocabulary earned by tasks EARLIER in the recorded order.
    """
    vocabulary: set[str] = set()
    curve: list[int] = []
    shared_with_earlier = 0
    tasks = 0
    per_task_new: list[int] = []
    for _task, chosen in _programs(record):
        own = set(chosen)
        if own & vocabulary:
            shared_with_earlier += 1
        per_task_new.append(len(own - vocabulary))
        vocabulary |= own
        curve.append(len(vocabulary))
        tasks += 1
    if tasks < 2:
        return {"outcome": "TOO_FEW_TASKS"}
    half = curve[len(curve) // 2 - 1]
    second_half_added = curve[-1] - half
    return {
        "schema": SCHEMA,
        "tasks": tasks,
        "distinct_descriptions": curve[-1],
        "reuse_ratio": round(sum(len(c) for _t, c in _programs(record)) / curve[-1], 3),
        "tasks_sharing_a_description_with_an_earlier_task": shared_with_earlier,
        "curve": curve,
        "curve_at_half": half,
        "added_by_the_second_half": second_half_added,
        "share_added_by_the_second_half": round(second_half_added / curve[-1], 3),
        "new_descriptions_per_task": round(sum(per_task_new) / tasks, 3),
        "saturates": second_half_added <= 0.25 * curve[-1],
        "verdict": ("THE_VOCABULARY_KEEPS_GROWING__EXPERIENCE_LOWERS_THE_PRICE_OF_A_DESCRIPTION_"
                    "IT_HAS_ALREADY_PAID_FOR_AND_NOT_THE_NUMBER_A_NEW_TASK_NEEDS"
                    if second_half_added > 0.25 * curve[-1] else
                    "THE_VOCABULARY_SATURATES__A_SMALL_SHARED_LANGUAGE_WOULD_COVER_NEW_TASKS"),
    }


def verdict(record: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The whole answer as one computed object, so it can be cited instead of paraphrased."""
    record = record if record is not None else json.loads(RECORDED.read_text())
    got = price(record)
    curve = compounding(record)
    return {
        "schema": SCHEMA,
        "authority": "NONE__READ_OF_A_RECORDED_RUN_NOT_A_NEW_EXPERIMENT",
        "read_from": str(RECORDED.relative_to(REPO)),
        "what_one_experience_pays": "about one bit, because one success strikes out the descriptions "
                                    "of that element that would have done something else there",
        "what_one_step_costs": got.as_dict(),
        "compounding": curve,
        "the_answer": (
            "One experience is permanent and it is ONE BIT. A step costs several, so a single "
            "demonstration cannot identify a program; that is arithmetic and not a shortcoming of "
            "this learner. Experience does compound -- 1.55x reuse -- and it does not saturate, so a "
            "new task keeps costing about "
            f"{curve.get('new_descriptions_per_task')} descriptions it has never needed before. "
            "Learning therefore lowers the price of what has already been paid for and does not "
            "make a new page cheap. That is why 'try it once everywhere' cannot total computer use, "
            "and why the bits are still worth keeping: each is measured, permanent, and costs no "
            "parameter."),
        "what_would_make_it_cheaper_and_is_a_separate_lever": (
            "a smaller description language. The price is log2 of the descriptions that still fit, "
            "so it is lowered by removing descriptions -- never by seeing more pages."),
    }
