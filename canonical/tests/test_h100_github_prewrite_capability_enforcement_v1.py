import copy,unittest
from canonical.runtime import h100_github_prewrite_capability_enforcement_v1 as p

class H100GitHubPrewriteCapabilityTests(unittest.TestCase):
    def test_exact_plan_authorizes_one_effect(self):
        plan=p.desired_plan()
        out=p.authorize(plan)
        self.assertEqual(out["status"],"AUTHORIZED_EXACTLY_ONE_CREATE_EFFECT")
        self.assertEqual(out["audit_expectation"]["maximum_mutation_calls"],1)
        self.assertEqual(out["external_effects_executed_by_broker"],0)
        self.assertEqual(out["persistent_learned_bytes"],0)

    def test_each_authority_field_deviation_fails_closed(self):
        mutations={
            "repository":"other/repo",
            "branch":"other-branch",
            "path":"other/path.json",
            "operation":"DELETE_FILE",
            "content_sha256":"0"*64,
            "idempotency_key":"OTHER_KEY",
        }
        for field,bad in mutations.items():
            with self.subTest(field=field):
                plan=p.desired_plan(); plan[field]=bad
                with self.assertRaisesRegex(p.PrewriteCapabilityError,"PLAN_AUTHORITY_MISMATCH"):
                    p.authorize(plan)

    def test_extra_field_fails_closed(self):
        plan=p.desired_plan(); plan["url"]="https://example.com"
        with self.assertRaisesRegex(p.PrewriteCapabilityError,"PLAN_FIELDS_MISMATCH"):
            p.authorize(plan)

    def test_idempotency_classification(self):
        self.assertEqual(p.classify_existing(None)["status"],"TARGET_ABSENT__ONE_CREATE_ALLOWED")
        exact=p.desired_plan()["content_utf8"]
        self.assertEqual(p.classify_existing(exact)["status"],"TARGET_EXACT_MATCH__NOOP")
        self.assertEqual(p.classify_existing(exact+"x")["status"],"TARGET_PRESENT_MISMATCH__FAIL_CLOSED")
        self.assertEqual(p.classify_existing(exact)["mutation_calls_authorized"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
