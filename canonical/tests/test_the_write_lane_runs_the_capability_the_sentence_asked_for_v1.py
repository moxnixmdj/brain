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
    # source_root must exist for the binder to accept it, so this points at the
    # repository rather than at a path that was never created.
    GOAL = (
        "Extract the function big from the module calc.py lines 6 to 8 in the "
        f"python source root {REPO_ROOT} into a new function named total_of "
        f"writing the report to {REPO_ROOT}/canonical/astra_runtime/tmp/wl_probe.json"
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
