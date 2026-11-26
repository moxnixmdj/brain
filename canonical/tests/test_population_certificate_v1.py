"""The certificate must refuse theatre and admit censuses.

These tests exist because the first version of the plan this module replaces proposed
running a deterministic door twenty times and quoting a probability bound. That would
have been a confident, quantitative lie.
"""
from __future__ import annotations

import sys
import unittest

sys.path.insert(0, ".")

from canonical.runtime.population_certificate_v1 import (
    PopulationCertificateError,
    certify,
    corpus_needed_for,
)

GOALS = [f"distinct goal {i}" for i in range(21)]


class RefusesRepetitionTests(unittest.TestCase):
    def test_twenty_identical_passes_are_refused(self):
        with self.assertRaises(PopulationCertificateError) as ctx:
            certify(["pass"] * 20)
        self.assertIn("UNANIMOUS_FATES_REQUIRE_DISTINCT_GOAL_IDENTITIES", str(ctx.exception))

    def test_unanimous_with_fewer_goals_than_fates_is_refused(self):
        with self.assertRaises(PopulationCertificateError):
            certify(["fail"] * 17, goals=["only one goal"])

    def test_unanimous_over_distinct_goals_is_a_census(self):
        cert = certify(["fail"] * 17, goals=[f"g{i}" for i in range(17)])
        self.assertEqual(cert.verdict, "CERTIFIED_MINORITY")
        self.assertTrue(cert.decided)

    def test_all_pass_over_distinct_goals_is_certified(self):
        cert = certify(["pass"] * 21, goals=GOALS[:21])
        self.assertEqual(cert.verdict, "CERTIFIED_MAJORITY")
        self.assertGreater(cert.lower, 0.5)

    def test_stochastic_claim_requires_a_named_source(self):
        with self.assertRaises(PopulationCertificateError):
            certify(["pass"] * 10, stochastic=True)
        # 20, not 10: ten perfect trials give a lower bound of 0.432 and certify nothing.
        self.assertEqual(
            certify(["pass"] * 10, stochastic=True, source="mutation sampling").verdict,
            "UNDECIDED",
        )
        self.assertEqual(
            certify(["pass"] * 20, stochastic=True, source="mutation sampling").verdict,
            "CERTIFIED_MAJORITY",
        )


class CensusHonestyTests(unittest.TestCase):
    def test_three_of_twenty_one_does_not_certify_a_rate(self):
        """The measured corpus: 3 of 21. It must say UNDECIDED, not '14% pass rate'."""
        cert = certify(["pass"] * 3 + ["fail"] * 18, goals=GOALS)
        self.assertEqual(cert.verdict, "UNDECIDED")
        self.assertFalse(cert.decided)
        self.assertIn("Report the counts, not a percentage", cert.claim)

    def test_claim_always_states_the_counts(self):
        cert = certify(["pass"] * 3 + ["fail"] * 18, goals=GOALS)
        self.assertIn("3 of 21", cert.claim)

    def test_empty_population_is_an_error_not_a_zero_rate(self):
        with self.assertRaises(PopulationCertificateError):
            certify([])


class CorpusSizingTests(unittest.TestCase):
    def test_a_middling_rate_needs_a_large_corpus(self):
        self.assertGreater(corpus_needed_for(target_rate=0.65), 200)

    def test_unanimity_is_cheap_to_certify(self):
        self.assertLess(corpus_needed_for(target_rate=1.0), 30)

    def test_sizing_is_fast(self):
        import time

        started = time.perf_counter()
        for rate in (0.95, 0.8, 0.65, 0.55):
            corpus_needed_for(target_rate=rate)
        self.assertLess(time.perf_counter() - started, 10.0)


if __name__ == "__main__":
    unittest.main()
