# PROJECT_BRAIN
"""Pins for the domain-coverage instrument behind the "what are all the problems?" inventory.

The instrument exists to find the holes a 43-act probe cannot reach, so the thing that must be
pinned is its *honesty*, not its size:

* an act is `BOUND` only when some capability's `provides` names it — a keyword that merely mentions
  it is `NAMED`, never `BOUND`.  This is exactly how `secret_scan` and `vulnerability_audit` were
  caught being credited to `bandit` at the front door while no capability claims them at all;
* an act nothing mentions is `ABSENT`, so the holes stay visible in the totals;
* every row lands in exactly one domain bucket, and the buckets sum to the rows.

Run: python -m pytest canonical/tests/test_hardcore_se_domain_coverage_is_measured_v1.py -q
"""

from __future__ import annotations

import json
import unittest

from execution_guard import hardcore_se_domain_coverage_v1 as C


class CoverageInstrumentTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.measured = C.measure()
        cls.by_act = {row["act"]: row for row in cls.measured["rows"]}

    def test_a_shipped_capability_is_bound_to_its_own_act(self):
        row = self.by_act["dynamic.fuzz"]
        self.assertEqual(row["state"], "BOUND")
        self.assertIn("python.dynamic.fuzz", row["owner"])

    def test_a_keyword_is_never_enough_to_count_as_bound(self):
        # The law, tested at the classifier rather than through whichever entry happens to hold
        # the word today: a capability that merely ROUTES by a word has not claimed the act.
        state, _ = C.classify(["security.secret"], [], ["leaked secrets", "secret", "security"])
        self.assertEqual(state, "NAMED")
        state, owner = C.classify(["leaked_secret"],
                                  ["python.supply_chain.leaked_secret.report"], [])
        self.assertEqual(state, "BOUND")
        self.assertIn("leaked_secret", owner)

    def test_the_acts_that_were_miscredited_now_have_real_owners(self):
        # before the supply-chain unit both of these were credited to bandit, which does neither
        self.assertEqual(self.by_act["security.secret_scan"]["state"], "BOUND")
        self.assertEqual(self.by_act["security.vulnerability_audit"]["state"], "BOUND")

    def test_an_act_nothing_mentions_stays_absent(self):
        self.assertEqual(self.by_act["dynamic.memory_profile"]["state"], "ABSENT")
        self.assertEqual(self.by_act["infra.iac"]["state"], "ABSENT")

    def test_every_row_lands_in_exactly_one_bucket(self):
        counts = self.measured["summary"]
        self.assertEqual(sum(bucket["total"] for bucket in counts.values()),
                         len(self.measured["rows"]))
        for bucket in counts.values():
            self.assertEqual(bucket["BOUND"] + bucket["NAMED"] + bucket["ABSENT"], bucket["total"])

    def test_the_registry_under_measurement_is_the_live_one(self):
        self.assertGreaterEqual(self.measured["capabilities_in_registry"], 158)

    def test_the_receipt_names_its_instrument(self):
        receipt = C.EVIDENCE
        if not receipt.is_file():
            self.skipTest("the receipt is written by a full run, not by this pin")
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(payload["instrument"],
                         "execution_guard/hardcore_se_domain_coverage_v1.py")
        self.assertEqual(len(payload["measured"]["rows"]), len(self.measured["rows"]))


if __name__ == "__main__":
    unittest.main()
