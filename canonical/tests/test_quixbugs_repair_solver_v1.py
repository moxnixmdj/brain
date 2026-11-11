"""Tests of the measurement "what the repair solver repairs, and what a lesson adds to it".

The solver that is measured is not this file's subject: most tests here put a stand-in where
the solver's process goes (and the stand-in organ and oracle of the earlier measurement's tests
where the store and the tests go), so that what is pinned is the measurement -- which bug is
given to the solver with which store, what counts as repaired, what counts as coming from
memory, and how it is added up. One class runs real processes around a stand-in worker, and
one class at the end runs the real solver with the real organ on three small programs.
"""
from __future__ import annotations

import inspect
import json
import os
import pathlib
import shutil
import sys
import tempfile
import threading
import time
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.tools import quixbugs_one_fix_transfer_measure_v1 as bench  # noqa: E402
from canonical.tools import quixbugs_repair_solver_measure_v1 as tool  # noqa: E402
from canonical.tests import test_quixbugs_one_fix_transfer_v1 as small  # noqa: E402 -- the small benchmark, the stand-in organ and oracle

EVERY = ("add_one", "at_most", "at_least", "capped", "always_right")
NAMES = ("add_one", "at_most", "at_least", "capped")
# at_most and capped have the same one-line defect; add_one and at_least have defects of their own.


def _program(args):
    return pathlib.Path(args["retained_learning"]["target_path"]).stem


def _fitting(held, source, name):
    """What a rule held in memory makes of this source, if one fits and the tests then pass."""
    lines = source.split("\n")
    for rule in held:
        if rule["removed"] in lines:
            candidate = "\n".join(rule["added"] if line == rule["removed"] else line for line in lines)
            if small.FakeOracle(name)(candidate).passed:
                return candidate
    return None


class FakeSolver:
    """Stands where the solver's process goes. Like the solver it repairs IN PLACE: from memory when
    a rule in the store it was given fits (no search), otherwise by 'search' if the bug is one it
    can find; after a search it keeps a lesson in that store."""

    def __init__(self, can_find=()):
        self.can_find = set(can_find)
        self.finds_only_from_an_empty_store: set = set()
        self.keeps_no_lesson: dict = {}                 # name -> the reason it gives
        self.says_pass_and_writes: dict = {}            # name -> the text it leaves on disk
        self.says_pass_and_writes_nothing: set = set()
        self.writes_the_fix_and_says_nothing: set = set()   # the fix is on disk; the report says no repair
        self.stopped: set = set()                       # still running at the wall limit
        self.stopped_having_written_the_fix: set = set()
        self.breaks: set = set()                        # the worker dies
        self.searches_though_memory_fits: set = set()
        self.seconds: dict = {}                         # name, or (question, name) -> seconds the run says it took
        self.calls: list = []

    def __call__(self, where, args, wall_limit_s):
        name = _program(args)
        target = where / args["retained_learning"]["target_path"]
        memory = where / args["retained_learning"]["db_path"]
        source = target.read_text()
        held = small.FakeStore(memory)._read() if memory.exists() else []
        project = where / args["source_root"]
        self.calls.append({"name": name, "where": where, "args": json.loads(json.dumps(args)), "wall_limit_s": wall_limit_s,
                           "source": source, "held": [rule["taught_on"] for rule in held],
                           "folders": sorted(p.name for p in where.iterdir()),
                           "project_files": sorted(str(p.relative_to(project)) for p in project.rglob("*") if p.is_file()),
                           "texts": {str(p.relative_to(where)): p.read_text() for p in where.rglob("*") if p.is_file()}})
        buggy, correct = small.PROGRAMS[name]
        fix = source.replace(buggy, correct)
        if name in self.breaks:
            return {"finished": False, "stopped_at_the_wall_limit": False, "seconds": 0.01, "worker_returncode": 1,
                    "worker_error": "Traceback: the worker died"}
        if name in self.stopped_having_written_the_fix:
            target.write_text(fix)
        if name in self.stopped or name in self.stopped_having_written_the_fix:
            return {"finished": False, "stopped_at_the_wall_limit": True, "seconds": float(wall_limit_s)}

        def answer(passed, status, searches, hit=False, teaching=None):
            retained = {"enabled": True, "hit": hit, "recall_strategy": "statement" if hit else None}
            if teaching is not None:
                retained["teaching"] = teaching
            return {"finished": True, "stopped_at_the_wall_limit": False,
                    "seconds": self.seconds.get((where.parent.name, name), self.seconds.get(name, 0.5 if hit else 20.0)),
                    "processes_started": 3 if hit else 60,
                    "result": {"pass": passed, "applied": passed, "status": status, "repair_status": status + "__DETAIL",
                               "repair_mode": "scoped_retained_repair" if hit else None,
                               "repair_search_invocations": searches, "retained_learning": retained}}

        if name in self.says_pass_and_writes_nothing:
            return answer(True, "PASS__FAKE", 1)
        if name in self.says_pass_and_writes:
            target.write_text(self.says_pass_and_writes[name])
            return answer(True, "PASS__FAKE", 1)
        if name in self.writes_the_fix_and_says_nothing:
            target.write_text(fix)
            return answer(False, "OPEN__FAKE", 1)
        from_memory = _fitting(held, source, name)
        if from_memory is not None:
            target.write_text(from_memory)
            return answer(True, "PASS__FAKE", 1 if name in self.searches_though_memory_fits else 0, hit=True)
        if name in self.can_find and not (name in self.finds_only_from_an_empty_store and held):
            target.write_text(fix)
            if name in self.keeps_no_lesson:
                teaching = {"crystallized": False, "reason": self.keeps_no_lesson[name]}
            else:
                taught = small.FakeStore(memory).crystallize_code_fix(
                    before_snippet=source, after_snippet=fix, language="python", error_class=bench.ERROR_CLASS,
                    contract=bench.CONTRACT, training_verifier=None)
                teaching = {"crystallized": bool(taught["crystallized"]), "reason": taught.get("reason")}
            return answer(True, "PASS__FAKE", 1, teaching=teaching)
        return answer(False, "OPEN__FAKE", 1)


class FakeProposer:
    """Stands where the question "does memory propose a repair?" goes."""

    def __init__(self):
        self.cannot_be_asked: set = set()
        self.calls: list = []

    def __call__(self, where, args, wall_limit_s):
        name = _program(args)
        source = (where / args["retained_learning"]["target_path"]).read_text()
        held = small.FakeStore(where / args["retained_learning"]["db_path"])._read()
        self.calls.append({"name": name, "where": where, "source": source, "held": [rule["taught_on"] for rule in held],
                           "wall_limit_s": wall_limit_s})
        if name in self.cannot_be_asked:
            return {"finished": False, "stopped_at_the_wall_limit": True, "seconds": float(wall_limit_s)}
        return {"finished": True, "stopped_at_the_wall_limit": False, "seconds": 0.1, "processes_started": 1,
                "result": {"proposed": _fitting(held, source, name) is not None, "retained_learning": {}, "unified_diffs": []}}


