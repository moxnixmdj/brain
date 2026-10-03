from __future__ import annotations
import unittest

from canonical.runtime import tool_discovery_owned_observability_closure_v1 as c


class Tests(unittest.TestCase):
    def test_candidate_closes_owned_registry_observability_only(self):
        out=c.evaluate()
        self.assertTrue(out["status"].startswith("PASS_CANDIDATE"),out)
        self.assertEqual(out["tool_count"],42)
        self.assertEqual(out["local_evidence_bound_count"],41)
        self.assertEqual(out["external_public_binding_count"],1)
        self.assertEqual(out["unbound_count"],0)
        self.assertTrue(out["all_invocable_identities_registry_gated"])
        self.assertTrue(out["all_registry_entries_have_nonempty_provides"])
        self.assertTrue(out["arbitrary_required_capability_membership_is_deterministically_decidable"])
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_positive_and_negative_membership_are_both_decidable_without_tool_execution(self):
        yes=c.safe_probe("auto.pypi.msgpack","structured.binary.encode")
        no=c.safe_probe("auto.pypi.msgpack","archive.tar_gz.create_from_manifest")
        self.assertTrue(yes["supported"])
        self.assertFalse(no["supported"])
        self.assertEqual(yes["registry_git_blob"],c.REGISTRY_BLOB)

    def test_unknown_identity_fails_closed(self):
        with self.assertRaisesRegex(c.ClosureError,"UNREGISTERED_TOOL_ID"):
            c.safe_probe("__outside_authority__","anything")

    def test_bm25_is_the_only_external_public_binding(self):
        out=c.evaluate()
        self.assertEqual(out["external_bindings"],[{
            "tool_id":"source.objective_relevance.rank.bm25",
            "public_repo":"moxnixmdj/verification-capsule-runner",
            "public_pr":143,
            "workflow_run_id":36678278264,
            "exact_producer_blob":"95d2b6bac6f6ffb5db97526407fcd22cbcc6c790",
            "independent_verifier_must_confirm_success":True,
        }])


if __name__=="__main__":
    unittest.main(verbosity=2)
