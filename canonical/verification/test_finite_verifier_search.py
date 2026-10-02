import unittest

from canonical.runtime.finite_verifier_search import exhaustive_acceptance_search


class FiniteVerifierSearchTests(unittest.TestCase):
    def test_unique_candidate(self):
        r = exhaustive_acceptance_search(["a", "b", "c"], lambda x: x == "b")
        self.assertEqual(r.status, "UNIQUE_ACCEPTED_CANDIDATE")
        self.assertEqual(r.passing, ("b",))
        self.assertTrue(r.complete_over_declared_universe)

    def test_ambiguity_preserved(self):
        r = exhaustive_acceptance_search([1, 2, 3, 4], lambda x: x % 2 == 0)
        self.assertEqual(r.status, "MULTIPLE_ACCEPTED_CANDIDATES__AMBIGUITY_PRESERVED")
        self.assertEqual(r.passing, (2, 4))

    def test_no_candidate(self):
        r = exhaustive_acceptance_search([1, 2], lambda x: False)
        self.assertEqual(r.status, "NO_ACCEPTED_CANDIDATE_IN_DECLARED_UNIVERSE")
        self.assertEqual(r.passing, ())

    def test_bound_fail_closed(self):
        r = exhaustive_acceptance_search([1, 2], lambda x: True, max_candidates=1)
        self.assertEqual(r.status, "BOUND_EXCEEDED")
        self.assertFalse(r.complete_over_declared_universe)
        self.assertEqual(r.examined, 0)

    def test_non_boolean_verifier_fails_closed_by_exception(self):
        with self.assertRaises(TypeError):
            exhaustive_acceptance_search([1], lambda x: 1)

    def test_negative_bound_rejected(self):
        with self.assertRaises(ValueError):
            exhaustive_acceptance_search([], lambda x: True, max_candidates=-1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

# Independent PR verification trigger v2.
