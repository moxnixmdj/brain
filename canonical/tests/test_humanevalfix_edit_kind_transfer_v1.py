"""The HumanEvalFix measurement of the edit-kind learner: stand-in bugs, then the real screen and interpreter."""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402
from canonical.tools import humanevalfix_edit_kind_transfer_measure_v1 as tool  # noqa: E402


# --------------------------------------------------------------------------- #
# a stand-in benchmark: four bugs, two of one kind
# --------------------------------------------------------------------------- #
def row(number, entry, declaration, buggy, fixed, checks, bug_type="operator misuse"):
    test = "\n\ndef check(" + entry + "):\n" + "".join(f"    assert {c}\n" for c in checks) + f"\ncheck({entry})\n"
    return {"task_id": f"Python/{number}", "entry_point": entry, "declaration": declaration, "buggy_solution": buggy,
            "canonical_solution": fixed, "test": test, "bug_type": bug_type}


ROWS = [
    row(0, "add", "def add(a, b):\n", "    return a - b\n", "    return a + b\n", ["add(2, 3) == 5", "add(-1, 1) == 0"]),
    row(1, "plus_one", "def plus_one(n):\n", "    return n - 1\n", "    return n + 1\n", ["plus_one(1) == 2", "plus_one(-1) == 0"]),
    row(2, "below", "def below(xs, top):\n", "    return [x for x in xs if x <= top]\n", "    return [x for x in xs if x < top]\n",
        ["below([1, 2, 3], 2) == [1]", "below([], 0) == []"]),
    row(3, "first", "def first(xs):\n", "    return xs[1]\n", "    return xs[0]\n", ["first([7, 8]) == 7", "first([1, 1, 2]) == 1"], "value misuse"),
]


@pytest.fixture()
def bugs(tmp_path):
    path = tmp_path / "humanevalpack.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in ROWS))
    return tool.load_bugs(path)


def passes(bug, program: str) -> bool:
    try:
        exec(compile(tool.PRELUDE + program + "\n" + bug["test"], "<stand-in>", "exec"), {"__name__": "__stand_in__"})
    except BaseException:
        return False
    return True


def checker(bug, seen=None):
    def check(programs):
        for index, program in enumerate(programs):
            if seen is not None:
                seen.append(program)
            if passes(bug, program):
                return index
        return None
    return check


def measured(bugs, tmp_path, names=None, **more):
    return tool.measure(bugs, names or [b["name"] for b in bugs], {}, tmp_path / "work", budget=50, curve_sizes=(1, 2),
                        curve_seeds=2, check_for=lambda bug, where: checker(bug), accepted_for=lambda bug: (lambda p: passes(bug, p)), **more)


# --------------------------------------------------------------------------- #
# the bugs, the split, the files
# --------------------------------------------------------------------------- #
def test_load_bugs_makes_programs_of_the_declaration_and_the_body(bugs):
    assert [b["name"] for b in bugs] == ["Python/0", "Python/1", "Python/2", "Python/3"]
    assert bugs[0] == {"name": "Python/0", "number": 0, "entry": "add", "bug_type": "operator misuse",
                       "buggy": "def add(a, b):\n    return a - b\n", "fixed": "def add(a, b):\n    return a + b\n", "test": ROWS[0]["test"]}


def test_load_bugs_refuses_tests_that_do_not_end_by_calling_check(tmp_path):
    bad = dict(ROWS[0], test=ROWS[0]["test"] + "print('done')\n")
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps(bad) + "\n")
    with pytest.raises(ValueError, match="Python/0"):
        tool.load_bugs(path)


def many(n):
    return [{"name": f"Python/{i}"} for i in range(n)]


def test_split_is_a_seeded_draw_that_never_scores_what_was_read():
    development, scored = tool.split(many(164))
    assert len(scored) == 100 and len(development) == 64
    assert not set(scored) & set(development) and set(scored) | set(development) == {f"Python/{i}" for i in range(164)}
    assert "Python/0" in development
    assert scored == sorted(scored, key=lambda n: int(n.split("/")[1]))
    assert (development, scored) == tool.split(many(164))
    assert tool.split(many(164), seed=1)[1] != scored
    for never in (["Python/5"], ["Python/5", "Python/77", "Python/163"]):
        assert not set(never) & set(tool.split(many(164), never_scored=never)[1])


def test_split_of_fewer_bugs_than_asked_for():
    development, scored = tool.split(many(5), scored=100)
    assert development == ["Python/0"] and scored == ["Python/1", "Python/2", "Python/3", "Python/4"]


def test_the_real_split_is_the_one_written_down():
    development, scored = tool.split(many(164))
    assert development[:6] == ["Python/0", "Python/2", "Python/6", "Python/7", "Python/8", "Python/10"]
    assert (tool.SPLIT_SEED, tool.SCORED, tool.READ_BEFORE_THE_DRAW) == (20261111, 100, ("Python/0",))