class WithAStandInSolver(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="solver-measure-test-"))
        self.root = small.write_benchmark(self.dir / "bench", names=EVERY)
        small.FakeStore.recalls, small.FakeStore.refuse, small.FakeStore.lie_about = [], set(), set()
        small.FakeStore.refuse_on_import, small.FakeStore.shipped = set(), []
        small.FakeOracle.log = []
        self._saved = (bench._store, bench.oracle_for, tool.solve, tool.propose)
        bench._store = small.FakeStore
        bench.oracle_for = lambda project, name, timeout_s=bench.DEFAULT_TIMEOUT_S: small.FakeOracle(name)
        self.solver = FakeSolver(can_find=("add_one", "at_most"))
        self.proposer = FakeProposer()

    def tearDown(self):
        bench._store, bench.oracle_for, tool.solve, tool.propose = self._saved
        shutil.rmtree(self.dir, ignore_errors=True)

    # -- helpers ------------------------------------------------------------------------------------------------
    def _measure(self, names=NAMES, **options):
        options.setdefault("workers", 1)
        return tool.measure(self.root, list(names), self.dir / "work", solve_with=self.solver, propose_with=self.proposer,
                            **options)

    def _buggy(self, name):
        return (self.root / "python_programs" / f"{name}.py").read_text()

    def _fixed(self, name):
        return self._buggy(name).replace(*small.PROGRAMS[name])

    def _calls(self, question, name=None):
        return [call for call in self.solver.calls
                if call["where"].parent.name == question and (name is None or call["name"] == name)]

    # -- nothing taught -----------------------------------------------------------------------------------------
    def test_every_bug_is_given_to_the_solver_once_from_an_empty_store(self):
        measured = self._measure()
        self.assertEqual(measured["targets"], list(NAMES))
        for name in NAMES:
            (call,) = self._calls("empty_memory", name)
            self.assertEqual(call["held"], [])
            self.assertEqual(call["source"], self._buggy(name))
        self.assertEqual(sorted(measured["outcomes"]["empty_memory"]), sorted(NAMES))

    def test_the_solver_gets_the_program_and_its_tests_and_not_the_answer(self):
        self._measure()
        (call,) = self._calls("empty_memory", "at_most")
        self.assertEqual(call["folders"], ["memory", "project", "reports"])
        self.assertIn("python_programs/at_most.py", call["project_files"])
        self.assertIn("python_testcases/test_at_most.py", call["project_files"])
        self.assertIn("conftest.py", call["project_files"])
        self.assertFalse([path for path in call["project_files"] if "correct" in path])
        self.assertFalse([path for path in call["project_files"] if "capped" in path or "add_one" in path])
        # nowhere in what the solver is given is the line that repairs it
        self.assertIn("if x <= top:", self._fixed("at_most"))
        self.assertTrue(call["texts"])
        self.assertFalse([path for path, text in call["texts"].items() if "if x <= top:" in text])

    def test_the_solver_is_told_where_things_are_and_given_no_search_bounds_of_ours(self):
        self._measure(timeout_s=5, wall_limit_s=77)
        (call,) = self._calls("empty_memory", "add_one")
        self.assertEqual(call["args"], {
            "source_root": "project", "test_paths": ["project/python_testcases/test_add_one.py"],
            "output_path": "reports/solver.json", "timeout_s": 5,
            "retained_learning": {"enabled": True, "db_path": "memory/skills.sqlite",
                                  "target_path": "project/python_programs/add_one.py",
                                  "contract": bench.CONTRACT, "context": bench.CONTEXT,
                                  "allow_operator_generalization": True, "allow_cross_scope_transfer": True}})
        self.assertEqual({call["wall_limit_s"] for call in self.solver.calls}, {77})
        self.assertEqual({call["wall_limit_s"] for call in self.proposer.calls}, {77})
        self.assertNotIn("retained_learning", tool.solver_args("add_one", timeout_s=5, memory=False))
        self.assertEqual(tool.solver_args("add_one", timeout_s=5, memory=False),
                         {key: value for key, value in call["args"].items() if key != "retained_learning"})

    def test_the_arguments_do_not_share_the_contract_with_the_next_bug(self):
        first = tool.solver_args("add_one", timeout_s=8)
        first["retained_learning"]["contract"]["scope_id"] = "changed"
        first["retained_learning"]["context"]["dependencies"]["x"] = 1
        second = tool.solver_args("at_most", timeout_s=8)
        self.assertEqual(second["retained_learning"]["contract"], {"schema_version": 1, "scope_id": "quixbugs-python",
                                                                  "verification_kind": "TEST_SUITE"})
        self.assertEqual(second["retained_learning"]["context"], {"dependencies": {}, "preconditions": {}})

    def test_a_program_that_already_passes_is_never_given_to_the_solver_and_never_taught(self):
        measured = self._measure(names=EVERY)
        self.assertEqual(measured["programs"], list(EVERY))
        self.assertNotIn("always_right", measured["targets"])
        self.assertFalse([call for call in self.solver.calls + self.proposer.calls if call["name"] == "always_right"])
        self.assertNotIn("always_right", measured["lessons"])
        self.assertEqual(tool.summarise(measured)["programs"], 5)
        self.assertEqual(tool.summarise(measured)["usable_as_targets"], 4)

    def test_a_census_made_before_is_used_as_it_is(self):
        checked = bench.census(self.root, list(NAMES), self.dir / "census")
        checked["capped"]["can_be_a_target"] = False
        measured = self._measure(checked=checked)
        self.assertEqual(measured["targets"], ["add_one", "at_most", "at_least"])
        self.assertEqual(measured["census"], checked)
        self.assertFalse((self.dir / "work" / "census").exists())

    def test_without_a_census_one_is_made_in_the_work_directory(self):
        measured = self._measure()
        self.assertTrue((self.dir / "work" / "census").is_dir())
        self.assertTrue(all(measured["census"][name]["can_be_a_target"] for name in NAMES))

    def test_what_was_in_the_work_directory_before_is_gone(self):
        stale = self.dir / "work" / "empty_memory" / "add_one" / "memory" / "skills.sqlite"
        small.FakeStore(stale).crystallize_code_fix(
            before_snippet=self._buggy("add_one"), after_snippet=self._fixed("add_one"), language="python",
            error_class=bench.ERROR_CLASS, contract=bench.CONTRACT, training_verifier=None)
        (self.dir / "work" / "left_over.txt").write_text("old")
        self._measure()
        self.assertEqual(self._calls("empty_memory", "add_one")[0]["held"], [])
        self.assertFalse((self.dir / "work" / "left_over.txt").exists())

    # -- what counts as repaired --------------------------------------------------------------------------------
    def test_a_search_that_finds_the_fix_is_a_repair_with_the_published_fix(self):
        measured = self._measure()
        outcome = measured["outcomes"]["empty_memory"]["at_most"]
        self.assertTrue(outcome["repaired"])
        self.assertTrue(outcome["finished"] and outcome["solver_says_pass"] and outcome["solver_says_applied"])
        self.assertTrue(outcome["file_changed"] and outcome["second_check_passes"] and outcome["is_the_published_fix"])
        self.assertFalse(outcome["stopped_at_the_wall_limit"])
        self.assertEqual(outcome["lines_changed"], {"removed": ["if x < top:"], "put_in": ["if x <= top:"]})
        self.assertEqual((outcome["status"], outcome["repair_status"], outcome["repair_mode"]), ("PASS__FAKE", "PASS__FAKE__DETAIL", None))
        self.assertEqual((outcome["searches"], outcome["memory_hit"], outcome["memory_strategy"]), (1, False, None))
        self.assertEqual((outcome["seconds"], outcome["processes_started"]), (20.0, 60))
        self.assertEqual((outcome["lesson_kept_after"], outcome["lesson_not_kept_because"]), (True, None))
        self.assertNotIn("worker_error", outcome)

    def test_a_bug_the_solver_does_not_repair_is_left_as_it_was_and_not_counted(self):
        measured = self._measure()
        outcome = measured["outcomes"]["empty_memory"]["at_least"]
        self.assertFalse(outcome["repaired"] or outcome["file_changed"] or outcome["second_check_passes"])
        self.assertFalse(outcome["solver_says_pass"] or outcome["solver_says_applied"])
        self.assertEqual(outcome["status"], "OPEN__FAKE")
        self.assertEqual((outcome["lesson_kept_after"], outcome["lesson_not_kept_because"]), (None, None))
        self.assertNotIn("is_the_published_fix", outcome)
        self.assertNotIn("lines_changed", outcome)
        self.assertEqual((self.dir / "work" / "empty_memory" / "at_least" / "project" / "python_programs" / "at_least.py").read_text(),
                         self._buggy("at_least"))
        # nothing was asked of the tests about a file that did not change
        self.assertNotIn(("at_least", self._buggy("at_least")), small.FakeOracle.log[len(NAMES) * 2:])

    def test_the_solvers_word_alone_is_not_a_repair(self):
        self.solver.says_pass_and_writes_nothing = {"at_most"}
        wrong = self._buggy("add_one").replace("x - 1", "x - 2")
        self.solver.says_pass_and_writes = {"add_one": wrong}
        measured = self._measure()
        unchanged, failing = (measured["outcomes"]["empty_memory"][name] for name in ("at_most", "add_one"))
        self.assertTrue(unchanged["solver_says_pass"] and unchanged["solver_says_applied"])
        self.assertFalse(unchanged["file_changed"] or unchanged["second_check_passes"] or unchanged["repaired"])
        self.assertTrue(failing["solver_says_pass"] and failing["file_changed"])
        self.assertFalse(failing["second_check_passes"] or failing["repaired"] or failing["is_the_published_fix"])
        self.assertIn(("add_one", wrong), small.FakeOracle.log)          # the tests were asked about the file on disk
        summary = tool.summarise(measured)
        self.assertEqual(summary["empty_memory"]["solver_said_pass_but_the_second_check_did_not"], ["add_one"])
        self.assertEqual(summary["empty_memory"]["repaired"], 0)
        self.assertEqual(summary["empty_memory"]["which"], [])
        # neither is asked again: there is no repair whose lesson could have been kept
        self.assertEqual(measured["outcomes"]["same_bug_again"], {})

    def test_a_passing_file_without_the_solvers_word_is_not_a_repair(self):
        self.solver.can_find = set()
        self.solver.writes_the_fix_and_says_nothing = {"at_most"}
        self.solver.stopped_having_written_the_fix = {"capped"}
        measured = self._measure()
        for name in ("at_most", "capped"):
            outcome = measured["outcomes"]["empty_memory"][name]
            self.assertTrue(outcome["file_changed"] and outcome["second_check_passes"], name)
            self.assertFalse(outcome["solver_says_pass"], name)
            self.assertFalse(outcome["repaired"], name)
        self.assertEqual(tool.summarise(measured)["empty_memory"]["repaired"], 0)
        self.assertEqual(tool.summarise(measured)["empty_memory"]["solver_said_pass_but_the_second_check_did_not"], [])

    def test_said_pass_without_applied_is_not_a_repair(self):
        real = self.solver

        def not_applied(where, args, wall_limit_s):
            run = real(where, args, wall_limit_s)
            if run.get("result", {}).get("pass"):
                run["result"]["applied"] = False
            return run
        measured = tool.measure(self.root, list(NAMES), self.dir / "work", workers=1, solve_with=not_applied,
                                propose_with=self.proposer)
        outcome = measured["outcomes"]["empty_memory"]["at_most"]
        self.assertTrue(outcome["solver_says_pass"] and outcome["file_changed"] and outcome["second_check_passes"])
        self.assertFalse(outcome["solver_says_applied"] or outcome["repaired"])

    def test_a_repair_other_than_the_published_one_is_a_repair_and_is_said_to_be_another(self):
        other = self._buggy("add_one").replace("return x - 1", "return x - 1 + 2")
        self.solver.says_pass_and_writes = {"add_one": other}
        measured = self._measure()
        outcome = measured["outcomes"]["empty_memory"]["add_one"]
        self.assertTrue(outcome["repaired"])
        self.assertFalse(outcome["is_the_published_fix"])
        self.assertEqual(outcome["lines_changed"], {"removed": ["return x - 1"], "put_in": ["return x - 1 + 2"]})
        summary = tool.summarise(measured)["empty_memory"]
        self.assertEqual((summary["repaired"], summary["which"], summary["of_which_with_the_published_fix"]),
                         (2, ["add_one", "at_most"], 1))

    def test_a_run_that_was_stopped_or_broke_is_not_a_repair_and_is_counted_as_what_it_was(self):
        self.solver.stopped = {"at_least", "capped"}
        self.solver.breaks = {"add_one"}
        measured = self._measure(wall_limit_s=33)
        stopped, broken = (measured["outcomes"]["empty_memory"][name] for name in ("at_least", "add_one"))
        self.assertTrue(stopped["stopped_at_the_wall_limit"])
        self.assertFalse(stopped["finished"] or stopped["repaired"] or stopped["solver_says_pass"])
        self.assertEqual((stopped["seconds"], stopped["status"], stopped["processes_started"]), (33.0, None, None))
        self.assertFalse(broken["finished"] or broken["stopped_at_the_wall_limit"] or broken["repaired"])
        self.assertEqual(broken["worker_error"], "Traceback: the worker died")
        self.assertNotIn("worker_error", stopped)
        summary = tool.summarise(measured)["empty_memory"]
        self.assertEqual(summary["how_the_runs_ended"], {"PASS__FAKE": 1, "STOPPED_AT_THE_WALL_LIMIT": 2, "WORKER_FAILED": 1})
        self.assertEqual((summary["repaired"], summary["of"]), (1, 4))

    def test_the_seconds_are_the_runs_own_and_the_middle_one_is_of_the_repairs(self):
        self.solver.can_find = {"add_one", "at_most", "capped"}
        self.solver.seconds = {"add_one": 5.04, "at_most": 50.0, "capped": 9.0, "at_least": 111.0}
        summary = tool.summarise(self._measure())
        self.assertEqual(summary["empty_memory"]["seconds_in_all"], 175.0)             # 175.04, to one decimal
        self.assertEqual(summary["empty_memory"]["seconds_of_the_middle_repair"], 9.0)
        self.assertEqual(summary["same_bug_again"]["seconds_of_the_middle_repair_by_search"], 9.0)

    def test_of_an_even_number_of_repairs_the_middle_is_the_upper_one(self):
        self.solver.can_find = set(NAMES)
        self.solver.seconds = {"add_one": 5.0, "at_most": 50.0, "capped": 9.0, "at_least": 111.0}
        summary = tool.summarise(self._measure())
        self.assertEqual(summary["empty_memory"]["repaired"], 4)
        self.assertEqual(summary["empty_memory"]["seconds_of_the_middle_repair"], 50.0)
        self.assertEqual(tool._middle([3.0, 1.0]), 3.0)
        self.assertEqual(tool._middle([4.0, 1.0, 3.0, 2.0, 5.0]), 3.0)
        self.assertEqual(tool._middle([7.0]), 7.0)
        self.assertIsNone(tool._middle([]))

    def test_the_middle_of_nothing_is_nothing(self):
        self.solver.can_find = set()
        summary = tool.summarise(self._measure())
        self.assertIsNone(summary["empty_memory"]["seconds_of_the_middle_repair"])
        self.assertIsNone(summary["same_bug_again"]["seconds_of_the_middle_repair_from_memory"])
        self.assertEqual(summary["same_bug_again"]["asked"], 0)

    # -- the same bug again -------------------------------------------------------------------------------------
    def test_the_same_bug_again_is_asked_only_where_the_repair_left_a_lesson(self):
        self.solver.can_find = {"add_one", "at_most", "at_least"}
        self.solver.keeps_no_lesson = {"at_least": "FAKE_NOT_KEPT"}
        measured = self._measure()
        self.assertEqual(sorted(measured["outcomes"]["same_bug_again"]), ["add_one", "at_most"])
        self.assertEqual(sorted(call["name"] for call in self._calls("same_bug_again")), ["add_one", "at_most"])
        summary = tool.summarise(measured)
        self.assertEqual(summary["empty_memory"]["lesson_kept_after_the_repair"], ["add_one", "at_most"])
        self.assertEqual(summary["empty_memory"]["lesson_not_kept_after_the_repair"], {"at_least": "FAKE_NOT_KEPT"})
        self.assertEqual(measured["outcomes"]["empty_memory"]["at_least"]["lesson_kept_after"], False)

    def test_the_same_bug_again_is_a_fresh_copy_of_the_bug_with_the_store_the_first_run_left(self):
        measured = self._measure()
        for name in ("add_one", "at_most"):
            (first,) = self._calls("empty_memory", name)
            (second,) = self._calls("same_bug_again", name)
            self.assertNotEqual(first["where"], second["where"])
            self.assertEqual(second["source"], self._buggy(name))               # the bug, not the repaired file
            self.assertEqual(second["held"], [self._buggy(name)])               # that run's lesson and no other
            outcome = measured["outcomes"]["same_bug_again"][name]
            self.assertTrue(outcome["repaired"] and outcome["memory_hit"] and outcome["is_the_published_fix"])
            self.assertEqual((outcome["searches"], outcome["rules_held"], outcome["memory_strategy"]), (0, 1, "statement"))
            self.assertEqual(outcome["repair_mode"], "scoped_retained_repair")
            # the first run's directory is as that run left it: repaired file, one rule
            self.assertEqual((first["where"] / "project" / "python_programs" / f"{name}.py").read_text(), self._fixed(name))
            self.assertEqual(len(small.FakeStore(first["where"] / tool.MEMORY)._read()), 1)
        summary = tool.summarise(measured)["same_bug_again"]
        self.assertEqual((summary["asked"], summary["repaired"], summary["of_which_from_memory_with_no_search"]), (2, 2, 2))
        self.assertEqual(summary["not_from_memory"], [])
        self.assertEqual((summary["seconds_of_the_middle_repair_by_search"], summary["seconds_of_the_middle_repair_from_memory"]),
                         (20.0, 0.5))

    def test_a_repair_of_the_same_bug_that_searched_again_is_not_from_memory(self):
        self.solver.searches_though_memory_fits = {"add_one"}
        self.solver.seconds = {("same_bug_again", "add_one"): 7.0}
        measured = self._measure()
        summary = tool.summarise(measured)["same_bug_again"]
        self.assertEqual((summary["asked"], summary["repaired"], summary["of_which_from_memory_with_no_search"]), (2, 2, 1))
        self.assertEqual(summary["not_from_memory"], ["add_one"])
        self.assertEqual(measured["outcomes"]["same_bug_again"]["add_one"]["seconds"], 7.0)
        self.assertEqual(summary["seconds_of_the_middle_repair_from_memory"], 0.5)     # of the one repair that did come from memory

    def test_the_same_bug_not_repaired_the_second_time_is_seen(self):
        calls = {"n": 0}
        real = self.solver

        def forgetful(where, args, wall_limit_s):
            if where.parent.name == "same_bug_again" and _program(args) == "at_most":
                calls["n"] += 1
                (where / tool.MEMORY).unlink()                                     # the store is lost before the solver looks
                real.can_find.discard("at_most")
            return real(where, args, wall_limit_s)
        measured = tool.measure(self.root, list(NAMES), self.dir / "work", workers=1, solve_with=forgetful, propose_with=self.proposer)
        self.assertEqual(calls["n"], 1)
        summary = tool.summarise(measured)["same_bug_again"]
        self.assertEqual((summary["asked"], summary["repaired"], summary["of_which_from_memory_with_no_search"]), (2, 1, 1))
        self.assertEqual(summary["not_from_memory"], ["at_most"])

    # -- the fixes of the other programs, taught first ----------------------------------------------------------
    def test_each_published_fix_is_taught_alone_through_the_organ(self):
        measured = self._measure()
        for name in NAMES:
            self.assertTrue(measured["lessons"][name]["crystallized"], name)
            (rule,) = small.FakeStore(self.dir / "work" / "lessons" / f"{name}.sqlite")._read()
            self.assertEqual(rule["taught_on"], self._buggy(name))
            removed, added = small._changed_line(*small.PROGRAMS[name])
            self.assertEqual((rule["removed"], rule["added"]), (removed, added))

    def test_memory_is_asked_about_every_bug_with_the_other_fixes_and_never_its_own(self):
        measured = self._measure()
        self.assertEqual(sorted(call["name"] for call in self.proposer.calls), sorted(NAMES))
        expected = {"add_one": {"at_least", "at_most"},                # capped's lesson is the same rule as at_most's
                    "at_least": {"add_one", "at_most"},
                    "at_most": {"add_one", "at_least", "capped"},
                    "capped": {"add_one", "at_least", "at_most"}}
        for call in self.proposer.calls:
            name = call["name"]
            self.assertEqual(call["source"], self._buggy(name))
            self.assertNotIn(self._buggy(name), call["held"])
            self.assertEqual(set(call["held"]), {self._buggy(other) for other in expected[name]}, name)
            self.assertEqual(call["where"].parent.name, "other_fixes")
            asked = measured["outcomes"]["other_fixes"]["memory_asked"][name]
            self.assertEqual((asked["lessons_given"], asked["rules_held"], asked["rules_refused_on_the_way"]),
                             (3, len(expected[name]), 0))
            self.assertTrue(asked["finished"])
            self.assertEqual(asked["seconds"], 0.1)

    def test_memory_proposes_where_another_bug_had_the_same_change_and_nowhere_else(self):
        measured = self._measure()
        asked = measured["outcomes"]["other_fixes"]["memory_asked"]
        self.assertEqual({name: asked[name]["memory_proposes"] for name in NAMES},
                         {"add_one": False, "at_least": False, "at_most": True, "capped": True})
        self.assertEqual(tool.summarise(measured)["other_fixes"]["memory_proposes_a_repair_for"], ["at_most", "capped"])

    def test_the_solver_is_run_in_full_where_memory_proposes_with_those_same_lessons(self):
        measured = self._measure(check_bugs=0)
        full = self._calls("other_fixes_full")
        self.assertEqual(sorted(call["name"] for call in full), ["at_most", "capped"])
        for call in full:
            name = call["name"]
            self.assertEqual(call["source"], self._buggy(name))
            self.assertNotIn(self._buggy(name), call["held"])
            self.assertEqual(len(call["held"]), 3)
            outcome = measured["outcomes"]["other_fixes"]["solver_run_where_memory_proposes"][name]
            self.assertTrue(outcome["repaired"] and outcome["memory_hit"])
            self.assertEqual((outcome["searches"], outcome["lessons_given"], outcome["rules_held"], outcome["rules_refused_on_the_way"]),
                             (0, 3, 3, 0))
        self.assertEqual(measured["outcomes"]["other_fixes"]["solver_run_where_memory_proposes_nothing"], {})

    def test_what_the_lessons_added_is_what_memory_repaired_and_search_had_not(self):
        summary = tool.summarise(self._measure())
        self.assertEqual(summary["empty_memory"]["which"], ["add_one", "at_most"])
        other = summary["other_fixes"]
        self.assertEqual(other["published_fixes_stored_as_lessons"], 4)
        self.assertEqual(other["repaired_from_memory"], ["at_most", "capped"])
        self.assertEqual(other["of_which_not_repaired_from_an_empty_memory"], ["capped"])
        self.assertEqual(other["of_which_also_repaired_from_an_empty_memory"], ["at_most"])
        self.assertEqual(other["proposed_but_not_repaired"], [])
        self.assertEqual(other["memory_could_not_be_asked"], [])
        self.assertEqual(summary["what_the_lessons_added"], ["capped"])
        self.assertEqual(summary["repaired_with_nothing_taught"], 2)
        self.assertEqual(summary["repaired_when_all_other_fixes_were_taught_first"], 3)

    def test_a_proposal_that_does_not_end_in_a_repair_is_listed_and_adds_nothing(self):
        self.solver.says_pass_and_writes_nothing = {"capped"}
        summary = tool.summarise(self._measure())
        self.assertEqual(summary["other_fixes"]["memory_proposes_a_repair_for"], ["at_most", "capped"])
        self.assertEqual(summary["other_fixes"]["proposed_but_not_repaired"], ["capped"])
        self.assertEqual(summary["other_fixes"]["repaired_from_memory"], ["at_most"])
        self.assertEqual(summary["what_the_lessons_added"], [])
        self.assertEqual(summary["repaired_when_all_other_fixes_were_taught_first"], 2)

    def test_a_repair_with_lessons_that_searched_is_not_put_down_to_memory(self):
        real = self.solver

        def searched(where, args, wall_limit_s):
            run = real(where, args, wall_limit_s)
            if where.parent.name == "other_fixes_full" and _program(args) == "capped":
                run["result"]["retained_learning"]["hit"] = False
            return run
        measured = tool.measure(self.root, list(NAMES), self.dir / "work", workers=1, solve_with=searched, propose_with=self.proposer)
        summary = tool.summarise(measured)
        self.assertTrue(measured["outcomes"]["other_fixes"]["solver_run_where_memory_proposes"]["capped"]["repaired"])
        self.assertEqual(summary["other_fixes"]["repaired_from_memory"], ["at_most"])
        self.assertEqual(summary["what_the_lessons_added"], [])
        self.assertEqual(summary["other_fixes"]["proposed_but_not_repaired"], [])

    def test_a_fix_the_organ_refuses_teaches_nothing_and_is_reported(self):
        small.FakeStore.refuse = {self._buggy("at_most")}
        measured = self._measure()
        self.assertEqual((measured["lessons"]["at_most"]["crystallized"], measured["lessons"]["at_most"]["reason"]),
                         (False, "FAKE_REFUSAL"))
        asked = measured["outcomes"]["other_fixes"]["memory_asked"]
        self.assertFalse(asked["capped"]["memory_proposes"])               # the one lesson that would have fitted was refused
        self.assertTrue(asked["at_most"]["memory_proposes"])               # capped's own lesson still fits at_most
        self.assertEqual({name: asked[name]["lessons_given"] for name in NAMES},
                         {"add_one": 2, "at_least": 2, "at_most": 3, "capped": 2})
        for call in self.proposer.calls:
            self.assertNotIn(self._buggy("at_most"), call["held"])
        self.assertEqual(tool.summarise(measured)["other_fixes"]["published_fixes_stored_as_lessons"], 3)

    def test_where_memory_is_silent_a_sample_drawn_by_seed_is_run_in_full_all_the_same(self):
        samples = {}
        for seed in range(8):
            self.solver.calls = []
            measured = self._measure(check_bugs=1, seed=seed)
            checks = measured["outcomes"]["other_fixes"]["solver_run_where_memory_proposes_nothing"]
            self.assertEqual(len(checks), 1)
            (name,) = checks
            self.assertIn(name, ("add_one", "at_least"))                    # only where memory proposed nothing
            self.assertEqual(sorted(call["name"] for call in self._calls("other_fixes_full")), sorted(["at_most", "capped", name]))
            samples[seed] = name
        self.assertEqual(set(samples.values()), {"add_one", "at_least"})
        self.solver.calls = []
        again = self._measure(check_bugs=1, seed=3)
        self.assertEqual(list(again["outcomes"]["other_fixes"]["solver_run_where_memory_proposes_nothing"]), [samples[3]])

    def test_the_sample_is_never_more_than_there_is_and_can_be_none(self):
        every = self._measure(check_bugs=9)
        self.assertEqual(sorted(every["outcomes"]["other_fixes"]["solver_run_where_memory_proposes_nothing"]), ["add_one", "at_least"])
        two = self._measure(check_bugs=2)
        self.assertEqual(sorted(two["outcomes"]["other_fixes"]["solver_run_where_memory_proposes_nothing"]), ["add_one", "at_least"])
        none = self._measure(check_bugs=0)
        self.assertEqual(none["outcomes"]["other_fixes"]["solver_run_where_memory_proposes_nothing"], {})

    def test_the_full_run_where_memory_is_silent_is_set_beside_the_run_from_an_empty_memory(self):
        self.solver.finds_only_from_an_empty_store = {"add_one"}
        measured = self._measure(check_bugs=9)
        for call in self._calls("other_fixes_full"):
            self.assertNotIn(self._buggy(call["name"]), call["held"])
        compared = tool.summarise(measured)["other_fixes"]["where_memory_proposes_nothing_the_outcome_is_as_from_an_empty_memory"]
        self.assertEqual(compared, {"add_one": {"with_lessons": False, "from_an_empty_memory": True, "the_same": False},
                                    "at_least": {"with_lessons": False, "from_an_empty_memory": False, "the_same": True}})
        # a repair by search with lessons in the store is not put down to the lessons
        self.solver.finds_only_from_an_empty_store = set()
        self.solver.can_find = {"at_least"}
        summary = tool.summarise(self._measure(check_bugs=9))
        self.assertEqual(summary["other_fixes"]["where_memory_proposes_nothing_the_outcome_is_as_from_an_empty_memory"]["at_least"],
                         {"with_lessons": True, "from_an_empty_memory": True, "the_same": True})
        self.assertEqual(summary["what_the_lessons_added"], ["at_most", "capped"])
        self.assertEqual(summary["repaired_when_all_other_fixes_were_taught_first"], 3)

    def test_memory_that_could_not_be_asked_is_reported_and_is_neither_proposing_nor_silent(self):
        self.proposer.cannot_be_asked = {"capped", "add_one"}
        measured = self._measure(check_bugs=9)
        asked = measured["outcomes"]["other_fixes"]["memory_asked"]
        self.assertEqual((asked["capped"]["finished"], asked["capped"]["memory_proposes"]), (False, False))
        summary = tool.summarise(measured)["other_fixes"]
        self.assertEqual(summary["memory_could_not_be_asked"], ["add_one", "capped"])
        self.assertEqual(summary["memory_proposes_a_repair_for"], ["at_most"])
        self.assertEqual(sorted(measured["outcomes"]["other_fixes"]["solver_run_where_memory_proposes_nothing"]), ["at_least"])
        self.assertEqual(sorted(measured["outcomes"]["other_fixes"]["solver_run_where_memory_proposes"]), ["at_most"])

    # -- side by side, progress, the command line ---------------------------------------------------------------
    def test_runs_side_by_side_come_to_what_runs_one_after_another_come_to(self):
        one = self._measure(workers=1, check_bugs=9)
        self.solver.calls = []
        two = self._measure(workers=2, check_bugs=9)
        self.assertEqual(one["outcomes"], two["outcomes"])
        self.assertEqual(one["lessons"], two["lessons"])
        self.assertEqual(list(two["outcomes"]["empty_memory"]), list(NAMES))      # each outcome under its own name, in order

    def test_as_many_runs_at_a_time_as_there_are_workers_and_no_more(self):
        real, lock = self.solver, threading.Lock()
        running, most = {"now": 0}, {}

        def watched(where, args, wall_limit_s):
            question = where.parent.name
            with lock:
                running["now"] += 1
                most[question] = max(most.get(question, 0), running["now"])
            time.sleep(0.15)
            try:
                return real(where, args, wall_limit_s)
            finally:
                with lock:
                    running["now"] -= 1

        for workers, expected in ((1, 1), (2, 2), (3, 3)):
            most.clear()
            tool.measure(self.root, list(NAMES), self.dir / "work", workers=workers, check_bugs=0, solve_with=watched,
                         propose_with=self.proposer)
            self.assertEqual(most["empty_memory"], expected, workers)                  # four bugs
            self.assertEqual(most["same_bug_again"], min(expected, 2), workers)        # two bugs
            self.assertEqual(most["other_fixes_full"], min(expected, 2), workers)      # two bugs

    def test_progress_is_said_for_every_run(self):
        lines: list = []
        self._measure(progress=lines.append, check_bugs=1)
        self.assertEqual(sum(1 for line in lines if line.startswith("[empty memory] ")), 4)
        self.assertEqual(sum(1 for line in lines if line.startswith("[same bug again] ")), 2)
        self.assertEqual(sum(1 for line in lines if line.startswith("taught ")), 4)
        self.assertEqual(sum(1 for line in lines if line.startswith("[other fixes] memory proposes a repair for 2 of 4")), 1)
        self.assertEqual(sum(1 for line in lines if line.startswith("[check] ")), 1)
        self.assertTrue([line for line in lines if line.startswith("[empty memory] at_most") and "REPAIRED" in line and "PASS__FAKE" in line])
        self.assertTrue([line for line in lines if line.startswith("[empty memory] at_least") and "not repaired" in line])

    def test_a_stopped_run_and_a_broken_one_are_said_as_such(self):
        self.solver.stopped = {"at_least"}
        self.solver.breaks = {"capped"}
        lines: list = []
        self._measure(progress=lines.append)
        self.assertTrue([line for line in lines if line.startswith("[empty memory] at_least") and "stopped at the wall limit" in line])
        self.assertTrue([line for line in lines if line.startswith("[empty memory] capped") and "worker failed" in line])

    def test_a_refused_lesson_is_said_with_its_reason(self):
        small.FakeStore.refuse = {self._buggy("add_one")}
        lines: list = []
        self._measure(progress=lines.append)
        self.assertIn("REFUSED FAKE_REFUSAL", [line for line in lines if line.startswith("taught add_one")][0])
        self.assertIn("stored", [line for line in lines if line.startswith("taught at_most")][0])

    def test_the_command_line_writes_what_was_measured(self):
        tool.solve, tool.propose = self.solver, self.proposer
        out = self.dir / "out.json"
        code = tool.main(["--quixbugs-dir", str(self.root), "--work-dir", str(self.dir / "cli"), "--timeout", "6",
                          "--wall-limit", "44", "--workers", "1", "--check-bugs", "1", "--seed", "5", "--out", str(out)])
        self.assertEqual(code, 0)
        written = json.loads(out.read_text())
        self.assertEqual((written["schema"], written["authority"]), ("BRAIN_QUIXBUGS_REPAIR_SOLVER_MEASUREMENT_V1",
                                                                    "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"))
        self.assertEqual(written["programs"], sorted(EVERY))                         # every program of the benchmark by default
        self.assertEqual(written["targets"], sorted(NAMES))
        self.assertEqual(written["parameters"]["timeout_s"], 6)
        self.assertEqual(written["parameters"]["wall_limit_s"], 44)
        self.assertEqual((written["parameters"]["workers"], written["parameters"]["check_bugs"], written["parameters"]["seed"]), (1, 1, 5))
        self.assertEqual(written["parameters"]["solver_arguments_for_one_bug"], tool.solver_args("NAME", timeout_s=6))
        self.assertEqual({call["wall_limit_s"] for call in self.solver.calls}, {44})
        self.assertEqual({call["args"]["timeout_s"] for call in self.solver.calls}, {6})
        self.assertEqual((written["producer_cognition_model_dependency_count"], written["incremental_spend_usd"]), (0, 0))
        self.assertEqual(written["environment"]["benchmark_sha256"], bench.benchmark_sha256(self.root, sorted(EVERY)))
        self.assertEqual(written["environment"]["code_sha256"], tool.code_sha256())
        self.assertEqual(sorted(written["environment"]), ["benchmark_sha256", "code_sha256", "processors", "python", "source"])
        self.assertEqual(written["environment"]["python"], sys.version.split()[0])
        self.assertEqual(written["environment"]["processors"], os.cpu_count())
        self.assertIn("github.com/jkoppel/QuixBugs", written["environment"]["source"])
        self.assertEqual(written["summary"], tool.summarise(written))
        self.assertEqual(written["summary"]["what_the_lessons_added"], ["capped"])
        self.assertTrue((self.dir / "cli" / "empty_memory" / "add_one").is_dir())
        self.assertRegex(written["generated_utc"], r"^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_the_command_line_takes_a_list_of_programs(self):
        tool.solve, tool.propose = self.solver, self.proposer
        out = self.dir / "out.json"
        tool.main(["--quixbugs-dir", str(self.root), "--work-dir", str(self.dir / "cli"), "--programs", "capped", "add_one",
                   "--out", str(out)])
        written = json.loads(out.read_text())
        self.assertEqual(written["programs"], ["capped", "add_one"])
        self.assertEqual({key: written["parameters"][key] for key in ("timeout_s", "wall_limit_s", "workers", "check_bugs", "seed")},
                         {"timeout_s": 8, "wall_limit_s": 300, "workers": 2, "check_bugs": 3, "seed": 0})
        self.assertEqual(sorted({call["name"] for call in self.solver.calls}), ["add_one", "capped"])

    def test_the_command_line_must_be_told_where_the_benchmark_is(self):
        with self.assertRaises(SystemExit):
            tool.main(["--out", str(self.dir / "out.json")])
        self.assertFalse((self.dir / "out.json").exists())

    def test_a_call_without_options_gets_the_stated_protocol(self):
        defaults = {name: parameter.default for name, parameter in inspect.signature(tool.measure).parameters.items()
                    if parameter.default is not inspect.Parameter.empty}
        self.assertEqual({key: defaults[key] for key in ("timeout_s", "wall_limit_s", "workers", "check_bugs", "seed")},
                         {"timeout_s": 8, "wall_limit_s": 300, "workers": 2, "check_bugs": 3, "seed": 0})

    def test_the_hashes_are_of_the_code_that_is_measured_and_of_the_code_that_measures(self):
        import hashlib
        hashes = tool.code_sha256()
        self.assertEqual(sorted(hashes), ["bench_tool", "organ_contract_and_oracle", "organ_store", "retained_repair_session",
                                          "solver", "tool"])
        self.assertEqual(hashes["tool"], hashlib.sha256(pathlib.Path(tool.__file__).read_bytes()).hexdigest())
        self.assertEqual(hashes["solver"], hashlib.sha256(
            (REPO / "canonical/runtime/bound_capabilities/python_repair_apply_verified_v1.py").read_bytes()).hexdigest())
        self.assertEqual(hashes["bench_tool"], hashlib.sha256(pathlib.Path(bench.__file__).read_bytes()).hexdigest())
        self.assertEqual(len(set(hashes.values())), 6)


class LayingABugOut(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="solver-layout-test-"))
        self.root = small.write_benchmark(self.dir / "bench", names=EVERY)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_a_bug_is_laid_out_as_a_project_a_place_for_memory_and_a_place_for_reports(self):
        where = tool.lay_out(self.root, "at_most", self.dir / "one")
        self.assertEqual(where, self.dir / "one")
        self.assertEqual(sorted(p.name for p in where.iterdir()), ["memory", "project", "reports"])
        self.assertEqual(list((where / "memory").iterdir()) + list((where / "reports").iterdir()), [])
        project = where / tool.PROJECT
        self.assertEqual((project / "python_programs" / "at_most.py").read_text(), (self.root / "python_programs" / "at_most.py").read_text())
        self.assertTrue((project / "python_testcases" / "test_at_most.py").is_file())
        self.assertTrue((project / "conftest.py").is_file())
        self.assertFalse((project / "correct_python_programs").exists())
        self.assertEqual(sorted(p.name for p in (project / "python_programs").iterdir()), ["at_most.py", "node.py"])

    def test_laying_out_again_starts_over(self):
        where = tool.lay_out(self.root, "at_most", self.dir / "one")
        (where / "memory" / "skills.sqlite").write_text("old")
        (where / "project" / "python_programs" / "at_most.py").write_text("changed")
        tool.lay_out(self.root, "at_most", self.dir / "one")
        self.assertFalse((where / "memory" / "skills.sqlite").exists())
        self.assertEqual((where / "project" / "python_programs" / "at_most.py").read_text(),
                         (self.root / "python_programs" / "at_most.py").read_text())

    def test_the_places_named_to_the_solver_are_the_places_laid_out(self):
        where = tool.lay_out(self.root, "capped", self.dir / "one")
        args = tool.solver_args("capped", timeout_s=8)
        self.assertTrue((where / args["source_root"]).is_dir())
        self.assertTrue((where / args["test_paths"][0]).is_file())
        self.assertTrue((where / args["retained_learning"]["target_path"]).is_file())
        self.assertTrue((where / args["retained_learning"]["db_path"]).parent.is_dir())
        self.assertTrue((where / args["output_path"]).parent.is_dir())
        self.assertTrue(args["retained_learning"]["db_path"].endswith(".sqlite"))


