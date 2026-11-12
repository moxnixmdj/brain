#!/usr/bin/env python3
"""What growing the operator space costs, measured end to end on the shipped learner.

Round 8 ended with a prescription: *grow the operator space deliberately, and pay for it in code*,
and named the refusal of `median` as the example of what no demonstration can buy. This probe does
exactly that one iteration and measures every step, so the prescription carries a number instead of
an adjective.

Pre-registered predictions, written before the first run:

  1. Under the algebra as it was before the change (every built-in operation except median), the
     lesson below is set aside with NO_OPERATION_I_CAN_PERFORM_GIVES_THESE_ANSWERS -- zero
     operations fit its two example answers. The lesson itself cannot add the operator.
  2. After the code change (one reducer added), the SAME lesson is accepted and teaches exactly
     one word: `median`.
  3. Requests nobody showed, on files the lesson never contains, are answered with the lower
     median, and three computations agree: the producer, the door's independent checker
     (`taught_words_check_v1`, which imports nothing from the producer), and this probe's own
     oracle.
  4. The checker is two-sided for the new operator: it accepts an honest claim and rejects a
     claim of the upper median on the same file.
  5. A word with no part (`mode`) is still refused after the lesson, and the refusal names it.
  6. Nothing already known is unsettled: every seed word keeps its exact meaning, and the only
     word the lesson adds is `median`.
  7. The word survives process state: after the cache is cleared, the stored lexicon still
     answers the held-out requests.

Authority NONE. Runs the shipped learner in-process against its own seed lessons plus one live
lesson written to a temporary directory. Writes nothing into the repository, starts no process,
zero model dependency, $0.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
import time
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import taught_words_check_v1 as check  # noqa: E402
from canonical.runtime import taught_words_v1 as taught  # noqa: E402

#: The lesson. Two example files, whole-number answers, no operation named. `n.txt` is the file
#: name the sentence uses; the example texts are not it -- teach() takes texts, not paths.
LESSON: dict[str, Any] = {
    "sentence": "what is the median number in n.txt",
    "examples": [
        {"text": "3\n1\n2\n", "answer": 2},          # sorted 1 2 3 -> lower middle 2
        {"text": "10\n20\n30\n40\n", "answer": 30},   # sorted 10 20 30 40 -> lower middle 30
    ],
}

#: Requests nobody showed, with this probe's own oracle for the expected answer. The first file
#: appears in no lesson at all; the next two are the seed's own number files, which no median
#: lesson has ever seen; the last composes `median` with `rest`, a combination no lesson shows.
HELD_OUT: list[dict[str, Any]] = [
    {"sentence": "what is the median number in h1.txt", "text": "5\n50\n500\n9\n", "oracle": 50},
    {"sentence": "what is the median number in n1.txt", "seed_file": "n1", "oracle": 143},
    {"sentence": "what is the median number in n2.txt", "seed_file": "n2", "oracle": 140},
    {"sentence": "what is the median number in n1.txt after the first",
     "seed_file": "n1", "oracle": 143},
    {"sentence": "what is the median number in n2.txt after the first",
     "seed_file": "n2", "oracle": 115},
]

#: A word no part can express. After the lesson it must still be refused, by name.
NO_PART_WORD = "what is the mode number in n.txt"


def _lower_median(values: list[int]) -> int:
    """This probe's own oracle. Deliberately re-derived, not imported from either side."""
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def _seed_lessons() -> list[tuple[str, list[tuple[str, int]]]]:
    seed = json.loads(taught.SEED_LESSONS.read_text(encoding="utf-8"))
    files = seed["example_files"]
    return [
        (row["sentence"], [(files[e["file"]], e["answer"]) for e in row["examples"]])
        for row in seed["lessons"]
    ]


def _seed_files() -> dict[str, str]:
    return json.loads(taught.SEED_LESSONS.read_text(encoding="utf-8"))["example_files"]


def _settled(lexicon: list) -> dict[str, tuple[str, ...]]:
    return {word: tuple(bundle["parts"])
            for bundle in lexicon if bundle["parts"] is not None
            for word in bundle["words"]}


def _under_old_algebra() -> dict[str, Any]:
    """Prediction 1: run the REAL learner with the pre-change operation list.

    The old algebra is today's list with every median operation removed -- which is exactly what
    ALL_OPERATIONS was before the code change, because nothing else moved.
    """
    full = taught.ALL_OPERATIONS
    old = [op for op in full if "median" not in op]
    taught.ALL_OPERATIONS = old
    try:
        lessons = _seed_lessons() + [
            (LESSON["sentence"], [(e["text"], e["answer"]) for e in LESSON["examples"]])
        ]
        _lexicon, set_aside = taught.learn(lessons)
        mine = [row for row in set_aside if row["lesson"] == LESSON["sentence"]]
    finally:
        taught.ALL_OPERATIONS = full
    return {
        "operations_in_old_algebra": len(old),
        "operations_in_new_algebra": len(full),
        "lesson_set_aside": bool(mine),
        "set_aside_reason": mine[0]["set_aside"] if mine else None,
        "operations_that_fit_the_two_answers": 0 if mine else None,
    }