def test_test_file_keeps_the_checks_and_calls_them_from_one_test(bugs):
    text = tool.test_file(bugs[0])
    assert text.startswith(tool.PRELUDE + "from prog import *\n")
    assert "def check(add):\n    assert add(2, 3) == 5\n" in text
    assert text.endswith("\n\n\ndef test_check():\n    check(add)\n")
    assert text.count("check(add)") == 2                      # the definition and the call inside the test: not the call at the end
    tree = ast.parse(text)
    assert [type(node).__name__ for node in tree.body][-2:] == ["FunctionDef", "FunctionDef"]


def test_lay_out_writes_the_buggy_program_and_its_tests(bugs, tmp_path):
    where = tool.lay_out(bugs[1], tmp_path / "bug")
    assert (where / "prog.py").read_text() == tool.PRELUDE + bugs[1]["buggy"]
    assert (where / "test_prog.py").read_text() == tool.test_file(bugs[1])
    (where / "stale").write_text("x")
    tool.lay_out(bugs[1], where)
    assert sorted(p.name for p in where.iterdir()) == ["prog.py", "test_prog.py"]


def test_extra_inputs_by_number(tmp_path):
    path = tmp_path / "plus.jsonl"
    path.write_text(json.dumps({"task_id": "HumanEval/7", "entry_point": "f", "atol": 0, "base_input": [[1], [2]], "plus_input": [[3]]}) + "\n\n"
                    + json.dumps({"task_id": "HumanEval/9", "entry_point": "g", "atol": 1e-6, "base_input": [], "plus_input": [[0.5]]}) + "\n")
    assert tool.extra_inputs(path) == {7: {"entry": "f", "atol": 0, "inputs": [[1], [2], [3]]}, 9: {"entry": "g", "atol": 1e-6, "inputs": [[0.5]]}}
    assert tool.extra_inputs(None) == {}


def test_changed_lines():
    assert tool.changed_lines("def f(a):\n    x = a   # note\n    return x\n", "def f(a):\n    x = a + 1\n    return x") == {
        "removed": ["x = a"], "put_in": ["x = a + 1"]}


# --------------------------------------------------------------------------- #
# candidates in order, the tests on each
# --------------------------------------------------------------------------- #
def ranked(*texts):
    return [(text, 1.0 / (n + 1), {}) for n, text in enumerate(texts)]


class Screen:
    def __init__(self, passing):
        self.passing, self.calls = set(passing), []

    def __call__(self, programs):
        self.calls.append(list(programs))
        return next((n for n, p in enumerate(programs) if p in self.passing), None)


def test_first_pass_finds_the_first_candidate_that_passes(bugs):
    screen = Screen({"c = 3", "e = 5"})
    bench = tool.Bench(bugs[0], screen, lambda program: True)
    assert bench.first_pass(ranked("a = 1", "b = 2", "c = 3", "d = 4", "e = 5"), 10) == (3, "c = 3", 3)
    assert screen.calls == [["a = 1", "b = 2", "c = 3", "d = 4", "e = 5"]]
    assert bench.runs == 3
    assert bench.known == {"a = 1": False, "b = 2": False, "c = 3": True}


def test_first_pass_runs_no_candidate_twice(bugs):
    screen = Screen({"c = 3"})
    bench = tool.Bench(bugs[0], screen, lambda program: True)
    bench.first_pass(ranked("a = 1", "b = 2", "c = 3"), 10)
    assert bench.first_pass(ranked("b = 2", "a = 1", "c = 3", "d = 4"), 10) == (3, "c = 3", 3)
    assert bench.first_pass(ranked("d = 4", "c = 3"), 10) == (2, "c = 3", 2)
    assert screen.calls == [["a = 1", "b = 2", "c = 3"], ["d = 4"]]
    assert bench.runs == 4


def test_first_pass_stops_at_the_budget(bugs):
    screen = Screen({"c = 3"})
    bench = tool.Bench(bugs[0], screen, lambda program: True)
    assert bench.first_pass(ranked("a = 1", "b = 2", "c = 3"), 2) == (None, None, 2)
    assert screen.calls == [["a = 1", "b = 2"]]
    assert bench.first_pass(ranked("a = 1", "b = 2", "c = 3"), 3) == (3, "c = 3", 3)
    assert bench.first_pass([], 5) == (None, None, 0)


def test_first_pass_skips_what_is_no_program_and_does_not_count_it(bugs):
    screen = Screen({"c = 3"})
    bench = tool.Bench(bugs[0], screen, lambda program: True)
    assert bench.first_pass(ranked("a + 1 = 1", "return 2", "b = 2", "c = 3"), 2) == (2, "c = 3", 2)
    assert screen.calls == [["b = 2", "c = 3"]]