SLOW_WITH_A_CHILD = r"""
import subprocess, sys, time
subprocess.Popen([sys.executable, '-c', "import time, pathlib, sys; time.sleep(2.5); pathlib.Path(sys.argv[1]).write_text('late')",
                  sys.argv[2] + '/late.txt'])
print('started', flush=True)
time.sleep(60)
"""
TALKATIVE = r"""
import json, sys
from pathlib import Path
mode, where, payload = sys.argv[1:4]
print('a line the solver printed')
print('{"not": "the answer"}')
print('\n' + json.dumps({'result': {'mode': mode, 'where': where, 'args': json.loads(Path(payload).read_text())},
                         'seconds': 1.25, 'processes_started': 7}))
"""
DYING = r"""
import sys
print('half a line')
sys.stderr.write('x' * 1000 + '\nTraceback (most recent call last):\nRuntimeError: no such organ\n')
sys.exit(3)
"""
SILENT = "pass\n"
IMPORTING = r"""
import json, os, sys
import canonical.tools.quixbugs_repair_solver_measure_v1 as found
print(json.dumps({'result': {'file': found.__file__, 'cwd': os.getcwd(), 'no_bytecode': os.environ.get('PYTHONDONTWRITEBYTECODE'),
                             'path': os.environ['PYTHONPATH'].split(os.pathsep)},
                  'seconds': 0.0, 'processes_started': 0}))
"""


