"""Fresh-instance tests for declared input derivation and typed SWE selection.

Independent oracle: the filesystem itself (files exist, parent directory is the
one the sentence names), plus the adapter's own AST as the evidence for a
defaulted slot.  Every test is generated on a fresh temporary tree; no instance
is checked into the repository.  The last test breaks the mechanism on purpose:
a test that cannot fail is not a test.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_selection_retrieval_v1 as selection  # noqa: E402
from canonical.runtime import declared_input_derivation_v1 as derivation  # noqa: E402
from canonical.runtime import goal_compiler  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_declared_derivation"


def _fresh(case: str) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    (base / "pkg/calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (base / "pkg/util.py").write_text("def total(old_price, qty):\n    return old_price * qty\n", encoding="utf-8")
    (base / "pkg/test_calc.py").write_text(
        "import calc, unittest\nclass T(unittest.TestCase):\n"
        "    def test_add(self): self.assertEqual(calc.add(2, 3), 5)\n"
        "if __name__ == '__main__': unittest.main()\n", encoding="utf-8")
    return base


def _rel(path: pathlib.Path) -> str:
    return str(path.relative_to(ROOT))


def _entry(contract: dict) -> dict:
    return {"action_template": {"args": {"capability_id": "x", **contract},
                                "expect": {"field": "output_verified", "type": "field_equals", "value": True}}}


class DerivationEvidenceTests(unittest.TestCase):
    def test_a_stated_file_determines_the_directory_slot(self):
        base = _fresh("dir_slot")
        goal = (f"Repair the python source {_rel(base / 'pkg/calc.py')} so that the unit test "
                f"{_rel(base / 'pkg/test_calc.py')} passes, and save the report to {_rel(base / 'r.json')}.")
        d = derivation.derive(goal, _entry({
            "source_root": "${input.source_root}", "test_argv": "${input.test_argv}",
            "test_paths": "${input.test_paths}", "output_path": "${input.output_path}"}), ROOT)
        self.assertEqual(d["source_root"]["value"], _rel(base / "pkg"))
        self.assertTrue((ROOT / d["source_root"]["value"]).is_dir())
        self.assertEqual(d["source_root"]["evidence"], _rel(base / "pkg/calc.py"))
        self.assertEqual(d["test_argv"]["value"][0], sys.executable)
        self.assertEqual(d["test_argv"]["value"][-1], _rel(base / "pkg/test_calc.py"))
        self.assertTrue((ROOT / d["test_argv"]["value"][-1]).is_file())

    def test_two_source_files_are_ambiguous_and_derive_nothing(self):
        base = _fresh("ambiguous")
        goal = (f"Repair the python source {_rel(base / 'pkg/calc.py')} and "
                f"{_rel(base / 'pkg/util.py')} so that the tests pass.")
        d = derivation.derive(goal, _entry({"source_root": "${input.source_root}",
                                            "output_path": "${input.output_path}"}), ROOT)
        self.assertNotIn("source_root", d)

    def test_a_stated_rename_determines_both_names(self):
        base = _fresh("rename")
        goal = (f"Rename the parameter old_price to price in the python module "
                f"{_rel(base / 'pkg/util.py')} and save the report to {_rel(base / 'r.json')}.")
        d = derivation.derive(goal, _entry({
            "source_root": "${input.source_root}", "old_param": "${input.old_param}",
            "new_param": "${input.new_param}", "output_path": "${input.output_path}"}), ROOT)
        self.assertEqual(d["old_param"]["value"], "old_price")
        self.assertEqual(d["new_param"]["value"], "price")
        self.assertEqual(d["new_param"]["rule"], "RENAME_NEW_NAME_STATED")

    def test_adapter_defaults_are_proved_from_the_adapter_ast(self):
        registry = json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())["capabilities"]
        entry = registry["python.refactor.rename_parameter.v1"]
        defaults = derivation.adapter_defaulted_keys(entry, ROOT)
        self.assertIn("python_executable", defaults)
        self.assertIn("timeout_s", defaults)
        self.assertTrue(all(":" in evidence for evidence in defaults.values()))
        # An output path is never defaulted away: the stated destination is the promise.
        self.assertNotIn("output_path", defaults)

    def test_a_generic_module_call_is_out_of_scope(self):
        self.assertFalse(derivation.is_swe_request(
            "Call the function classify_support in canonical/runtime/x.py with the payload a.json"))
        self.assertTrue(derivation.is_swe_request("fix the bug in calc.py"))


class TypedSelectionMeasurementTests(unittest.TestCase):
    # (sentence template, which source module it is about).  The rename case
    # names a parameter that really exists in util.py; the repair cases name the
    # buggy calc.py.  A probe that names a parameter no function declares MUST
    # NOT bind a qualname -- that is the negative control in the evidence tests.
    HUMAN_SENTENCES = (
        ("Rename the parameter old_price to price in the python module {src} and save the report to {out}.", "util"),
        ("Repair the python source {src} so that the unit test {test} passes, and save the repair report to {out}.", "calc"),
        ("the add function in {src} is broken, fix it so its tests pass", "calc"),
        ("fix {src}", "calc"),
        ("Bug: {src} add() returns the wrong value. Failing test: {test}.", "calc"),
    )

    def test_human_shaped_swe_sentences_select_a_relevant_capability(self):
        base = _fresh("selection")
        calc, util = _rel(base / "pkg/calc.py"), _rel(base / "pkg/util.py")
        test, out = _rel(base / "pkg/test_calc.py"), _rel(base / "out.json")
        registry = dict(load_verified_registry())
        selected = []
        for template, which in self.HUMAN_SENTENCES:
            goal = template.format(src=util if which == "util" else calc, test=test, out=out)
            decision = selection.select(goal, registry, ROOT, 8)
            self.assertEqual(decision["status"], "SELECTED", (goal[:80], decision.get("reason")))
            cid = str(decision["selected_capability"])
            self.assertTrue(any(word in cid for word in ("refactor", "repair", "patch", "audit", "fault")),
                            (goal[:80], cid))
            selected.append(cid)
        self.assertEqual(len(selected), 5)

    def test_breaking_the_derivation_breaks_the_selection(self):
        """Mutation control: with no stated evidence the selector must refuse.

        The evidence has TWO readers now, and breaking only one of them proved
        nothing: the derivation supplies the typed slots, and the sentence's own
        paths supply the scope.  Measured 2026-10-31: with
        ``derivation.stated_existing_files`` emptied, a row that declares its
        ``source_root`` may be a FILE still admitted the request and answered
        SELECTED -- the control passed a selector that had lost its evidence.
        Both readers are cut here, which is what "no stated evidence" means.
        """
        base = _fresh("mutation")
        goal = f"Repair the python source {_rel(base / 'pkg/calc.py')} so that the tests pass."
        registry = dict(load_verified_registry())
        with mock.patch.object(derivation, "stated_existing_files", return_value=[]), \
                mock.patch.object(goal_compiler, "_repo_paths", return_value=[]):
            decision = selection.select(goal, registry, ROOT, 8)
        self.assertNotEqual(decision.get("status"), "SELECTED", decision)


if __name__ == "__main__":
    unittest.main()
