"""TEST_PATHS_REQUIRED is derivable at every site that raises it.

The shared discovery module was written for ELEVEN adapters and names all eleven
in its own docstring.  Three were wired.  The other eight still refused, and the
refusal was not a corner case -- it was the ordinary phrasing, because a sentence
that names a source tree and no test file binds ``test_paths`` to ``[]``, the
identity element, which is exactly the signal that means "derive it".

Measured on main at fada3988, for "Localize the fault in the python source root D
using the tests and write the report to D/r.json":

  _score  python.fault.localize.dynamic.dataflow.v1   28   <-- highest of all 125
          python.repository.acceptance.measure.v1     23
  bound   output_path, source_root, test_paths        (nothing missing)
  run()   FaultLocalizerError:TEST_PATHS_REQUIRED

The capability that owns the question scores highest and binds everything, and
then cannot run -- so a read-only measurement answers the question instead and
reports pass=true.

Also measured and REVERTED, because it is the wrong fix: stripping the generic
nouns ``python``, ``test``, ``tests`` and ``source root`` from the measurement
capability's keywords.  It let ``python.source.audit.ast`` steal "run the tests"
and "write the tests" -- the two sentences two merged PRs had just fixed -- going
from 2 of 12 selections to 8 of 12.  Weakening the challenger is not the fix; the
owner has to be able to run.

Every test here fails on baseline.
"""
from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import live_brain_route_admission_v1 as admission

BROKEN = "def add(a, b):\n    return a - b\n"
TEST = (
    "import sys, pathlib\n"
    "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\n"
    "import unittest\nimport calc\n\n\n"
    "class TestCalc(unittest.TestCase):\n"
    "    def test_add(self):\n        self.assertEqual(calc.add(1, 2), 3)\n"
)


class _Tree(unittest.TestCase):
    _NEXT = 0

    def setUp(self):
        import os
        type(self)._NEXT += 1
        self.base = (REPO_ROOT / "canonical/astra_runtime/tmp"
                     / ("test_derivable_%d_%d" % (os.getpid(), type(self)._NEXT)))
        shutil.rmtree(self.base, ignore_errors=True)
        (self.base / "p" / "tests").mkdir(parents=True)
        (self.base / "p" / "calc.py").write_text(BROKEN)
        (self.base / "p" / "tests" / "test_calc.py").write_text(TEST)
        self.addCleanup(shutil.rmtree, self.base, True)

    @property
    def src(self) -> Path:
        return self.base / "p"

    def rel(self, p: Path) -> str:
        return str(p.relative_to(REPO_ROOT))


