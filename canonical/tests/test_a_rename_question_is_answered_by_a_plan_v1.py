"""Which files a rename must touch is answered by a PLAN -- and a refused plan is not an answer.

Measured 2026-10-30, before this wire existed: the registry has carried
``python.source.crossfile_edit.choreograph.v1`` all along (it plans every site a checked-in change
must touch, with the evidence for each), and NO sentence could reach it.  Two ordinary phrasings
were routed to the wrong lane and a third was refused:

    "Which files must change to rename the symbol `mul` to `multiply` in <dir>?"
        -> software.repair.choreograph.crossfile.v1 (a MUTATOR) and refused
           STATED_READ_ONLY_QUESTION_ANSWERED_BY_A_WRITER      (a question answered by a writer)
    "Plan the rename of the symbol `mul` to `multiply` across <dir>."
        -> python.source.symbols.index.ast, refused PROMISED_SOURCE_CHANGE_NOT_APPLIED
    "Rename the symbol `mul` to `multiply` in <dir>."
        -> refused: no producer anywhere for the row's ``edits_path`` slot

Four rules are pinned here, each read off one of those measurements:

  1. ``edits_path`` IS DERIVED, NOT SUPPLIED.  A stated rename pair, the one stated directory and
     the ONE module under it that really defines the symbol (parsed with ``ast``) are enough to
     write the edit set the row declares; zero or several defining modules derive nothing.
  2. THE OP'S MODULE IS THE REPOSITORY-RELATIVE PATH.  The consumer compares it against the symbol
     index's own ``path`` column.  The first derivation emitted the path under ``source_root`` and
     the plan refused its only op with ``MODULE_NOT_IN_INDEX``.
  3. A ROW THAT SAYS IT DOES NOT WRITE IS NOT A WRITER, and a question is not a promise.  Both
     readings are taken from the row's OWN registry declaration and from the shape of the
     sentence -- never from an id.
  4. A PLAN THAT PLANNED NOTHING AND REFUSED ITS ONLY OP IS NOT AN ANSWER, whatever
     ``output_verified`` says.

The last rule keeps the exemption honest: an IMPERATIVE rename ("Rename `mul` to `multiply` in
<dir>") is a promise that bytes move, so a plan-only row still fails it.
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

from canonical.runtime import declared_input_derivation_v1 as derivation  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import (  # noqa: E402
    is_verified_entry,
    load_verified_registry,
)

TREE = "canonical/astra_runtime/tmp/test_rename_question_tree"
PLANNER = "python.source.crossfile_edit.choreograph.v1"


def _planner_entry() -> dict:
    """The row's own declaration -- the derivation reads the slots it declares."""
    entry = dict(load_verified_registry()[PLANNER])
    entry["action_template"] = {"args": {"capability_id": PLANNER, "edits_path": "PATH",
                                         "source_root": "DIR", "output_path": "PATH"}}
    return entry

CALC = "def mul(a, b):\n    return a * b\n"
UTIL = "from pkg.calc import mul\n\n\ndef twice(a, b):\n    return mul(a, b)\n"


def _make_tree() -> None:
    base = ROOT / TREE
    shutil.rmtree(base, ignore_errors=True)
    (base / "pkg").mkdir(parents=True)
    (base / "pkg" / "calc.py").write_text(CALC, encoding="utf-8")
    (base / "pkg" / "util.py").write_text(UTIL, encoding="utf-8")


def _plan_artifact(result: dict) -> dict:
    rows = [row for row in (result.get("execution") or []) if isinstance(row, dict)]
    for row in rows:
        inner = row.get("result") or {}
        if str(inner.get("adapter") or "") == "python_crossfile_edit_choreograph":
            path = str(inner.get("output_path") or "")
            if path and (ROOT / path).is_file():
                return json.loads((ROOT / path).read_text(encoding="utf-8"))
    return {}