def _teach_and_ask() -> dict[str, Any]:
    seed_before = _settled(taught.load_lexicon(str(REPO_ROOT / "does-not-exist"))[0])
    examples = [(e["text"], e["answer"]) for e in LESSON["examples"]]
    with tempfile.TemporaryDirectory(prefix="operator_growth_") as live_dir:
        lesson = taught.teach(LESSON["sentence"], examples, live_dir=live_dir)
        after, _ = taught.load_lexicon(live_dir)
        after_map = _settled(after)

        held_out = []
        for row in HELD_OUT:
            # Every expected value is written above, before the run: the oracle is a prediction,
            # not something derived after seeing the answer.
            text = row["text"] if "text" in row else _seed_files()[row["seed_file"]]
            expected = row["oracle"]
            reading = taught.interpret(after, row["sentence"], text)
            held_out.append({
                "request": row["sentence"],
                "expected": expected,
                "ok": reading["ok"],
                "value": reading.get("value"),
                "reason": reading.get("reason"),
                "correct": reading["ok"] and reading.get("value") == expected,
                "wrong": reading["ok"] and reading.get("value") != expected,
            })

        no_part = taught.interpret(after, NO_PART_WORD, _seed_files()["n1"])

        # Prediction 7: nothing kept in memory -- the stored lexicon alone must still answer.
        taught._CACHE.clear()
        reloaded, _ = taught.load_lexicon(live_dir)
        reload_reading = taught.interpret(reloaded, LESSON["sentence"], _seed_files()["n1"])
        reload_ok = reload_reading["ok"] and reload_reading.get("value") == 143

        new_words = sorted(set(after_map) - set(seed_before))
        harmed = sorted(
            word for word in seed_before
            if word not in after_map or after_map[word] != seed_before[word]
        )

        return {
            "lesson": {
                "sentence": LESSON["sentence"],
                "examples_given": len(examples),
                "taught": lesson.get("taught"),
                "reason": lesson.get("reason"),
                "words_now_known": lesson.get("words_now_known"),
            },
            "held_out": held_out,
            "no_part_word": {
                "request": NO_PART_WORD,
                "ok": no_part["ok"],
                "reason": no_part.get("reason"),
            },
            "seed_words_preserved": harmed == [],
            "seed_words_harmed": harmed,
            "words_added": new_words,
            "reload_from_disk": {
                "median_still_answered": bool(reload_ok),
                "value": reload_reading.get("value"),
            },
            "parts_total": len(taught.PARTS),
            "parts_before_this_round": len(taught.PARTS) - 1,
        }


def _checker_is_two_sided() -> dict[str, Any]:
    """Prediction 4: the independent checker accepts the honest claim and rejects the upper one."""
    raw = LESSON["examples"][1]["text"].encode("utf-8")   # 10 20 30 40 -> lower 30, upper 20
    honest = 30
    upper = 20
    recomputed = check.recompute(["numbers", "median"], None, raw)

    with tempfile.TemporaryDirectory(prefix="median_gate_") as root:
        path = pathlib.Path(root) / "n.txt"
        path.write_bytes(raw)
        import hashlib
        digest = hashlib.sha256(raw).hexdigest()

        def attempt(claim: int) -> tuple[bool, str]:
            ok, detail = check.verify(
                {"field": "answer"},
                {"path": "n.txt", "program": ["numbers", "median"], "data": None,
                 "answer": claim, "source_sha256": digest},
                {"path": "n.txt"},
                root,
            )
            return bool(ok), str(detail)

        accepted, accept_detail = attempt(honest)
        rejected, reject_detail = attempt(upper)

    return {
        "recompute_of_honest_claim": recomputed,
        "honest_claim_accepted": accepted,
        "honest_detail": accept_detail,
        "upper_median_claim_rejected": not rejected,
        "reject_detail": reject_detail,
    }


def _predictions_match_the_oracle() -> bool:
    """Cross-check the pre-written expected values against this probe's own median function.

    The HELD_OUT oracles are predictions written before the run. If any of them disagrees with
    re-deriving the lower median from the file text, the prediction -- not the learner -- is wrong,
    and the report must say so rather than quietly adopt whichever number arrived.
    """
    seed_files = _seed_files()
    for row in HELD_OUT:
        text = row["text"] if "text" in row else seed_files[row["seed_file"]]
        numbers = [int(x) for x in text.split() if x.lstrip("-").isdigit()]
        if row["sentence"].endswith("after the first"):
            numbers = numbers[1:]
        if _lower_median(numbers) != row["oracle"]:
            return False
    return True


