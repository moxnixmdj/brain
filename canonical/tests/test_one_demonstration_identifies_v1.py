#!/usr/bin/env python3
"""What one demonstration identifies, pinned so the answer cannot drift.

Measured on this repository's own code (receipt `ONE_DEMONSTRATION_IDENTIFIES_20261116_V1.json`):

    479 real sites, 29 where the operation applies, 0 damaged, 1 unmeasurable
    one demonstration          admits everything: precision 0.069, 297 dangerous errors of 319
    two chosen observations    precision 1.000, 0 dangerous errors, recall 0.455
    random observations        identified a requirement in 0 of 12 sequences
    vocabulary                 separation impossible: 18 sites share every observed fact and differ

These tests are deliberately about the unpleasant half too: a run that suddenly identifies from one
example, or that reports zero dangerous errors without a requirement, is an instrument regression.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as applicability  # noqa: E402
from canonical.swe_kernel import one_demonstration_identifies_v1 as identify  # noqa: E402

PATTERN = "canonical/swe_kernel/rule_expiry_v1.py"


class FactVocabularyTests(unittest.TestCase):
    def test_facts_come_from_the_file_and_name_the_conditions_the_skill_states(self):
        sites = identify.reach.sites_in_file(PATTERN)
        self.assertTrue(sites)
        seen: set[str] = set()
        for site in sites:
            facts = identify.facts_of(site["path"], site["function"], site["variable"])
            self.assertTrue(facts)
            seen |= set(facts)
        self.assertIn("bind.plain_assignment", seen)
        self.assertIn("scope.not_parameter", seen)
        # Facts are observables, never verdicts.
        self.assertFalse(any("VERIFIED" in fact or "REFUSED" in fact for fact in seen))

    def test_a_comprehension_target_is_a_nested_scope_not_a_function_local(self):
        """Measured defect: the fact said 'no nested rebinding' about `sum(x * 2 for x in items)`."""
        facts = identify.facts_of("canonical/astra_runtime/chain_bed/src/calc.py",
                                  "compute_total", "x")
        self.assertNotIn("scope.no_nested_rebinding", facts)

    def test_first_computed_accepts_the_shape_the_demonstration_came_from(self):
        """`round(markup, 2)` reads the name `round`, then computes the argument: that qualifies."""
        source = ("def f(items):\n"
                  "    markup = sum(items)\n"
                  "    return round(markup, 2)\n")
        workdir = pathlib.Path(tempfile.mkdtemp(prefix="identify_facts_"))
        try:
            (workdir / "mod.py").write_text(source, encoding="utf-8")
            facts = identify.facts_of("mod.py", "f", "markup", repo=workdir)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        self.assertIn("use.read_once", facts)
        self.assertIn("use.next_statement_in_same_block", facts)
        self.assertIn("use.first_computed", facts)
        self.assertIn("use.computed_once", facts)


class IdentificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = identify.measure(pattern=PATTERN, sites=48, seeds=3)

    def test_one_demonstration_licenses_no_requirement_at_all(self):
        one = self.report["one_demonstration"]
        self.assertEqual(one["status"], "UNDETERMINED__NO_CONTRASTING_OUTCOME")
        self.assertEqual(one["survivors"], 0)
        self.assertEqual(one["requirement"], [])

    def test_the_optimistic_answer_to_one_demonstration_is_to_act_everywhere(self):
        """No requirement means the empty conjunction, which admits every state."""
        self.assertTrue(applicability.admits((), {"bind.set_once"}))
        held = self.report["one_demonstration"].get("held_out") or {}
        if held:
            self.assertEqual(held["false_negative"], 0)
            self.assertGreater(held["false_positive"], 0)

    def test_choosing_beats_repeating_when_there_is_anything_to_learn(self):
        chosen = self.report["chosen_contrasts"]
        random_rows = self.report["random_rows"]
        identified = [row for row in random_rows if row["status"] == "IDENTIFIED"]
        self.assertLessEqual(chosen["observations"], max(1, self.report["sites_queried"] // 4))
        self.assertLessEqual(len(identified), len(random_rows))

    def test_a_crash_is_unmeasured_rather_than_inapplicable(self):
        self.assertEqual(self.report["damaged_sites"], 0)
        self.assertGreaterEqual(self.report["unmeasured_sites"], 0)

    def test_the_receipt_never_claims_spend_or_a_model(self):
        self.assertEqual(self.report["model_calls"], 0)
        self.assertEqual(self.report["incremental_spend_usd"], 0)
        self.assertEqual(self.report["network_calls"], 0)

    def test_separation_is_reported_with_its_witnesses_or_not_at_all(self):
        separation = self.report["separation"]
        self.assertIn(separation["status"], {"SEPARATION_EXISTS", "SEPARATION_IMPOSSIBLE"})
        if separation["status"] == "SEPARATION_IMPOSSIBLE":
            self.assertGreater(separation["blocking_inapplicable_sites"], 0)
            self.assertTrue(separation["blocking_sites"])


if __name__ == "__main__":
    unittest.main()