class ARenameQuestionIsAnsweredByAPlan(unittest.TestCase):

    def setUp(self):
        _make_tree()

    def tearDown(self):
        shutil.rmtree(ROOT / TREE, ignore_errors=True)

    # ---------------------------------------------------------------- 1. the derivation
    def test_the_edit_set_is_derived_from_the_stated_rename(self):
        goal = ("Which files must change to rename the symbol `mul` to `multiply` in %s?"
                % TREE)
        derived = derivation.derive(goal, _planner_entry(), ROOT)
        self.assertIn("edits_path", derived)
        value = derived["edits_path"]["value"]
        self.assertEqual(derived["edits_path"]["rule"],
                         "EDITS_FROM_STATED_RENAME_AND_PROVED_MODULE")
        path = ROOT / value
        self.assertTrue(path.is_file(), value)
        self.assertTrue(value.startswith("canonical/astra_runtime/tmp/"), value)
        ops = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(ops, [{"op": "rename_symbol",
                                "module": TREE + "/pkg/calc.py",
                                "name": "mul", "new_name": "multiply"}])
        self.assertEqual(derived["source_root"]["value"], TREE)

    def test_an_ambiguous_or_absent_definition_derives_nothing(self):
        # Two modules define the symbol at module scope: no single module can be proved.
        (ROOT / TREE / "pkg" / "other.py").write_text("def mul(a, b):\n    return b * a\n",
                                                      encoding="utf-8")
        goal = ("Which files must change to rename the symbol `mul` to `multiply` in %s?"
                % TREE)
        entry = _planner_entry()
        self.assertNotIn("edits_path", derivation.derive(goal, entry, ROOT))
        # No stated directory at all: the coordinate is incomplete, so nothing is written.
        self.assertNotIn("edits_path", derivation.derive(
            "Rename the symbol `mul` to `multiply`.", entry, ROOT))

    # ---------------------------------------------------------------- 2. the route
    def test_the_rename_question_is_answered_by_the_planner_and_the_plan_is_real(self):
        goal = ("Which files must change to rename the symbol `mul` to `multiply` in %s?"
                % TREE)
        result = door.solve({"task_id": "rename_question", "goal": goal})
        self.assertTrue(result.get("pass"), result.get("status"))
        self.assertEqual(result.get("compiled_capability_id"), PLANNER)
        plan = _plan_artifact(result)
        self.assertEqual(plan.get("refused_op_count"), 0, plan.get("refusals"))
        self.assertEqual(plan.get("planned_op_count"), 1)
        self.assertEqual(plan.get("ambiguous_site_count"), 0)
        self.assertEqual(sorted(plan.get("affected_files") or []),
                         [TREE + "/pkg/calc.py", TREE + "/pkg/util.py"])
        kinds = sorted(site["kind"] for site in plan["plans"][0]["sites"])
        self.assertEqual(kinds, ["DEFINITION", "IMPORT_SITE", "REFERENCE"])

    def test_the_planning_phrasing_reaches_the_same_row_and_changes_nothing(self):
        goal = "Plan the rename of the symbol `mul` to `multiply` across %s." % TREE
        result = door.solve({"task_id": "rename_plan", "goal": goal})
        self.assertTrue(result.get("pass"), result.get("status"))
        self.assertEqual(result.get("compiled_capability_id"), PLANNER)
        # A request to PLAN is not a request to DO.  Measured 2026-10-31: once the rename WRITER
        # became reachable, this sentence (whose own word is "Plan") rewrote both modules.
        self.assertEqual((ROOT / TREE / "pkg" / "calc.py").read_text(encoding="utf-8"), CALC)
        self.assertIn("from pkg.calc import mul",
                      (ROOT / TREE / "pkg" / "util.py").read_text(encoding="utf-8"))

    # ---------------------------------------------------------------- 3. the exemptions
    def test_only_a_row_that_declares_it_does_not_write_is_exempt_from_the_byte_gate(self):
        registry = load_verified_registry()
        exempt = {cid for cid, entry in registry.items()
                  if is_verified_entry(entry) and door._declares_it_does_not_write(entry)}
        self.assertEqual(exempt, {PLANNER})
        # The repair choreographer rewrites sources; it must never be read as a planner.
        self.assertFalse(door._declares_it_does_not_write(
            registry["software.repair.choreograph.crossfile.v1"]))
        # And a question is not a promise, which is what turns the exemption on.
        self.assertFalse(door._sentence_promises_a_change(
            "Which files must change to rename the symbol `mul` to `multiply` in %s?" % TREE))
        self.assertTrue(door._sentence_promises_a_change(
            "Rename the symbol `mul` to `multiply` in %s." % TREE))

    def test_an_imperative_rename_is_performed_by_the_writer_and_never_called_verified(self):
        """An imperative is a promise of bytes, and only the WRITER may answer it.

        Two over-claims are refused here.  When only the planner existed, the imperative was refused
        PROMISED_SOURCE_CHANGE_NOT_APPLIED -- a plan is not the change.  Now that the writer answers,
        the change really lands, and the remaining hazard is the opposite one: with no test named the
        adapter reports ``gate: PASS_BLIND, verified: false``, so the door must not stamp VERIFIED.
        """
        goal = "Rename the symbol `mul` to `multiply` in %s." % TREE
        result = door.solve({"task_id": "rename_imperative", "goal": goal})
        self.assertEqual(result.get("compiled_capability_id"),
                         "python.refactor.rename_symbol.v1")
        self.assertTrue(result.get("pass"), result.get("status"))
        # The promise is discharged: the symbol really was renamed, in both files.
        self.assertIn("def multiply(", (ROOT / TREE / "pkg" / "calc.py").read_text(encoding="utf-8"))
        self.assertIn("from pkg.calc import multiply",
                      (ROOT / TREE / "pkg" / "util.py").read_text(encoding="utf-8"))
        # And nothing measured it, so nothing may call it verified.
        self.assertIs(result.get("change_verified"), False)
        self.assertNotIn("AND_VERIFIED", str(result.get("status")))
        self.assertIn("APPLIED_UNVERIFIED", str(result.get("status")))

    # ---------------------------------------------------------------- 4. the truth rule
    def test_a_plan_that_planned_nothing_and_refused_its_only_op_is_not_an_answer(self):
        refused = {"execution": [{
            "capability_id": PLANNER,
            "result": {"adapter": "python_crossfile_edit_choreograph", "output_verified": True,
                       "edit_op_count": 1, "planned_op_count": 0, "refused_op_count": 1,
                       "affected_file_count": 0}}]}
        self.assertEqual(door.tool_truth_errors(refused),
                         ["TOOL_PLANNED_NOTHING_AND_REFUSED:%s:refused=1" % PLANNER])
        planned = {"execution": [{
            "capability_id": PLANNER,
            "result": {"output_verified": True, "planned_op_count": 1, "refused_op_count": 0}}]}
        self.assertEqual(door.tool_truth_errors(planned), [])


if __name__ == "__main__":
    unittest.main()
