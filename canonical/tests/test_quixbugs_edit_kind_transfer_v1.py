"""The edit-kind learner beside the tree's repair solver on QuixBugs: the stand-in for pytest, the two ways of asking, the counting."""
from __future__ import annotations

import ast
import json
import pathlib
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402
from canonical.tools import quixbugs_edit_kind_transfer_measure_v1 as tool  # noqa: E402
from canonical.tests.test_quixbugs_one_fix_transfer_v1 import PROGRAMS, write_benchmark  # noqa: E402

HEF = [{"name": "Python/0", "buggy": "def inc(n):\n    return n - 1\n", "fixed": "def inc(n):\n    return n + 1\n"},
       {"name": "Python/1", "buggy": "def cap(v, top):\n    if v < top:\n        return v\n    return top\n",
        "fixed": "def cap(v, top):\n    if v <= top:\n        return v\n    return top\n"}]


# --------------------------------------------------------------------------- #
# the stand-in for what the benchmark's test files ask of pytest
# --------------------------------------------------------------------------- #
@pytest.fixture()
def stand_in():
    module = types.ModuleType("pytest_stand_in")
    exec(tool.PYTEST_STAND_IN, module.__dict__)
    return module


def test_the_stand_in_has_the_five_things_and_runs_the_buggy_side(stand_in):
    assert stand_in.use_correct is False and stand_in.run_slow is False
    with pytest.raises(stand_in.Skipped):
        stand_in.skip("slow")

    @stand_in.mark.parametrize("a,b", [(1, 2), (3, 4)])
    def cases(a, b):
        return a + b
    assert cases._cases == (["a", "b"], [(1, 2), (3, 4)]) and cases(1, 2) == 3

    @stand_in.mark.parametrize("x", [5, 6])
    def single(x):
        return x
    assert single._cases == (["x"], [5, 6])


@pytest.mark.parametrize("got, expected, rel, absolute, same", [
    (1.0000005, 1.0, None, None, True), (1.00001, 1.0, None, None, False), (0.0, 0.0, None, None, True),
    (1e-13, 0.0, None, None, True), (1e-9, 0.0, None, None, False), (-2.0000001, -2.0, None, None, True),
    (2.5, 2.0, None, 0.6, True), (2.7, 2.0, None, 0.6, False), (105.0, 100.0, 0.1, None, True), (120.0, 100.0, 0.1, None, False)])
def test_the_stand_ins_approx_agrees_with_pytests(stand_in, got, expected, rel, absolute, same):
    more = {k: v for k, v in (("rel", rel), ("abs", absolute)) if v is not None}
    assert (got == stand_in.approx(expected, **more)) is same
    assert (got != stand_in.approx(expected, **more)) is (not same)
    assert (got == pytest.approx(expected, **more)) is same                      # the real one says the same


def test_the_one_test_runs_every_case_and_fails_when_one_fails(tmp_path):
    project = tmp_path / "p"
    (project / "python_testcases").mkdir(parents=True)
    (project / "python_programs").mkdir()
    (project / "python_programs" / "__init__.py").write_text("")
    (project / "pytest.py").write_text(tool.PYTEST_STAND_IN)
    (project / tool.SCREEN_TEST).write_text(tool.SCREEN_TEST_TEXT.replace("test_NAME.py", "test_twice.py"))
    test_file = ("import pytest\nfrom python_programs.twice import twice\n\n\n@pytest.mark.parametrize('x,want', [(1, 2), (3, 6)])\n"
                 "def test_twice(x, want):\n    assert twice(x) == want\n\n\ndef test_slow():\n    if not pytest.run_slow:\n        pytest.skip('slow')\n    assert False\n")
    (project / "python_testcases" / "test_twice.py").write_text(test_file)

    def outcome(program: str) -> str:
        (project / "python_programs" / "twice.py").write_text(program)
        code = ("import sys, runpy\nsys.path.insert(0, '.')\nfor m in [m for m in sys.modules if m.startswith(('python_programs', 'pytest', 'quixbugs_tests'))]:\n"
                "    del sys.modules[m]\nspace = runpy.run_path('" + tool.SCREEN_TEST + "')\nspace['test_every_case']()\n")
        import subprocess
        # -B: the two programs have the same length and are written within the same second -- a kept bytecode file would be taken for the new source
        done = subprocess.run([sys.executable, "-B", "-c", code], cwd=project, capture_output=True, text=True)
        return "passes" if done.returncode == 0 else done.stderr.strip().split("\n")[-1].split(":")[0]

    assert outcome("def twice(x):\n    return 2 * x\n") == "passes"                 # the skipped test does not count against it
    assert outcome("def twice(x):\n    return x + 1\n") == "AssertionError"         # right for 1, wrong for 3: every case is run
    (project / "python_testcases" / "test_twice.py").write_text("def helper():\n    pass\n")
    assert outcome("def twice(x):\n    return 2 * x\n") == "AssertionError"         # a test file with no test in it is not a pass