class TheProcessAroundTheSolver(unittest.TestCase):
    """Real processes, with a stand-in for what runs inside."""

    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="solver-process-test-"))
        self._worker = tool._WORKER
        self._path = os.environ.get("PYTHONPATH")

    def tearDown(self):
        tool._WORKER = self._worker
        if self._path is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = self._path
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_a_run_past_the_wall_limit_is_stopped_with_everything_it_started(self):
        tool._WORKER = SLOW_WITH_A_CHILD
        started = time.monotonic()
        run = tool.solve(self.dir, {"x": 1}, 1)
        took = time.monotonic() - started
        self.assertEqual((run["finished"], run["stopped_at_the_wall_limit"]), (False, True))
        self.assertGreaterEqual(run["seconds"], 1.0)
        self.assertLessEqual(run["seconds"], took)        # the seconds are those this run took
        self.assertLess(took, 10)
        self.assertNotIn("result", run)
        time.sleep(3.5)                                   # the child would have written its file by now
        self.assertFalse((self.dir / "late.txt").exists())

    def test_the_answer_is_the_last_line_whatever_was_printed_before(self):
        tool._WORKER = TALKATIVE
        args = {"source_root": "project", "timeout_s": 8, "nested": {"a": [1, 2]}}
        for ask, mode in ((tool.solve, "solve"), (tool.propose, "propose")):
            run = ask(self.dir, args, 30)
            self.assertEqual((run["finished"], run["stopped_at_the_wall_limit"]), (True, False))
            self.assertEqual((run["seconds"], run["processes_started"]), (1.25, 7))
            self.assertEqual(run["result"], {"mode": mode, "where": str(self.dir), "args": args})
            self.assertEqual(json.loads((self.dir / "reports" / f"{mode}.args.json").read_text()), args)

    def test_a_place_that_is_not_there_yet_is_made(self):
        tool._WORKER = TALKATIVE
        where = self.dir / "not" / "there" / "yet"
        run = tool.solve(where, {"a": 1}, 30)
        self.assertTrue(run["finished"], run)
        self.assertEqual(json.loads((where / "reports" / "solve.args.json").read_text()), {"a": 1})

    def test_a_worker_that_dies_is_not_finished_and_its_last_words_are_kept(self):
        tool._WORKER = DYING
        started = time.monotonic()
        run = tool.solve(self.dir, {}, 30)
        took = time.monotonic() - started
        self.assertEqual((run["finished"], run["stopped_at_the_wall_limit"], run["worker_returncode"]), (False, False, 3))
        self.assertIn("RuntimeError: no such organ", run["worker_error"])
        self.assertEqual(len(run["worker_error"]), 400)                # the end of what it said, not all of it
        self.assertTrue(run["worker_error"].endswith("RuntimeError: no such organ\n"))
        self.assertNotIn("result", run)
        self.assertIsInstance(run["seconds"], float)
        self.assertTrue(0 <= run["seconds"] <= took)

    def test_a_worker_that_says_nothing_is_not_finished(self):
        tool._WORKER = SILENT
        run = tool.solve(self.dir, {}, 30)
        self.assertEqual((run["finished"], run["stopped_at_the_wall_limit"], run["worker_returncode"]), (False, False, 0))

    def test_the_worker_runs_in_this_tree_and_leaves_no_bytecode_in_it(self):
        tool._WORKER = IMPORTING
        run = tool.solve(self.dir, {}, 60)
        self.assertTrue(run["finished"], run)
        self.assertEqual(pathlib.Path(run["result"]["file"]).resolve(), pathlib.Path(tool.__file__).resolve())
        self.assertEqual(pathlib.Path(run["result"]["cwd"]).resolve(), REPO.resolve())
        self.assertEqual(run["result"]["no_bytecode"], "1")
        self.assertEqual(pathlib.Path(run["result"]["path"][0]).resolve(), REPO.resolve())

    def test_this_tree_comes_first_on_the_path_whatever_was_on_it(self):
        tool._WORKER = IMPORTING
        os.environ["PYTHONPATH"] = "/somewhere/else"
        run = tool.solve(self.dir, {}, 60)
        self.assertTrue(run["finished"], run)
        self.assertEqual(run["result"]["path"], [str(tool.REPO), "/somewhere/else"])
        os.environ.pop("PYTHONPATH")
        run = tool.solve(self.dir, {}, 60)
        self.assertEqual(run["result"]["path"], [str(tool.REPO)])


