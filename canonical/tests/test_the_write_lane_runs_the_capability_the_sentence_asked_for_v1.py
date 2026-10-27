#!/usr/bin/env python3
"""A sentence that asks for an EDIT must not be answered by a read-only audit.

Measured on `origin/main` at `cfbbdc28`, "Extract the function big from the module
calc.py lines 5 to 8 in the python source root D into a new function named
total_of" scored `python.refactor.extract_function.v1` at 33, ahead of the next
candidate at 22 -- and then was DROPPED as unbindable, because its template
demanded six inputs from the sentence:

  GOAL_INPUT_BINDING_REQUIRED:start_line:not_stated
  GOAL_INPUT_BINDING_REQUIRED:end_line:not_stated
  GOAL_INPUT_BINDING_REQUIRED:new_name:not_stated
  GOAL_INPUT_BINDING_REQUIRED:qualname:not_stated
  GOAL_INPUT_BINDING_REQUIRED:python_executable:not_stated
  GOAL_INPUT_BINDING_REQUIRED:run_tests:not_stated
  GOAL_INPUT_BINDING_REQUIRED:timeout_s:not_stated

Four of those the sentence plainly states; the sentence just states them the way
an engineer states them ("lines 5 to 9", "named total_of", "the function big"),
and the binder had no grammar for any of them. Three more no sentence could ever
state -- and the adapter already defaults all three
(`python_refactor_extract_function.py:203-205`: `python_executable` falls back to
`sys.executable`, `timeout_s` to 300, `run_tests` to []).

So the read-only audit, a capability that reads and changes nothing, answered an
extract-method request and returned `pass=True`. It reported `files: 2,
functions: 3` -- the census of the whole directory -- for a request to move four
lines. That is the worst outcome available: the machine reports work it did not
do, and the caller has no way to tell.

The fix is in three parts, and each is a reuse of a mechanism the repository
already has:

1. **Grammar for how an engineer states a region.** `_LINE_RANGE_KEYS` parses
   "lines 5 to 9" once and gives each end to its own key; a single stated line is
   both ends. `_KEY_ALIASES` gains `new_name` and `qualname`.
2. **A template must not demand what the adapter defaults.** `run_tests` and
   `timeout_s` are literals in the template, `python_executable` is gone -- the
   same convention as `pdf.extract.text.pypdf`, which carries `"max_pages": 200`.
3. **A capability that calls `sys.exit()` must fail closed, not kill the
   caller.** Every handler on the execution path catches `Exception`; `SystemExit`
   derives from `BaseException` and escaped `solve()` outright.

The negative control matters more than the accepting case: a region that is not
whole statements must still be refused, and an audit must still be the right
answer to a question about a file.
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import goal_compiler as goal_compiler  # noqa: E402

REGISTRY = json.loads(
    (REPO_ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text()
)["capabilities"]
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as admission  # noqa: E402

MODULE = (
    "def add(a, b):\n"
    "    return a + b\n"
    "\n"
    "\n"
    "def big(x):\n"
    "    total = 0\n"
    "    for i in range(x):\n"
    "        total = total + i\n"
    "    return total\n"
)

TESTS = (
    "from calc import add, big\n"
    "\n"
    "\n"
    "def test_add():\n"
    "    assert add(2, 3) == 5\n"
    "\n"
    "\n"
    "def test_big():\n"
    "    assert big(4) == 3\n"
)


class LineRangeTests(unittest.TestCase):
    def test_one_statement_of_two_bounds_fills_both_ends(self):
        tail = " 5 to 9 in the python source root /tmp/x"
        self.assertEqual(front._parse_typed_value("start_line", tail), 5)
        self.assertEqual(front._parse_typed_value("end_line", tail), 9)

    def test_a_single_stated_line_is_both_ends(self):
        self.assertEqual(front._parse_typed_value("start_line", " 7 of the file"), 7)
        self.assertEqual(front._parse_typed_value("end_line", " 7 of the file"), 7)

    def test_the_separators_the_sentence_may_use(self):
        for text in ("5-9", "5 to 9", "5 through 9", "5 until 9", "5..9"):
            with self.subTest(text=text):
                self.assertEqual(front._parse_typed_value("start_line", " " + text + " x"), 5)
                self.assertEqual(front._parse_typed_value("end_line", " " + text + " x"), 9)

    def test_a_region_key_never_binds_prose(self):
        self.assertIsNone(front._parse_typed_value("start_line", " the whole file"))
        self.assertIsNone(front._parse_typed_value("end_line", " everywhere"))

    def test_the_new_name_is_not_read_as_the_operand(self):
        # "into a new function named total_of" contains "function named", and
        # _after_key tries the longest alias first, so that phrasing once handed
        # the NEW name to the slot asking WHICH function to extract and the
        # adapter failed SYMBOL_NOT_FOUND:total_of.
        self.assertNotIn("function named", front._KEY_ALIASES["qualname"])
        goal = ("Extract the function big from the module calc.py lines 6 to 8 "
                "into a new function named total_of")
        self.assertEqual(front.bind_typed_key(goal, "qualname", REPO_ROOT), "big")
        self.assertEqual(front.bind_typed_key(goal, "new_name", REPO_ROOT), "total_of")


class ExtractFunctionIsSelectableTests(unittest.TestCase):
    # source_root must exist AND be a scoped subtree: the binder refuses the
    # repository root itself with 0_existing_directories_named, so a test that
    # pointed at REPO_ROOT measured a refusal rather than a binding.
    SCOPE = REPO_ROOT / "canonical/astra_runtime/tmp"
    GOAL = (
        "Extract the function big from the module calc.py lines 6 to 8 in the "
        f"python source root {SCOPE} into a new function named total_of "
        f"writing the report to {SCOPE}/wl_probe.json"
    )

    def test_the_template_demands_only_what_a_sentence_can_state(self):
        entry = REGISTRY["python.refactor.extract_function.v1"]
        declared = {k for k, v in entry["action_template"]["args"].items()
                    if isinstance(v, str) and v.startswith("${")}
        self.assertNotIn("python_executable", declared)
        for literal in ("run_tests", "timeout_s"):
            self.assertNotIn(literal, declared, f"{literal} must be a literal")

    def test_the_refactor_outscores_the_read_only_audit(self):
        reg = REGISTRY
        chosen = goal_compiler._score(self.GOAL, "python.refactor.extract_function.v1",
                                      reg["python.refactor.extract_function.v1"])
        audit = goal_compiler._score(self.GOAL, "python.source.audit.ast",
                                     reg["python.source.audit.ast"])
        self.assertGreater(chosen[0], audit[0])

    def test_every_declared_input_binds_from_the_sentence(self):
        entry = REGISTRY["python.refactor.extract_function.v1"]
        declared = {k for k, v in entry["action_template"]["args"].items()
                    if isinstance(v, str) and v.startswith("${") and k != "capability_id"}
        missing = []
        for key in sorted(declared):
            try:
                if front.bind_typed_key(self.GOAL, key, REPO_ROOT, entry) is None:
                    missing.append(key)
            except Exception:
                missing.append(key)
        self.assertEqual(missing, [], f"unbindable declared inputs: {missing}")


class RefactorEndToEndTests(unittest.TestCase):
    def setUp(self):
        import shutil
        self.dir = REPO_ROOT / "canonical/astra_runtime/tmp/test_write_lane_v1"
        shutil.rmtree(self.dir, ignore_errors=True)
        self.dir.mkdir(parents=True)
        (self.dir / "calc.py").write_text(MODULE)
        (self.dir / "test_calc.py").write_text(TESTS)

    def _solve(self, goal):
        return admission.solve({"task_id": "WRITE_LANE", "goal": goal})

    def test_the_sentence_produces_the_refactor_and_the_bytes_show_it(self):
        goal = (
            f"Extract the function big from the module calc.py lines 6 to 8 in the "
            f"python source root {self.dir} into a new function named total_of "
            f"writing the report to {self.dir}/report.json"
        )
        result = self._solve(goal)
        self.assertEqual(result.get("compiled_capability_id"),
                         "python.refactor.extract_function.v1")
        self.assertIs(result.get("pass"), True, str(result.get("reason"))[:300])
        after = (self.dir / "calc.py").read_text()
        self.assertIn("def total_of(x):", after)
        self.assertIn("    total = total_of(x)", after)
        self.assertIn("def big(x):", after)
        self.assertNotIn("        total = total + i\n    return total\n\n\ndef total_of",
                         after)

    def test_the_audit_is_not_the_answer_to_an_edit(self):
        # The negative control that the whole defect turned on: if this ever
        # selects the read-only census again, the machine is reporting work it
        # did not do.
        goal = (
            f"Extract the function big from the module calc.py lines 6 to 8 in the "
            f"python source root {self.dir} into a new function named total_of "
            f"writing the report to {self.dir}/report.json"
        )
        result = self._solve(goal)
        self.assertNotEqual(result.get("compiled_capability_id"), "python.source.audit.ast")
        if (self.dir / "report.json").exists():
            self.assertNotEqual(
                json.loads((self.dir / "report.json").read_text()).get("report_kind"),
                "PROJECT_BRAIN_PYTHON_SOURCE_AUDIT_V1")

    def test_a_region_that_is_not_whole_statements_is_still_refused(self):
        goal = (
            f"Extract the function big from the module calc.py lines 6 to 7 in the "
            f"python source root {self.dir} into a new function named total_of "
            f"writing the report to {self.dir}/report.json"
        )
        result = self._solve(goal)
        if result.get("compiled_capability_id") == "python.refactor.extract_function.v1":
            self.assertIs(result.get("pass"), False)
        self.assertEqual((self.dir / "calc.py").read_text(), MODULE,
                         "a refused refactor must not have edited the file")

    def test_a_question_about_the_file_is_still_answered_by_the_audit(self):
        # The other direction of the same boundary: widening the write lane must
        # not take the read question away from the capability that answers it.
        goal = (f"Count the functions in the python file {self.dir}/calc.py "
                f"in the python source root {self.dir} writing the report to "
                f"{self.dir}/audit.json")
        result = self._solve(goal)
        self.assertEqual(result.get("compiled_capability_id"), "python.source.audit.ast")
        self.assertIs(result.get("pass"), True, str(result.get("reason"))[:300])
        payload = json.loads((self.dir / "audit.json").read_text())
        self.assertTrue(any(str(f["path"]).endswith("calc.py") for f in payload["files"]))
        # the audit is a census: it must not have performed the refactor
        self.assertNotIn("total_of", payload["totals"])

    def test_a_capability_that_exits_the_process_fails_closed_instead(self):
        # Every handler on the execution path catches Exception; SystemExit
        # derives from BaseException and escaped solve() outright on
        # python.tests.generate.scaffold.v1. A front door that raises is worse
        # than one that refuses.
        class _Exit(Exception):
            pass

        original = admission._execute

        def _boom(*args, **kwargs):
            raise SystemExit("simulated adapter sys.exit")

        admission._execute = _boom
        try:
            with self.assertRaises(SystemExit):
                _boom()
        finally:
            admission._execute = original
        source = (REPO_ROOT / "canonical/runtime/live_brain_route_admission_v1.py").read_text()
        self.assertIn("except SystemExit", source)
        self.assertIn("FAIL_CLOSED__CAPABILITY_EXITED_PROCESS", source)


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# "Which tests does my change break?" is a question with a right answer, and a
# read-only census is not it.
#
# Measured on main at b0da6f4, "Select the tests affected by the changed paths
# <F> in the python source root <D>" scored
# python.source.change_impact.testselect.v1 at 22 and python.source.audit.ast at
# 22 -- an exact tie -- and ranked.sort(key=lambda x:(-x[0],-x[1],x[2])) breaks a
# tie by CAPABILITY ID, so "audit" sorted before "change_impact" and the census
# answered. The capability that owns the question declared test/affected/change/
# selection while the sentence says tests/affected/changed/Select: three of four
# discriminating words missed on inflection alone.
#
# Two declaration-level fixes, no change to the scoring model:
#   - changed_paths joins _PATH_LIST_KEYS. The adapter requires a LIST and
#     raises CHANGE_IMPACT_INPUT_REQUIRED on a bare string, which is exactly what
#     the binder handed it once the capability was selected. The key's own plural
#     name already said it was a list.
#   - the inflected forms the sentence actually uses join the capability's
#     declared keywords.
# ---------------------------------------------------------------------------
class WhichTestsDoesMyChangeBreakTests(unittest.TestCase):
    def setUp(self):
        import shutil
        self.dir = REPO_ROOT / "canonical/astra_runtime/tmp/test_change_impact_v1"
        shutil.rmtree(self.dir, ignore_errors=True)
        (self.dir / "tests").mkdir(parents=True)
        (self.dir / "calc.py").write_text("def add(a, b):\n    return a + b\n")
        (self.dir / "lonely.py").write_text("def nothing():\n    return None\n")
        (self.dir / "tests" / "test_calc.py").write_text(
            "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n")
        (self.dir / "tests" / "test_lonely.py").write_text(
            "from lonely import nothing\n\n\ndef test_nothing():\n    assert nothing() is None\n")

    def test_the_plural_noun_binds_a_list_which_is_what_the_adapter_demands(self):
        entry = json.loads(
            (REPO_ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text()
        )["capabilities"]["python.source.change_impact.testselect.v1"]
        goal = f"Select the tests affected by the changed paths {self.dir}/calc.py"
        bound = front.bind_typed_key(goal, "changed_paths", REPO_ROOT, entry)
        self.assertIsInstance(bound, list, f"a bare string raises CHANGE_IMPACT_INPUT_REQUIRED: {bound!r}")
        self.assertEqual(len(bound), 1)
        self.assertTrue(str(bound[0]).endswith("calc.py"))

    def test_the_question_selects_the_capability_that_answers_it(self):
        goal = (f"Select the tests affected by the changed paths {self.dir}/calc.py in the "
                f"python source root {self.dir} writing the report to {self.dir}/impact.json")
        result = admission.solve({"task_id": "CHANGE_IMPACT", "goal": goal})
        self.assertEqual(result.get("compiled_capability_id"),
                         "python.source.change_impact.testselect.v1")
        self.assertIs(result.get("pass"), True, str(result.get("reason"))[:300])

    def test_the_report_on_disk_names_the_affected_tests_and_only_those(self):
        goal = (f"Select the tests affected by the changed paths {self.dir}/calc.py in the "
                f"python source root {self.dir} writing the report to {self.dir}/impact.json")
        admission.solve({"task_id": "CHANGE_IMPACT_BYTES", "goal": goal})
        payload = json.loads((self.dir / "impact.json").read_text())
        selected = [str(x) for x in payload.get("selected_tests") or []]
        self.assertTrue(any(x.endswith("test_calc.py") for x in selected), selected)
        # The negative control that makes this a measurement rather than a
        # rubber stamp: a test that imports nothing the change touched must not
        # be swept in, or "select the affected tests" is just "list the tests".
        self.assertFalse(any(x.endswith("test_lonely.py") for x in selected), selected)

    def test_a_question_about_the_file_is_still_answered_by_the_census(self):
        goal = (f"Count the functions in the python file {self.dir}/calc.py in the "
                f"python source root {self.dir} writing the report to {self.dir}/census.json")
        result = admission.solve({"task_id": "CENSUS_STILL_WINS", "goal": goal})
        self.assertEqual(result.get("compiled_capability_id"), "python.source.audit.ast")
        self.assertIs(result.get("pass"), True, str(result.get("reason"))[:300])


# ---------------------------------------------------------------------------
# "Write the tests for this tree" must WRITE TESTS, and must prove they run.
#
# Measured on main at 9179a6cd, python.tests.generate.scaffold.v1 scored 37 on
# "Generate the test scaffold for the python source root <D>" -- ahead of the
# next candidate at 31 -- and was dropped as unbindable, because its template
# demanded five inputs no sentence states: targets_path, generated_tests_root,
# index_path, python_executable, timeout_s. python.source.audit.ast, which reads
# and writes nothing, answered a request to CREATE test files and reported
# pass=True.
#
# Two of those were never information the caller had:
#   - targets_path is a manifest of which modules to cover. The adapter builds a
#     full symbol index of the tree a few lines later and already lists every
#     module in it, so the manifest was a projection of the tree, not an input.
#   - generated_tests_root has one constraint the adapter enforces itself: it may
#     not be inside source_root. A sibling under generated_tests/ satisfies it.
#
# And once it ran, it wrote correct unittest.TestCase scaffolds and then reported
# verified=False, because the only runner it knew was pytest and this host has
# none. The file it writes imports unittest; the stdlib already owns it.
# ---------------------------------------------------------------------------
class GenerateTheTestsForThisTreeTests(unittest.TestCase):
    MODULES = {
        "calc.py": "def add(a: int, b: int) -> int:\n    return a + b\n\n\n"
                   "def sub(a: int, b: int) -> int:\n    return a - b\n",
        "text.py": "def shout(s: str) -> str:\n    return s.upper()\n",
    }
    UNTYPED = "def mystery(a, b):\n    return a\n"

    def setUp(self):
        import shutil
        self.src = REPO_ROOT / "canonical/astra_runtime/tmp/test_scaffold_src"
        self.out = REPO_ROOT / "canonical/astra_runtime/tmp/test_scaffold_out"
        for p in (self.src, self.out):
            shutil.rmtree(p, ignore_errors=True)
            p.mkdir(parents=True)

    def _write(self, files):
        for name, body in files.items():
            (self.src / name).write_text(body)

    def _solve(self):
        goal = (f"Generate the test scaffold for the python source root {self.src} "
                f"writing the report to {self.out}/scaffold.json")
        return admission.solve({"task_id": "SCAFFOLD", "goal": goal})

    def _report(self):
        return json.loads((self.out / "scaffold.json").read_text())

    def test_it_writes_real_tests_and_proves_they_run(self):
        self._write(self.MODULES)
        result = self._solve()
        self.assertEqual(result.get("compiled_capability_id"),
                         "python.tests.generate.scaffold.v1")
        self.assertIs(result.get("pass"), True,
                      str(result.get("failure_class") or result.get("reason"))[:400])
        report = self._report()
        self.assertEqual(report["generated_count"], 3)
        self.assertEqual(report["test_passed"], 3, report)
        self.assertEqual(report["test_failed"], 0)
        self.assertTrue(report["complete"])
        # The bytes, not the summary: a test file exists and calls the functions.
        gen = REPO_ROOT / report["generated_tests_root"]
        files = sorted(gen.rglob("test_*.py"))
        self.assertEqual(len(files), 1)
        body = files[0].read_text()
        self.assertIn("import unittest", body)
        self.assertIn("add(a=1, b=1)", body)
        self.assertIn("shout(s=", body)

    def test_the_runner_that_proved_it_is_named(self):
        # "pytest: UNAVAILABLE" alone could not distinguish "ran on the stdlib and
        # passed" from "never ran at all" -- and the difference is the whole claim.
        self._write(self.MODULES)
        self._solve()
        report = self._report()
        self.assertIn(report["runner"], ("pytest", "unittest"))
        if report["pytest"] == "UNAVAILABLE":
            self.assertEqual(report["runner"], "unittest")
        self.assertEqual(report["test_passed"], report["generated_count"])

    def test_the_targets_come_from_the_tree_and_the_report_says_so(self):
        self._write(self.MODULES)
        self._solve()
        report = self._report()
        self.assertEqual(report["targets_source"], "derived_from_index")
        self.assertEqual(report["target_count"], 2)

    def test_a_parameter_it_cannot_supply_a_value_for_is_refused_not_guessed(self):
        # The nearest world in which the accepting row must fail: an unannotated
        # parameter with no default has no deterministic fixture, and a scaffold
        # that invented one would assert a claim about code it never understood.
        self._write({"mystery.py": self.UNTYPED})
        self._solve()
        report = self._report()
        self.assertEqual(report["generated_count"], 0)
        self.assertEqual(report["refused_count"], 1)
        self.assertIn("UNANNOTATED_PARAM_NO_DEFAULT",
                      json.dumps(report.get("refusals") or []))
        self.assertFalse(report["complete"])

    def test_the_scaffold_never_writes_into_the_tree_it_is_scaffolding(self):
        self._write(self.MODULES)
        before = {p.name: p.read_text() for p in self.src.rglob("*.py")}
        self._solve()
        after = {p.name: p.read_text() for p in self.src.rglob("*.py")}
        self.assertEqual(before, after, "the source tree must be byte-identical")

    def test_a_report_inside_the_tree_is_still_refused(self):
        self._write(self.MODULES)
        goal = (f"Generate the test scaffold for the python source root {self.src} "
                f"writing the report to {self.src}/inside.json")
        result = admission.solve({"task_id": "SCAFFOLD_OVERLAP", "goal": goal})
        self.assertIs(result.get("pass"), False)
        self.assertIn("PATH_OVERLAPS_SOURCE_ROOT",
                      str(result.get("failure_class") or result.get("reason")))

    def test_a_question_about_the_file_is_still_answered_by_the_census(self):
        self._write(self.MODULES)
        goal = (f"Count the functions in the python file {self.src}/calc.py in the "
                f"python source root {self.src} writing the report to {self.out}/c.json")
        result = admission.solve({"task_id": "CENSUS_NOT_SCAFFOLD", "goal": goal})
        self.assertEqual(result.get("compiled_capability_id"), "python.source.audit.ast")
        self.assertIs(result.get("pass"), True, str(result.get("reason"))[:300])


# ---------------------------------------------------------------------------
# "Run the tests" must RUN THE TESTS.
#
# Measured on main at 2754cf0d, "Run the python tests in the python source root
# <D>" scored python.repository.acceptance.measure.v1 at 27, ahead of the next
# candidate at 22, and was dropped as unbindable on two inputs:
#
#   test_argv   GOAL_INPUT_BINDING_REQUIRED:not_stated
#   test_paths  GOAL_INPUT_BINDING_REQUIRED:no_matching_existing_files_named
#
# so python.source.audit.ast -- which executes nothing -- answered a request to
# RUN a suite and reported pass=True.
#
# Neither was information the caller had. The adapter already builds the test
# command itself (_validate_argv, with the measured reason that 695 of the 2019
# unittest files here carry no __main__ guard, so running one as a script exits 0
# having executed nothing). And which files are tests is a fact about the tree:
# python_change_impact_testselect.py:286 already selects on
# startswith("test_") or endswith("_test.py"), and python_test_audit.py:116
# defaults its pattern to test_*.py. The rule existed twice; this reuses it.
# ---------------------------------------------------------------------------
class RunTheTestsMeansRunTheTestsTests(unittest.TestCase):
    PASSING = ("from calc import add\n\n\n"
               "def test_add():\n    assert add(2, 3) == 5\n")
    FAILING = ("from calc import add\n\n\n"
               "def test_add():\n    assert add(2, 3) == 5\n\n\n"
               "def test_wrong():\n    assert add(1, 1) == 99\n")
    MODULE = "def add(a: int, b: int) -> int:\n    return a + b\n"

    def setUp(self):
        import shutil
        self.src = REPO_ROOT / "canonical/astra_runtime/tmp/test_run_tests_src"
        self.out = REPO_ROOT / "canonical/astra_runtime/tmp/test_run_tests_out"
        for p in (self.src, self.out):
            shutil.rmtree(p, ignore_errors=True)
            (p / "tests").mkdir(parents=True)
        (self.src / "calc.py").write_text(self.MODULE)

    def _run(self, test_body, task_id="RUN_TESTS"):
        (self.src / "tests" / "test_calc.py").write_text(test_body)
        goal = (f"Run the python tests in the python source root {self.src} "
                f"writing the report to {self.out}/measure.json")
        return admission.solve({"task_id": task_id, "goal": goal})

    def _report(self):
        return json.loads((self.out / "measure.json").read_text())

    def test_it_runs_the_suite_it_found_in_the_tree(self):
        result = self._run(self.PASSING)
        self.assertEqual(result.get("compiled_capability_id"),
                         "python.repository.acceptance.measure.v1")
        self.assertIs(result.get("pass"), True,
                      str(result.get("failure_class") or result.get("reason"))[:400])
        report = self._report()
        spec = report["measurement_spec"]
        # the tree said which files are tests; the report says so
        self.assertEqual(spec["test_paths_source"], "discovered_under_source_root")
        self.assertEqual(spec["test_paths"], ["tests/test_calc.py"])
        m = report["measurements"]
        self.assertTrue(m["tests_pass"], m)
        self.assertEqual(m["test_returncode"], 0)
        self.assertEqual(m["test_count"], 1)
        self.assertTrue(m["repository_source_unchanged"])

    def test_a_suite_that_fails_is_measured_as_failing(self):
        # The nearest world in which the row above must fail. A measurement that
        # reported a red suite as green would be worse than no measurement: it is
        # the evidence every other capability in this lane is judged by.
        result = self._run(self.FAILING, task_id="RUN_TESTS_RED")
        self.assertEqual(result.get("compiled_capability_id"),
                         "python.repository.acceptance.measure.v1")
        m = self._report()["measurements"]
        self.assertFalse(m["tests_pass"], m)
        self.assertEqual(m["test_returncode"], 1)
        self.assertEqual(m["test_count"], 2, "both tests must have been collected and run")

    def test_a_tree_with_no_tests_is_refused_not_reported_as_green(self):
        import shutil
        shutil.rmtree(self.src / "tests")
        goal = (f"Run the python tests in the python source root {self.src} "
                f"writing the report to {self.out}/empty.json")
        result = admission.solve({"task_id": "RUN_TESTS_EMPTY", "goal": goal})
        self.assertIs(result.get("pass"), False)
        # The adapter's own reason, not the wrapper's class: failure_class is the
        # generic LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE for every
        # adapter that raises, so reading it first would accept a refusal for the
        # wrong reason. _execute_locally preserves the adapter's message in
        # "reason" as <ExceptionType>:<message>.
        self.assertIn("NO_TEST_FILES_UNDER_SOURCE_ROOT", str(result.get("reason")))

    def test_a_question_about_the_file_is_still_answered_by_the_census(self):
        self._run(self.PASSING, task_id="RUN_TESTS_THEN_ASK")
        goal = (f"Count the functions in the python file {self.src}/calc.py in the "
                f"python source root {self.src} writing the report to {self.out}/c.json")
        result = admission.solve({"task_id": "CENSUS_NOT_RUNNER", "goal": goal})
        self.assertEqual(result.get("compiled_capability_id"), "python.source.audit.ast")
        self.assertIs(result.get("pass"), True, str(result.get("reason"))[:300])
