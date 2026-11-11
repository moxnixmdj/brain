#!/usr/bin/env python3
"""A word taught by example answers becomes an ability at the front door, and nothing else changes.

What is pinned here, through ``door.solve`` and under the execution lock:

* a combination of taught words that NO lesson shows is answered by the taught-words row, and the
  door's independent recomputation confirms the value;
* a sentence with one word nobody taught is refused, and the refusal names the word;
* a sentence the usual path answers is never read with taught words (the taught reading comes second);
* a request to change a file is never read as a question;
* one new lesson adds an ability that is still there after the lexicon is loaded again from disk;
* a lesson with one example file, or with a wrong answer, is not kept.

Measured 2026-11-11 on the frozen 32-task file set (96 requests): right answers 13 -> 35 with the
taught-words row, wrong answers 0 -> 0.  See external_probes_20261110/README.md, section P.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime import taught_words_v1 as taught  # noqa: E402

# Seven lines: two blank, three with ERROR, five different.  Five numbers: 500 4 9 9 20.
NOTES = "ERROR disk full\nalpha beta\n\nERROR disk full\ngamma\n\nthe last ERROR line\n"
NUMBERS = "500\n4\n9\n9\n20\n"
WORLD = ROOT / "canonical/astra_runtime/tmp/zqtw_front_door"


def _world() -> str:
    shutil.rmtree(WORLD, ignore_errors=True)
    WORLD.mkdir(parents=True)
    (WORLD / "kx.txt").write_text(NOTES, encoding="utf-8")
    (WORLD / "nb.txt").write_text(NUMBERS, encoding="utf-8")
    return WORLD.relative_to(ROOT).as_posix()


def _ask(sentence: str) -> dict:
    return door.solve({"task_id": "taught_words_front_door", "goal": sentence})


def _value(result: dict):
    answer = result.get("answer")
    return answer.get("value") if isinstance(answer, dict) else answer


def test_a_combination_no_lesson_shows_is_answered_and_recomputed() -> None:
    d = _world()
    try:
        cases = [
            ("how many unique lines are in %s/kx.txt" % d, 5),                     # a lesson sentence
            ("how many unique lines contain ERROR in %s/kx.txt" % d, 2),           # no lesson shows this
            ("how many lines are in %s/kx.txt after the first" % d, 6),            # no lesson shows this
            ("what is the largest number in %s/nb.txt after the first" % d, 20),   # no lesson shows this
            ("how many lines mention ERROR in %s/kx.txt" % d, 3),
            ("add up the numbers in %s/nb.txt" % d, 542),                          # "add" is not a change here
        ]
        for sentence, expected in cases:
            result = _ask(sentence)
            assert result.get("pass") is True, (sentence, result.get("status"))
            assert str(_value(result)) == str(expected), (sentence, _value(result), expected)
            assert result.get("compiled_capability_id") == taught.CAPABILITY_ID, (sentence, result.get("compiled_capability_id"))
            assert (result.get("taught_words_reading") or {}).get("operation"), sentence
        assert (WORLD / "kx.txt").read_text(encoding="utf-8") == NOTES
        assert (WORLD / "nb.txt").read_text(encoding="utf-8") == NUMBERS
    finally:
        shutil.rmtree(WORLD, ignore_errors=True)


def test_a_sentence_with_a_word_nobody_taught_is_refused_and_names_the_word() -> None:
    d = _world()
    try:
        for sentence, word in (("how many lines are not blank in %s/kx.txt" % d, "not"),
                               ("how many lines are in %s/kx.txt yesterday" % d, "yesterday")):
            result = _ask(sentence)
            assert result.get("pass") is not True, (sentence, _value(result))
            assert result.get("compiled_capability_id") != taught.CAPABILITY_ID, sentence
            assert word in str((result.get("taught_words_reading") or {}).get("reason")), (sentence, result.get("taught_words_reading"))
    finally:
        shutil.rmtree(WORLD, ignore_errors=True)


def test_a_sentence_the_usual_path_answers_is_never_read_with_taught_words() -> None:
    kept_request, kept_attempt = door._solve_request, door._answer_from_taught_words
    consulted = []
    door._answer_from_taught_words = lambda request: consulted.append(request) or (None, None)
    try:
        door._solve_request = lambda request: {"pass": True, "status": "USUAL_PATH_ANSWERED", "answer": "usual"}
        result = door.solve({"task_id": "taught_words_ordering", "goal": "how many unique lines are in whatever.txt"})
        assert result.get("pass") is True and result.get("answer") == "usual", result
        assert consulted == [], "the taught reading was consulted for a sentence the usual path answered"
        door._solve_request = lambda request: {"pass": False, "status": "USUAL_PATH_FAILED_AFTER_EXECUTING", "executed": True}
        door.solve({"task_id": "taught_words_ordering", "goal": "how many unique lines are in whatever.txt"})
        assert consulted == [], "the taught reading was consulted after the usual path had executed something"
        door._solve_request = lambda request: {"pass": False, "status": "USUAL_PATH_REFUSED", "executed": False}
        door.solve({"task_id": "taught_words_ordering", "goal": "how many unique lines are in whatever.txt"})
        assert len(consulted) == 1, "a sentence the usual path refused was not offered to the taught reading"
    finally:
        door._solve_request, door._answer_from_taught_words = kept_request, kept_attempt


def test_a_request_to_change_the_file_is_never_read_as_a_question() -> None:
    d = _world()
    try:
        sentence = "delete the blank lines in %s/kx.txt" % d
        reading = taught.read_request(sentence, ROOT)
        assert reading.get("ok") is False and "delete" in str(reading.get("reason")), reading
        result = _ask(sentence)
        assert result.get("compiled_capability_id") != taught.CAPABILITY_ID, result.get("compiled_capability_id")
    finally:
        shutil.rmtree(WORLD, ignore_errors=True)


def test_one_lesson_adds_an_ability_that_is_still_there_after_a_reload() -> None:
    d = _world()
    kept = taught.LIVE_DIR
    live = pathlib.Path(tempfile.mkdtemp(prefix="zqtw_live_"))
    taught.LIVE_DIR = live
    taught._CACHE.clear()
    try:
        sentence = "what is the total of the numbers in %s/nb.txt" % d
        before = _ask(sentence)
        assert before.get("pass") is not True, _value(before)
        assert "total" in str((before.get("taught_words_reading") or {}).get("reason")), before.get("taught_words_reading")
        lesson = taught.teach("what is the total of the numbers in t.txt", [(NUMBERS, 542), ("3\n4\n", 7)])
        assert lesson.get("taught") is True and lesson.get("words_now_known") == {"total": ["sum"]}, lesson
        taught._CACHE.clear()                       # nothing is kept in memory: the next answer comes from disk
        after = _ask(sentence)
        assert after.get("pass") is True, after.get("status")
        assert str(_value(after)) == "542", _value(after)
        assert after.get("compiled_capability_id") == taught.CAPABILITY_ID
        # the new word combines with a word from an earlier lesson, in a sentence nobody showed
        combined = _ask("what is the total of the numbers in %s/nb.txt after the first" % d)
        assert combined.get("pass") is True and str(_value(combined)) == "42", (combined.get("status"), _value(combined))
        still = _ask("how many unique lines are in %s/kx.txt" % d)   # what was known before is still known
        assert still.get("pass") is True and str(_value(still)) == "5", (still.get("status"), _value(still))
    finally:
        taught.LIVE_DIR = kept
        taught._CACHE.clear()
        shutil.rmtree(live, ignore_errors=True)
        shutil.rmtree(WORLD, ignore_errors=True)


def test_a_lesson_with_one_file_or_a_wrong_answer_is_not_kept() -> None:
    live = pathlib.Path(tempfile.mkdtemp(prefix="zqtw_live_"))
    try:
        one = taught.teach("what is the size of t.txt", [(NOTES, len(NOTES.encode("utf-8")))], live_dir=live)
        assert one.get("taught") is False and one.get("reason") == "TWO_EXAMPLE_FILES_NEEDED", one
        wrong = taught.teach("how many lines are in t.txt", [(NOTES, 8), (NUMBERS, 6)], live_dir=live)
        assert wrong.get("taught") is False, wrong
        blur = taught.teach("what is the size in bytes of t.txt", [(NOTES, len(NOTES.encode("utf-8"))), ("caf\u00e9\n", 6)], live_dir=live)
        assert blur.get("taught") is False and "byte" in str(blur.get("reason")), blur
        assert not (live / taught.LIVE_LESSONS_NAME).exists()
    finally:
        taught._CACHE.clear()
        shutil.rmtree(live, ignore_errors=True)


def main() -> int:
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("ok  ", name)
        except Exception as exc:  # noqa: BLE001 - report every test
            failed += 1
            print("FAIL", name + ":", repr(exc)[:400])
    print("%d/%d passed" % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
