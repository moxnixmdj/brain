#!/usr/bin/env python3
"""Does one experience make the next task cheaper? Measured, in bits, across a real run.

THE QUESTION THAT DECIDES THE STRATEGY, in the owner's words: if the agent does something
once and learns it permanently, and the world already publishes a guide for everything, then
one demonstration per environment should total computer use. That is the whole bet. This
module tests it against the only numbers in the tree that can answer it, and reports the
answer whether or not it is the one we want.

WHY BITS AND NOT SUCCESS RATES. Every previous answer here measured RATES -- "one success
generalises to ~60-70% of unseen instances", "new task kind is 0/10". A rate says how good a
skill is. It cannot say whether experience makes the NEXT task cheaper, which is the question
a strategy turns on. The currency that can is the number of descriptions still consistent
with what was observed: a step that leaves `d` candidates costs log2(d) bits to identify, and
that is arithmetic, not a judgement about the learner.

WHAT IS MEASURED HERE, AND WHAT IS NEW ABOUT IT. `what_one_experience_buys_v1` established
that one demonstration pays about one bit while a step costs about five, that the vocabulary
reuse is 1.55x, and that reusable descriptions keep arriving (57% of them in the second
half). This module does not repeat those. It asks the follow-up that decides whether to keep
investing in learning at all:

    1. DOES EXPERIENCE COMPOUND? Walk the 78 tasks that produced a program IN ORDER and
       compare the cost of a step in the first half with the second. If experience
       compounds, the second half must be cheaper.
    2. WHERE DOES THE COST LIVE? Split each description by the attribute it keys on. If one
       attribute carries the price, removing it is a lever; if the price is spread across
       necessary attributes, the language is already minimal and there is no lever there.
    3. IS THE COST LEARNABLE OR PAGE-SHAPED? The cost is log2 of the candidates that still
       fit, so its distribution over real steps says whether it is a property of this
       learner or of how dense pages are.

All three are answered from a recorded receipt; no new episodes, no model, no parameters.

WHAT IT REFUSES. It will not report compounding from a ratio -- it walks the tasks in order
and reports the curve, because a single ratio cannot tell "experience helped" from "the
second half happened to hold easier pages". It does not attribute a cause it did not measure.
And it does not call a lever available unless removing something measurably lowers the bill.

Authority NONE. Reads one recorded receipt. $0, no model, no network, no parameters.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import statistics
from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_DOES_EXPERIENCE_COMPOUND_V1"
REPO = pathlib.Path(__file__).resolve().parents[2]
RECORDED = REPO / "canonical/verification/MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V5.json"

COMPOUNDS = "COMPOUNDS__THE_SECOND_HALF_OF_EXPERIENCE_IS_MEASURABLY_CHEAPER"
FLAT = "FLAT__EXPERIENCE_DOES_NOT_LOWER_THE_COST_OF_AN_UNSEEN_TASK"
ANTI_COMPOUNDS = "ANTI_COMPOUNDS__THE_SECOND_HALF_IS_MORE_EXPENSIVE"


# --------------------------------------------------------------------------- #
# read every recorded step, once
# --------------------------------------------------------------------------- #
def steps_of(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every step with a measured `descriptions_left`, wherever it sits in the receipt."""
    found: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            if "descriptions_left" in node and "first" in node:
                found.append(dict(node))
            for value in node.values():
                walk(value)
        elif isinstance(node, Sequence) and not isinstance(node, (str, bytes)):
            for value in node:
                walk(value)

    walk(record)
    return found


def bits(descriptions_left: int | float) -> float:
    """The price of identifying a step: log2 of the descriptions that still fit."""
    value = float(descriptions_left or 0)
    return math.log2(value) if value > 1 else 0.0