def test_first_pass_goes_on_when_the_fresh_interpreter_says_no(bugs):
    screen = Screen({"b = 2", "d = 4"})
    bench = tool.Bench(bugs[0], screen, lambda program: program == "d = 4")
    assert bench.first_pass(ranked("a = 1", "b = 2", "c = 3", "d = 4"), 10) == (4, "d = 4", 4)
    assert bench.screen_said_pass_fresh_interpreter_said_no == 1
    assert bench.known == {"a = 1": False, "b = 2": False, "c = 3": False, "d = 4": True}
    assert screen.calls == [["a = 1", "b = 2", "c = 3", "d = 4"], ["c = 3", "d = 4"]]


def test_first_pass_asks_in_chunks(bugs):
    many_texts = [f"v = {n}" for n in range(tool.CHUNK * 2 + 5)]
    screen = Screen({many_texts[-1]})
    bench = tool.Bench(bugs[0], screen, lambda program: True)
    assert bench.first_pass(ranked(*many_texts), 1000) == (len(many_texts), many_texts[-1], len(many_texts))
    assert [len(call) for call in screen.calls] == [tool.CHUNK, tool.CHUNK, 5]
    assert bench.runs == len(many_texts)


# --------------------------------------------------------------------------- #
# one bug asked every question
# --------------------------------------------------------------------------- #
def test_a_fix_of_the_same_kind_repairs_the_other_bug_and_its_own_fix_is_never_among_the_lessons(bugs, tmp_path):
    per_bug = measured(bugs, tmp_path)["per_bug"]
    add, plus_one, below, first = (per_bug[f"Python/{n}"] for n in range(4))
    assert all(row["usable"] and all(row["benchmark_holds"].values()) for row in per_bug.values())
    # add and plus_one teach each other
    assert plus_one["all_other_fixes"]["repaired"] and plus_one["all_other_fixes"]["is_the_published_fix"]
    assert plus_one["all_other_fixes"]["voted_by"] == ["Python/0"]
    assert plus_one["all_other_fixes"]["lines"] == {"removed": ["return n - 1"], "put_in": ["return n + 1"]}
    assert plus_one["all_other_fixes"]["operator"] == "replace: __E0__ - __E1__  ->  __E0__ + __E1__"
    assert add["all_other_fixes"]["repaired"] and add["all_other_fixes"]["voted_by"] == ["Python/1"]
    # nobody teaches the kind of below or of first: only their own fixes would, and those are never used
    for alone in (below, first):
        assert not alone["all_other_fixes"]["repaired"] and alone["all_other_fixes"]["published_fix_rank"] is None
        assert alone["own_fix_shown"] == {"taught_something": True, "rank_among_its_own_candidates": 1, "rank_among_all_candidates": 1}
    assert all(row["all_other_fixes"]["lessons"] == 3 for row in per_bug.values())
    # no QuixBugs lessons were given here
    assert all(row["another_benchmark"] == {"lessons": 0, "candidates": 0, "published_fix_rank": None, "first_pass_rank": None,
                                            "repaired": False} for row in per_bug.values())


def test_the_curve_draws_lessons_from_the_other_fixes_only(bugs, tmp_path):
    per_bug = measured(bugs, tmp_path)["per_bug"]
    assert set(per_bug["Python/1"]["curve"]) == {"1", "2"}                       # 3 other lessons: sizes below that
    assert all(len(draws) == 2 for draws in per_bug["Python/1"]["curve"].values())
    for draws in per_bug["Python/2"]["curve"].values():
        assert all(not d["repaired"] and d["published_fix_rank"] is None for d in draws)
    again = measured(bugs, tmp_path)["per_bug"]
    assert again["Python/1"]["curve"] == per_bug["Python/1"]["curve"]
    other_seed = [measured(bugs, tmp_path, seed=s)["per_bug"]["Python/1"]["curve"]["1"] for s in range(6)]
    assert len({json.dumps(c) for c in other_seed}) > 1


def test_a_bug_whose_benchmark_does_not_hold_is_not_asked(bugs, tmp_path):
    broken = [dict(b) for b in bugs]
    broken[3]["fixed"] = broken[3]["buggy"]                                      # the "fix" fails its tests
    out = tool.measure(broken, ["Python/3", "Python/1"], {}, tmp_path / "work", budget=50, curve_sizes=(1,), curve_seeds=1,
                       check_for=lambda bug, where: checker(bug), accepted_for=lambda bug: (lambda p: passes(bug, p)))
    assert out["per_bug"]["Python/3"] == {"bug_type": "value misuse", "usable": False, "benchmark_holds": {
        "buggy_fails_in_the_screen": True, "published_fix_passes_in_the_screen": False,
        "buggy_fails_in_a_fresh_interpreter": True, "published_fix_passes_in_a_fresh_interpreter": False}}
    assert out["per_bug"]["Python/1"]["usable"]
    assert out["lessons"] == {"given": 3, "from_quixbugs": 0, "taught_nothing": ["Python/3"], "operators": out["lessons"]["operators"]}


