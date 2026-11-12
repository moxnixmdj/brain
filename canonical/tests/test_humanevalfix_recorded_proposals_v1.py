"""A language model's published programs beside the tree's search and memory: reading the files, one bug, the counting."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402
from canonical.tools import humanevalfix_edit_kind_transfer_measure_v1 as hef  # noqa: E402
from canonical.tools import humanevalfix_recorded_proposals_measure_v1 as tool  # noqa: E402
from canonical.tests.test_humanevalfix_edit_kind_transfer_v1 import ROWS, passes  # noqa: E402


@pytest.fixture()
def bugs(tmp_path):
    path = tmp_path / "humanevalpack.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in ROWS))
    return hef.load_bugs(path)


# --------------------------------------------------------------------------- #
# the published proposals
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("answer, program", [
    ("def f():\n    return 1\n", "def f():\n    return 1\n"),
    ("Here is the fix:\n```python\ndef f():\n    return 1\n```\nIt works.", "def f():\n    return 1\n"),
    ("```\ndef f():\n    return 1\n```", "def f():\n    return 1\n"),
    ("```py\na = 1\n```\n```python\nb = 2\n```", "a = 1\n"),
    ("\n\ndef f():\n    return 1", "def f():\n    return 1\n"),
    ("", "\n"), (None, "\n")])
def test_code_of_takes_what_is_inside_the_first_fence_or_the_answer_itself(answer, program):
    assert tool.code_of(answer) == program


def test_load_proposals_reads_one_object_per_line(bugs, tmp_path):
    path = tmp_path / "samples.jsonl"
    path.write_text(json.dumps({"task_id": "Python/1", "extracted": "def plus_one(n):\n    return n + 1\n", "completion": "ignored"}) + "\n\n"
                    + json.dumps({"task_id": "Python/0", "completion": "```python\ndef add(a, b):\n    return a + b\n```"}) + "\n"
                    + json.dumps({"task_id": "Python/0", "extracted": "def add(a, b):\n    return b + a\n"}) + "\n")
    assert tool.load_proposals(path, bugs) == {"Python/1": ["def plus_one(n):\n    return n + 1\n"],
                                               "Python/0": ["def add(a, b):\n    return a + b\n", "def add(a, b):\n    return b + a\n"]}


def test_load_proposals_reads_one_list_of_programs_per_bug_in_the_benchmarks_order(bugs, tmp_path):
    path = tmp_path / "generations.json"
    path.write_text(json.dumps([["a = 0\n", "a = 1\n"], ["b = 0\n"], [], ["d = 0\n"]]))
    assert tool.load_proposals(path, bugs) == {"Python/0": ["a = 0\n", "a = 1\n"], "Python/1": ["b = 0\n"], "Python/2": [], "Python/3": ["d = 0\n"]}


def test_load_proposals_refuses_files_that_do_not_belong_to_the_benchmark(bugs, tmp_path):
    short = tmp_path / "generations.json"
    short.write_text(json.dumps([["a = 0\n"]]))
    with pytest.raises(ValueError, match="1 lists of programs for 4 bugs"):
        tool.load_proposals(short, bugs)
    other = tmp_path / "samples.jsonl"
    other.write_text(json.dumps({"task_id": "Python/99", "extracted": "x = 1\n"}) + "\n")
    with pytest.raises(ValueError, match="Python/99"):
        tool.load_proposals(other, bugs)


# --------------------------------------------------------------------------- #
# one bug, one model
# --------------------------------------------------------------------------- #
def checker(bug):
    def check(programs):
        return next((n for n, program in enumerate(programs) if passes(bug, program)), None)
    return check


def asked(bug, programs, lessons, tmp_path, **more):
    more.setdefault("agreement", lambda bug_, program, extra: {"inputs_used": 3, "agree": 3, "first_difference": None})
    return tool.one_bug(bug, programs, lessons, tmp_path / "w", check=checker(bug), accepted=lambda p: passes(bug, p), **more)


def test_the_models_first_program_that_passes_is_taken(bugs, tmp_path):
    add = bugs[0]
    row = asked(add, ["def add(a, b):\n    return a * b\n", "def add(a, b:\n", "def add(a, b):\n    return a + b\n", "def add(a, b):\n    return b + a\n"], None, tmp_path)
    assert row == {"bug_type": "operator misuse", "programs": 4, "programs_that_pass": 2, "first_program_passes": False, "first_that_passes": 3,
                   "the_models_program": {"is_the_published_fix": True, "right_as_far_as_checked": True}}
    first = asked(add, ["def add(a, b):\n    return a + b\n"], None, tmp_path)
    assert first["first_program_passes"] is True and first["first_that_passes"] == 1


def test_a_passing_program_that_is_not_the_published_fix_is_compared_on_extra_inputs(bugs, tmp_path):
    add = bugs[0]
    seen = []

    def agreement(bug, program, extra):
        seen.append((bug["name"], program, extra))
        return {"inputs_used": 5, "agree": 4, "first_difference": {"input": "[1, 1]"}}
    row = asked(add, ["def add(a, b):\n    return b + a\n"], None, tmp_path, extra={"entry": "add"}, agreement=agreement)
    assert row["the_models_program"] == {"is_the_published_fix": False, "right_as_far_as_checked": False,
                                         "on_inputs_the_tests_do_not_have": {"inputs_used": 5, "agree": 4, "first_difference": {"input": "[1, 1]"}}}
    assert seen == [("Python/0", "def add(a, b):\n    return b + a\n", {"entry": "add"})]
    same = asked(add, ["def add(a, b):\n    return b + a\n"], None, tmp_path)
    assert same["the_models_program"]["right_as_far_as_checked"] is True
    none = asked(add, ["def add(a, b):\n    return b + a\n"], None, tmp_path, agreement=lambda b, p, e: None)
    assert none["the_models_program"]["right_as_far_as_checked"] is False        # nothing to compare on: not called right


def test_no_program_of_the_model_passes_and_no_lessons_given(bugs, tmp_path):
    row = asked(bugs[0], ["def add(a, b):\n    return a * b\n"], None, tmp_path)
    assert row == {"bug_type": "operator misuse", "programs": 1, "programs_that_pass": 0, "first_program_passes": False, "first_that_passes": None}
    assert asked(bugs[0], [], None, tmp_path)["first_that_passes"] is None


def test_the_models_failed_attempt_is_repaired_with_operators_from_the_fixes_of_other_bugs(bugs, tmp_path):
    lessons = hef.taught(bugs, {})
    plus_one = bugs[1]                                                           # its fix: n - 1 becomes n + 1; "add" teaches minus-to-plus
    attempt = "def plus_one(n):\n    result = n - 1\n    return result\n"        # the model rewrote it and kept the bug
    row = asked(plus_one, [attempt], lessons, tmp_path)
    assert row["first_that_passes"] is None and row["attempts_the_operators_were_applied_to"] == 1
    repaired = row["repaired_around_the_models_attempt"]
    assert repaired["attempt"] == 1 and repaired["rank"] == 1
    assert repaired["lines"] == {"removed": ["result = n - 1"], "put_in": ["result = n + 1"]}
    assert repaired["is_the_published_fix"] is False and repaired["right_as_far_as_checked"] is True
    assert row["candidates_run_around_the_models_attempts"] == 1


def test_the_bugs_own_fix_is_not_among_the_lessons_used_on_the_models_attempt(bugs, tmp_path):
    below = bugs[2]                                                              # nobody else's fix turns <= into <
    lessons = hef.taught(bugs, {})
    attempt = "def below(xs, top):\n    out = [x for x in xs if x <= top]\n    return out\n"
    row = asked(below, [attempt], lessons, tmp_path)
    assert "repaired_around_the_models_attempt" not in row and row["attempts_the_operators_were_applied_to"] == 1
    own_only = kinds.Lessons()
    own_only.learn(below["name"], below["buggy"], below["fixed"])
    assert "repaired_around_the_models_attempt" not in asked(below, [attempt], own_only, tmp_path)


def test_only_different_attempts_are_repaired_and_only_so_many(bugs, tmp_path):
    lessons = hef.taught(bugs, {})
    plus_one = bugs[1]
    wrong = ["def plus_one(n):\n    return n * 5\n", "def plus_one( n ):\n    return n * 5  # the same\n", "def plus_one(n:\n",
             "def plus_one(n):\n    return n * 7\n", "def plus_one(n):\n    return n - 1\n"]
    row = asked(plus_one, wrong, lessons, tmp_path, attempts=2)
    assert row["attempts_the_operators_were_applied_to"] == 2 and "repaired_around_the_models_attempt" not in row   # the fourth different one is never reached
    row = asked(plus_one, wrong, lessons, tmp_path, attempts=3)
    assert row["repaired_around_the_models_attempt"]["attempt"] == 3              # the two spellings of one program count once; the broken one not at all
    assert "attempts_the_operators_were_applied_to" in row
    assert "repaired_around_the_models_attempt" not in asked(plus_one, wrong, lessons, tmp_path, attempts=0)


# --------------------------------------------------------------------------- #
# what it came to
# --------------------------------------------------------------------------- #
def test_search_outcomes_reads_the_learners_record():
    same = {"inputs_used": 4, "agree": 4}
    record = {"per_bug": {
        "a": {"usable": True, "all_other_fixes": {"repaired": True, "is_the_published_fix": True}},
        "b": {"usable": True, "all_other_fixes": {"repaired": True, "is_the_published_fix": False, "on_inputs_the_tests_do_not_have": same}},
        "c": {"usable": True, "all_other_fixes": {"repaired": True, "is_the_published_fix": False, "on_inputs_the_tests_do_not_have": {"inputs_used": 4, "agree": 3}}},
        "d": {"usable": True, "all_other_fixes": {"repaired": False}},
        "e": {"usable": False},
        "f": {"usable": True, "all_other_fixes": {"repaired": True, "is_the_published_fix": False, "on_inputs_the_tests_do_not_have": None}}}}
    assert tool.search_outcomes(record) == {"a": {"repaired": True, "right_as_far_as_checked": True}, "b": {"repaired": True, "right_as_far_as_checked": True},
                                            "c": {"repaired": True, "right_as_far_as_checked": False}, "d": {"repaired": False, "right_as_far_as_checked": False},
                                            "f": {"repaired": True, "right_as_far_as_checked": False}}


def test_the_learners_own_record_is_readable():
    record = json.loads((ROOT / "canonical/verification/HUMANEVALFIX_EDIT_KIND_TRANSFER_20261111_V1.json").read_text())
    search = tool.search_outcomes(record)
    assert len(search) == 100
    assert sum(1 for row in search.values() if row["repaired"]) == 62 and sum(1 for row in search.values() if row["right_as_far_as_checked"]) == 53


def model_row(first=None, right=True, around=None, bug_type="x"):
    row = {"bug_type": bug_type, "programs": 1, "programs_that_pass": int(first is not None), "first_program_passes": first == 1, "first_that_passes": first}
    if first is not None:
        row["the_models_program"] = {"right_as_far_as_checked": right}
    if around is not None:
        row["repaired_around_the_models_attempt"] = {"right_as_far_as_checked": around}
    return row


def test_summarise_counts_the_model_the_search_and_both():
    per_bug = {"a": model_row(1), "b": model_row(3, right=False), "c": model_row(1), "d": model_row(), "e": model_row(around=True),
               "f": model_row(around=False, bug_type="y"), "g": model_row(bug_type="y"), "not scored": model_row(1)}
    search = {"a": {"repaired": True, "right_as_far_as_checked": True}, "b": {"repaired": True, "right_as_far_as_checked": True},
              "c": {"repaired": False, "right_as_far_as_checked": False}, "d": {"repaired": True, "right_as_far_as_checked": False},
              "e": {"repaired": False, "right_as_far_as_checked": False}, "f": {"repaired": True, "right_as_far_as_checked": True},
              "g": {"repaired": False, "right_as_far_as_checked": False}}
    summary = tool.summarise(per_bug, search)
    assert summary["bugs"] == 7 and summary["the_model_alone_first_program"] == 2
    assert summary["the_model_and_the_tests"] == {"passes": 3, "right_as_far_as_checked": 2, "passes_and_is_wrong_on_an_extra_input": 1}
    assert summary["the_search_alone"] == {"passes": 4, "right_as_far_as_checked": 3}
    # either: a, b, c by the model; d, f by the search. Right: the model's program is what comes out for a, b, c (b is wrong); the search's for d (wrong), f (right)
    assert summary["either"] == {"passes": 5, "right_as_far_as_checked": 3}
    assert summary["bug_by_bug"] == {"both": 2, "the_model_only": 1, "the_search_only": 2, "neither": 2}
    assert summary["the_models_attempt_repaired"] == {"asked_where_no_program_of_the_model_passed": 4, "passes": 2, "right_as_far_as_checked": 1,
                                                      "of_those_where_the_search_had_also_failed": 1}
    assert summary["all_three"] == {"passes": 6, "right_as_far_as_checked": 4}
    assert summary["by_bug_type"] == {"x": {"bugs": 5, "the_model_and_the_tests": 3, "the_search_alone": 3, "either": 4, "all_three": 5},
                                      "y": {"bugs": 2, "the_model_and_the_tests": 0, "the_search_alone": 1, "either": 1, "all_three": 1}}


# --------------------------------------------------------------------------- #
# the command line
# --------------------------------------------------------------------------- #
def test_main_reads_a_models_file_and_writes_the_record(bugs, tmp_path, monkeypatch, capsys):
    data = tmp_path / "humanevalpack.jsonl"
    proposals = tmp_path / "generations.json"
    proposals.write_text(json.dumps([["def add(a, b):\n    return a + b\n"],                                      # the model passes
                                     ["def plus_one(n):\n    result = n - 1\n    return result\n"],                   # fails; repaired around its attempt
                                     ["def below(xs, top):\n    return xs\n"],                                        # fails; nothing helps
                                     ["def first(xs):\n    return xs[0]\n"]]))                                        # not scored
    search_record = tmp_path / "search.json"
    search_record.write_text(json.dumps({"frozen_commit": "abc", "code_sha256": {"x": "y"}, "per_bug": {
        "Python/0": {"usable": True, "all_other_fixes": {"repaired": True, "is_the_published_fix": True}},
        "Python/1": {"usable": True, "all_other_fixes": {"repaired": False}},
        "Python/2": {"usable": True, "all_other_fixes": {"repaired": True, "is_the_published_fix": True}}}}))
    monkeypatch.setattr(hef, "quixbugs_lessons", lambda root: {})
    by_entry = {r["entry_point"]: r for r in ROWS}

    def stand_in_screen(where, programs, **k):
        text = (where / "test_prog.py").read_text()
        bug = next({"test": r["test"]} for entry, r in by_entry.items() if f"check({entry})" in text)
        return checker(bug)(programs)
    monkeypatch.setattr(hef, "screen", stand_in_screen)
    monkeypatch.setattr(hef, "accept", lambda bug, program, **k: passes(bug, program))
    monkeypatch.setattr(hef, "agreement", lambda bug, program, extra, **k: {"inputs_used": 2, "agree": 2, "first_difference": None})
    arguments = ["--humanevalfix", str(data), "--quixbugs-dir", str(tmp_path), "--search-record", str(search_record), "--proposals", str(proposals),
                 "--model", "some/model", "--published-at", "github.com/some/where", "--work-dir", str(tmp_path / "work")]
    assert tool.main(arguments + ["--out", str(tmp_path / "out.json")]) == 0
    record = json.loads((tmp_path / "out.json").read_text())
    assert (record["schema"], record["authority"], record["model_calls"], record["model"], record["published_at"]) == (
        tool.SCHEMA, tool.AUTHORITY, 0, "some/model", "github.com/some/where")
    assert sorted(record["per_bug"]) == ["Python/0", "Python/1", "Python/2"]      # the bug that was not scored is left out
    summary = record["summary"]
    assert summary["the_model_and_the_tests"]["passes"] == 1 and summary["the_search_alone"]["passes"] == 2
    assert summary["either"]["passes"] == 2 and summary["bug_by_bug"] == {"both": 1, "the_model_only": 0, "the_search_only": 1, "neither": 1}
    assert summary["the_models_attempt_repaired"]["passes"] == 1 and summary["all_three"]["passes"] == 3
    assert record["on_every_bug_judged"] == {"bugs": 3, "first_program_passes": 1, "some_program_passes": 1, "programs": 3, "programs_that_pass": 1}
    assert record["search_record"] == {"path": "search.json", "frozen_commit": "abc", "code_sha256": {"x": "y"}} and len(record["proposals_sha256"]) == 64
    assert "Python/1" in capsys.readouterr().out
    assert tool.main(arguments + ["--out", str(tmp_path / "all.json"), "--all-bugs"]) == 0
    everything = json.loads((tmp_path / "all.json").read_text())
    assert sorted(everything["per_bug"]) == ["Python/0", "Python/1", "Python/2", "Python/3"]
    assert everything["on_every_bug_judged"]["bugs"] == 4 and everything["on_every_bug_judged"]["some_program_passes"] == 2
    assert everything["summary"]["bugs"] == 3                                     # the counts beside the search stay on the scored bugs
    assert "repaired_around_the_models_attempt" not in everything["per_bug"]["Python/3"]
