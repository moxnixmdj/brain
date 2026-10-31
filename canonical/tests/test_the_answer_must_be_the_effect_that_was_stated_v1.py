"""The answer must BE the effect the sentence stated -- measured on the filesystem.

Each case below was a live defect on 2026-10-30, and each assertion is an
independent oracle (the tree bytes, the selected capability's own artifact, or
the verdict the capability emitted), never the door's self-report:

  * "which tests must I run after changing <f>" answered PASS while the impact
    report selected ZERO tests and named the module's own test file in
    ``affected_modules`` -- the green light to skip the tests that cover a change;
  * a test file sitting beside the changed module was not even considered,
    because the selector only looked in two literal test roots;
  * "rename the symbol X to Y in <f>" (quoted identifiers) reached a read-only
    symbol INDEX, which cannot rename anything, and the refusal was read as a
    verdict about the world;
  * a rename with no test to verify it rewrote the file and THEN reported a
    closed failure -- a refused request that had already edited the tree;
  * a gate that refused with its own JSON reason was reported as a statement
    about the registry's source type, from a different executor.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_answer_is_the_effect"


def _rel(path: pathlib.Path) -> str:
    return str(path.relative_to(ROOT))


def _tree(case: str, *, tests: bool = True) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    (base / "pkg/calc.py").write_text(
        "def add(a, b):\n    total = a + b\n    return total\n\n\ndef mul(a, b):\n    return a * b\n",
        encoding="utf-8")
    if tests:
        (base / "pkg/test_calc.py").write_text(
            "import unittest\n\nimport calc\n\n\nclass T(unittest.TestCase):\n"
            "    def test_mul(self):\n        self.assertEqual(calc.mul(2, 3), 6)\n\n"
            "    def test_add(self):\n        self.assertEqual(calc.add(2, 3), 5)\n",
            encoding="utf-8")
    return base


class TheAnswerIsTheEffectTests(unittest.TestCase):
    def test_a_change_impact_answer_selects_the_test_that_covers_the_change(self):
        """The impact row must NAME a test, not merely run to completion."""
        base = _tree("impact")
        goal = "Which tests do I need to run after changing %s?" % _rel(base / "pkg/calc.py")
        result = door.solve({"task_id": "IMPACT", "goal": goal})
        self.assertIs(result.get("pass"), True, (result.get("status"), result.get("reason")))
        artifact_path = ROOT / "canonical/astra_runtime/tmp/spool_0_output.json"
        self.assertTrue(artifact_path.is_file())
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        self.assertTrue(artifact.get("selected_tests"), artifact.get("totals"))
        self.assertTrue(any("test_calc" in p for p in artifact["selected_tests"]),
                        artifact["selected_tests"])

    def test_a_test_beside_the_module_is_a_candidate_test(self):
        """A test that lives next to the changed module covers it (measured: zero before)."""
        base = _tree("beside")
        result = door.solve({
            "task_id": "BESIDE",
            "goal": "Which tests are affected if I change %s?" % _rel(base / "pkg/calc.py")})
        self.assertIs(result.get("pass"), True, result.get("status"))
        artifact = json.loads(
            (ROOT / "canonical/astra_runtime/tmp/spool_0_output.json").read_text(encoding="utf-8"))
        self.assertTrue(artifact.get("candidate_tests") or artifact.get("selected_tests"),
                        artifact.get("totals"))

    def test_a_quoted_identifier_is_still_an_identifier(self):
        """`mul` and mul are the same symbol; the backticks are typography."""
        base = _tree("quoted")
        goal = "Rename the symbol `mul` to `multiply` in %s." % _rel(base / "pkg/calc.py")
        result = door.solve({"task_id": "QUOTED", "goal": goal})
        after = (base / "pkg/calc.py").read_text(encoding="utf-8")
        self.assertIn("def multiply(", after, result.get("status"))
        self.assertNotIn("def mul(", after)
        # the importer's call site moved with it, and the suite stayed green
        self.assertIn("calc.multiply", (base / "pkg/test_calc.py").read_text(encoding="utf-8"))
        self.assertIs(result.get("pass"), True, (result.get("status"), result.get("reason")))

    def test_a_rename_that_cannot_be_verified_is_never_called_verified(self):
        """NO TEST, NO CERTIFICATE: the blind rename lands and the result says so.

        This test used to demand that a blind rename write NOTHING, on the ground that
        an edit the door then refuses is the worst of both.  That ground is gone: the
        door no longer refuses it (measured 2026-10-31 -- ``PASS__..._EXECUTED_APPLIED_
        UNVERIFIED``, ``change_verified`` false), so the only remaining question is
        whether a correct binding-proved rename with no witness should be withheld from
        a caller who asked for it.  It should not: the rename is proved complete by the
        residual law, and what is unmeasured is the behaviour, which the payload states
        in its own words rather than claiming as verified.  So the assertions that
        matter are: the bytes moved, and nothing anywhere says VERIFIED.
        """
        base = _tree("blind", tests=False)
        source = base / "pkg/calc.py"
        before = source.read_bytes()
        result = door.solve({
            "task_id": "BLIND",
            "goal": "Rename the symbol `mul` to `multiply` in %s." % _rel(source)})
        # the work landed -- a real rename, not a dry run
        self.assertIn(b"def multiply(", source.read_bytes(), result.get("status"))
        self.assertNotEqual(source.read_bytes(), before)
        # ... and not one word of the verdict claims it was measured
        self.assertIs(result.get("change_verified"), False, result.get("status"))
        self.assertNotIn("_EXECUTED_AND_VERIFIED", str(result.get("status") or ""))
        self.assertNotIn("EXACT_SEMANTIC_ACCEPTANCE_VERIFIED", str(result.get("status") or ""))
        self.assertTrue(result.get("blind_change_evidence"), result.get("status"))

    def test_a_structured_refusal_is_reported_in_its_own_words(self):
        """A gate's own JSON reason must reach the caller, not another executor's blocker."""
        result = door.solve({
            "task_id": "REFUSAL",
            "goal": "Measure the mutation score of %s."
                    % "canonical/astra_runtime/tmp/test_answer_is_the_effect/none/cov.py"})
        # no such tree -> some closed failure whose reason is NOT a registry complaint
        self.assertIs(result.get("pass"), False)
        self.assertNotIn("BOUND_CAPABILITY_SOURCE_UNSUPPORTED",
                         json.dumps(result, default=str))

    def test_a_flaky_verdict_is_not_a_test_selection(self):
        """Nothing in the registry measures stability; a selection index must not answer it."""
        base = _tree("flaky")
        result = door.solve({
            "task_id": "FLAKY",
            "goal": "Rerun the failing test %s three times and tell me if it is flaky."
                    % _rel(base / "pkg/test_calc.py")})
        self.assertIs(result.get("pass"), False, result.get("status"))
        self.assertIn("STATED_FLAKY_VERDICT_NOT_PROVIDED_BY_CAPABILITY",
                      json.dumps(result.get("stated_answer_errors") or []))

    def test_a_stack_frame_is_not_a_symbol_index(self):
        base = _tree("debugger")
        result = door.solve({
            "task_id": "DBG",
            "goal": "Attach a debugger to the failing test in %s and show me the frame where it "
                    "breaks." % _rel(base / "pkg/test_calc.py")})
        self.assertIs(result.get("pass"), False, result.get("status"))
        self.assertIn("STATED_DEBUGGER_FRAME_NOT_PROVIDED_BY_CAPABILITY",
                      json.dumps(result.get("stated_answer_errors") or []))

    def test_running_the_suite_is_not_planning_the_run(self):
        """"Run the test suite" must reach something that RUNS tests, not an index of them."""
        base = _tree("suite")
        result = door.solve({
            "task_id": "SUITE",
            "goal": "Run the test suite for %s." % _rel(base / "pkg/test_calc.py")})
        cid = str(result.get("compiled_capability_id") or "")
        self.assertNotIn("testselect", cid, cid)
        self.assertIs(result.get("pass"), True, (result.get("status"), cid))

    def test_which_tests_a_change_breaks_is_a_selection_not_a_repository_run(self):
        base = _tree("impactroute")
        result = door.solve({
            "task_id": "IMPACTSEL",
            "goal": "Which tests do I need to run after changing %s?" % _rel(base / "pkg/calc.py")})
        cid = str(result.get("compiled_capability_id") or "")
        self.assertIn("impact", cid, cid)
        self.assertIs(result.get("pass"), True, (result.get("status"), cid))

    def test_a_request_whose_state_already_holds_is_answered_not_refused(self):
        """Idempotency: the baseline run is the proof, so no byte has to move."""
        base = _tree("already")
        # calc.py in this fixture is correct and its test passes: nothing to repair.
        result = door.solve({
            "task_id": "ALREADY",
            "goal": "Repair the python source %s so that the unit tests in %s pass."
                    % (_rel(base / "pkg/calc.py"), _rel(base / "pkg/test_calc.py"))})
        self.assertIs(result.get("pass"), True, (result.get("status"), result.get("reason")))
        self.assertIs(result.get("already_satisfied"), True, result.get("status"))
        self.assertIs(result.get("edited"), False, "nothing may be reported as edited")

    def test_a_repair_that_was_only_reported_is_not_a_repair(self):
        """FALSE-PASS REGRESSION: source byte-identical + its own test red is not PASS."""
        base = _tree("report_only")
        source = base / "pkg/calc.py"
        source.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        before = source.read_bytes()
        result = door.solve({
            "task_id": "REPORTONLY",
            "goal": "Repair the python source %s so that the unit test %s passes, and save the "
                    "repair report to %s." % (_rel(source), _rel(base / "pkg/test_calc.py"),
                                              _rel(base / "repair.json"))})
        self.assertIs(result.get("pass"), False, result.get("status"))
        self.assertTrue(str(result.get("status")).startswith("FAIL"), result.get("status"))
        # Independent oracle: the file is exactly as it was found.
        self.assertEqual(source.read_bytes(), before)

    def test_a_parse_is_not_a_lint(self):
        """A syntax tree was written; nothing was linted. That is not a lint."""
        base = WORK / "lint_js"
        if base.exists():
            shutil.rmtree(base)
        base.mkdir(parents=True)
        (base / "app.js").write_text("export function add(a, b) {\n  return a + b;\n}\n",
                                     encoding="utf-8")
        result = door.solve({"task_id": "JSLINT",
                             "goal": "Lint the javascript file %s." % _rel(base / "app.js")})
        self.assertIs(result.get("pass"), False, result.get("status"))
        self.assertNotIn("parse.tree_sitter", str(result.get("compiled_capability_id") or ""))

    def test_an_empty_test_selection_is_not_an_answer(self):
        """The sentence asked which tests to run; zero selected is not an answer."""
        base = _tree("empty", tests=False)
        result = door.solve({
            "task_id": "EMPTYSEL",
            "goal": "Which tests do I need to run after changing %s?" % _rel(base / "pkg/calc.py")})
        self.assertIs(result.get("pass"), False, result.get("status"))
        self.assertTrue(str(result.get("status") or "").startswith("FAIL_CLOSED"), result.get("status"))


if __name__ == "__main__":
    unittest.main()
