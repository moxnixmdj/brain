"""The project-test baseline refuses neither slow suites nor empty ones.

Measured 2026-11-12 on ``8439f609``: every suite measurement -- the baseline
before an edit, the verification after it, and the runner they share -- inherited
``_run_cmd``'s implicit 20 s helper default.  A ``unittest.TestCase`` fixture
suite that sleeps 21 s died at 20.3 s with ``PROJECT_TEST_BASELINE_UNMEASURABLE``
while it was still running; the engine's own ``canonical/tests`` did not finish
in 300 s either.  Worse, a project whose tests are pytest-shaped bare
``def test_*`` functions loads as ZERO tests under Python 3.11's unittest loader
(it collects ``TestCase`` subclasses only, ``/usr/lib/python3.11/unittest/loader.py:120``),
so the gate read "no failures" and stamped the edit -- an empty measurement sold
as a green one.

The round pins both directions: a slow suite is now measured inside the
reviewed ``BASELINE_BUDGET_S`` budget, and test files inside discovery's scope
that load zero tests refuse by name instead of passing silently.  The end-to-end
extract-constant chain executes against a measured suite (the showcase that
previously passed vacuously).
"""
from __future__ import annotations

import pathlib
import shutil
import tempfile
import textwrap
import unittest

from canonical.swe_kernel import egraph_and_deductive_synthesizer_v1 as engine

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SHOWCASE = _ROOT / "canonical" / "astra_runtime" / "tmp" / "extract_chain_measured_showcase"


def _fixture(test_body: str, *, style: str = "case") -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix="baseline_gate_"))
    (root / "tests").mkdir()
    (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (root / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    if style == "case":
        body = (
            "import unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_ok(self):\n"
            f"        {test_body}\n"
        )
    else:
        body = f"def test_ok():\n    {test_body}\n"
    (root / "tests" / "test_subject.py").write_text(body, encoding="utf-8")
    return root


class TheGateWaitsForTheSuiteItMeasures(unittest.TestCase):
    def test_the_reviewed_budget_is_the_one_passed_to_every_suite_measurement(self) -> None:
        self.assertEqual(engine.BASELINE_BUDGET_S, 300.0)
        seen: list[float] = []
        original = engine._run_cmd

        def spy(argv, cwd, timeout: float = 20.0, **kw):
            seen.append(timeout)
            return original(argv, cwd, timeout=timeout, **kw)

        root = _fixture("self.assertTrue(True)")
        engine._run_cmd = spy
        try:
            engine._collect_project_bad_tests(root)
            engine._run_project_tests(root, root)
            engine._verify_no_new_test_failures(root, root, set(), [])
        finally:
            engine._run_cmd = original
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(len(seen), 3, seen)
        self.assertTrue(all(t == 300.0 for t in seen), seen)

    def test_test_files_that_discovery_loads_none_refuse_by_name(self) -> None:
        """A pytest-shaped suite is not a measurement -- the old code returned set()."""
        root = _fixture("assert True", style="function")
        try:
            with self.assertRaises(RuntimeError) as ctx:
                engine._collect_project_bad_tests(root)
            self.assertIn(
                "PROJECT_TEST_BASELINE_UNMEASURABLE:TEST_FILES_FOUND_NONE_DISCOVERABLE",
                str(ctx.exception),
            )
            ok, detail = engine._run_project_tests(root, root)
            self.assertFalse(ok)
            self.assertIn("TEST_FILES_FOUND_NONE_DISCOVERABLE", detail)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_an_empty_project_proceeds_with_nothing_to_measure(self) -> None:
        root = pathlib.Path(tempfile.mkdtemp(prefix="baseline_empty_"))
        (root / "mod.py").write_text("X = 1\n", encoding="utf-8")
        try:
            self.assertEqual(engine._collect_project_bad_tests(root), set())
            ok, _ = engine._run_project_tests(root, root)
            self.assertTrue(ok)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_tests_outside_discovery_scope_are_not_mistaken_for_this_run(self) -> None:
        """``discover`` never descends a non-package directory; files there are not evidence."""
        root = pathlib.Path(tempfile.mkdtemp(prefix="baseline_outscope_"))
        (root / "repo" / "tests").mkdir(parents=True)
        (root / "repo" / "tests" / "test_a.py").write_text(
            "import unittest\nclass T(unittest.TestCase):\n"
            "    def test_a(self): self.assertTrue(True)\n",
            encoding="utf-8",
        )
        (root / "util.py").write_text("def total(x):\n    return sum(x)\n", encoding="utf-8")
        try:
            self.assertEqual(engine._collect_project_bad_tests(root), set())
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_twenty_one_second_suite_is_measured_not_refused(self) -> None:
        """The measured before-state: this suite died at 20.3 s under the old default."""
        root = _fixture("import time; time.sleep(21); self.assertTrue(True)")
        try:
            self.assertEqual(engine._collect_project_bad_tests(root), set())
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_the_extract_chain_executes_on_a_measured_suite(self) -> None:
        """The door's showcase sentence, end to end, with a suite the gate can see."""
        shutil.rmtree(_SHOWCASE, ignore_errors=True)
        pkg = _SHOWCASE / "pkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "calc.py").write_text("def calc_total(n):\n    return n * 31 + 7\n", encoding="utf-8")
        tests = _SHOWCASE / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "test_calc.py").write_text(
            "import unittest\nfrom pkg.calc import calc_total\n"
            "class T(unittest.TestCase):\n"
            "    def test_total(self):\n"
            "        self.assertEqual(calc_total(1), 38)\n",
            encoding="utf-8",
        )
        rel = "canonical/astra_runtime/tmp/extract_chain_measured_showcase/pkg/calc.py"
        try:
            from canonical.runtime import live_brain_route_admission_v1 as door

            result = door.solve({
                "task_id": "measured_extract_showcase",
                "goal": f"refactor the function calc_total in {rel} to extract the constant",
            })
            self.assertTrue(result.get("pass"), result)
            self.assertIn(
                "EXTRACTED_CONSTANT", (pkg / "calc.py").read_text(encoding="utf-8")
            )
        finally:
            shutil.rmtree(_SHOWCASE, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