# --------------------------------------------------------------------------- #
# the projects, the bugs, the lessons
# --------------------------------------------------------------------------- #
@pytest.fixture()
def quixbugs(tmp_path):
    return write_benchmark(tmp_path / "quixbugs")


def test_screen_project_is_the_benchmarks_project_with_the_stand_in_in_place_of_its_configuration(quixbugs, tmp_path):
    made = tool.screen_project(quixbugs, "add_one", tmp_path / "work")
    assert made == tmp_path / "work" / "add_one"
    assert not (made / "conftest.py").exists()
    assert (made / "pytest.py").read_text() == tool.PYTEST_STAND_IN
    assert "test_add_one.py" in (made / tool.SCREEN_TEST).read_text() and "test_NAME.py" not in (made / tool.SCREEN_TEST).read_text()
    assert (made / "python_testcases" / "test_add_one.py").read_text() == (quixbugs / "python_testcases" / "test_add_one.py").read_text()
    assert not (made / "correct_python_programs").exists()


def test_bugs_of_names_them_as_lessons_are_named_and_keeps_the_published_fix(quixbugs):
    bugs = tool.bugs_of(quixbugs, ["add_one", "at_most"])
    assert [(b["name"], b["program"], b["entry"]) for b in bugs] == [("quixbugs/add_one", "add_one", "add_one"), ("quixbugs/at_most", "at_most", "at_most")]
    first = lambda text: ast.unparse(ast.parse(text).body[0])                    # noqa: E731  (the benchmark's files end with a description in a string)
    assert first(bugs[0]["fixed"]) == first(PROGRAMS["add_one"][1]) and first(bugs[0]["buggy"]) == first(PROGRAMS["add_one"][0])
    assert not kinds.same_program(bugs[0]["fixed"], bugs[0]["buggy"])
    assert len(tool.bugs_of(quixbugs)) == 4


def test_taught_shows_every_fix_of_both_benchmarks_once(quixbugs):
    lessons = tool.taught(quixbugs, HEF)
    assert lessons.lessons == ["Python/0", "Python/1", "quixbugs/add_one", "quixbugs/at_least", "quixbugs/at_most"]
    assert lessons.taught_nothing == ["quixbugs/always_right"]                    # its buggy and correct programs are the same


# --------------------------------------------------------------------------- #
# one bug, with stand-ins for the two runners
# --------------------------------------------------------------------------- #
def runs(name: str):
    checks = {"add_one": lambda f: f(1) == 2 and f(-1) == 0,
              "at_most": lambda f: f(1, 3) == 1 and f(5, 3) == 3 and type(f(3.0, 3)) is float,
              "at_least": lambda f: f(5, 3) == 5 and f(1, 3) == 3 and type(f(3.0, 3)) is float}

    def accepted(program: str) -> bool:
        space: dict = {}
        try:
            exec(compile(program, "<stand-in>", "exec"), space)
            return bool(checks[name](space[name]))
        except BaseException:
            return False
    return accepted


def test_a_fix_of_the_same_kind_from_the_other_benchmark_repairs_the_bug(quixbugs, tmp_path):
    lessons = tool.taught(quixbugs, HEF)
    bug = tool.bugs_of(quixbugs, ["add_one"])[0]
    accepted = runs("add_one")
    row = tool.one_bug(quixbugs, bug, lessons, tmp_path / "w", budget=50, check=tool.one_at_a_time(accepted), accepted=accepted)
    assert row["usable"] and row["benchmark_holds"] == {"buggy_fails_in_the_benchmarks_runner": True, "published_fix_passes_in_the_benchmarks_runner": True}
    assert row["budget"] == 50
    other = row["another_benchmark"]
    assert other["repaired"] and other["is_the_published_fix"] and other["lessons"] == 2 and other["voted_by"] == ["Python/0"]
    assert other["lines"] == {"removed": ["return x - 1"], "put_in": ["return x + 1"]}
    assert row["all_other_fixes"]["lessons"] == 4                                 # both HumanEvalFix fixes and the two other QuixBugs fixes: never its own
    assert row["own_fix_shown"] == {"rank_among_its_own_candidates": 1}
    assert row["candidates_run"] >= 1 and row["screen_said_pass_runner_said_no"] == 0


