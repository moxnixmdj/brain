#!/usr/bin/env python3
"""Which files are tests is a fact about the tree, and it belongs in one place.

Eleven bound capabilities refuse ``TEST_PATHS_REQUIRED`` when the caller does not
hand them a list of test files. Every one of them already builds the test COMMAND
itself on the very next line -- each calls ``suite_argv(sys.executable, *tests)``
-- because executing a unittest file as a script only runs it when the file
carries a ``__main__`` guard, and 695 of the 2019 unittest files in this
repository do not. So the command was never the missing input.

The list of files was, and no sentence states one. Measured on main at c57b2173,
"Repair the python source root <D> so the test command passes" scored
python.software.repair.loop.coupled.ast.v1 at 34, ahead of the next candidate at
31, and was dropped as unbindable on
``test_paths:no_matching_existing_files_named``. One omission kept the whole
repair lane out of reach from the front door.

The name rule is not invented here: python_change_impact_testselect.py:286
already selects on ``name.startswith("test_") or name.endswith("_test.py")`` and
python_test_audit.py:116 defaults its pattern to ``test_*.py``. This suite pins
the shared module those two and the eleven adapters should read.
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import goal_compiler as goal_compiler  # noqa: E402
from canonical.runtime.bound_capabilities import (  # noqa: E402
    python_test_corpus_discovery_v1 as discovery,
)

REGISTRY = json.loads(
    (REPO_ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text()
)["capabilities"]


class _Tree(unittest.TestCase):
    def setUp(self):
        import shutil
        self.dir = REPO_ROOT / "canonical/astra_runtime/tmp/test_corpus_discovery_v1"
        shutil.rmtree(self.dir, ignore_errors=True)
        # Removing at setUp only left the tree behind for the next command that
        # walked the repository -- including the repo-integrity guard, which then
        # failed on TAUTOLOGICAL_ASSERTION against these fixtures' `assert True`.
        # A fixture is scratch, and scratch does not outlive the test.
        self.addCleanup(shutil.rmtree, self.dir, True)
        (self.dir / "tests").mkdir(parents=True)
        (self.dir / "calc.py").write_text("def add(a, b):\n    return a + b\n")
        (self.dir / "tests" / "test_calc.py").write_text("def test_add():\n    assert True\n")
        (self.dir / "tests" / "calc_test.py").write_text("def test_sub():\n    assert True\n")

    def write(self, rel, body="def test_x():\n    assert True\n"):
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
        return p


class TheNameRuleTests(unittest.TestCase):
    def test_the_two_spellings_the_repository_already_uses(self):
        for name in ("test_calc.py", "test_a_b.py", "calc_test.py", "test_.py"):
            with self.subTest(name=name):
                self.assertTrue(discovery.is_test_file_name(name))

    def test_a_module_under_test_is_not_a_test(self):
        for name in ("calc.py", "testing.py", "contest.py", "latest.py", "protest.py"):
            with self.subTest(name=name):
                self.assertFalse(discovery.is_test_file_name(name))

    def test_the_rule_matches_the_selector_that_already_encodes_it(self):
        # If this ever diverges, two capabilities will disagree about which files
        # are tests and the change-impact report will not match the suite that ran.
        src = (REPO_ROOT / "canonical/runtime/bound_capabilities"
               / "python_change_impact_testselect.py").read_text()
        self.assertIn('name.startswith("test_")', src)
        self.assertIn('name.endswith("_test.py")', src)


class DiscoveryTests(_Tree):
    def test_it_finds_tests_in_a_subdirectory_not_just_at_the_top(self):
        # The whole reason the walk is recursive: the ordinary layout puts tests
        # in tests/, and glob("test_*.py") over the root finds none of them.
        found = discovery.discover_test_paths(self.dir)
        self.assertEqual(found, ["tests/calc_test.py", "tests/test_calc.py"])

    def test_both_spellings_of_a_test_file_are_found(self):
        found = discovery.discover_test_paths(self.dir)
        self.assertIn("tests/test_calc.py", found)
        self.assertIn("tests/calc_test.py", found)

    def test_the_answer_is_sorted_so_two_runs_agree(self):
        self.assertEqual(discovery.discover_test_paths(self.dir),
                         sorted(discovery.discover_test_paths(self.dir)))

    def test_caches_and_vendored_trees_are_not_measured_as_the_project(self):
        for rel in ("__pycache__/test_cached.py", ".git/test_hook.py",
                    "node_modules/test_dep.py", ".tox/py311/test_env.py",
                    "build/test_built.py"):
            self.write(rel)
        found = discovery.discover_test_paths(self.dir)
        self.assertEqual(found, ["tests/calc_test.py", "tests/test_calc.py"], found)

    def test_a_symlink_is_never_handed_to_a_caller_that_checks_containment(self):
        target = self.write("tests/test_real.py")
        link = self.dir / "tests" / "test_link.py"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        found = discovery.discover_test_paths(self.dir)
        self.assertNotIn("tests/test_link.py", found)

    def test_a_tree_with_no_tests_raises_instead_of_returning_an_empty_list(self):
        # The negative control the whole design turns on. An empty list would let
        # a caller record test_count 0 with returncode 0 -- a green verdict for a
        # suite that was never found.
        import shutil
        shutil.rmtree(self.dir / "tests")
        with self.assertRaises(FileNotFoundError) as ctx:
            discovery.discover_test_files(self.dir)
        self.assertIn("NO_TEST_FILES_UNDER_SOURCE_ROOT", str(ctx.exception))


class ProvenanceTests(_Tree):
    def test_a_stated_list_is_reported_as_stated(self):
        files, source = discovery.stated_or_discovered(self.dir, ["tests/test_calc.py"])
        self.assertEqual(source, "stated")
        self.assertEqual([p.name for p in files], ["test_calc.py"])

    def test_a_tree_supplied_list_says_the_tree_supplied_it(self):
        files, source = discovery.stated_or_discovered(self.dir, None)
        self.assertEqual(source, "discovered_under_source_root")
        self.assertEqual(len(files), 2)

    def test_an_empty_list_is_not_a_statement(self):
        # An empty list means the caller said nothing, not that there is nothing.
        _, source = discovery.stated_or_discovered(self.dir, [])
        self.assertEqual(source, "discovered_under_source_root")


class TheMeasurementAdapterReadsTheSharedRuleTests(_Tree):
    def test_there_is_exactly_one_copy_of_the_walk(self):
        src = (REPO_ROOT / "canonical/runtime/bound_capabilities"
               / "python_repository_acceptance_measurement_v1.py").read_text()
        self.assertIn("from canonical.runtime.bound_capabilities"
                      ".python_test_corpus_discovery_v1 import", src)
        # A second copy of the rule in the adapter would be a rule edited once.
        self.assertNotIn("_SKIP_DISCOVERY_DIRS = {", src)

    def test_the_measurement_still_discovers_and_still_refuses_an_empty_tree(self):
        from canonical.runtime import live_brain_route_admission_v1 as admission
        out = REPO_ROOT / "canonical/astra_runtime/tmp/test_corpus_discovery_out"
        out.mkdir(parents=True, exist_ok=True)
        goal = (f"Run the python tests in the python source root {self.dir} "
                f"writing the report to {out}/m.json")
        result = admission.solve({"task_id": "CORPUS_MEASURE", "goal": goal})
        self.assertEqual(result.get("compiled_capability_id"),
                         "python.repository.acceptance.measure.v1")
        self.assertIs(result.get("pass"), True,
                      str(result.get("failure_class") or result.get("reason"))[:300])
        spec = json.loads((out / "m.json").read_text())["measurement_spec"]
        self.assertEqual(spec["test_paths_source"], "discovered_under_source_root")
        self.assertEqual(sorted(spec["test_paths"]),
                         ["tests/calc_test.py", "tests/test_calc.py"])


class TheRepairLaneFallsBackToTheTreeTests(unittest.TestCase):
    """A stated test file still wins; an unstated one falls back to the tree.

    The template keeps declaring test_paths and test_argv, and it must:
    test_live_brain_route_admission_v1 pins BOTH directions of that binding --
    test_a_paths_key_binds_the_tests_the_sentence_names_not_the_report requires
    test_paths to bind to the file the sentence names, and
    test_test_argv_is_the_adapters_own_default_not_an_invented_command requires
    test_argv to be the adapter's own suite_argv. Dropping the keys from the
    template to satisfy an unnamed phrasing deleted the named one's binding and
    broke both. The fallback therefore belongs in the adapter, where an EMPTY
    list is what arrives, not in the template.
    """

    CID = "python.software.repair.loop.coupled.ast.v1"
    NAMED = ("Repair the python source file canonical/runtime/goal_compiler.py so that "
             "the test canonical/tests/test_goal_compiler.py passes, and write the "
             "report to canonical/astra_runtime/tmp/test_corpus_discovery_v1/rep.json.")

    def test_the_template_still_declares_both_keys(self):
        declared = {k for k, v in REGISTRY[self.CID]["action_template"]["args"].items()
                    if isinstance(v, str) and v.startswith("${") and k != "capability_id"}
        self.assertIn("test_paths", declared)
        self.assertIn("test_argv", declared)

    def test_a_stated_test_file_still_binds_and_still_selects_the_repair(self):
        # The path the pinned spec owns. If this regresses, the fallback has
        # replaced the statement instead of covering for its absence.
        from canonical.runtime import goal_compiler as gc, live_integrated_brain_v1 as lb
        entry = REGISTRY[self.CID]
        bound = gc._bind_inputs(self.NAMED, REPO_ROOT, entry)
        self.assertEqual(bound["test_paths"], ["canonical/tests/test_goal_compiler.py"])
        self.assertEqual(bound["test_argv"][0], sys.executable)
        compiled = lb.compile_against_live_registry(self.NAMED, str(REPO_ROOT))[2]
        # Which repair capability wins is the ranking's business and moves as the
        # registry grows; what this pins is that a repair capability is reached at
        # all, and that the one reached declares the two inputs the sentence fed
        # it. Asserting one specific id here would fail on the next registry
        # addition without anything being wrong.
        selected = compiled.get("selected_capability")
        self.assertTrue(str(selected).startswith("python.software.repair."), selected)
        self.assertIn("test_paths", REGISTRY[selected]["action_template"]["args"])

    def test_the_adapter_discovers_the_corpus_when_no_list_arrives(self):
        src = (REPO_ROOT / "canonical/runtime/bound_capabilities"
               / "python_coupled_software_repair_loop_v1.py").read_text()
        self.assertIn("discover_test_files", src)
        self.assertIn("NO_TEST_FILES_UNDER_SOURCE_ROOT", src)

    def test_the_discovery_it_falls_back_to_is_the_shared_one(self):
        src = (REPO_ROOT / "canonical/runtime/bound_capabilities"
               / "python_coupled_software_repair_loop_v1.py").read_text()
        self.assertIn("python_test_corpus_discovery_v1", src)


if __name__ == "__main__":
    unittest.main()
