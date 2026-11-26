"""Guard the three-layer capability coverage measure.

The premise this pins: *"we have tremendous hidden capabilities under non-obvious names."* Those are
three separate claims -- reachable, sayable, routable -- and this repository has had the first and
assumed the second and third.

Measured 2026-11-24: 2,248 runtime modules, 581 reachable (26%), 1 registered as an askable
capability, and of 25 reachable mechanisms >= 50 KB only 54% of the vocabulary their authors used to
describe them can be acted on by the router.
"""
from __future__ import annotations

import pathlib
import unittest

from canonical.tools.capability_concept_coverage_v1 import coverage

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestThreeLayersAreNotTheSameThing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = coverage(REPO_ROOT)

    def test_reachable_is_not_askable(self):
        report = self.report
        self.assertGreater(report["reachable"], 400)
        self.assertLess(
            report["askable"], 50,
            "askable capability count rose unexpectedly; if the registry was widened on purpose, "
            "update this guard and the plan that cites it",
        )
        self.assertGreater(
            report["reachable"], report["askable"] * 20,
            "reachable and askable have converged; the two layers are no longer distinct",
        )

    def test_most_of_the_runtime_is_not_reachable(self):
        report = self.report
        self.assertLess(
            report["reachable"] / report["modules"], 0.40,
            "reachable share rose above 40%: the import closure grew, which is good news that "
            "invalidates the plan's central number -- re-measure rather than delete this guard",
        )

    def test_large_mechanisms_are_only_half_sayable(self):
        mechanisms = self.report["large_mechanisms"]
        self.assertGreaterEqual(mechanisms["count"], 10)
        self.assertLess(
            mechanisms["sayable_share_mean"], 0.80,
            "the mechanisms became sayable -- this is the L1 fix landing for them, and the plan "
            "should say so",
        )

    def test_known_mechanism_concepts_are_not_addressable(self):
        """These are words the code uses about itself and a request cannot use."""
        unusable = set(self.report["concepts_unusable"])
        for concept in ("computer", "derivation", "self-improvement"):
            self.assertIn(
                concept, unusable,
                f"'{concept}' is now in the router index. That is the fix this measurement was "
                "built to demand; re-measure before relaxing the guard.",
            )

    def test_a_module_with_no_docstring_is_reported_not_guessed(self):
        """"astra_runtime.py" is 359 KB with no first sentence; sayable_share must be None."""
        rows = {row["module"]: row for row in self.report["modules_detail"]}
        target = rows.get("canonical/runtime/astra_runtime.py")
        if target is not None:
            self.assertIsNone(target["sayable_share"])


if __name__ == "__main__":
    unittest.main()
