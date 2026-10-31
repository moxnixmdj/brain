"""A package-rooted suite must be run where its imports resolve, and a localization that
localized nothing is not a PASS.

Measured 2026-10-31 on the 18-sentence probe (`swe_probe_20261029/swe_probe.py`), fixture
``<d>/pkg`` with ``<d>/pkg/test_calc.py`` doing ``from pkg.calc import add`` and
``<d>/pkg/calc.py`` returning ``a - b``:

* ``fix_broken`` / ``repair_full`` / ``bug_report`` all came back
  ``FAIL__LIVE_CONTROLLER_EXECUTION`` (``GuidedRepairError:GUIDANCE_EMPTY``).  The dynamic
  localizer had reported ``PASS__BOUNDED_DYNAMIC_FAULT_LOCALIZATION`` with
  ``ranked_lines == []``, because the only directory on ``PYTHONPATH`` was the source
  directory itself, so every test died on its own import line and no application line was
  ever executed.
* Once the import path was fixed the guided engine found the one-token patch
  (``Sub->Add``) and verified it, but the repair adapter's own in-place gate still failed:
  it built the environment from the working directory alone.
* With both fixed, all three sentences repair the source and pass; the probe goes 3/18 -> 7/18.

The oracle here is the TREE: the function is read back out of the file, never the report.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import python_dynamic_fault_localizer_v1 as localizer
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as patch_search

BASE = ROOT / "canonical/astra_runtime/tmp/import_root_tests"

CALC = "def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n"
TEST_CALC = (
    "import unittest\nfrom pkg.calc import add, mul\n\nclass T(unittest.TestCase):\n"
    "    def test_add(self):\n        self.assertEqual(add(2,3),5)\n"
    "    def test_mul(self):\n        self.assertEqual(mul(2,3),6)\n"
)


def _tree(tag: str) -> pathlib.Path:
    d = BASE / tag
    if d.exists():
        shutil.rmtree(d)
    (d / "pkg").mkdir(parents=True)
    (d / "pkg/__init__.py").write_text("", encoding="utf-8")
    (d / "pkg/calc.py").write_text(CALC, encoding="utf-8")
    (d / "pkg/test_calc.py").write_text(TEST_CALC, encoding="utf-8")
    return d


class TheSuiteRunsWhereTheImportsPointTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(BASE, ignore_errors=True)

    def test_the_project_root_is_derived_from_the_tests_imports(self):
        d = _tree("env")
        env = patch_search._source_env(d / "pkg", d / "pkg/test_calc.py")
        parts = [p for p in env["PYTHONPATH"].split(":") if p]
        self.assertIn(str(d.resolve()), parts,
                      "the directory the suite imports through is not on PYTHONPATH: %r" % (parts,))
        # The IMPORT-DERIVED root is a PARENT of the package, never the package itself: putting
        # the package directory on the path is the measured stdlib shadowing receipt
        # (`import locale` -> tornado/locale.py) this rule may not repeat.
        self.assertEqual(parts[-1], str(d.resolve()),
                         "the import-derived root is not last (it may shadow): %r" % (parts,))

    def test_the_localizer_localizes_the_failing_test_not_the_last_one_run(self):
        d = _tree("attribute")
        result = localizer.run({"source_root": str(d / "pkg"),
                                "test_paths": [str(d / "pkg/test_calc.py")],
                                "output_path": str(d / "loc.json"), "timeout_s": 60}, ROOT)
        self.assertTrue(result["ranked_lines"], "the localization is empty")
        top = result["ranked_lines"][0]
        self.assertEqual(top["function"], "add",
                         "the ranking named %r, not the function the failing test exercises"
                         % (top["function"],))
        self.assertEqual(top["line"], 2, result["ranked_lines"][:3])

    def test_an_empty_localization_is_not_a_pass(self):
        d = _tree("empty")
        (d / "pkg/calc.py").write_text("VALUE = 1\n", encoding="utf-8")
        (d / "pkg/test_calc.py").write_text(
            "import unittest\n\nclass T(unittest.TestCase):\n"
            "    def test_always_fails(self):\n        self.assertEqual(1, 2)\n",
            encoding="utf-8")
        with self.assertRaises(localizer.FaultLocalizerError) as caught:
            localizer.run({"source_root": str(d / "pkg"),
                           "test_paths": [str(d / "pkg/test_calc.py")],
                           "output_path": str(d / "loc.json"), "timeout_s": 60}, ROOT)
        self.assertIn("NO_LOCALIZED_LINE_FROM_THE_FAILING_RUN", str(caught.exception))

    def test_a_package_rooted_repair_sentence_repairs_the_source(self):
        """The whole sentence, through the door, judged by the file on disk."""
        from canonical.runtime import live_brain_route_admission_v1 as door
        d = _tree("door")
        rel = d.relative_to(ROOT).as_posix()
        result = door.solve({"task_id": "IMPORT_ROOT_REPAIR",
                             "goal": "the add function in %s/pkg/calc.py is broken, "
                                     "fix it so its tests pass" % rel})
        self.assertIs(result.get("pass"), True,
                      "%s / %s" % (result.get("status"), result.get("reason")))
        self.assertIn("def add(a, b):\n    return a + b",
                      (d / "pkg/calc.py").read_text(encoding="utf-8"),
                      "the door reported a repair the file does not contain")


if __name__ == "__main__":
    unittest.main()