class WithTheRealSolverAndTheRealOrgan(unittest.TestCase):
    """The real solver in its own processes, the real store and the real tests, on three small
    programs written for these tests. What is pinned is what must hold whatever the solver finds."""
    names = ("add_one", "at_most", "capped")

    @classmethod
    def setUpClass(cls):
        cls.dir = pathlib.Path(tempfile.mkdtemp(prefix="solver-real-test-"))
        cls.root = small.write_benchmark(cls.dir / "bench", names=cls.names)
        cls.lines: list = []
        cls.measured = tool.measure(cls.root, list(cls.names), cls.dir / "work", timeout_s=8, wall_limit_s=240, workers=2,
                                    check_bugs=1, progress=cls.lines.append)
        cls.summary = tool.summarise(cls.measured)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_every_bug_was_run_to_the_end_by_the_real_solver(self):
        self.assertEqual(self.measured["targets"], list(self.names))
        for name in self.names:
            outcome = self.measured["outcomes"]["empty_memory"][name]
            self.assertTrue(outcome["finished"], (name, outcome))
            self.assertIsInstance(outcome["status"], str)
            self.assertGreaterEqual(outcome["processes_started"], 1)          # it ran the tests at least once
            self.assertGreaterEqual(outcome["searches"], 0)
            self.assertFalse(outcome["memory_hit"])                           # there was nothing to remember

    def test_what_is_counted_as_repaired_passes_the_tests_when_asked_again(self):
        for question in ("empty_memory", "same_bug_again"):
            for name, outcome in self.measured["outcomes"][question].items():
                if outcome["repaired"]:
                    self.assertTrue(outcome["solver_says_pass"] and outcome["file_changed"] and outcome["second_check_passes"], (question, name))
                    project = bench.build_project(self.root, name, self.dir / "asked_again")
                    on_disk = (self.dir / "work" / question / name / "project" / "python_programs" / f"{name}.py").read_text()
                    self.assertTrue(bench.oracle_for(project, name)(on_disk).passed, (question, name))

    def test_the_boundary_bug_is_repaired_by_search_with_the_published_fix(self):
        outcome = self.measured["outcomes"]["empty_memory"]["at_most"]
        self.assertTrue(outcome["repaired"], outcome)
        self.assertEqual(outcome["lines_changed"], {"removed": ["if x < top:"], "put_in": ["if x <= top:"]})
        self.assertTrue(outcome["is_the_published_fix"])
        self.assertGreaterEqual(outcome["searches"], 1)

    def test_the_same_bug_again_is_repaired_from_memory_without_a_search(self):
        self.assertTrue(self.measured["outcomes"]["empty_memory"]["at_most"]["lesson_kept_after"])
        again = self.measured["outcomes"]["same_bug_again"]["at_most"]
        self.assertTrue(again["repaired"] and again["memory_hit"], again)
        self.assertEqual(again["searches"], 0)
        self.assertEqual(again["rules_held"], 1)
        self.assertLess(again["processes_started"], self.measured["outcomes"]["empty_memory"]["at_most"]["processes_started"])
        self.assertEqual(sorted(self.measured["outcomes"]["same_bug_again"]),
                         sorted(name for name in self.names if self.measured["outcomes"]["empty_memory"][name]["repaired"]
                                and self.measured["outcomes"]["empty_memory"][name]["lesson_kept_after"]))

    def test_memory_was_asked_in_a_process_of_its_own_about_every_bug_with_the_other_lessons(self):
        stored = [name for name in self.names if self.measured["lessons"][name]["crystallized"]]
        for name in self.names:
            asked = self.measured["outcomes"]["other_fixes"]["memory_asked"][name]
            self.assertTrue(asked["finished"], (name, asked))
            self.assertEqual(asked["lessons_given"], len([other for other in stored if other != name]))
            self.assertEqual(asked["rules_refused_on_the_way"], 0)

    def test_the_lesson_from_the_same_defect_elsewhere_repairs_from_memory(self):
        self.assertTrue(self.measured["lessons"]["at_most"]["crystallized"], self.measured["lessons"]["at_most"])
        self.assertTrue(self.measured["outcomes"]["other_fixes"]["memory_asked"]["capped"]["memory_proposes"])
        outcome = self.measured["outcomes"]["other_fixes"]["solver_run_where_memory_proposes"]["capped"]
        self.assertTrue(outcome["repaired"] and outcome["memory_hit"], outcome)
        self.assertEqual(outcome["searches"], 0)
        self.assertIn("capped", self.summary["other_fixes"]["repaired_from_memory"])

    def test_the_summary_adds_up(self):
        empty = self.summary["empty_memory"]
        self.assertEqual(empty["of"], 3)
        self.assertEqual(empty["repaired"], len(empty["which"]))
        self.assertEqual(sum(empty["how_the_runs_ended"].values()), 3)
        self.assertEqual(empty["solver_said_pass_but_the_second_check_did_not"], [])
        self.assertEqual(self.summary["repaired_with_nothing_taught"], empty["repaired"])
        self.assertEqual(self.summary["repaired_when_all_other_fixes_were_taught_first"],
                         len(set(empty["which"]) | set(self.summary["other_fixes"]["repaired_from_memory"])))
        self.assertEqual(self.summary["what_the_lessons_added"],
                         sorted(set(self.summary["other_fixes"]["repaired_from_memory"]) - set(empty["which"])))
        self.assertTrue([line for line in self.lines if line.startswith("[empty memory] at_most")])


if __name__ == "__main__":
    unittest.main()
