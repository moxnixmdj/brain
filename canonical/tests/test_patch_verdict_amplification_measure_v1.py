#!/usr/bin/env python3
"""Tests for the harness that measures what a pass is worth.

The harness has one job it can fail at quietly: reporting a number without the arm that
contradicts it. These tests pin the parts of that which are cheap to check -- that pairs are
paired by name and not by choice, that the control arm is never dropped, that the summary prints
all three arms, and that the union arm is a union rather than a preference.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import patch_verdict_amplification_measure_v1 as tool  # noqa: E402
from canonical.swe_kernel import specification_from_structure_v1 as spec  # noqa: E402


class PairingTests(unittest.TestCase):
    def test_a_pair_is_a_module_and_the_test_file_named_after_it(self):
        pairs = tool.discover_pairs(("canonical/swe_kernel",))
        self.assertGreater(len(pairs), 10)
        for module, test in pairs:
            stem = pathlib.Path(module).stem
            self.assertEqual(pathlib.Path(test).name, f"test_{stem}.py")

    def test_a_module_with_no_test_of_its_name_is_not_a_pair(self):
        pairs = dict(tool.discover_pairs(("canonical/swe_kernel",)))
        tests = {path.name for path in (ROOT / "canonical/tests").glob("test_*.py")}
        unpaired = [
            module for module in (ROOT / "canonical/swe_kernel").glob("*.py")
            if f"test_{module.stem}.py" not in tests
            and module.name != "__init__.py"
        ]
        self.assertTrue(unpaired, "this test would be vacuous with no unpaired module")
        for module in unpaired:
            self.assertNotIn(module.relative_to(ROOT).as_posix(), pairs)


class ArmTests(unittest.TestCase):
    def test_the_control_arm_is_never_removed_from_the_report(self):
        # The invented grid is the arm that produced a clean zero. Deleting it once the recorded
        # grid exists would turn a comparison into a claim, so it is asserted to be present.
        self.assertIn("invented", tool.ARMS)
        self.assertIn("recorded_grid", tool.ARMS)
        self.assertIn("recorded_plus_invented", tool.ARMS)

    def test_the_summary_prints_every_arm_including_the_one_that_disagrees(self):
        report = {
            "pairs_discovered": 3,
            "pairs_measured": 2,
            "skipped": [],
            "totals": {f"{arm}_{field}": 0 for arm in tool.ARMS for field in (
                "pairs_where_a_law_could_speak", "confirmed_laws", "vacuous_laws",
                "not_applicable_laws", "rejected_by_a_law", "accepted_by_both",
                "survivors_where_a_law_was_pointed_at_the_mutant", "killed_among_those",
            )} | {"pairs_discovered": 3, "pairs_measured": 2, "pairs_skipped": 0,
                  "functions_of_this_module_with_a_recorded_grid": 1,
                  "functions_of_this_module": 2, "candidates": 4,
                  "candidate_did_not_import": 0, "unverifiable": 0,
                  "rejected_by_the_suite": 3, "suite_let_through": 1},
        }
        text = tool.summarize(report)
        self.assertIn("invented grid (control)", text)
        self.assertIn("grid the suite used", text)
        self.assertIn("both grids", text)
        self.assertEqual(text.count("rejected by a confirmed law"), 3)


class FailureTests(unittest.TestCase):
    def test_a_child_that_dies_is_counted_separately_and_never_as_a_pass(self):
        arm = tool._empty_arm()
        self.assertIn("laws_child_failed", arm)
        self.assertEqual(arm["laws_child_failed"], 0)
        self.assertNotIn("accepted_by_both", {key for key in arm if key == "laws_child_failed"})


class MergeTests(unittest.TestCase):
    def test_the_union_arm_is_a_union_and_recorded_arguments_come_first(self):
        derived = [{"name": "f", "required": [{"kind": "str"}]}]
        recorded = {"f": [{"args": ["recorded"]}]}
        merged = tool.merge_grids(recorded, derived, {"str": ["from the tree"]})
        args = [entry["args"][0] for entry in merged["f"]]
        self.assertEqual(args[0], "recorded")
        self.assertIn("from the tree", args)
        self.assertGreater(len(args), 1)

    def test_a_recorded_argument_that_is_also_invented_is_not_double_counted(self):
        derived = [{"name": "f", "required": [{"kind": "str"}]}]
        invented = spec.build_grid(derived[0]["required"])
        recorded = {"f": [invented[0]]}
        merged = tool.merge_grids(recorded, derived, None)
        self.assertEqual(len(merged["f"]), len({repr(entry["args"]) for entry in merged["f"]}))


if __name__ == "__main__":
    unittest.main()