def test_the_bugs_own_fix_is_never_among_its_lessons(quixbugs, tmp_path):
    lessons = tool.taught(quixbugs, [])                                           # nothing from the other benchmark
    bug = tool.bugs_of(quixbugs, ["add_one"])[0]
    accepted = runs("add_one")
    row = tool.one_bug(quixbugs, bug, lessons, tmp_path / "w", budget=50, check=tool.one_at_a_time(accepted), accepted=accepted)
    assert row["another_benchmark"] == {"lessons": 0, "candidates": 0, "published_fix_rank": None, "first_pass_rank": None, "repaired": False}
    assert row["all_other_fixes"]["lessons"] == 2 and not row["all_other_fixes"]["repaired"]      # the comparison fixes do not make "+ 1"
    assert row["own_fix_shown"] == {"rank_among_its_own_candidates": 1}


def test_a_bug_whose_benchmark_does_not_hold_is_not_asked(quixbugs, tmp_path):
    lessons = tool.taught(quixbugs, HEF)
    bug = tool.bugs_of(quixbugs, ["add_one"])[0]
    row = tool.one_bug(quixbugs, bug, lessons, tmp_path / "w", check=tool.one_at_a_time(lambda p: True), accepted=lambda p: True)
    assert row == {"benchmark_holds": {"buggy_fails_in_the_benchmarks_runner": False, "published_fix_passes_in_the_benchmarks_runner": True},
                   "usable": False, "asked_through": "the_benchmarks_runner_alone"}


def test_one_at_a_time_names_the_first_that_is_accepted():
    check = tool.one_at_a_time(lambda program: program in ("c", "d"))
    assert check(["a", "b", "c", "d"]) == 2 and check(["a", "b"]) is None and check([]) is None


def test_where_the_screen_cannot_tell_the_bug_from_its_fix_the_benchmarks_runner_is_asked_about_fewer_candidates(quixbugs, tmp_path, monkeypatch):
    lessons = tool.taught(quixbugs, HEF)
    bug = tool.bugs_of(quixbugs, ["add_one"])[0]
    accepted = runs("add_one")
    asked_of_the_screen = []
    monkeypatch.setattr(tool, "screen", lambda project, name, programs, **k: asked_of_the_screen.append(len(programs)) or 0)   # says pass to everything
    row = tool.one_bug(quixbugs, bug, lessons, tmp_path / "w", budget=1000, accepted=accepted)
    assert row["benchmark_holds"]["buggy_fails_in_the_screen"] is False and row["benchmark_holds"]["published_fix_passes_in_the_screen"] is True
    assert row["asked_through"] == "the_benchmarks_runner_alone" and row["budget"] == tool.BUDGET_WITHOUT_THE_SCREEN
    assert asked_of_the_screen == [1, 1]                                          # only the two checks of the benchmark; no candidate went there
    assert row["another_benchmark"]["repaired"]

    def broken(project, name, programs, **k):
        raise RuntimeError("the candidate screen did not answer with authority: {}")
    monkeypatch.setattr(tool, "screen", broken)
    row = tool.one_bug(quixbugs, bug, lessons, tmp_path / "w2", budget=1000, accepted=accepted)
    assert "authority" in row["benchmark_holds"]["screen_error"] and row["asked_through"] == "the_benchmarks_runner_alone"
    assert row["another_benchmark"]["repaired"]


def test_where_the_screen_tells_them_apart_candidates_go_through_it_first(quixbugs, tmp_path, monkeypatch):
    lessons = tool.taught(quixbugs, HEF)
    bug = tool.bugs_of(quixbugs, ["add_one"])[0]
    accepted = runs("add_one")
    monkeypatch.setattr(tool, "screen", lambda project, name, programs, **k: next((n for n, p in enumerate(programs) if accepted(p)), None))
    row = tool.one_bug(quixbugs, bug, lessons, tmp_path / "w", budget=1000, accepted=accepted)
    assert row["asked_through"] == "the_screen_then_the_benchmarks_runner" and row["budget"] == 1000
    assert all(row["benchmark_holds"].values()) and len(row["benchmark_holds"]) == 4
    assert row["another_benchmark"]["repaired"] and row["another_benchmark"]["is_the_published_fix"]