def test_a_bug_that_already_passes_is_not_asked(bugs, tmp_path):
    passing = [dict(b) for b in bugs]
    passing[0]["buggy"] = passing[0]["fixed"]
    out = tool.measure(passing, ["Python/0"], {}, tmp_path / "work", budget=50, curve_sizes=(1,), curve_seeds=1,
                       check_for=lambda bug, where: checker(bug), accepted_for=lambda bug: (lambda p: passes(bug, p)))
    assert out["per_bug"]["Python/0"]["usable"] is False
    assert out["per_bug"]["Python/0"]["benchmark_holds"]["buggy_fails_in_the_screen"] is False


def test_lessons_from_another_benchmark_are_asked_alone(bugs, tmp_path):
    quixbugs = {"quixbugs/minus": ("def sub(p, q):\n    return q - p\n", "def sub(p, q):\n    return q + p\n")}
    out = tool.measure(bugs, ["Python/0", "Python/2"], quixbugs, tmp_path / "work", budget=50, curve_sizes=(1,), curve_seeds=1,
                       check_for=lambda bug, where: checker(bug), accepted_for=lambda bug: (lambda p: passes(bug, p)))
    add = out["per_bug"]["Python/0"]
    assert add["another_benchmark"]["repaired"] and add["another_benchmark"]["voted_by"] == ["quixbugs/minus"]
    assert add["another_benchmark"]["lessons"] == 1 and add["all_other_fixes"]["lessons"] == 4
    assert sorted(add["all_other_fixes"]["voted_by"]) == ["Python/1", "quixbugs/minus"]
    assert not out["per_bug"]["Python/2"]["another_benchmark"]["repaired"]
    assert out["lessons"]["given"] == 5 and out["lessons"]["from_quixbugs"] == 1


def test_lessons_shown_backwards_are_the_control(bugs, tmp_path):
    forwards, backwards = tool.taught(bugs, {}), tool.taught(bugs, {}, backwards=True)
    assert forwards.lessons == backwards.lessons
    assert any("__E0__ - __E1__  ->  __E0__ + __E1__" in o.shown() for o in forwards.operators.values())
    assert not any("__E0__ - __E1__  ->  __E0__ + __E1__" in o.shown() for o in backwards.operators.values())
    assert any("__E0__ + __E1__  ->  __E0__ - __E1__" in o.shown() for o in backwards.operators.values())
    out = measured(bugs, tmp_path, backwards=True)
    # add and plus_one both need "- becomes +"; read backwards the other one teaches "+ becomes -": no repair
    assert [out["per_bug"][f"Python/{n}"]["all_other_fixes"]["repaired"] for n in range(4)] == [False, False, False, False]
    with_quixbugs = tool.taught(bugs, {"quixbugs/q": ("def s(p):\n    return p + 1\n", "def s(p):\n    return p - 1\n")}, backwards=True)
    assert any("__E0__ - __E1__  ->  __E0__ + __E1__" in o.shown() for o in with_quixbugs.operators.values())


def test_no_candidate_is_run_twice_for_one_bug(bugs, tmp_path):
    seen: dict[str, list[str]] = {}
    tool.measure(bugs, [b["name"] for b in bugs], {}, tmp_path / "work", budget=50, curve_sizes=(1, 2), curve_seeds=2,
                 check_for=lambda bug, where: checker(bug, seen.setdefault(bug["name"], [])), accepted_for=lambda bug: (lambda p: passes(bug, p)))
    for name, programs in seen.items():
        asked_about = programs[2:]                                               # the first two calls are the benchmark check
        assert len(asked_about) == len(set(asked_about)), name


def test_a_repair_that_is_another_program_is_compared_on_extra_inputs(bugs, tmp_path, monkeypatch):
    # a lesson that turns "n - 1" into "n + True": passes plus_one's tests, is not the published fix
    odd = {"quixbugs/odd": ("def g(k):\n    return k - 1\n", "def g(k):\n    return k + True\n")}
    calls = []
    monkeypatch.setattr(tool, "agreement", lambda bug, program, extra: calls.append((bug["name"], program, extra)) or {"inputs_used": 4, "agree": 4, "first_difference": None})
    out = tool.measure(bugs, ["Python/1"], odd, tmp_path / "work", budget=50, curve_sizes=(), curve_seeds=1, extra={1: {"entry": "plus_one"}},
                       check_for=lambda bug, where: checker(bug), accepted_for=lambda bug: (lambda p: passes(bug, p)))
    row_ = out["per_bug"]["Python/1"]["another_benchmark"]
    assert row_["repaired"] and row_["is_the_published_fix"] is False
    assert row_["on_inputs_the_tests_do_not_have"] == {"inputs_used": 4, "agree": 4, "first_difference": None}
    assert calls == [("Python/1", "def plus_one(n):\n    return n + True", {"entry": "plus_one"})]
    assert "on_inputs_the_tests_do_not_have" not in out["per_bug"]["Python/1"]["all_other_fixes"]   # there the published fix came first


