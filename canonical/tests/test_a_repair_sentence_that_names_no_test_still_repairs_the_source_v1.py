"""A repair sentence that names no test file must still repair the source.

Three defects, measured on main at 96015b9, each of which on its own was enough
to make the whole repair lane report success without doing anything.

1. THE BINDER HANDED THE REPAIR ADAPTER ITS OWN REPORT AS THE TEST TO FIX.

   goal       "Fix the failing test in the python source root D and write the
               report to D_out/r1.json"
   selected   python.software.repair.apply.verified.v1
   test_paths ["canonical/astra_runtime/tmp/hx/r1.json"]

   ``goal_compiler._bind_inputs`` has a fallback for a ``*_paths`` key whose
   role word was stated but whose files were named separately.  Two filters --
   the output-verb exclusion and ``_claimed_paths`` -- were already applied to
   the role list above it and to the derived ``*_argv`` below it, but not to
   this fallback, which is the one that fires for the ordinary phrasing.

2. A COMMAND LINE BOUND BEFORE THE CORPUS EXISTED CANNOT NAME THE CORPUS.

   With the corpus discovered at run time, the adapter honoured the argv bound
   at compile time from targets that did not exist yet.  It collected zero
   tests and returned 0:

   pre_apply_test_returncode  0
   applied                    false
   status                     PASS__STATED_TEST_ALREADY_PASSES_NOTHING_TO_REPAIR

   on a fixture whose ``add(1, 2)`` returned -1 and whose test genuinely failed.
   Zero tests passing is not a passing suite, and gate 1 read it as "already
   correct" and declined to repair a file that was broken.

3. ONE OF THE ELEVEN ``TEST_PATHS_REQUIRED`` ADAPTERS HAD NO DISCOVERY.

   ``python_test_corpus_discovery_v1`` was written for all eleven and wired into
   two.  This is the third.

The end-to-end result on this branch, through the front door:

    BEFORE  def add(a, b): return a - b     test FAILS
    solve("Fix the failing test in the python source root D and write the
           report to D_out/r1.json")
    AFTER   def add(a, b): return a + b     test PASSES

Every test here fails on baseline.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import goal_compiler as gc
from canonical.runtime import live_brain_route_admission_v1 as admission
from canonical.runtime import live_integrated_brain_v1 as lb
from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as apply_mod

BROKEN_CALC = "def add(a, b):\n    return a - b\n"
FIXED_CALC = "def add(a, b):\n    return a + b\n"
TEST_CALC = (
    "import sys, pathlib\n"
    "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\n"
    "import unittest\n"
    "import calc\n"
    "\n"
    "\n"
    "class TestCalc(unittest.TestCase):\n"
    "    def test_add(self):\n"
    "        self.assertEqual(calc.add(1, 2), 3)\n"
    "\n"
    "\n"
    'if __name__ == "__main__":\n'
    "    unittest.main()\n"
)

REPAIR_CID = "python.software.repair.apply.verified.v1"


def _broken_tree(base: Path) -> Path:
    """A source tree whose one test genuinely fails on the source as written."""
    src = base / "p"
    (src / "tests").mkdir(parents=True)
    (src / "calc.py").write_text(BROKEN_CALC)
    (src / "tests" / "test_calc.py").write_text(TEST_CALC)
    return src


class _Tree(unittest.TestCase):
    """A fixture UNDER the repository.

    The adapter resolves every path against the repository root and refuses
    anything outside it (SOURCE_ROOT_OUTSIDE_REPOSITORY).  A tempdir in /tmp
    would therefore measure the adapter's path law rather than the defect under
    test -- and the refusal would look like a pass on every assertion that only
    checks "it raised".
    """

    _NEXT = 0

    def setUp(self):
        type(self)._NEXT += 1
        self.base = (REPO_ROOT / "canonical/astra_runtime/tmp"
                     / ("test_repair_no_test_named_%d_%d"
                        % (os.getpid(), type(self)._NEXT)))
        if self.base.exists():
            shutil.rmtree(self.base)
        self.base.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.base, True)


class TheReportIsNeverATestTests(_Tree):
    """Defect 1: the binder gave the adapter its own report as the test."""

    def _goal(self, src: Path, out: Path) -> str:
        return ("Fix the failing test in the python source root %s and write the "
                "report to %s" % (src, out))

    def test_a_sentence_naming_no_test_binds_no_test_path(self):
        src = _broken_tree(self.base)
        out = self.base / "r1.json"
        goal = self._goal(src, out)
        bound = gc._bind_inputs(goal, REPO_ROOT,
                                _registry_entry(REPAIR_CID))
        self.assertNotIn(str(out), [str(x) for x in bound.get("test_paths", [])],
                         "the report was handed to the adapter as a test to fix")
        self.assertEqual(bound.get("test_paths"), [],
                         "the identity element, so the adapter derives the corpus")

    def test_the_output_path_keeps_its_own_role(self):
        src = _broken_tree(self.base)
        out = self.base / "r1.json"
        bound = gc._bind_inputs(self._goal(src, out), REPO_ROOT,
                                _registry_entry(REPAIR_CID))
        self.assertTrue(str(bound["output_path"]).endswith("r1.json"), bound)

    def test_the_same_sentence_still_selects_the_repair_capability(self):
        # Losing the bogus test_paths must not cost the capability the ranking:
        # a capability that cannot bind every arg it declares is silently
        # replaced by a weaker one, which is the defect class this pins against.
        src = _broken_tree(self.base)
        out = self.base / "r1.json"
        compiled = lb.compile_against_live_registry(
            self._goal(src, out), str(REPO_ROOT))[2]
        self.assertEqual(compiled.get("selected_capability"), REPAIR_CID)


class ZeroCollectedTestsIsNotAPassingSuiteTests(_Tree):
    """Defect 2: a stale argv ran nothing and gate 1 called that a pass."""

    def _args(self, src: Path, out: Path) -> dict:
        return {"source_root": str(src), "test_paths": [],
                "output_path": str(out), "timeout_s": 60}

    def test_a_discovered_corpus_yields_a_command_that_runs_it(self):
        src = _broken_tree(self.base)
        out = self.base / "r.json"
        result = apply_mod.run(self._args(src, out), REPO_ROOT)
        # The whole defect in one assertion: a suite that was found must be run.
        self.assertEqual(result.get("test_paths_source"),
                         "discovered_under_source_root")
        self.assertEqual(result.get("pre_apply_test_returncode"), 1,
                         "the broken test must be measured as failing, not as "
                         "already passing")

    def test_a_stale_argv_cannot_make_a_broken_source_look_correct(self):
        src = _broken_tree(self.base)
        out = self.base / "r.json"
        args = self._args(src, out)
        # Exactly the argv the binder produced on baseline: the collecting
        # runner built for targets that did not exist.  It must be ignored
        # rather than honoured, because it collects nothing.
        args["test_argv"] = [sys.executable, "-c", "pass"]
        result = apply_mod.run(args, REPO_ROOT)
        self.assertEqual(result.get("pre_apply_test_returncode"), 1,
                         "a command that collects zero tests returned 0 and was "
                         "read as 'the test already passes'")
        self.assertNotEqual(result.get("status"),
                            "PASS__STATED_TEST_ALREADY_PASSES_NOTHING_TO_REPAIR")


class TheRepairActuallyHappensTests(_Tree):
    """The bytes on disk are the only evidence that matters here."""

    def test_the_broken_source_is_repaired_and_the_test_then_passes(self):
        src = _broken_tree(self.base)
        out = self.base / "r.json"
        result = apply_mod.run({"source_root": str(src), "test_paths": [],
                                "output_path": str(out), "timeout_s": 60},
                               REPO_ROOT)
        self.assertTrue(result.get("applied"), result.get("status"))
        self.assertEqual((src / "calc.py").read_text(), FIXED_CALC,
                         "the file on disk is the only proof the repair landed")
        self.assertEqual(result.get("post_apply_test_returncode"), 0)

    def test_end_to_end_through_the_front_door(self):
        # Everything above could pass while the sentence still never reached the
        # capability.  This is the assertion the other three exist to serve.
        src = _broken_tree(self.base)
        out = self.base / "r.json"
        goal = ("Fix the failing test in the python source root %s and write the "
                "report to %s" % (src, out))
        result = admission.solve({"task_id": "t", "goal": goal}) or {}
        self.assertEqual((src / "calc.py").read_text(), FIXED_CALC,
                         "solve() did not change the source: " +
                         str(result.get("failure_class") or result.get("status")))
        self.assertIsNone(result.get("failure_class"), result.get("failure_class"))


class TheNearestWorldsInWhichItMustNotFireTests(_Tree):
    """Fail closed, every time."""

    def test_a_tree_with_no_tests_is_refused_not_reported_green(self):
        src = self.base / "empty"
        src.mkdir()
        (src / "calc.py").write_text("def add(a, b):\n    return a - b\n")
        with self.assertRaises(Exception) as ctx:
            apply_mod.run({"source_root": str(src), "test_paths": [],
                           "output_path": str(self.base / "r.json"),
                           "timeout_s": 60}, REPO_ROOT)
        self.assertIn("NO_TEST_FILES_UNDER_SOURCE_ROOT", str(ctx.exception))

    def test_a_stated_test_that_already_passes_changes_nothing(self):
        src = self.base / "ok"
        (src / "tests").mkdir(parents=True)
        (src / "calc.py").write_text(FIXED_CALC)
        (src / "tests" / "test_calc.py").write_text(TEST_CALC)
        before = (src / "calc.py").read_text()
        result = apply_mod.run({"source_root": str(src), "test_paths": [],
                                "output_path": str(self.base / "r.json"),
                                "timeout_s": 60}, REPO_ROOT)
        self.assertFalse(result.get("applied"))
        self.assertEqual((src / "calc.py").read_text(), before)

    def test_a_stated_test_file_still_wins_over_discovery(self):
        src = _broken_tree(self.base)
        out = self.base / "r.json"
        # A stated path resolves against the REPOSITORY root, not the source
        # root -- that is the adapter's own contract (_safe_file(repo, raw)),
        # and stating a source-root-relative path here would measure that
        # contract instead of the stated-versus-discovered precedence.
        rel = (src / "tests" / "test_calc.py").relative_to(REPO_ROOT)
        result = apply_mod.run(
            {"source_root": str(src),
             "test_paths": [str(rel)],
             "output_path": str(out), "timeout_s": 60}, REPO_ROOT)
        self.assertEqual(result.get("test_paths_source"), "stated")
        self.assertEqual((src / "calc.py").read_text(), FIXED_CALC)

    def test_discovery_never_leaves_the_source_root(self):
        # A stray test file outside the tree must not be repaired against.
        src = _broken_tree(self.base)
        (self.base / "elsewhere_test.py").write_text(TEST_CALC)
        from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 \
            import discover_test_paths
        found = discover_test_paths(src)
        self.assertEqual([str(x) for x in found], ["tests/test_calc.py"], found)


def _registry_entry(cid: str) -> dict:
    reg = json.loads((REPO_ROOT / "canonical/runtime"
                      / "BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    return reg["capabilities"][cid]


if __name__ == "__main__":
    unittest.main()