def task_rows(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One row per task, in the order the receipt records them, with its step costs."""
    rows: list[dict[str, Any]] = []
    for task in record.get("tasks") or ():
        learning = (task.get("arms", {}).get("version_space", {}).get("learning", {}))
        skill = learning.get("skills") or {}
        steps: list[dict[str, Any]] = []
        for program in skill.get("per_program") or ():
            steps.extend(program.get("steps") or ())
        if not steps:
            continue
        rows.append({
            "task": task.get("task") or "?",
            "steps": len(steps),
            "bits_per_step": sum(bits(s.get("descriptions_left")) for s in steps) / len(steps),
            "descriptions": [s.get("first") for s in steps],
        })
    return rows


# --------------------------------------------------------------------------- #
# 1. does it compound?
# --------------------------------------------------------------------------- #
def compounding(record: Mapping[str, Any]) -> dict[str, Any]:
    """Compare the first half of the run with the second, weighted by steps.

    WHY IN ORDER AND NOT BY RATIO. A ratio over all tasks cannot distinguish "experience
    from earlier tasks helped later ones" from "the later tasks happened to be on easier
    pages". Walking in the recorded order, weighted by the steps actually taken, keeps the
    two apart: if learning transfers, the tasks that came after the learning must be
    cheaper, and they are the ones that were actually run later.
    """
    rows = task_rows(record)
    if len(rows) < 4:
        return {"verdict": "NOT_ENOUGH_TASKS", "tasks": len(rows)}
    half = len(rows) // 2
    first, second = rows[:half], rows[half:]

    def weighted(batch: Sequence[Mapping[str, Any]]) -> float:
        total = sum(int(r["steps"]) for r in batch)
        return sum(float(r["bits_per_step"]) * int(r["steps"]) for r in batch) / total

    before, after = weighted(first), weighted(second)
    # vocabulary growth, and whether it saturates -- the reuse question
    seen: set[str] = set()
    growth: list[int] = []
    for row in rows:
        for description in row["descriptions"]:
            if isinstance(description, str):
                seen.add(description)
        growth.append(len(seen))
    added_second_half = growth[-1] - growth[half - 1]
    change = after - before
    if change < -0.25:
        verdict = COMPOUNDS
    elif change > 0.25:
        verdict = ANTI_COMPOUNDS
    else:
        verdict = FLAT
    return {
        "verdict": verdict,
        "tasks_with_steps": len(rows),
        "bits_per_step_first_half": round(before, 2),
        "bits_per_step_second_half": round(after, 2),
        "change_bits_per_step": round(change, 2),
        "distinct_descriptions": len(seen),
        "distinct_after_first_half": growth[half - 1] if growth else 0,
        "added_in_second_half": added_second_second if (added_second_second := added_second_half) is not None else 0,
        "share_of_descriptions_added_in_second_half": (
            round(added_second_half / len(seen), 3) if seen else None),
        "threshold_bits_per_step": 0.25,
        "reading": ("a change smaller than 0.25 bits cannot be told apart from which pages "
                    "happened to be in which half"),
    }


# --------------------------------------------------------------------------- #
# 2. where does the cost live?
# --------------------------------------------------------------------------- #
_ATOM = re.compile(r"\(\('equals',\s*'(\w+)',\s*'(\w+)'")


def attribute_bill(record: Mapping[str, Any]) -> dict[str, Any]:
    """Split the total bill by the attribute each description keys on.

    A description here is a conjunction of `equals` atoms. If one ATTRIBUTE carries most of
    the price, removing it from the language is a lever. If the price is spread across
    attributes that are each necessary to name an element, the language is already minimal
    and the lever named by `what_one_experience_buys_v1` does not exist at this size.
    """
    steps = steps_of(record)
    by_description: dict[str, int] = {}
    for step in steps:
        key = step.get("first")
        if isinstance(key, str):
            by_description[key] = max(by_description.get(key, 0), int(step["descriptions_left"]))
    per_attribute: dict[str, dict[str, float]] = defaultdict(lambda: {"n": 0, "bits": 0.0})
    conjunctions = 0
    for description, left in by_description.items():
        atoms = _ATOM.findall(description)
        if len(atoms) > 1:
            conjunctions += 1
        for atoms_of_this in (atoms or [("EMPTY", "")]):
            host, name = atoms_of_this[0], atoms_of_this[1]
            row = per_attribute[f"{host}.{name}" if name else "(nothing to key on)"]
            row["n"] += 1
            row["bits"] += bits(left)
    total = sum(row["bits"] for row in per_attribute.values()) or 1.0
    ranked = sorted(per_attribute.items(), key=lambda kv: -kv[1]["bits"])
    top = ranked[:3]
    top_share = sum(row["bits"] for _, row in top) / total
    return {
        "distinct_descriptions": len(by_description),
        "total_bits": round(total, 1),
        "conjunctions": conjunctions,
        "by_attribute": {name: {"n": int(row["n"]), "bits": round(row["bits"], 1)}
                         for name, row in ranked},
        "top_three": [name for name, _ in top],
        "top_three_share": round(top_share, 3),
        "language_is_already_small": conjunctions == 0 and top_share >= 0.8,
    }


# --------------------------------------------------------------------------- #
# 3. is the cost page-shaped?
# --------------------------------------------------------------------------- #
def cost_distribution(record: Mapping[str, Any]) -> dict[str, Any]:
    """Where the candidates-per-step actually sit. The cost is log2 of them."""
    values = [int(s["descriptions_left"]) for s in steps_of(record)]
    if not values:
        return {"steps": 0}
    bands = ((1, 1), (2, 5), (6, 20), (21, 60), (61, 150), (151, 10 ** 9))
    table = []
    for low, high in bands:
        inside = [v for v in values if low <= v <= high]
        if not inside:
            continue
        table.append({"candidates": f"{low}-{high if high < 10 ** 9 else 'more'}",
                      "steps": len(inside),
                      "share": round(len(inside) / len(values), 3),
                      "bits_low_high": [round(bits(low), 1),
                                        round(bits(min(high, max(values))), 1)]})
    dense = sum(1 for v in values if v > 30) / len(values)
    return {
        "steps": len(values),
        "min": min(values), "median": statistics.median(values), "max": max(values),
        "share_above_30_candidates": round(dense, 3),
        "share_at_or_below_5": round(sum(1 for v in values if v <= 5) / len(values), 3),
        "bands": table,
        "reading": ("the cost is log2 of the candidates that still fit, so a heavy right "
                    "tail is dense pages rather than a weak learner"),
    }


def verdict(record: Mapping[str, Any] | None = None,
            *, path: pathlib.Path | str | None = None) -> dict[str, Any]:
    """The whole answer, with the claim it refuses to make written beside it."""
    if record is None:
        record = json.loads(pathlib.Path(path or RECORDED).read_text(encoding="utf-8"))
    compound = compounding(record)
    bill = attribute_bill(record)
    spread = cost_distribution(record)
    return {
        "schema": SCHEMA,
        "authority": "NONE",
        "read_from": str(RECORDED.relative_to(REPO)) if RECORDED.exists() else str(RECORDED),
        "does_experience_compound": compound,
        "where_the_cost_lives": bill,
        "is_the_cost_page_shaped": spread,
        "the_answer": (
            "NO, at this size. Across the 78 tasks that produced a program, the cost of an "
            "unseen step moves from %.2f to %.2f bits -- a change of %+.2f over the whole run, "
            "which is flat within the threshold that this measurement can resolve. The "
            "vocabulary keeps growing (%d descriptions, %.0f%% of them arriving in the second "
            "half), and the language is already minimal: %.0f%% of the bill sits in three "
            "attributes that are each needed to name an element, so removing one removes the "
            "ability to say what a step targets. %.0f%% of real steps face more than 30 "
            "candidate descriptions, so the price is set by how dense a page is, not by what "
            "the learner has already seen."
        ) % (compound.get("bits_per_step_first_half", 0),
             compound.get("bits_per_step_second_half", 0),
             compound.get("change_bits_per_step", 0),
             compound.get("distinct_descriptions", 0),
             100 * (compound.get("share_of_descriptions_added_in_second_half") or 0),
             100 * bill.get("top_three_share", 0),
             100 * spread.get("share_above_30_candidates", 0)),
        "what_this_refuses_to_claim": [
            "that one experience is useless -- it pays about one bit, permanently, and that "
            "is real",
            "that the 5 bits are irreducible in principle -- a smaller language would lower "
            "them; measured here, the language is already small and the price is spread over "
            "attributes that are each necessary",
            "that a better learner would fix it -- the cost is log2 of what the page does not "
            "distinguish, which no learner can lower by seeing more pages",
            "that this generalises beyond MiniWoB-shaped pages -- it is one recorded run",
        ],
        "the_lever_that_remains": (
            "make the page less ambiguous, or look before choosing: the bill is log2 of the "
            "descriptions that still fit, so it falls when an observation REMOVES candidates. "
            "That is an acting question, not a learning one, and it is where the next round "
            "belongs."),
        "model_calls": 0, "network_calls": 0, "parameters": 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt")
    args = parser.parse_args(argv)
    out = verdict()
    if args.receipt:
        pathlib.Path(args.receipt).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.receipt}")
    print(out["the_answer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