# --------------------------------------------------------------------------- #
# what it came to
# --------------------------------------------------------------------------- #
def test_summarise_counts_the_stand_in_benchmark(bugs, tmp_path):
    out = measured(bugs, tmp_path)
    summary = tool.summarise(out["per_bug"], 50)
    assert (summary["bugs_asked"], summary["bugs_usable"], summary["not_usable"]) == (4, 4, [])
    everything = summary["all_other_fixes"]
    assert (everything["bugs"], everything["repaired"], everything["the_repair_is_the_published_fix"]) == (4, 2, 2)
    assert everything["repaired_within"] == {"1": 2, "10": 2}
    assert everything["published_fix_among_the_candidates"] == 2 and everything["published_fix_within"]["1"] == 2
    assert everything["the_repair_is_another_program"] == 0 and everything["repaired_and_right_as_far_as_checked"] == 2
    assert everything["by_bug_type"] == {
        "operator misuse": {"bugs": 3, "repaired": 2, "the_repair_is_the_published_fix": 2, "published_fix_among_the_candidates": 2},
        "value misuse": {"bugs": 1, "repaired": 0, "the_repair_is_the_published_fix": 0, "published_fix_among_the_candidates": 0}}
    assert summary["another_benchmark"]["repaired"] == 0
    assert summary["own_fix_shown"] == {"bugs": 4, "taught_something": 4, "first_among_its_own_candidates": 4, "among_all_candidates": 4,
                                        "first_among_all_candidates": 4, "within_10_among_all_candidates": 4}
    assert set(summary["curve"]) == {"1", "2"} and summary["curve"]["1"]["draws"] == 8
    assert summary["curve"]["2"]["repaired"] >= summary["curve"]["1"]["repaired"]
    assert summary["candidates_run"] == sum(row["candidates_run"] for row in out["per_bug"].values()) > 0


def test_summarise_leaves_out_what_was_not_usable():
    per_bug = {"Python/1": {"bug_type": "x", "usable": False, "benchmark_holds": {}}}
    summary = tool.summarise(per_bug, 1000)
    assert (summary["bugs_asked"], summary["bugs_usable"], summary["not_usable"]) == (1, 0, ["Python/1"])
    assert summary["all_other_fixes"]["bugs"] == 0 and summary["curve"] == {}


def test_a_question_is_counted_by_what_the_repair_turned_out_to_be():
    same = {"inputs_used": 9, "agree": 9, "first_difference": None}
    differs = {"inputs_used": 9, "agree": 7, "first_difference": {"input": "[1]"}}
    rows = [
        {"repaired": True, "first_pass_rank": 1, "published_fix_rank": 1, "is_the_published_fix": True, "candidates": 10},
        {"repaired": True, "first_pass_rank": 5, "published_fix_rank": 9, "is_the_published_fix": False, "candidates": 30,
         "on_inputs_the_tests_do_not_have": same},
        {"repaired": True, "first_pass_rank": 150, "published_fix_rank": None, "is_the_published_fix": False, "candidates": 400,
         "on_inputs_the_tests_do_not_have": differs},
        {"repaired": True, "first_pass_rank": 900, "published_fix_rank": None, "is_the_published_fix": False, "candidates": 2000,
         "on_inputs_the_tests_do_not_have": None},
        {"repaired": True, "first_pass_rank": 12, "published_fix_rank": None, "is_the_published_fix": False, "candidates": 50,
         "on_inputs_the_tests_do_not_have": {"inputs_used": 0, "agree": 0, "first_difference": None, "error": "x"}},
        {"repaired": False, "first_pass_rank": None, "published_fix_rank": 1500, "candidates": 3000},
        {"repaired": False, "first_pass_rank": None, "published_fix_rank": None, "candidates": 0},
    ]
    assert tool._question(rows, 1000) == {
        "bugs": 7, "repaired": 5, "repaired_within": {"1": 1, "10": 2, "100": 3, "200": 4, "1000": 5},
        "the_repair_is_the_published_fix": 1, "the_repair_is_another_program": 4,
        "of_those_same_answers_on_every_extra_input": 1, "of_those_a_different_answer_on_some_extra_input": 1, "of_those_not_compared": 2,
        "published_fix_among_the_candidates": 3, "published_fix_within": {"1": 1, "10": 2, "100": 2, "200": 2, "1000": 2},
        "candidates_median": 50, "repaired_and_right_as_far_as_checked": 2}
    assert tool._question(rows, 100)["repaired_within"] == {"1": 1, "10": 2, "100": 3}


