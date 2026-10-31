"""A row that finds a patch is not the row that repairs the file.

Measured 2026-10-31, on the 54-case capability matrix: ``repair_with_report`` --
"Repair the python source <pkg>/calc.py so that the unit test <pkg>/test_calc.py
passes, and save the repair report to <pkg>/out.json." -- was the last FALSE row.
It came back ``PASS__..._EXECUTED_AND_VERIFIED`` with ``answer
{"status": "PASS__VERIFIED_CANDIDATE_PATCH_FOUND"}`` and the source BYTE-IDENTICAL
to how it was found.  The row that answered was
``python.patch.search.test_guided.ast.v1``, which says in its own registry row
that source bytes are restored after every trial and that it holds "no source
write or promotion authority".  It is a PROPOSER.

Three assertions, each an independent oracle:

  * the authority is read from the row's OWN declaration, never from its id
    (``is_source_transformer`` reads the id, and "python.patch.search..." contains
    "patch"), and a question about a change is still not a promise to make one;
  * the typed selector refuses a declared candidate-only row for a sentence that
    promises a change, and reaches the applier;
  * the whole front door, on a genuinely broken tree, leaves the source CHANGED
    (``applied`` true, ``source_restored`` false) and writes the report the
    sentence asked for -- and on an already-green tree still answers without
    editing anything.
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

from canonical.runtime import capability_selection_retrieval_v1 as selection  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime import write_authority_v1 as authority  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_a_proposer_is_not_a_repair"
PROPOSER = "python.patch.search.test_guided.ast.v1"
APPLIER = "python.software.repair.apply.verified.v1"


def _rel(path: pathlib.Path) -> str:
    return str(path.relative_to(ROOT))


def _tree(case: str, *, broken: bool) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    (base / "pkg/calc.py").write_text(
        "def add(a, b):\n    return a - b\n" if broken
        else "def add(a, b):\n    return a + b\n",
        encoding="utf-8")
    (base / "pkg/test_calc.py").write_text(
        "import unittest\n\nimport calc\n\n\nclass T(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(calc.add(2, 3), 5)\n",
        encoding="utf-8")
    return base


def _report_goal(base: pathlib.Path) -> str:
    return ("Repair the python source %s so that the unit test %s passes, and save the "
            "repair report to %s." % (_rel(base / "pkg/calc.py"),
                                      _rel(base / "pkg/test_calc.py"),
                                      _rel(base / "out.json")))


class TheAuthorityIsReadFromTheDeclarationTests(unittest.TestCase):
    def test_the_reader_separates_a_proposer_from_an_applier(self):
        registry = door.load_verified_registry()
        self.assertTrue(authority.declares_no_source_write_authority(registry[PROPOSER]))
        self.assertFalse(authority.declares_no_source_write_authority(registry[APPLIER]))

    def test_exactly_the_declared_candidate_rows_are_refused(self):
        """The set is read from the registry, so a fifth proposer cannot slip in."""
        registry = door.load_verified_registry()
        declared = {cid for cid, entry in registry.items()
                    if authority.declares_no_source_write_authority(entry)}
        self.assertEqual(declared, {
            PROPOSER,
            "python.software.repair.loop.coupled.ast.v1",
            "python.software.repair.loop.strict_progress.ast.v1",
            "python.software.repair.loop.test_guided.ast.v1",
        })

    def test_a_change_the_row_cannot_make_is_refused_and_a_question_is_not(self):
        registry = door.load_verified_registry()
        base = _tree("authority", broken=True)
        self.assertTrue(authority.cannot_perform_the_stated_change(
            _report_goal(base), registry[PROPOSER], PROPOSER).endswith(PROPOSER))
        # A question about a change promises nothing, whatever change words it uses.
        self.assertIsNone(authority.cannot_perform_the_stated_change(
            "Which files must change to rename the symbol `mul` in %s?" % _rel(base),
            registry[PROPOSER], PROPOSER))
        # An applier is never refused by this rule.
        self.assertIsNone(authority.cannot_perform_the_stated_change(
            _report_goal(base), registry[APPLIER], APPLIER))


class TheSelectorReachesTheRowWithAuthorityTests(unittest.TestCase):
    def test_the_sentence_selects_the_applier_not_the_proposer(self):
        base = _tree("select", broken=True)
        registry = dict(door.load_verified_registry())
        decision = selection.select(_report_goal(base), registry, ROOT, 8)
        self.assertEqual(decision.get("status"), "SELECTED", decision)
        self.assertEqual(decision.get("selected_capability"), APPLIER)
        # And the proposer was not silently dropped: it was ADMITTED-FALSE with a reason.
        refused = {row.get("capability_id"): row for row in decision.get("admissions") or []
                   if row.get("capability_id") == PROPOSER}
        self.assertTrue(refused, "the proposer must appear in the shortlist")
        self.assertFalse(refused[PROPOSER].get("admitted"))
        self.assertTrue(str(refused[PROPOSER].get("reason") or "")
                        .startswith("CANDIDATE_ONLY_ROW_DECLARES_NO_SOURCE_WRITE_AUTHORITY"),
                        refused[PROPOSER].get("reason"))


class TheFrontDoorRepairsTheFileTests(unittest.TestCase):
    def test_the_source_really_changes_and_the_report_is_written(self):
        base = _tree("broken", broken=True)
        source = base / "pkg/calc.py"
        result = door.solve({"task_id": "PROPOSER_IS_NOT_A_REPAIR", "goal": _report_goal(base)})
        self.assertIs(result.get("pass"), True, (result.get("status"), result.get("reason")))
        self.assertEqual(result.get("compiled_capability_id"), APPLIER)
        # Independent oracle: the bytes, not the report.
        self.assertIn("a + b", source.read_text(encoding="utf-8"))
        self.assertTrue((base / "out.json").is_file(), "the promised report must exist")
        payload = json.loads((base / "out.json").read_text(encoding="utf-8"))
        self.assertIs(payload.get("applied"), True, payload.get("status"))
        self.assertIs(payload.get("source_restored"), False, payload.get("status"))

    def test_an_unparseable_source_is_not_called_already_satisfied(self):
        """A green suite that never imports the broken file proves nothing about it."""
        base = _tree("unparseable", broken=False)
        (base / "pkg/broken.py").write_text("def oops(:\n    return 1\n", encoding="utf-8")
        result = door.solve({
            "task_id": "UNPARSEABLE",
            "goal": "Repair the python source %s so that its tests pass."
                    % _rel(base / "pkg/broken.py")})
        self.assertIs(result.get("pass"), False, result.get("status"))
        self.assertEqual(result.get("status"), "FAIL_CLOSED__NAMED_SOURCE_UNPARSEABLE",
                         result.get("status"))
        self.assertIn("def oops(:", (base / "pkg/broken.py").read_text(encoding="utf-8"))

    def test_an_already_green_tree_is_answered_without_an_edit(self):
        """Idempotency survives: the baseline run is the proof, so no byte must move."""
        base = _tree("already", broken=False)
        source = base / "pkg/calc.py"
        before = source.read_bytes()
        result = door.solve({"task_id": "ALREADY_GREEN", "goal": _report_goal(base)})
        self.assertIs(result.get("pass"), True, (result.get("status"), result.get("reason")))
        self.assertIs(result.get("already_satisfied"), True, result.get("status"))
        self.assertIs(result.get("edited"), False, "nothing may be reported as edited")
        self.assertEqual(source.read_bytes(), before, "the file must be byte-identical")


if __name__ == "__main__":
    unittest.main()
