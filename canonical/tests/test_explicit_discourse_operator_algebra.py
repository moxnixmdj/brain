import unittest

from canonical.runtime.explicit_discourse_operator_algebra import (
    resolve_former_latter,
    resolve_respectively,
    resolve_too_ellipsis,
    resolve_demonstrative_event,
)

class ExplicitDiscourseOperatorAlgebraTests(unittest.TestCase):
    def test_former(self):
        r=resolve_former_latter(["producer","verifier"],"former")
        self.assertEqual(r["status"],"RESOLVED")
        self.assertEqual(r["target_id"],"producer")

    def test_latter(self):
        r=resolve_former_latter(["producer","verifier"],"latter")
        self.assertEqual(r["target_id"],"verifier")

    def test_former_latter_bad_arity_fails(self):
        r=resolve_former_latter(["only"],"former")
        self.assertEqual(r["status"],"FAIL_CLOSED")

    def test_respectively(self):
        r=resolve_respectively(["producer","verifier"],["candidate.json","verdict.json"])
        self.assertEqual(r["status"],"RESOLVED")
        self.assertEqual(r["bindings"],[
            {"left_id":"producer","right_value":"candidate.json"},
            {"left_id":"verifier","right_value":"verdict.json"},
        ])

    def test_respectively_mismatch_fails(self):
        r=resolve_respectively(["a","b"],["x"])
        self.assertEqual(r["status"],"FAIL_CLOSED")

    def test_too_ellipsis_reuses_predicate_only(self):
        prior={"operator":"persist","subject_id":"primary","object_id":"lease","modality":"MUST"}
        r=resolve_too_ellipsis(prior,"replica",marker="too")
        self.assertEqual(r["status"],"RESOLVED")
        self.assertEqual(r["predicate"]["subject_id"],"replica")
        self.assertEqual(r["predicate"]["object_id"],"lease")
        self.assertEqual(r["predicate"]["operator"],"persist")

    def test_too_without_operator_fails(self):
        r=resolve_too_ellipsis({"subject_id":"primary"},"replica")
        self.assertEqual(r["status"],"FAIL_CLOSED")

    def test_demonstrative_event_unique(self):
        r=resolve_demonstrative_event(["recompute_manifest_hash"],"This validation")
        self.assertEqual(r["status"],"RESOLVED")
        self.assertEqual(r["target_event_id"],"recompute_manifest_hash")

    def test_demonstrative_event_ambiguous_fails(self):
        r=resolve_demonstrative_event(["a","b"],"this validation")
        self.assertEqual(r["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main()