@pytest.mark.parametrize("values, middle", [([], None), ([4], 4), ([1, 9], 5.0), ([3, 1, 2], 2), ([1, 2, 3, 100], 2.5)])
def test_median(values, middle):
    assert tool._median(values) == middle


# --------------------------------------------------------------------------- #
# the real interpreter and the real screen
# --------------------------------------------------------------------------- #
def test_accept_is_the_benchmarks_check_in_a_fresh_interpreter(bugs):
    assert tool.accept(bugs[0], bugs[0]["fixed"]) is True
    assert tool.accept(bugs[0], bugs[0]["buggy"]) is False
    assert tool.accept(bugs[0], "def add(a, b):\n    while True:\n        pass\n", limit_s=1) is False
    assert tool.accept(bugs[0], "def add(a, b:\n") is False
    # what the harness puts in front is there
    uses_math = dict(bugs[0], fixed="def add(a, b):\n    return int(math.fsum([a, b]))\n")
    assert tool.accept(uses_math, uses_math["fixed"]) is True


def test_agreement_compares_the_candidate_with_the_published_fix(bugs):
    extra = {"entry": "below", "atol": 0, "inputs": [[[1, 2, 3], 2], [[5, 5], 5], [[], 1], [[1, 2], "x"], [[4, 1], 3]]}
    below = bugs[2]
    assert tool.agreement(below, below["fixed"], extra) == {"inputs_used": 4, "agree": 4, "first_difference": None}   # one input raises in the fix: left out
    out = tool.agreement(below, below["buggy"], extra)
    assert (out["inputs_used"], out["agree"]) == (4, 2)
    assert out["first_difference"] == {"input": "[[1, 2, 3], 2]", "published": "[1]", "candidate": "('value', [1, 2])"}
    raises = "def below(xs, top):\n    return [x for x in xs if x < top][0:1] + [xs[5]]\n"
    assert tool.agreement(below, raises, extra)["first_difference"]["candidate"] == "('raised', 'IndexError')"


def test_agreement_stops_a_candidate_that_does_not_end(bugs):
    extra = {"entry": "add", "atol": 0, "inputs": [[1, 2], [0, 0]]}
    loops = "def add(a, b):\n    while a:\n        pass\n    return a + b\n"
    out = tool.agreement(bugs[0], loops, extra, limit_s=0.3)
    assert (out["inputs_used"], out["agree"]) == (2, 1)
    assert out["first_difference"]["candidate"] == "('late', None)"


def test_agreement_takes_a_tolerance_for_numbers_and_tells_true_from_one(bugs):
    half = dict(bugs[0], fixed="def add(a, b):\n    return (a + b) / 2\n")
    extra = {"entry": "add", "atol": 1e-6, "inputs": [[1, 2], [3, 3]]}
    assert tool.agreement(half, "def add(a, b):\n    return (a + b) / 2 + 1e-9\n", extra)["agree"] == 2
    assert tool.agreement(half, "def add(a, b):\n    return (a + b) / 2 + 1e-3\n", extra)["agree"] == 0
    truth = dict(bugs[0], fixed="def add(a, b):\n    return a + b == 2\n")
    assert tool.agreement(truth, "def add(a, b):\n    return int(a + b == 2)\n", {"entry": "add", "atol": 0, "inputs": [[1, 1]]})["agree"] == 0
    listed = dict(bugs[0], fixed="def add(a, b):\n    return [a, b]\n")
    assert tool.agreement(listed, "def add(a, b):\n    return (a, b)\n", {"entry": "add", "atol": 0, "inputs": [[1, 1]]})["agree"] == 0


def test_agreement_without_inputs_for_this_function(bugs):
    assert tool.agreement(bugs[0], bugs[0]["fixed"], None) is None
    assert tool.agreement(bugs[0], bugs[0]["fixed"], {}) is None
    assert tool.agreement(bugs[0], bugs[0]["fixed"], {"entry": "other", "atol": 0, "inputs": [[1, 2]]}) is None


def test_agreement_says_so_when_a_program_cannot_be_loaded(bugs):
    out = tool.agreement(bugs[0], "def add(a, b:\n", {"entry": "add", "atol": 0, "inputs": [[1, 2]]})
    assert (out["inputs_used"], out["agree"]) == (0, 0) and "SyntaxError" in out["error"]


def screen_works() -> bool:
    try:
        from canonical.runtime import brokered_workspace_execution_v1 as broker
        return bool(broker.namespace_broker_available())
    except Exception:
        return False


needs_the_screen = pytest.mark.skipif(not screen_works(), reason="the confined candidate screen is not available on this machine")


