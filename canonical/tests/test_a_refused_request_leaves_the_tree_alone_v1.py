"""A refused request may not arrive after the damage, and a wrong answer may not arrive as PASS.

Measured 2026-10-30 on a fresh tree (`canonical/astra_runtime/tmp/…`), four advanced SWE requests:

    "Move the function mul from <calc.py> into a new module <ops.py>."
      -> the composed chain bound `mv calc.py ops.py`, which OVERWROTE ops.py with calc.py's bytes
         and DELETED calc.py; only then did the door notice that a file the sentence named was gone
         and refuse with FAIL_CLOSED__NAMED_INPUT_REMOVED.  The report was honest about the damage
         and the damage was already done.

    "Rerun the failing test <T> three times and tell me if it is flaky."
      -> PASS with code.impact.tree_sitter.testselect.v1, which named <T> once.  Nothing ran three
         times, no outcome was compared, no flakiness was decided.

    "Attach a debugger to the failing test <T> and show me the frame where it breaks."
      -> PASS with the same test selection.  No process was debugged, no breakpoint was set.

    "Which tests do I need to run after changing <f>?"
      -> PASS with python.repository.acceptance.measure.v1 -- the repository's suite measured, not
         the change's impact (and the artifact it wrote carried `selected_tests: []`).

The first is a data-loss defect and the other three are the "a file write is not an answer" seam.
Each is closed at the layer that owns the decision: the composer refuses a FILE command for a
DEFINITION before it runs, the answer gate's own table refuses the two effects no row declares, and
the impact question is shortlisted onto the rows that declare impact analysis (with the stated file
derived into the `changed_paths` list the row declares).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_refusal_after_damage"
REL = WORK.relative_to(ROOT).as_posix()

CALC = ("def mul(a, b):\n    return a * b\n\n\ndef add(a, b):\n    return a + b\n")


def _fresh() -> pathlib.Path:
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / "pkg").mkdir(parents=True)
    (WORK / "pkg/calc.py").write_text(CALC, encoding="utf-8")
    (WORK / "pkg/test_calc.py").write_text(
        "import unittest\n\nimport calc\n\n\nclass T(unittest.TestCase):\n"
        "    def test_mul(self):\n        self.assertEqual(calc.mul(2, 3), 6)\n", encoding="utf-8")
    return WORK


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ARefusedRequestLeavesTheTreeAlone(unittest.TestCase):
    def setUp(self):
        _fresh()

    def tearDown(self):
        shutil.rmtree(WORK, ignore_errors=True)

    def test_a_symbol_move_is_not_a_file_move(self) -> None:
        """The source must survive a request the machine declines to answer."""
        source = WORK / "pkg/calc.py"
        before = _digest(source)
        result = door.solve({"task_id": "MOVE_FN",
                             "goal": "Move the function mul from %s/pkg/calc.py into a new module "
                                     "%s/pkg/ops.py." % (REL, REL)})
        self.assertFalse(result.get("pass"), result.get("status"))
        self.assertTrue(source.is_file(), "the stated source was deleted by a refused request")
        self.assertEqual(_digest(source), before, "the stated source was rewritten")
        self.assertNotIn("NAMED_INPUT_REMOVED", str(result.get("failure_class") or ""),
                         "the refusal arrived after the damage again")

    def test_a_flaky_verdict_is_not_a_test_selection(self) -> None:
        result = door.solve({"task_id": "FLAKY",
                             "goal": "Rerun the failing test %s/pkg/test_calc.py three times and tell "
                                     "me if it is flaky." % REL})
        self.assertFalse(result.get("pass"), result.get("status"))
        self.assertIn("STATED_FLAKY_VERDICT_NOT_PROVIDED_BY_CAPABILITY",
                      json.dumps(result.get("stated_answer_errors") or []))
        # The refusal must land BEFORE anything runs.  A named row is expected here: the door
        # compiles, then the answer gate says "this row does not provide the stated effect".
        # Asserting that no particular row was named would be a claim about routing internals, and
        # it went stale the moment the shortlist changed -- what must never happen is EXECUTION.
        self.assertFalse(result.get("executed"), result.get("status"))
        self.assertFalse(result.get("tool_executed"), result.get("status"))

    def test_a_debugger_is_not_an_index(self) -> None:
        result = door.solve({"task_id": "DEBUGGER",
                             "goal": "Attach a debugger to the failing test in %s/pkg/test_calc.py "
                                     "and show me the frame where it breaks." % REL})
        self.assertFalse(result.get("pass"), result.get("status"))
        self.assertIn("STATED_DEBUGGER_FRAME_NOT_PROVIDED_BY_CAPABILITY",
                      json.dumps(result.get("stated_answer_errors") or []))

    def test_which_tests_a_change_breaks_is_not_a_repository_measurement(self) -> None:
        result = door.solve({"task_id": "IMPACT",
                             "goal": "Which tests do I need to run after changing %s/pkg/calc.py?" % REL})
        self.assertNotEqual(result.get("compiled_capability_id"),
                            "python.repository.acceptance.measure.v1",
                            "a repository measurement answered an impact question")
        self.assertEqual(result.get("compiled_capability_id"),
                         "python.source.change_impact.testselect.v1", result.get("status"))

    def test_the_derived_impact_input_is_the_list_the_row_declares(self) -> None:
        """The front binder fills the slot with one path; the row declares a LIST of them."""
        from canonical.runtime import declared_input_derivation_v1 as derivation
        from canonical.runtime import live_integrated_brain_v1 as brain
        registry = brain.load_verified_registry(include_extended=True)
        entry = registry["python.source.change_impact.testselect.v1"]
        proven = {key: row["value"] for key, row in derivation.derive(
            "Which tests do I need to run after changing %s/pkg/calc.py?" % REL,
            entry, ROOT).items()}
        self.assertEqual(proven.get("changed_paths"), [REL + "/pkg/calc.py"])
        self.assertTrue(derivation.is_swe_request(
            "Which tests do I need to run after changing %s/pkg/calc.py?" % REL),
            "an impact question is an explicit software-engineering request")


if __name__ == "__main__":
    unittest.main()