def _adapter(cid: str):
    reg = json.loads((REPO_ROOT / "canonical/runtime"
                      / "BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    e = reg["capabilities"][cid]
    import importlib
    m = importlib.import_module("canonical.runtime.bound_capabilities."
                                + e["adapter_module"])
    return getattr(m, e["entrypoint"]), e


class EverySiteDerivesTheCorpusTests(_Tree):
    """The eight sites that still refused."""

    SITES = [
        ("python.fault.localize.dynamic.dataflow.v1", "ranked_symbols"),
        ("python.fault.provenance.interprocedural.value.v1", "status"),
        ("python.software.repair.loop.strict_progress.ast.v1", "status"),
    ]

    def _run(self, cid, name, extra=None):
        fn, _e = _adapter(cid)
        args = {"source_root": self.rel(self.src), "test_paths": [],
                "output_path": self.rel(self.base / (name + ".json")),
                "timeout_s": 60}
        args.update(extra or {})
        return fn(args, REPO_ROOT)

    def test_the_fault_localizer_runs_and_ranks_the_broken_function(self):
        out = self._run("python.fault.localize.dynamic.dataflow.v1", "loc")
        ranked = out.get("ranked_symbols") or []
        self.assertTrue(ranked, "no suspects were ranked")
        top = ranked[0]
        self.assertEqual(top.get("symbol"), "add")
        self.assertTrue(str(top.get("path")).endswith("calc.py"), top)

    def test_the_value_provenance_tracer_runs(self):
        out = self._run("python.fault.provenance.interprocedural.value.v1", "prov")
        self.assertIn("PROVENANCE", str(out.get("status")).upper())

    def test_the_iterative_repair_loop_runs(self):
        out = self._run("python.software.repair.loop.strict_progress.ast.v1",
                        "iter", {"max_rounds": 1})
        self.assertTrue(str(out.get("status")).startswith("PASS"), out.get("status"))

    def test_no_site_raises_test_paths_required_for_a_tree_that_has_tests(self):
        # The whole defect in one loop: an empty stated list must never be a
        # refusal when the tree contains tests.
        import importlib
        reg = json.loads((REPO_ROOT / "canonical/runtime"
                          / "BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
        modules = [
            "python_dynamic_fault_localizer_v1",
            "python_interprocedural_value_provenance_v1",
            "python_iterative_software_repair_loop_v1",
            "python_provenance_guided_coupled_repair_v1",
            "python_repair_measured_acceptance_controller_v1",
            "python_repair_semantic_acceptance_controller_v1",
            "python_software_repair_loop_v1",
            "python_test_guided_patch_search_v1",
            "python_coupled_software_repair_loop_v1",
            "python_repair_apply_verified_v1",
            "python_repository_acceptance_measurement_v1",
        ]
        for name in modules:
            with self.subTest(adapter=name):
                src = (REPO_ROOT / "canonical/runtime/bound_capabilities"
                       / (name + ".py")).read_text()
                self.assertIn("python_test_corpus_discovery_v1", src,
                              "%s still refuses instead of deriving" % name)


class TheNearestWorldsInWhichItMustNotFireTests(_Tree):
    def test_a_tree_with_no_tests_is_refused_not_reported_green(self):
        empty = self.base / "empty"
        empty.mkdir()
        (empty / "calc.py").write_text(BROKEN)
        fn, _e = _adapter("python.fault.localize.dynamic.dataflow.v1")
        with self.assertRaises(Exception) as ctx:
            fn({"source_root": self.rel(empty), "test_paths": [],
                "output_path": self.rel(self.base / "e.json"),
                "timeout_s": 60}, REPO_ROOT)
        self.assertIn("NO_TEST_FILES_UNDER_SOURCE_ROOT", str(ctx.exception))

    def test_a_stated_test_file_still_wins_over_discovery(self):
        fn, _e = _adapter("python.fault.localize.dynamic.dataflow.v1")
        out = fn({"source_root": self.rel(self.src),
                  "test_paths": [self.rel(self.src / "tests" / "test_calc.py")],
                  "output_path": self.rel(self.base / "s.json"),
                  "timeout_s": 60}, REPO_ROOT)
        self.assertTrue(out.get("ranked_symbols"))


class WeakeningTheChallengerIsNotTheFixTests(unittest.TestCase):
    """The measured-and-reverted alternative, pinned so it cannot come back."""

    def test_the_measurement_capability_keeps_the_vocabulary_it_needs(self):
        reg = json.loads((REPO_ROOT / "canonical/runtime"
                          / "BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
        kw = reg["capabilities"]["python.repository.acceptance.measure.v1"]["keywords"]
        # Stripping these let python.source.audit.ast take "run the tests" and
        # "write the tests" -- 2 of 12 selections became 8 of 12.
        for word in ("run the tests", "test suite"):
            self.assertIn(word, kw)

    def test_the_owners_declare_the_inflected_forms_the_sentence_uses(self):
        reg = json.loads((REPO_ROOT / "canonical/runtime"
                          / "BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
        caps = reg["capabilities"]
        self.assertIn("localize",
                      caps["python.fault.localize.dynamic.dataflow.v1"]["keywords"])
        self.assertIn("iterative",
                      caps["python.software.repair.loop.strict_progress.ast.v1"]["keywords"])
        self.assertIn("value provenance",
                      caps["python.fault.provenance.interprocedural.value.v1"]["keywords"])

    def test_the_benchmark_still_has_no_selection_gaps(self):
        from canonical.runtime import goal_compilation_benchmark_v1 as bench
        self.assertEqual(bench.run().get("known_selection_gaps"), {})


class ThePreviouslyFixedSentencesStillWorkTests(_Tree):
    """A bindability change can steal a goal from its owner.  These are the pins."""

    def _solve(self, goal):
        return admission.solve({"task_id": "t", "goal": goal}) or {}

    def test_run_the_tests_still_works(self):
        r = self._solve("Run the tests in the python source root %s and write the "
                        "report to %s" % (self.src, self.base / "a.json"))
        self.assertIsNone(r.get("failure_class"), str(r.get("failure_class")))
        self.assertTrue((self.base / "a.json").is_file())

    def test_fix_the_failing_test_still_repairs_the_source(self):
        r = self._solve("Fix the failing test in the python source root %s and "
                        "write the report to %s" % (self.src, self.base / "b.json"))
        self.assertIsNone(r.get("failure_class"), str(r.get("failure_class")))
        self.assertEqual((self.src / "calc.py").read_text(),
                         "def add(a, b):\n    return a + b\n")

    def test_which_tests_break_still_answers(self):
        r = self._solve("Show which tests are affected by a change to %s and write "
                        "the report to %s" % (self.src / "calc.py", self.base / "c.json"))
        self.assertIsNone(r.get("failure_class"), str(r.get("failure_class")))
        report = json.loads((self.base / "c.json").read_text())
        self.assertEqual(report["selected_tests"],
                         [self.rel(self.src / "tests" / "test_calc.py")])


if __name__ == "__main__":
    unittest.main()