@needs_the_screen
def test_the_real_screen_names_the_first_candidate_that_passes(bugs, tmp_path):
    where = tool.lay_out(bugs[0], tmp_path / "bug")
    wrong, loops = "def add(a, b):\n    return a * b\n", "def add(a, b):\n    while True:\n        pass\n"
    assert tool.screen(where, [wrong, loops, bugs[0]["fixed"], "def add(a, b):\n    return b + a\n"]) == 2
    assert tool.screen(where, [wrong, bugs[0]["buggy"], loops, "def add(a, b:\n"]) is None
    assert tool.screen(where, []) is None
    assert (where / "prog.py").read_text() == tool.PRELUDE + bugs[0]["buggy"]


@needs_the_screen
def test_the_real_screen_gives_the_program_what_the_harness_puts_in_front(bugs, tmp_path):
    where = tool.lay_out(bugs[0], tmp_path / "bug")
    assert tool.screen(where, ["def add(a, b):\n    return int(math.fsum([a, b]))\n"]) == 0


def test_screen_raises_when_the_organ_does_not_answer_with_authority(bugs, tmp_path, monkeypatch):
    from canonical.swe_kernel import zygote_worker_pool_v1 as organ
    where = tool.lay_out(bugs[0], tmp_path / "bug")
    for answer in ({"ok": False, "screen_authoritative": False, "passing_indices": [0, 1], "live_workspace_untouched": True},
                   {"ok": True, "screen_authoritative": False, "passing_indices": [0], "live_workspace_untouched": True},
                   {"ok": True, "screen_authoritative": True, "passing_indices": [0], "live_workspace_untouched": False}):
        monkeypatch.setattr(organ, "screen_python_candidates_cow", lambda *a, _answer=answer, **k: _answer)
        with pytest.raises(RuntimeError, match="authority"):
            tool.screen(where, [bugs[0]["fixed"]])


def test_screen_hands_the_organ_the_programs_with_the_prelude_and_its_limits(bugs, tmp_path, monkeypatch):
    from canonical.swe_kernel import zygote_worker_pool_v1 as organ
    where = tool.lay_out(bugs[0], tmp_path / "bug")
    seen = {}

    def organ_stand_in(root, target, tests, candidates, **more):
        seen.update(root=root, target=target, tests=tests, candidates=candidates, **more)
        return {"ok": True, "screen_authoritative": True, "passing_indices": [3, 1], "live_workspace_untouched": True}
    monkeypatch.setattr(organ, "screen_python_candidates_cow", organ_stand_in)
    assert tool.screen(where, ["a = 1", "b = 2", "c = 3", "d = 4"], limit_s=0.25) == 1
    assert seen == {"root": str(where), "target": "prog.py", "tests": ["test_prog.py"], "stop_on_first_pass": True,
                    "candidates": [tool.PRELUDE + p for p in ("a = 1", "b = 2", "c = 3", "d = 4")],
                    "timeout_s": 4 * 0.25 + 20.0, "per_candidate_timeout_s": 0.25}


@needs_the_screen
def test_one_bug_end_to_end_with_the_real_screen_and_interpreter(bugs, tmp_path):
    lessons = tool.taught(bugs, {})
    row_ = tool.one_bug(bugs[1], lessons, [], tmp_path / "bug", budget=30, curve_sizes=(), curve_seeds=1)
    assert row_["usable"] and all(row_["benchmark_holds"].values())
    assert row_["all_other_fixes"]["repaired"] and row_["all_other_fixes"]["is_the_published_fix"]
    assert row_["all_other_fixes"]["first_pass_rank"] == 1
    assert row_["screen_said_pass_fresh_interpreter_said_no"] == 0


# --------------------------------------------------------------------------- #
# the command line
# --------------------------------------------------------------------------- #
@pytest.fixture()
def on_disk(tmp_path, monkeypatch):
    data = tmp_path / "humanevalpack.jsonl"
    data.write_text("".join(json.dumps(r) + "\n" for r in ROWS))
    monkeypatch.setattr(tool, "quixbugs_lessons", lambda root: {})
    monkeypatch.setattr(tool, "split", lambda bugs, **k: (["Python/0", "Python/1"], ["Python/2", "Python/3"]))
    by_entry = {r["entry_point"]: r for r in ROWS}

    def stand_in_screen(where, programs, **k):
        text = (where / "test_prog.py").read_text()
        bug = next({"test": r["test"]} for entry, r in by_entry.items() if f"check({entry})" in text)
        return checker(bug)(programs)
    monkeypatch.setattr(tool, "screen", stand_in_screen)
    monkeypatch.setattr(tool, "accept", lambda bug, program, **k: passes(bug, program))
    return data


def run(on_disk, tmp_path, out, *more):
    return tool.main(["--humanevalfix", str(on_disk), "--quixbugs-dir", str(tmp_path), "--work-dir", str(tmp_path / "work"),
                      "--out", str(tmp_path / out), "--budget", "40", *more])