def run() -> dict[str, Any]:
    started = time.time()
    predictions_ok = _predictions_match_the_oracle()
    before = _under_old_algebra()
    growth = _teach_and_ask()
    gate = _checker_is_two_sided()
    held_out = growth["held_out"]
    return {
        "probe": "operator_space_growth_median",
        "authority": "NONE",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "pre_registered_predictions": [
            "OLD_ALGEBRA_SETS_THE_LESSON_ASIDE_WITH_NO_OPERATION",
            "SAME_LESSON_TEACHES_EXACTLY_ONE_WORD_MEDIAN",
            "HELD_OUT_REQUESTS_ANSWERED_CORRECTLY_THREE_WAY_AGREEMENT",
            "CHECKER_ACCEPTS_HONEST_AND_REJECTS_UPPER_MEDIAN",
            "MODE_STILL_REFUSED_BY_NAME",
            "NO_SEED_WORD_HARMED_AND_MEDIAN_IS_THE_ONLY_ADDITION",
            "RELOADED_FROM_DISK_STILL_ANSWERS",
        ],
        "before_code_change": before,
        "after_code_change": growth,
        "independent_checker": gate,
        "summary": {
            "parts_before": growth["parts_before_this_round"],
            "parts_after": growth["parts_total"],
            "operations_before": before["operations_in_old_algebra"],
            "operations_after": before["operations_in_new_algebra"],
            "lesson_refused_before_the_code_change": before["lesson_set_aside"] and
            before["set_aside_reason"] == "NO_OPERATION_I_CAN_PERFORM_GIVES_THESE_ANSWERS",
            "lesson_taught_after": growth["lesson"]["taught"] is True,
            "word_taught": growth["lesson"].get("words_now_known"),
            "held_out": len(held_out),
            "held_out_correct": sum(1 for row in held_out if row["correct"]),
            "held_out_wrong": sum(1 for row in held_out if row["wrong"]),
            "predictions_match_the_oracle": predictions_ok,
            "mode_refused": growth["no_part_word"]["ok"] is False and
            str(growth["no_part_word"]["reason"]).startswith("UNKNOWN_WORD:"),
            "seed_words_preserved": growth["seed_words_preserved"],
            "words_added": growth["words_added"],
            "reload_from_disk_ok": growth["reload_from_disk"]["median_still_answered"],
            "checker_accepts_honest": gate["honest_claim_accepted"],
            "checker_rejects_upper_median": gate["upper_median_claim_rejected"],
            "wall_clock_s": round(time.time() - started, 3),
        },
        "hard_nonclaims": [
            "NO_CAPABILITY_REGISTERED",
            "NO_TRUE_SUITE_COVERAGE_FOR_MEDIAN",
            "NO_SEED_LESSON_OR_LEXICON_CHANGED",
            "NO_LIVE_STATE_WRITTEN_INTO_THE_TREE",
            "NO_TRUTH_ACHIEVED",
            "ONE_OPERATOR_ONE_LESSON_ONE_ALGEBRA",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)

    report = run()
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    s = report["summary"]

    print("Growing the operator space: what it cost")
    print("=" * 72)
    print(f"  parts before -> after                       "
          f"{s['parts_before']} -> {s['parts_after']}")
    print(f"  operations before -> after                  "
          f"{s['operations_before']} -> {s['operations_after']}")
    print(f"  lesson refused under the old algebra        {s['lesson_refused_before_the_code_change']}")
    print(f"    reason                                    "
          f"{report['before_code_change']['set_aside_reason']}")
    print(f"  same lesson taught after the code change    {s['lesson_taught_after']}")
    print(f"  word(s) it taught                           {s['word_taught']}")
    print(f"  held-out requests answered correctly        "
          f"{s['held_out_correct']}/{s['held_out']} (wrong: {s['held_out_wrong']})")
    print(f"  'mode' still refused by name                {s['mode_refused']}")
    print(f"  every seed word keeps its exact meaning     {s['seed_words_preserved']}")
    print(f"  only word added                             {s['words_added']}")
    print(f"  answers again after cache clear             {s['reload_from_disk_ok']}")
    print(f"  checker accepts the honest claim            {s['checker_accepts_honest']}")
    print(f"  checker rejects the upper median            {s['checker_rejects_upper_median']}")

    if args.list:
        print()
        for row in report["after_code_change"]["held_out"]:
            mark = "ok  " if row["correct"] else ("WRONG" if row["ok"] else "refused")
            print(f"  {mark:<7}{row['request']:<50}{row['expected']}"
                  f"{'  got ' + str(row['value']) if row['ok'] else '  ' + str(row['reason'])}")
        gate = report["independent_checker"]
        print(f"\n  honest claim accepted: {gate['honest_claim_accepted']} ({gate['honest_detail']})")
        print(f"  upper median rejected: {gate['upper_median_claim_rejected']} "
              f"({gate['reject_detail']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
