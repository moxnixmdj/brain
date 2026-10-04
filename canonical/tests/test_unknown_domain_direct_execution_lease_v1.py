from __future__ import annotations
import json
import unittest
from canonical.runtime import unknown_domain_direct_execution_lease_v1 as m

class UnknownDomainExecutionLeaseV1Tests(unittest.TestCase):
    def test_frozen_lease_digest_and_claim_ref(self):
        lease=m.build_execution_lease()
        out=m.verify_execution_lease(lease)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["lease_digest_sha256"],m.EXPECTED_DIGEST_SHA256)
        self.assertEqual(
            out["claim_ref"],
            "refs/heads/unknown-domain-direct-claims/"+m.EXPECTED_DIGEST_SHA256,
        )

    def test_canonical_bytes_ignore_mapping_insertion_order(self):
        lease=m.build_execution_lease()
        reverse={k:lease[k] for k in reversed(list(lease))}
        self.assertEqual(m.canonical_lease_bytes(lease),m.canonical_lease_bytes(reverse))
        self.assertEqual(m.lease_digest_sha256(lease),m.lease_digest_sha256(reverse))

    def test_any_subject_mutation_changes_digest_and_fails(self):
        lease=json.loads(json.dumps(m.build_execution_lease()))
        lease["bound_components"]["canonical/runtime/unknown_domain_direct_candidate_v2.py"]="0"*40
        self.assertNotEqual(m.lease_digest_sha256(lease),m.EXPECTED_DIGEST_SHA256)
        self.assertFalse(m.verify_execution_lease(lease)["pass"])

    def test_lease_contains_no_case_beacon_secret_or_dynamic_time(self):
        raw=m.canonical_lease_bytes(m.build_execution_lease()).decode()
        for forbidden in ["beacon","evaluator_secret","case_id","timestamp","nonce"]:
            self.assertNotIn(forbidden,raw.lower())

    def test_zero_resource_and_one_shot_budget_are_frozen(self):
        lease=m.build_execution_lease()
        self.assertEqual(lease["resource_boundary"],{
            "persistent_learned_bytes":0,
            "external_frontier_model_calls":0,
            "external_learned_capability_calls":0,
            "incremental_spend_usd":0,
        })
        self.assertEqual(lease["production_budget"]["production_populations_allowed"],1)
        self.assertEqual(lease["production_budget"]["production_cases_allowed"],27)
        self.assertFalse(lease["production_budget"]["replay_allowed"])
        self.assertFalse(lease["production_budget"]["replacement_allowed"])
        self.assertFalse(lease["production_budget"]["post_result_tuning_allowed"])

if __name__=="__main__":
    unittest.main(verbosity=2)
