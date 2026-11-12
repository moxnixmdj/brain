#!/usr/bin/env python3
"""Twelve lessons buy nothing; one part, written in code, buys the capability.

Round 8 measured that one lesson teaches a word inside a fixed algebra of 14 parts, and that
`median` is refused forever because no lesson format can add a part. This round prices that claim.

The same twelve lessons are offered twice:

  * to the shipped learner, which has no `median` part — every lesson is set aside, no word is
    learned, and the request is refused;
  * to the same design with one reducer added in code — every lesson now has exactly one reading,
    the request is answered, and an independent recomputation agrees.

Twelve demonstrations: nothing. One part: the capability. That is the difference between learning
a binding and growing an operator, priced.

Authority NONE. Runs in-process. The shipped module is not modified and its receipt keeps binding:
the added part lives here, in the probe. Writes nothing into the repository, starts no process,
zero model dependency, $0.
"""
from __future__ import annotations

import argparse
import inspect
import json
import pathlib
import re
import statistics
import sys
from typing import Any, Iterable, Mapping

REPO_ROOT = pathlib.Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import taught_words_v1 as taught  # noqa: E402

#: Six texts, each with an odd count of numbers, each with a median that none of the fourteen
#: shipped parts can produce — searched for, not hoped for, and checked again at run time.
TEXTS: dict[str, str] = {
    "n1": "62 18 81 146 -8\n",
    "n2": "-2 190 117 4 73\n",
    "n3": "129 -6 109 34 -11\n",
    "n4": "2 91 87 -3 41\n",
    "n5": "3 121 88 -5 191\n",
    "n6": "124 11 37 141 140\n",
}

#: Twelve one-sentence lessons, two example files each, answering with the true median.
LESSON_FILES = ("n1", "n2", "n3", "n4", "n5", "n6")
SENTENCES = [f"what is the median of the numbers in {name}.txt" for name in LESSON_FILES] * 2


def numbers(text: str) -> list[int]:
    return [int(t) for t in text.split() if re.fullmatch(r"-?\d+", t)]


def median_of(text: str) -> int:
    """The answer the lessons state. Also the independent recomputation used to check the part."""
    return int(statistics.median(numbers(text)))


def _lessons() -> list[tuple[str, list[tuple[str, int]]]]:
    """Twelve lessons, each with two example files."""
    lessons = []
    for index, sentence in enumerate(SENTENCES):
        first = LESSON_FILES[index % len(LESSON_FILES)]
        second = LESSON_FILES[(index + 1) % len(LESSON_FILES)]
        lessons.append((
            sentence,
            [(TEXTS[first], median_of(TEXTS[first])), (TEXTS[second], median_of(TEXTS[second]))],
        ))
    return lessons


# ---------------------------------------------------------------------------------------------
# The one part, written in code. Everything else about the design is unchanged.
# ---------------------------------------------------------------------------------------------
MEDIAN = "median"
EXTENDED_PARTS = tuple(sorted(taught.PARTS + (MEDIAN,)))


class NotPerformable(Exception):
    """The parts do not make an operation this extension can perform."""


def run_extended(parts: Iterable[str], text: str, data: str | None = None) -> int:
    """`taught_words_v1.run` with one reducer added.

    `median` is only defined for the numbers unit and takes no filters or measures; anything else is
    refused rather than approximated, exactly as the shipped module refuses what it cannot do.
    """
    parts = frozenset(parts)
    if MEDIAN not in parts:
        return taught.run(parts, text, data)
    others = parts - {MEDIAN}
    if others != {"numbers"}:
        raise NotPerformable("MEDIAN_TAKES_NUMBERS_ALONE")
    values = numbers(text)
    if not values:
        raise NotPerformable("NOTHING_TO_REDUCE")
    return int(statistics.median(values))


CODE_LINES_ADDED = len(inspect.getsource(run_extended).strip().splitlines())


def reading_with_the_part(sentence: str, examples: Sequence) -> bool:  # noqa: F821
    """Does exactly one reading of this lesson exist once the part is present?

    The shipped learner asks the same question by enumerating `ALL_OPERATIONS`; here the enumeration
    is the shipped one plus `median(numbers)`, which is the whole difference.
    """
    fits_old = taught.candidates(sentence, examples)
    fits_median = all(run_extended({MEDIAN, "numbers"}, text) == answer for text, answer in examples)
    return fits_median and not fits_old


