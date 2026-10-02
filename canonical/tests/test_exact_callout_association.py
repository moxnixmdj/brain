import unittest
from canonical.runtime.exact_callout_association import solve

class ExactAssociationTests(unittest.TestCase):
    def test_unique_singleton_domains(self):
        r=solve([
            {"id":"C1","candidate_targets":["F1"]},
            {"id":"C2","candidate_targets":["F2"]},
        ])
        self.assertEqual(r["status"],"UNIQUE")
        self.assertEqual(r["assignment"],{"C1":"F1","C2":"F2"})

    def test_ambiguous_is_not_ranked(self):
        r=solve([{"id":"C1","candidate_targets":["F1","F2"]}])
        self.assertEqual(r["status"],"AMBIGUOUS")
        self.assertEqual(r["next"],"ACQUIRE_DISCRIMINATING_SOURCE_EVIDENCE")

    def test_distinct_targets_can_disambiguate(self):
        r=solve([
            {"id":"C1","candidate_targets":["F1"]},
            {"id":"C2","candidate_targets":["F1","F2"]},
        ],distinct_targets=True)
        self.assertEqual(r["status"],"UNIQUE")
        self.assertEqual(r["assignment"]["C2"],"F2")

    def test_same_target_relation(self):
        r=solve([
            {"id":"A","candidate_targets":["F1"]},
            {"id":"B","candidate_targets":["F1","F2"]},
        ],same_target=[["A","B"]])
        self.assertEqual(r["status"],"UNIQUE")
        self.assertEqual(r["assignment"],{"A":"F1","B":"F1"})

    def test_different_target_relation(self):
        r=solve([
            {"id":"A","candidate_targets":["F1"]},
            {"id":"B","candidate_targets":["F1","F2"]},
        ],different_target=[["A","B"]])
        self.assertEqual(r["status"],"UNIQUE")
        self.assertEqual(r["assignment"]["B"],"F2")

    def test_inconsistent_evidence_fails_closed(self):
        r=solve([
            {"id":"A","candidate_targets":["F1"]},
            {"id":"B","candidate_targets":["F1"]},
        ],distinct_targets=True)
        self.assertEqual(r["status"],"FAIL_CLOSED")
        self.assertEqual(r["error"],"NO_CONSISTENT_ASSOCIATION")

    def test_duplicate_callout_id_fails_closed(self):
        r=solve([
            {"id":"A","candidate_targets":["F1"]},
            {"id":"A","candidate_targets":["F2"]},
        ])
        self.assertEqual(r["status"],"FAIL_CLOSED")

    def test_invalid_relation_reference_fails_closed(self):
        r=solve([{"id":"A","candidate_targets":["F1"]}],same_target=[["A","MISSING"]])
        self.assertEqual(r["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main()
