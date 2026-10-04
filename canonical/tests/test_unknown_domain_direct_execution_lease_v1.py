from __future__ import annotations
import copy
import unittest
from canonical.runtime import unknown_domain_direct_execution_lease_v1 as lease


def ready_state():
    return {
        "target_predicate": lease.TARGET,
        "authorized_leaves": list(lease.AUTHORIZED_LEAVES),
        "activation_git_blob_sha": lease.ACTIVATION_BLOB,
        "qualification_receipt_git_blob_sha": lease.QUALIFICATION_RECEIPT_BLOB,
        "production_precommit_git_blob_sha": lease.PRODUCTION_PRECOMMIT_BLOB,
        "exact_execution_subject": dict(lease.EXACT_SUBJECTS),
        "qualification_independent_pass": True,
        "activation_independent_pass": True,
        "exact_subject_blobs_rechecked": True,
        "production_cases_consumed": 0,
        "production_populations_generated": 0,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "incremental_spend_usd": 0,
        "production_beacon_generated": False,
        "candidate_mutated_after_qualification": False,
        "global_fresh_reality": False,
        "execution_started": False,
    }


class UnknownDomainExecutionLeaseV1Tests(unittest.TestCase):
    def test_digest_is_deterministic_and_nonce_free(self):
        a = lease.canonical_lease_payload()
        b = lease.canonical_lease_payload()
        self.assertEqual(lease.lease_digest_sha256(a), lease.lease_digest_sha256(b))
        self.assertNotIn("nonce", str(a).lower())
        self.assertNotIn("timestamp", str(a).lower())

    def test_exact_tuple_has_one_claim_ref(self):
        out = lease.verify_point_of_use_state(ready_state())
        self.assertTrue(out["ready_for_atomic_claim_only"], out)
        self.assertEqual(out["claim_ref"], lease.expected_claim_ref())
        self.assertTrue(out["claim_ref"].startswith("refs/heads/unknown-domain-direct-claims/"))
        self.assertFalse(out["case_generation_authority"])
        self.assertFalse(out["execution_authority"])

    def test_mutating_subject_changes_identity_and_fails_preflight(self):
        state = ready_state()
        state["exact_execution_subject"] = dict(state["exact_execution_subject"])
        state["exact_execution_subject"]["candidate_v2"] = "0" * 40
        out = lease.verify_point_of_use_state(state)
        self.assertFalse(out["ready_for_atomic_claim_only"])
        self.assertIn("EXACT_EXECUTION_SUBJECT_MISMATCH", out["reasons"])
        altered = lease.canonical_lease_payload()
        altered["exact_execution_subject"] = dict(altered["exact_execution_subject"])
        altered["exact_execution_subject"]["candidate_v2"] = "0" * 40
        self.assertNotEqual(lease.lease_digest_sha256(altered), lease.lease_digest_sha256())

    def test_transitive_generator_v1_is_load_bearing(self):
        self.assertEqual(
            lease.EXACT_SUBJECTS["generator_v1"],
            "f974a4594c78e74693c7ba5a19f131dfa481b937",
        )
        altered = lease.canonical_lease_payload()
        altered["exact_execution_subject"] = dict(altered["exact_execution_subject"])
        altered["exact_execution_subject"]["generator_v1"] = "0" * 40
        self.assertNotEqual(lease.lease_digest_sha256(altered), lease.lease_digest_sha256())

    def test_replay_or_prior_generation_fails_closed(self):
        for field, value in (
            ("production_cases_consumed", 1),
            ("production_populations_generated", 1),
            ("production_beacon_generated", True),
            ("execution_started", True),
        ):
            with self.subTest(field=field):
                state = ready_state()
                state[field] = value
                self.assertFalse(lease.verify_point_of_use_state(state)["ready_for_atomic_claim_only"])

    def test_resource_or_global_scope_escape_fails_closed(self):
        state = ready_state()
        state["persistent_learned_bytes"] = 1
        state["external_frontier_model_calls"] = 1
        state["incremental_spend_usd"] = 1
        state["global_fresh_reality"] = True
        out = lease.verify_point_of_use_state(state)
        self.assertFalse(out["ready_for_atomic_claim_only"])
        self.assertFalse(out["case_generation_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
