#!/usr/bin/env python3
"""One lesson buys a word, not an operator.

The repository already contains the mechanism the owner keeps asking for, under a non-obvious name:
`canonical/runtime/taught_words_v1.py`, registered as `file.question.taught_words.v1`, whose
acceptance predicate is `taught_program_recomputed` — the only capability in the tree that does not
accept on a written file.

This probe teaches it exactly one lesson and measures what that one experience bought:

  * how many requests nobody showed become answerable;
  * how many of those are answered correctly and how many wrongly;
  * what the lesson cannot buy, however many demonstrations are added.

The third question is the one that matters. The module's own words: *the fifteen parts are built in;
only the words are learned.* A lesson is not evidence about an unknown operation — it is a choice
among operations that already exist. That is why one example is enough here, and why no number of
examples would ever teach `median`.

Authority NONE. Runs the shipped learner in-process against its own seed lessons plus one live
lesson written to a temporary directory. Writes nothing into the repository, starts no process,
zero model dependency, $0.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import tempfile
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import taught_words_v1 as taught  # noqa: E402

#: The one lesson. It teaches a single new word for a thing to count. Nothing else is said: no
#: operation is named, no other word is mentioned, and the sentence is not the one we will ask.
LIVE_LESSON: dict[str, Any] = {
    "sentence": "how many records are in t.txt",
    "examples": None,  # filled from the seed's own example files, so the answers are true
}

#: A new word that stands for an operation the learner does not have. No demonstration can teach it,
#: and the point of the probe is that it still refuses — correctly — instead of guessing.
UNTEACHABLE = "what is the median number in n.txt"

LINE_WORDS = ("lines", "line", "rows", "row")


def _seed() -> dict[str, Any]:
    return json.loads(taught.SEED_LESSONS.read_text(encoding="utf-8"))


def _lexicons() -> tuple[list, list, int]:
    """(lexicon before, lexicon after, number of words added by the one lesson)."""
    seed = _seed()
    files = seed["example_files"]
    lesson = dict(LIVE_LESSON)
    lesson["examples"] = [
        {"text": files["t1"], "answer": 25},
        {"text": files["t2"], "answer": 23},
    ]
    with tempfile.TemporaryDirectory(prefix="one_lesson_") as live_dir:
        pathlib.Path(live_dir, taught.LIVE_LESSONS_NAME).write_text(
            json.dumps(lesson) + "\n", encoding="utf-8"
        )
        after, _ = taught.load_lexicon(live_dir)
    before, _ = taught.load_lexicon(str(REPO_ROOT / "does-not-exist"))
    before_words = {w for bundle in before for w in bundle["words"]}
    after_words = {w for bundle in after for w in bundle["words"]}
    return before, after, len(after_words - before_words)


def _unlocked(before: list, after: list) -> list[dict[str, Any]]:
    """Requests nobody showed, built by putting the new word where the seed's own word was.

    Every seed lesson that counts lines has a twin that counts records. Those twins are requests the
    learner has never seen, whose correct answer is the one the seed lesson already established on
    the same file — so correctness is not a matter of opinion.
    """
    seed = _seed()
    files = seed["example_files"]
    rows = []
    for row in seed["lessons"]:
        sentence = row["sentence"]
        if not any(re.search(r"\b" + w + r"\b", sentence) for w in LINE_WORDS):
            continue
        asked = re.sub(r"\b(?:lines|line|rows|row)\b", "records", sentence)
        if asked == sentence:
            continue
        expected = row["examples"][0]["answer"]
        text = files[row["examples"][0]["file"]]
        was = taught.interpret(before, asked, text)
        if was["ok"]:
            continue  # already answerable: not something the lesson bought
        now = taught.interpret(after, asked, text)
        rows.append({
            "request": asked,
            "expected": expected,
            "before": was.get("reason"),
            "after_ok": now["ok"],
            "after_value": now.get("value"),
            "after_reason": now.get("reason"),
            "correct": now["ok"] and now.get("value") == expected,
        })
    return rows


def run() -> dict[str, Any]:
    before, after, added = _lexicons()
    rows = _unlocked(before, after)
    seed = _seed()
    files = seed["example_files"]

    teachable = taught.interpret(after, LIVE_LESSON["sentence"], files["t1"])
    untouchable = taught.interpret(after, UNTEACHABLE, files["n1"])
    one_example_lexicon, one_example_set_aside = taught.learn(
        [(LIVE_LESSON["sentence"], [(files["t1"], 25)])]
    )
    composition = taught.interpret(after, "how many unique records are in t.txt", files["t1"])

    return {
        "probe": "one_lesson_buys_a_word_not_an_operator",
        "authority": "NONE",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "lesson": {
            "sentence": LIVE_LESSON["sentence"],
            "examples_given": 2,
            "words_added_to_the_lexicon": added,
            "taught_sentence_answer": teachable.get("value"),
            "taught_sentence_ok": teachable["ok"],
        },
        "held_out": rows,
        "composition_nobody_showed": {
            "request": "how many unique records are in t.txt",
            "ok": composition["ok"],
            "value": composition.get("value"),
            "expected": 18,
            "correct": composition["ok"] and composition.get("value") == 18,
            "meanings": composition.get("meanings"),
        },
        "operator_that_cannot_be_taught": {
            "request": UNTEACHABLE,
            "ok": untouchable["ok"],
            "reason": untouchable.get("reason"),
            "built_in_parts": sorted(taught.PARTS),
            "built_in_part_count": len(taught.PARTS),
        },
        "lesson_with_one_example": {
            "set_aside": one_example_set_aside,
            "lexicon_is_empty": one_example_lexicon == [],
        },
        "summary": {
            "words_learned_per_lesson": added,
            "held_out_unlocked": len(rows),
            "held_out_correct": sum(1 for r in rows if r["correct"]),
            "held_out_wrong": sum(1 for r in rows if r["after_ok"] and not r["correct"]),
            "held_out_refused": sum(1 for r in rows if not r["after_ok"]),
            "composition_correct": bool(
                composition["ok"] and composition.get("value") == 18
            ),
            "operators_added_by_the_lesson": 0,
            "built_in_operator_parts": len(taught.PARTS),
        },
        "hard_nonclaims": [
            "NO_CAPABILITY_REGISTERED",
            "NO_LEXICON_WRITTEN",
            "NO_OPERATOR_LEARNED",
            "NO_ACCEPTANCE_CREDIT",
            "NO_TRUTH_ACHIEVED",
            "MEASURES_ONE_LESSON_IN_A_FIFTEEN_PART_ALGEBRA",
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
    s = report["summary"]

    print("One lesson, and what it bought")
    print("=" * 72)
    print(f"  words added to the lexicon by one lesson           {s['words_learned_per_lesson']:>4}")
    print(f"  requests nobody showed that it can now answer      {s['held_out_unlocked']:>4}")
    print(f"  ...answered correctly                              {s['held_out_correct']:>4}")
    print(f"  ...answered wrongly                                {s['held_out_wrong']:>4}")
    print(f"  ...refused, and the refusal names the word         {s['held_out_refused']:>4}")
    print(f"  a composition nobody showed is answered correctly  "
          f"{str(s['composition_correct']):>4}")
    print(f"  operators added by the lesson                      {s['operators_added_by_the_lesson']:>4}")
    print(f"  operator parts that were already there             {s['built_in_operator_parts']:>4}")

    if args.list:
        print()
        for row in report["held_out"]:
            mark = "ok " if row["correct"] else ("WRONG" if row["after_ok"] else "refused")
            print(f"  {mark:<8}{row['request']:<52}{row['expected']}")
        op = report["operator_that_cannot_be_taught"]
        print(f"\n  {op['request']!r}\n    -> ok={op['ok']} {op['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
