"""Wave-6 families: coupled python repair, cluster 1 of the alive-mass plan.

ONE_SHOT_ALIVE_MASS_PLAN_20261017_V1.md measured alive-mass at 27 of 67 and
found 40 of the 44 unexercised capabilities fail for one reason: RC-1, no
family exists. Cluster 1 (python repair/acceptance) has the highest ratio of
capabilities-unblocked x bar-leverage over effort.

The property that makes these COUPLED families and not a re-labelling of
PYTHON_REPAIR_TEST_GUIDED is the negative control below: a patch that repairs
only one of the two defects must still fail. If that ever stops holding, the
family has quietly decayed into a single-edit test and no longer exercises the
coupled loop at all.
"""
from __future__ import annotations

import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from execution_guard import live_solver_families_v6 as v6  # noqa: E402


class CoupledBugConstruction(unittest.TestCase):
    def setUp(self) -> None:
        # Generators emit repo-relative paths into the goal sentence, so the
        # fixture has to live inside the tree -- the gitignored tmp dir, same
        # place the heartbeat puts its work.
        self.work = ROOT / "canonical/astra_runtime/tmp/fam6_unit"
        shutil.rmtree(self.work, ignore_errors=True)
        self.work.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.work, ignore_errors=True)

    def _run(self, source: str, tests: dict, cwd: Path, mod_name: str) -> dict[str, int]:
        # the tests import the module by name, so the filename must match
        for path, text in tests.items():
            (cwd / path.name).write_text(text, encoding="utf-8")
        (cwd / mod_name).write_text(source, encoding="utf-8")
        return {
            path.name: subprocess.run([sys.executable, "-B", path.name],
                                      cwd=str(cwd), capture_output=True).returncode
            for path in tests
        }

    def test_two_defects_are_injected(self):
        bug = v6.fresh_coupled_bug(random.Random(1), self.work, 0)
        self.assertEqual(bug.src.read_text(encoding="utf-8"), bug.source)

    def test_the_negative_control_fixing_one_defect_is_not_enough(self):
        """The coupled property. If this fails, the family is no longer coupled."""
        bug = v6.fresh_coupled_bug(random.Random(2), self.work, 0)
        one_fixed = bug.source.replace("a - b", "a + b")   # repair ONLY defect one
        self.assertNotEqual(one_fixed, bug.source)

        trial = self.work / "neg"
        trial.mkdir()
        codes = self._run(one_fixed, bug.tests, trial, bug.src.name)
        coupled = [name for name in codes if name.endswith("_coupled.py")]
        self.assertEqual(len(coupled), 1)
        self.assertNotEqual(codes[coupled[0]], 0,
                            "the coupled test passed after only one repair")

    def test_both_defects_fixed_satisfies_every_test(self):
        bug = v6.fresh_coupled_bug(random.Random(2), self.work, 1)
        both = (bug.source.replace("a - b", "a + b")
                          .replace("total - v", "total + v"))
        trial = self.work / "both"
        trial.mkdir()
        codes = self._run(both, bug.tests, trial, bug.src.name)
        self.assertEqual(set(codes.values()), {0}, codes)

    def test_test_files_exist_before_the_goal_is_compiled(self):
        """The front compiler binds test_paths only to files already on disk."""
        bug = v6.fresh_coupled_bug(random.Random(4), self.work, 0)
        self.assertTrue(bug.tests)
        for path in bug.tests:
            self.assertTrue(path.is_file(), path)


class FamilyContract(unittest.TestCase):
    def test_both_families_are_registered(self):
        self.assertEqual(
            set(v6.GENERATORS_V6),
            {"PYTHON_REPAIR_COUPLED_AST", "PYTHON_REPAIR_COUPLED_PROV"},
        )

    def test_goals_name_a_source_root_and_a_quoted_test_command(self):
        """The two things that made these compile at all:

        - coupled loops bind source_root to a DIRECTORY, so a file path yields
          `0_existing_directories_named`;
        - test_argv is shlex-split from a QUOTED value and IS the whole command,
          so an unquoted or script-less argv yields `value_not_parseable` or a
          baseline that trivially 'passes'.
        """
        for seed in (5, 6, 7):
            for name, gen in v6.GENERATORS_V6.items():
                with self.subTest(name=name, seed=seed):
                    work = ROOT / "canonical/astra_runtime/tmp/fam6_unit_contract"
                    shutil.rmtree(work, ignore_errors=True)
                    work.mkdir(parents=True, exist_ok=True)
                    case = gen(random.Random(seed), work, 0)
                    self.assertIn("source root", case.goal)
                    self.assertIn('test command "', case.goal)
                    self.assertTrue(case.artifacts)


if __name__ == "__main__":
    unittest.main()