def screen_works() -> bool:
    try:
        from canonical.runtime import brokered_workspace_execution_v1 as broker
        return bool(broker.namespace_broker_available())
    except Exception:
        return False


@pytest.mark.skipif(not screen_works(), reason="the confined candidate screen is not available on this machine")
def test_the_real_screen_runs_the_benchmarks_test_file_through_the_stand_in(quixbugs, tmp_path):
    project = tool.screen_project(quixbugs, "at_most", tmp_path / "work")
    buggy, fixed = (ast.unparse(ast.parse(text)) for text in PROGRAMS["at_most"])
    assert tool.screen(project, "at_most", [buggy]) is None
    assert tool.screen(project, "at_most", [buggy, "def at_most(x, top):\n    while True:\n        pass\n", fixed], limit_s=0.5) == 2
    assert tool.screen(project, "at_most", []) is None


# --------------------------------------------------------------------------- #
# what it came to, beside the solver
# --------------------------------------------------------------------------- #
def answer(rank=None, published=None, fix_rank=None):
    return {"repaired": rank is not None, "first_pass_rank": rank, "is_the_published_fix": published, "published_fix_rank": fix_rank}


PER_BUG = {
    "a": {"usable": True, "asked_through": "the_screen_then_the_benchmarks_runner", "another_benchmark": answer(5, True, 5), "all_other_fixes": answer(2, True, 2),
          "candidates_run": 7, "seconds": 1.0, "screen_said_pass_runner_said_no": 0},
    "b": {"usable": True, "asked_through": "the_benchmarks_runner_alone", "another_benchmark": answer(), "all_other_fixes": answer(150, False, 900),
          "candidates_run": 300, "seconds": 2.5, "screen_said_pass_runner_said_no": 1},
    "c": {"usable": True, "asked_through": "the_screen_then_the_benchmarks_runner", "another_benchmark": answer(40, False), "all_other_fixes": answer(),
          "candidates_run": 1040, "seconds": 3.0, "screen_said_pass_runner_said_no": 0},
    "d": {"usable": False, "asked_through": "the_benchmarks_runner_alone", "benchmark_holds": {}},
}


def test_summarise_counts_and_sets_the_learner_beside_the_solver():
    solver = {"the_solver_with_nothing_taught": ["a", "d"], "the_solver_with_all_other_fixes_taught_first": ["a", "b", "d"]}
    summary = tool.summarise(PER_BUG, solver)
    assert (summary["bugs_asked"], summary["bugs_usable"], summary["not_usable"]) == (4, 3, ["d"])
    assert summary["asked_through_the_benchmarks_runner_alone"] == ["b"]
    assert summary["another_benchmark"] == {"bugs": 3, "repaired": 2, "repaired_within": {"1": 0, "10": 1, "100": 2, "1000": 2},
                                            "the_repair_is_the_published_fix": 1, "the_repair_is_another_program": 1,
                                            "published_fix_among_the_candidates": 1, "which": ["a", "c"]}
    assert summary["all_other_fixes"]["repaired"] == 2 and summary["all_other_fixes"]["which"] == ["a", "b"]
    assert summary["all_other_fixes"]["repaired_within"] == {"1": 0, "10": 1, "100": 1, "1000": 2}
    assert (summary["candidates_run"], summary["seconds"], summary["screen_said_pass_runner_said_no"]) == (1347, 6.5, 1)
    beside = summary["beside_the_trees_repair_solver"]
    assert beside["another_benchmark__beside__the_solver_with_nothing_taught"] == {
        "the_learner": 2, "the_solver": 2, "both": ["a"], "the_learner_alone": ["c"], "the_solver_alone": ["d"], "neither": 1}
    assert beside["all_other_fixes__beside__the_solver_with_all_other_fixes_taught_first"] == {
        "the_learner": 2, "the_solver": 3, "both": ["a", "b"], "the_learner_alone": [], "the_solver_alone": ["d"], "neither": 1}
    assert "beside_the_trees_repair_solver" not in tool.summarise(PER_BUG)


def test_solver_record_reads_what_the_solver_repaired(tmp_path):
    path = tmp_path / "solver.json"
    path.write_text(json.dumps({"summary": {"empty_memory": {"which": ["sieve", "knapsack"]}, "other_fixes": {"repaired_from_memory": ["gcd", "knapsack"]}}}))
    assert tool.solver_record(path) == {"the_solver_with_nothing_taught": ["knapsack", "sieve"],
                                        "the_solver_with_all_other_fixes_taught_first": ["gcd", "knapsack", "sieve"]}


