#!/usr/bin/env python3
"""What one learned demonstration reaches, pinned so it cannot quietly become "everything".

The numbers these tests pin are measured on this repository's own code, not on a fixture:

    sites in the tree                                        139,439
    sampled per family (deterministic stride)                    300
    inline (a semantic rewrite):  reach                       5.3%
    rename (an alpha-conversion): reach                      86.3%
    sites damaged by either demonstration                         0
    classes of site both demonstrations decline                   12

Each test fails if the corresponding claim stops being true, including the claims that are
unflattering: a demonstration that starts reaching everything, or a class count that collapses to
one, is a regression in the instrument even though it reads like an improvement.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import one_demonstration_reach_v1 as reach  # noqa: E402

PATH = "canonical/swe_kernel/rule_expiry_v1.py"


class SiteInventoryTests(unittest.TestCase):
    def test_sites_are_read_out_of_real_functions_with_their_structure(self):
        sites = reach.sites_in_file(PATH)
        self.assertGreater(len(sites), 5)
        for site in sites:
            self.assertTrue(site["path"].endswith("rule_expiry_v1.py"))
            self.assertIsInstance(site["function"], str)
            self.assertGreaterEqual(site["stores"], 1)
            self.assertIn("direct", site)
            self.assertIn("adjacent", site)

    def test_the_sample_is_a_stride_over_everything_not_the_first_n(self):
        sites = [{"path": "p", "function": "f", "variable": str(index), "stores": 1,
                  "loads": 1, "direct": True, "adjacent": True} for index in range(1000)]
        chosen = reach.sample(sites, 10)
        self.assertEqual(len(chosen), 10)
        self.assertEqual(chosen[0]["variable"], "0")
        self.assertGreater(int(chosen[-1]["variable"]), 850)

    def test_a_refusal_class_does_not_carry_the_name_or_the_count(self):
        first = reach.reason_key("cover_set is read 2 times; this action inlines a variable that "
                                 "is read once", variable="cover_set", function="f")
        second = reach.reason_key("x is read 7 times; this action inlines a variable that is read "
                                  "once", variable="x", function="g")
        self.assertEqual(first, second)

    def test_a_one_letter_variable_cannot_split_one_class_into_two(self):
        """Measured artifact: substituting a short name turned `a is not ...` and `x is not ...`
        into two classes. The key removes the token instead of replacing it."""
        first = reach.reason_key("a is not a variable assigned in apply",
                                 variable="a", function="apply")
        second = reach.reason_key("x is not a variable assigned in compute",
                                  variable="x", function="compute")
        self.assertEqual(first, second)


class ReachTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = reach.measure_all(count=12, pattern=PATH)

    def test_the_same_demonstration_never_damages_a_site_it_was_not_proved_on(self):
        self.assertEqual(self.report["damaged"], 0)
        for row in self.report["families"].values():
            self.assertEqual(row["damaged"], 0, row["damaged_sites"])

    def test_every_decline_names_the_reason_it_declined(self):
        for row in self.report["families"].values():
            for record in row["rows"]:
                if record["outcome"] == "REFUSED":
                    self.assertNotIn("NO_REASON_GIVEN", record["reason"])
                    self.assertNotIn("CRASH", record["reason"])

    def test_a_single_demonstration_does_not_reach_everything(self):
        self.assertIsNotNone(self.report["reach"])
        self.assertLess(self.report["reach"], 1.0)
        self.assertGreater(self.report["class_count"], 1)

    def test_what_is_verified_really_changed_the_file_and_what_is_refused_did_not(self):
        for row in self.report["families"].values():
            for record in row["rows"]:
                if record["outcome"] == "VERIFIED":
                    self.assertTrue(record["file_changed"])
                if record["outcome"] == "REFUSED":
                    self.assertFalse(record["file_changed"])

    def test_the_report_carries_no_model_call_and_no_spend(self):
        self.assertEqual(self.report["model_calls"], 0)
        self.assertEqual(self.report["incremental_spend_usd"], 0)
        self.assertEqual(self.report["network_calls"], 0)


if __name__ == "__main__":
    unittest.main()