def test_main_writes_the_record(on_disk, tmp_path, capsys):
    assert run(on_disk, tmp_path, "dev.json") == 0
    record = json.loads((tmp_path / "dev.json").read_text())
    assert (record["schema"], record["authority"], record["model_calls"]) == (tool.SCHEMA, tool.AUTHORITY, 0)
    assert record["which"] == "development" and record["names"] == ["Python/0", "Python/1"]
    assert record["summary"]["all_other_fixes"]["repaired"] == 2
    assert record["lessons"]["given"] == 4
    assert record["budget"] == 40 and record["curve_budget"] == 40 and record["screen_limit_s"] == tool.SCREEN_LIMIT_S
    assert set(record["code_sha256"]) == {"canonical/runtime/edit_kind_learning_v1.py", "canonical/tools/humanevalfix_edit_kind_transfer_measure_v1.py",
                                         "canonical/swe_kernel/zygote_worker_pool_v1.py", "canonical/runtime/brokered_workspace_execution_v1.py"}
    assert record["benchmark"]["bugs"] == 4 and len(record["benchmark"]["humanevalfix_sha256"]) == 64
    printed = capsys.readouterr().out
    assert "Python/0" in printed and "Python/1" in printed


def test_main_asks_the_scored_bugs_only_when_told_to(on_disk, tmp_path):
    assert run(on_disk, tmp_path, "scored.json", "--which", "scored") == 0
    record = json.loads((tmp_path / "scored.json").read_text())
    assert record["names"] == ["Python/2", "Python/3"] and record["summary"]["all_other_fixes"]["repaired"] == 0


def test_main_takes_a_shard_and_names(on_disk, tmp_path):
    assert run(on_disk, tmp_path, "a.json", "--shard", "1/2") == 0
    assert json.loads((tmp_path / "a.json").read_text())["names"] == ["Python/1"]
    assert run(on_disk, tmp_path, "b.json", "--bugs", "Python/0", "Python/3") == 0
    assert json.loads((tmp_path / "b.json").read_text())["names"] == ["Python/0"]


def test_main_puts_shards_together_and_refuses_shards_measured_differently(on_disk, tmp_path):
    assert run(on_disk, tmp_path, "a.json", "--shard", "0/2") == 0
    assert run(on_disk, tmp_path, "b.json", "--shard", "1/2") == 0
    assert run(on_disk, tmp_path, "whole.json") == 0
    assert run(on_disk, tmp_path, "merged.json", "--merge", str(tmp_path / "b.json"), str(tmp_path / "a.json")) == 0
    merged, whole = (json.loads((tmp_path / name).read_text()) for name in ("merged.json", "whole.json"))
    assert merged["names"] == ["Python/0", "Python/1"] and "shard" not in merged

    def without_times(record):
        text = json.dumps(record["per_bug"], sort_keys=True)
        return json.loads(text, object_hook=lambda d: {k: v for k, v in d.items() if k != "seconds"})
    assert without_times(merged) == without_times(whole)
    assert merged["summary"]["all_other_fixes"] == whole["summary"]["all_other_fixes"]
    assert run(on_disk, tmp_path, "c.json", "--shard", "1/2", "--seed", "5") == 0
    with pytest.raises(SystemExit, match="same way"):
        run(on_disk, tmp_path, "bad.json", "--merge", str(tmp_path / "a.json"), str(tmp_path / "c.json"))


def test_main_shows_the_lessons_backwards_when_told_to_and_does_not_mix_the_two(on_disk, tmp_path):
    assert run(on_disk, tmp_path, "a.json", "--shard", "0/2") == 0
    assert run(on_disk, tmp_path, "b.json", "--shard", "1/2", "--lessons-backwards") == 0
    forwards, backwards = (json.loads((tmp_path / name).read_text()) for name in ("a.json", "b.json"))
    assert forwards["lessons_shown"] == "as_fixes" and backwards["lessons_shown"].startswith("backwards")
    assert backwards["summary"]["all_other_fixes"]["repaired"] == 0
    with pytest.raises(SystemExit, match="same way"):
        run(on_disk, tmp_path, "bad.json", "--merge", str(tmp_path / "a.json"), str(tmp_path / "b.json"))


def test_main_writes_what_is_done_after_every_bug(on_disk, tmp_path, monkeypatch):
    seen = []
    real = tool.one_bug

    def watched(bug, *a, **k):
        if (tmp_path / "dev.json").exists():
            seen.append(sorted(json.loads((tmp_path / "dev.json").read_text())["per_bug"]))
        return real(bug, *a, **k)
    monkeypatch.setattr(tool, "one_bug", watched)
    assert run(on_disk, tmp_path, "dev.json") == 0
    assert seen == [["Python/0"]]