def test_the_trees_own_solver_record_is_readable():
    record = tool.solver_record(ROOT / "canonical/verification/QUIXBUGS_REPAIR_SOLVER_20261111_V1.json")
    assert record["the_solver_with_nothing_taught"] == ["get_factors", "knapsack", "pascal", "quicksort", "sieve"]
    assert record["the_solver_with_all_other_fixes_taught_first"] == ["gcd", "get_factors", "knapsack", "pascal", "quicksort", "sieve"]


# --------------------------------------------------------------------------- #
# the command line
# --------------------------------------------------------------------------- #
@pytest.fixture()
def on_disk(quixbugs, tmp_path, monkeypatch):
    hef_file = tmp_path / "hef.jsonl"
    hef_file.write_text("")
    monkeypatch.setattr(tool.hef, "load_bugs", lambda path: list(HEF))
    real = tool.one_bug

    def with_stand_ins(root, bug, lessons, work, **more):
        accepted = runs(bug["program"]) if bug["program"] != "always_right" else (lambda p: True)
        return real(root, bug, lessons, work, check=tool.one_at_a_time(accepted), accepted=accepted, **more)
    monkeypatch.setattr(tool, "one_bug", with_stand_ins)
    return quixbugs, hef_file


def run(on_disk, tmp_path, out, *more):
    quixbugs, hef_file = on_disk
    return tool.main(["--quixbugs-dir", str(quixbugs), "--humanevalfix", str(hef_file), "--work-dir", str(tmp_path / "work"),
                      "--out", str(tmp_path / out), "--budget", "60", "--solver-record", str(tmp_path / "no-such-file.json"), *more])


def test_main_writes_the_record(on_disk, tmp_path, capsys):
    assert run(on_disk, tmp_path, "all.json") == 0
    record = json.loads((tmp_path / "all.json").read_text())
    assert (record["schema"], record["authority"], record["model_calls"], record["budget"]) == (tool.SCHEMA, tool.AUTHORITY, 0, 60)
    assert record["names"] == ["add_one", "always_right", "at_least", "at_most"]
    assert record["lessons"] == {"given": 5, "from_humanevalfix": 2, "from_quixbugs": 3, "taught_nothing": ["quixbugs/always_right"],
                                 "operators": record["lessons"]["operators"]}
    summary = record["summary"]
    assert summary["not_usable"] == ["always_right"] and summary["bugs_usable"] == 3
    assert summary["another_benchmark"]["which"] == ["add_one", "at_most"]        # each has a fix of its kind among the two HumanEvalFix fixes
    assert summary["all_other_fixes"]["which"] == ["add_one", "at_most"]          # no fix shown turns > into >=
    assert "beside_the_trees_repair_solver" not in summary
    assert len(record["benchmark"]["quixbugs_sha256"]) == 64 and len(record["code_sha256"]) == 6
    assert "add_one" in capsys.readouterr().out


def test_main_takes_names_and_shards_and_puts_shards_together(on_disk, tmp_path):
    assert run(on_disk, tmp_path, "a.json", "--shard", "0/2") == 0
    assert run(on_disk, tmp_path, "b.json", "--shard", "1/2") == 0
    assert json.loads((tmp_path / "a.json").read_text())["names"] == ["add_one", "at_least"]
    assert json.loads((tmp_path / "b.json").read_text())["names"] == ["always_right", "at_most"]
    assert run(on_disk, tmp_path, "merged.json", "--merge", str(tmp_path / "b.json"), str(tmp_path / "a.json")) == 0
    merged = json.loads((tmp_path / "merged.json").read_text())
    assert sorted(merged["per_bug"]) == ["add_one", "always_right", "at_least", "at_most"] and "shard" not in merged
    assert merged["summary"]["another_benchmark"]["which"] == ["add_one", "at_most"]
    assert run(on_disk, tmp_path, "one.json", "--programs", "at_most") == 0
    assert json.loads((tmp_path / "one.json").read_text())["names"] == ["at_most"]
    assert run(on_disk, tmp_path, "c.json", "--shard", "1/2", "--budget", "61") == 0
    with pytest.raises(SystemExit, match="same way"):
        tool.main(["--quixbugs-dir", str(on_disk[0]), "--humanevalfix", str(on_disk[1]), "--work-dir", str(tmp_path / "w"),
                   "--out", str(tmp_path / "bad.json"), "--merge", str(tmp_path / "a.json"), str(tmp_path / "c.json")])
