import unittest
from canonical.runtime.structured_failure_hypotheses import Event,generate_failure_hypotheses

class StructuredFailureHypothesesTests(unittest.TestCase):
    def test_first_violation_localized(self):
        es=[
          Event("a",0),
          Event("b",1,frozenset({"I1"})),
          Event("c",2,frozenset({"I1","I2"})),
        ]
        o=generate_failure_hypotheses(es)
        self.assertEqual(o["status"],"CANDIDATES")
        self.assertEqual(o["earliest_candidate_id"],"failure@b")
        self.assertEqual(o["candidates"][0]["first_new_invariant_violations"],["I1"])
        self.assertFalse(o["candidates"][0]["causal_supported"])
    def test_explicit_error_generates_candidate(self):
        o=generate_failure_hypotheses([Event("x",3,explicit_error="E_IO")])
        self.assertEqual(o["candidates"][0]["explicit_error"],"E_IO")
    def test_repeated_invariant_not_reintroduced(self):
        o=generate_failure_hypotheses([
          Event("a",1,frozenset({"I"})),
          Event("b",2,frozenset({"I"})),
        ])
        self.assertEqual(len(o["candidates"]),1)
    def test_no_failure_is_explicit(self):
        self.assertEqual(generate_failure_hypotheses([Event("a",0)])["status"],"NO_OBSERVABLE_FAILURE_LOCUS")
    def test_duplicate_ids_fail_closed(self):
        self.assertEqual(generate_failure_hypotheses([Event("x",0),Event("x",1)])["status"],"FAIL_CLOSED")
if __name__=="__main__": unittest.main()
