"""Growing the operator space is a code change; the lesson then buys the word, measured.

What is pinned here, from `operator_space_growth_median_20261112.py` running the shipped learner:

  * under the pre-change algebra the median lesson is set aside -- no operation fits its two
    example answers, so no number of demonstrations could have taught it;
  * after one reducer is added in code, the SAME lesson teaches exactly one word, `median`;
  * five held-out requests nobody showed -- including a composition with `rest` -- are answered
    correctly and none wrongly, against expected values written down before the run;
  * the independent checker (no shared code with the producer) accepts an honest median claim and
    rejects the upper median on the same file;
  * `mode` still has no part and is still refused by name;
  * no seed word changes meaning, the cache can be cleared and the word survives, the front door
    answers a median question through its own recomputation gate, and nothing is written into the
    repository's live state.

The numbers are the point: 14 -> 15 parts, 400 -> 560 operations, one lesson, five answers.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from operator_space_growth_median_20261112 import (  # noqa: E402
    HELD_OUT,
    LESSON,
    NO_PART_WORD,
    run,
)

from canonical.runtime import taught_words_check_v1 as check  # noqa: E402
from canonical.runtime import taught_words_v1 as taught  # noqa: E402

_CACHE: dict = {}


def _report() -> dict:
    if "r" not in _CACHE:
        _CACHE["r"] = run()
    return _CACHE["r"]


def _held_out(request_suffix: str) -> dict:
    rows = [row for row in _report()["after_code_change"]["held_out"]
            if row["request"].endswith(request_suffix)]
    assert len(rows) == 1, rows
    return rows[0]


def test_under_the_old_algebra_no_operation_fits_the_lesson():
    """Prediction 1. The lesson could not have been accepted before the code change."""
    before = _report()["before_code_change"]
    assert before["lesson_set_aside"] is True
    assert before["set_aside_reason"] == "NO_OPERATION_I_CAN_PERFORM_GIVES_THESE_ANSWERS"
    assert before["operations_that_fit_the_two_answers"] == 0
    assert before["operations_in_old_algebra"] == 400
    assert before["operations_in_new_algebra"] == 560


def test_the_same_lesson_teaches_exactly_one_word_after_the_code_change():
    """Prediction 2. One reducer in code, one word from the lesson -- nothing else."""
    after = _report()["after_code_change"]
    assert after["lesson"]["taught"] is True, after["lesson"]
    assert after["lesson"]["examples_given"] == 2
    assert after["lesson"]["words_now_known"] == {"median": ["median"]}
    assert after["words_added"] == ["median"]


def test_held_out_requests_are_answered_correctly_and_never_wrongly():
    """Prediction 3, against expected values written before the run."""
    summary = _report()["summary"]
    assert summary["predictions_match_the_oracle"] is True
    assert summary["held_out"] == len(HELD_OUT) == 5
    assert summary["held_out_correct"] == 5
    assert summary["held_out_wrong"] == 0


def test_the_composition_no_lesson_shows_is_right():
    """`median` composed with `after the first` -- a combination in no lesson."""
    row = _held_out("n2.txt after the first")
    assert row["ok"] is True
    assert row["value"] == 115 == row["expected"]


def test_a_file_in_no_lesson_is_answered():
    row = _held_out("h1.txt")
    assert row["ok"] is True
    assert row["value"] == 50 == row["expected"]


def test_a_word_with_no_part_is_still_refused_by_name():
    """Prediction 5. The algebra grew by one; `mode` is not in it and never can be."""
    no_part = _report()["after_code_change"]["no_part_word"]
    assert no_part["request"] == NO_PART_WORD
    assert no_part["ok"] is False
    assert no_part["reason"] == "UNKNOWN_WORD:mode"


def test_no_seed_word_changed_meaning():
    """Prediction 6. The only word added is `median`; every seed word keeps its exact parts."""
    after = _report()["after_code_change"]
    assert after["seed_words_preserved"] is True
    assert after["seed_words_harmed"] == []


def test_the_word_survives_a_cache_clear_from_the_stored_lexicon_alone():
    """Prediction 7. Nothing kept in memory: the stored lexicon still answers."""
    reload_state = _report()["after_code_change"]["reload_from_disk"]
    assert reload_state["median_still_answered"] is True
    assert reload_state["value"] == 143


def test_the_independent_checker_is_two_sided_for_the_new_operator():
    """Prediction 4. The gate that admits the new operator can also say no to it."""
    gate = _report()["independent_checker"]
    assert gate["recompute_of_honest_claim"] == 30
    assert gate["honest_claim_accepted"] is True
    assert gate["upper_median_claim_rejected"] is True
    assert gate["reject_detail"].startswith("TAUGHT_ANSWER_RECOMPUTED_DIFFERENTLY")


def test_the_checker_module_shares_no_code_with_the_producer():
    """Structural: the checker must not import the producer, or the check is the producer.

    Checked on the import statements themselves -- the checker's docstring is allowed to *name*
    the producer; it is not allowed to load it.
    """
    import ast

    source = (ROOT / "canonical/runtime/taught_words_check_v1.py").read_text(encoding="utf-8")
    loaded = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            loaded.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            loaded.append(node.module)
    offenders = [name for name in loaded if "taught_words_v1" in name]
    assert offenders == [], offenders
    assert "canonical.runtime.taught_words_v1" not in loaded


def test_parts_grew_by_exactly_one_and_the_prose_now_matches_the_code():
    summary = _report()["summary"]
    assert summary["parts_before"] == 14
    assert summary["parts_after"] == 15
    assert len(taught.PARTS) == 15
    # The module docstring and the registry limitation both said fifteen when PARTS held fourteen.
    assert "fifteen parts" in (ROOT / "canonical/runtime/taught_words_v1.py").read_text(
        encoding="utf-8")


def test_the_probe_wrote_nothing_into_the_trees_live_state():
    state = ROOT / "canonical" / "astra_runtime" / "state"
    assert not (state / taught.LIVE_LESSONS_NAME).exists()
    assert not (state / taught.LIVE_LEXICON_NAME).exists()
    assert LESSON["sentence"] == "what is the median number in n.txt"


def test_the_run_is_deterministic_apart_from_the_clock():
    first, second = run(), run()
    first["summary"].pop("wall_clock_s", None)
    second["summary"].pop("wall_clock_s", None)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_the_front_door_answers_a_median_question_through_its_own_gate():
    """End to end: teach at the door's layer, then ask the door -- its recomputation must pass."""
    from canonical.runtime import live_brain_route_admission_v1 as door

    world = ROOT / "canonical/astra_runtime/tmp/zqtw_median_growth"
    numbers = "500\n4\n9\n9\n20\n"          # lower median 9
    kept_live, cache = taught.LIVE_DIR, dict(taught._CACHE)
    live = pathlib.Path(tempfile.mkdtemp(prefix="zqtw_median_live_"))
    try:
        shutil.rmtree(world, ignore_errors=True)
        world.mkdir(parents=True)
        (world / "nb.txt").write_text(numbers, encoding="utf-8")
        taught.LIVE_DIR = live
        taught._CACHE.clear()
        lesson = taught.teach(LESSON["sentence"],
                              [(e["text"], e["answer"]) for e in LESSON["examples"]])
        assert lesson.get("taught") is True, lesson

        asked = "what is the median number in %s/nb.txt" % world.relative_to(ROOT).as_posix()
        before = door.solve({"task_id": "median_growth_before", "goal":
                             "what is the mode number in %s/nb.txt" % world.relative_to(ROOT
                                                                                      ).as_posix()})
        result = door.solve({"task_id": "median_growth", "goal": asked})
        assert result.get("pass") is True, (result.get("status"),
                                            result.get("taught_words_reading"))
        answer = result.get("answer")
        value = answer.get("value") if isinstance(answer, dict) else answer
        assert str(value) == "9", value
        assert result.get("compiled_capability_id") == taught.CAPABILITY_ID
        # and the refusal the door reports for `mode` still names the word
        reading = before.get("taught_words_reading") or {}
        assert before.get("pass") is not True
        assert "mode" in str(reading.get("reason")), before
        assert (world / "nb.txt").read_text(encoding="utf-8") == numbers
    finally:
        taught.LIVE_DIR, taught._CACHE = kept_live, cache
        taught._CACHE.clear()
        shutil.rmtree(live, ignore_errors=True)
        shutil.rmtree(world, ignore_errors=True)


def main() -> int:
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
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