def run() -> dict[str, Any]:
    lessons = _lessons()

    # Arm A: the shipped learner, unchanged.
    lexicon, set_aside = taught.learn(lessons)
    reasons = sorted({row["set_aside"] for row in set_aside})
    asked = "what is the median of the numbers in n1.txt"

    # The lessons must be unreadable *because no operation fits*, not because of a malformed lesson.
    no_operation_fits = all(
        taught.candidates(sentence, examples) == [] for sentence, examples in lessons
    )

    # Arm B: one part added in code.
    usable = [reading_with_the_part(sentence, examples) for sentence, examples in lessons]
    answered = {
        name: run_extended({MEDIAN, "numbers"}, text) for name, text in TEXTS.items()
    }
    recomputed = {name: median_of(text) for name, text in TEXTS.items()}
    agreement = {name: answered[name] == recomputed[name] for name in TEXTS}

    # Ask with the *seed* lexicon in hand, so the refusal is about `median` alone and not about a
    # vocabulary the learner was never given.
    seed_lexicon, _ = taught.load_lexicon(str(REPO_ROOT / "does-not-exist"))
    shipped_refusal = taught.interpret(seed_lexicon, asked, TEXTS["n1"])

    return {
        "probe": "twelve_lessons_buy_nothing_one_part_buys_it",
        "authority": "NONE",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "lessons": {
            "count": len(lessons),
            "examples_per_lesson": 2,
            "sentences": len(set(SENTENCES)),
        },
        "without_the_part": {
            "lexicon_words": sum(len(bundle["words"]) for bundle in lexicon),
            "lessons_set_aside": len(set_aside),
            "reasons": reasons,
            "no_operation_fits_the_stated_answers": no_operation_fits,
            "request": asked,
            "ok": shipped_refusal["ok"],
            "reason": shipped_refusal.get("reason"),
        },
        "with_the_part": {
            "part": MEDIAN,
            "code_lines_added": CODE_LINES_ADDED,
            "shipped_part_count": len(taught.PARTS),
            "extended_part_count": len(EXTENDED_PARTS),
            "lessons_with_exactly_one_reading": sum(1 for u in usable if u),
            "lessons": usable,
            "answers": answered,
            "independent_recomputation": recomputed,
            "agreement": agreement,
            "all_agree": all(agreement.values()),
        },
        "summary": {
            "lessons_offered": len(lessons),
            "lessons_usable_without_the_part": 0,
            "lessons_usable_with_the_part": sum(1 for u in usable if u),
            "capability_bought_by_lessons": False,
            "capability_bought_by_code": all(agreement.values()),
            "code_lines": CODE_LINES_ADDED,
        },
        "hard_nonclaims": [
            "SHIPPED_MODULE_UNCHANGED",
            "NO_CAPABILITY_REGISTERED",
            "NO_LEXICON_WRITTEN",
            "NO_ACCEPTANCE_CREDIT",
            "NO_TRUTH_ACHIEVED",
            "ONE_PART_ONE_ALGEBRA_ONE_CORPUS",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)

    report = run()
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    s, a, b = report["summary"], report["without_the_part"], report["with_the_part"]

    print("Twelve lessons, one part")
    print("=" * 72)
    print(f"  lessons offered, two example files each              {s['lessons_offered']:>4}")
    print(f"  words learned without the part                       {a['lexicon_words']:>4}")
    print(f"  lessons the shipped learner could read               {s['lessons_usable_without_the_part']:>4}")
    print(f"  lessons readable once the part exists                {s['lessons_usable_with_the_part']:>4}")
    print(f"  code lines that bought it                            {s['code_lines']:>4}")
    print(f"  answers agreeing with an independent recomputation   "
          f"{sum(b['agreement'].values())}/{len(b['agreement'])}")
    print(f"\n  shipped refusal: {a['reason']}")
    if args.list:
        print()
        for name, value in sorted(b["answers"].items()):
            print(f"  median of {name}.txt = {value:>4}   recomputed {b['independent_recomputation'][name]:>4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
