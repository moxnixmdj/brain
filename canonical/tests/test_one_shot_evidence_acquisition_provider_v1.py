from __future__ import annotations

import unittest

from canonical.runtime import one_shot_evidence_acquisition_provider_v1 as p
from canonical.runtime import residual_witness_retrieval_compiler_v1 as retrieval


WAKE = "NEW_AUTHENTICATED_SENSE_DISCRIMINATOR_OBSERVATION_RECEIPT"


def contract():
    request = {
        "kind": "R2_STRUCTURED_POLICY_CHANGING_ACQUISITION",
        "blocker": "R2_PENDING_ACQUISITION:FINANCE_SEMANTIC_ADEQUACY_TAIL",
        "r2_cell_id": "FINANCE_SEMANTIC_ADEQUACY_TAIL",
        "source_request_sha256": "1" * 64,
        "source_r2_authority_sha256": "2" * 64,
        "required_action": "ACQUIRE_ONLY_MINIMUM_AUTHENTICATED_DISCRIMINATOR",
        "remaining_boundary": "UNBOUND_SEMANTIC_MANIFEST_OR_EVIDENCE",
        "wake_conditions": [WAKE],
        "required_property": (
            "OBSERVATION_OR_CERTIFICATE_MUST_SATISFY_AT_LEAST_ONE_BOUND_"
            "WAKE_CONDITION_AND_CHANGE_OR_CLOSE_THE_EXACT_R2_CELL"
        ),
        "proof_or_existing_receipt_precedes_new_reality": True,
        "broad_acquisition_forbidden_without_minimality_proof": True,
        "full_benchmark_default": False,
        "request_id": "minimum-info:r2:" + "3" * 64,
    }
    return {
        "schema": "PROJECT_BRAIN_PROOF_CARRYING_GAP_CONTRACT_V1",
        "gap_class": "PENDING_ACQUISITION_OR_EXPERIMENT",
        "minimum_information_contract": {
            "schema": "PROJECT_BRAIN_MINIMUM_POLICY_CHANGING_INFORMATION_CONTRACT_V1",
            "requests": [request],
            "request_count": 1,
            "structured_r2_request_count": 1,
            "digest": "4" * 64,
        },
    }


def verified(payload):
    evidence = payload["evidence"]
    if evidence.get("candidate_id") not in {"existing-good", "retrieved-good"}:
        return {"pass": False}
    return {
        "pass": True,
        "independently_verified": True,
        "verification_authority_mutated": False,
        "witness_id": "witness:" + evidence["candidate_id"],
        "independent_receipt_sha256": "a" * 64,
        "evidence_sha256": "b" * 64,
        "satisfied_wake_condition": WAKE,
        "closes_exact_obligation": True,
    }


def commit(_payload):
    return {
        "pass": True,
        "frontier_changed": True,
        "verification_authority_mutated": False,
        "new_frontier_digest": "c" * 64,
        "commit_receipt_sha256": "d" * 64,
    }


def providers(candidate_id):
    def backend(action):
        return {
            "backend_id": "TEST_BACKEND",
            "candidates": [{
                "candidate_id": candidate_id,
                "url": "https://example.invalid/evidence",
            }],
            "complete": False,
            "independently_complete": False,
        }
    return {surface: backend for surface in retrieval.SURFACES}


class OneShotEvidenceAcquisitionProviderV1Tests(unittest.TestCase):
    def test_existing_verified_receipt_precedes_new_reality(self):
        backend_called = []

        def forbidden_backend(action):
            backend_called.append(action)
            raise AssertionError("backend must not run after sufficient existing receipt")

        provider = p.make_provider(
            independent_verifier=verified,
            frontier_committer=commit,
            existing_receipt_lookup=lambda request: [{
                "candidate_id": "existing-good",
                "source_surface": "CANONICAL_BRAIN_RECEIPT",
            }],
            backend_providers={
                surface: forbidden_backend for surface in retrieval.SURFACES
            },
            discovery_delegated=True,
        )
        out = provider(contract())
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["existing_verified_receipt_reused"])
        self.assertFalse(out["acquisition_or_experiment_attempted"])
        self.assertFalse(out["new_reality_consumed"])
        self.assertEqual(backend_called, [])
        self.assertEqual(out["satisfied_wake_condition"], WAKE)

    def test_retrieved_candidate_never_self_verifies(self):
        commits = []

        def reject_all(_payload):
            return {"pass": False}

        provider = p.make_provider(
            independent_verifier=reject_all,
            frontier_committer=lambda payload: commits.append(payload),
            existing_receipt_lookup=lambda request: [],
            backend_providers=providers("retrieved-good"),
            discovery_delegated=True,
            max_backend_actions=2,
        )
        out = provider(contract())
        self.assertFalse(out["pass"])
        self.assertTrue(out["acquisition_or_experiment_attempted"])
        self.assertFalse(out["frontier_changed"])
        self.assertEqual(commits, [])
        self.assertIn("NO_VERIFIED_POLICY_CHANGING_WITNESS", out["status"])

    def test_verified_retrieved_candidate_commits_frontier(self):
        provider = p.make_provider(
            independent_verifier=verified,
            frontier_committer=commit,
            existing_receipt_lookup=lambda request: [],
            backend_providers=providers("retrieved-good"),
            discovery_delegated=True,
            max_backend_actions=2,
        )
        out = provider(contract())
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["existing_verified_receipt_reused"])
        self.assertTrue(out["acquisition_or_experiment_attempted"])
        self.assertTrue(out["new_reality_consumed"])
        self.assertTrue(out["frontier_changed"])
        self.assertEqual(out["new_frontier_digest"], "c" * 64)

    def test_no_discovery_delegation_does_not_search(self):
        calls = []

        def backend(action):
            calls.append(action)
            raise AssertionError("research must not run without delegated discovery")

        provider = p.make_provider(
            independent_verifier=verified,
            frontier_committer=commit,
            existing_receipt_lookup=lambda request: [],
            backend_providers={surface: backend for surface in retrieval.SURFACES},
            discovery_delegated=False,
        )
        out = provider(contract())
        self.assertFalse(out["pass"])
        self.assertFalse(out["acquisition_or_experiment_attempted"])
        self.assertTrue(out["existing_receipt_lookup_attempted"])
        self.assertEqual(calls, [])

    def test_bound_source_never_expands_to_global_retrieval(self):
        calls = []

        def backend(action):
            calls.append(action)
            raise AssertionError("bound source must not expand to global retrieval")

        provider = p.make_provider(
            independent_verifier=verified,
            frontier_committer=commit,
            existing_receipt_lookup=lambda request: [],
            backend_providers={surface: backend for surface in retrieval.SURFACES},
            discovery_delegated=True,
            source_scope={"kind": "BOUND_SOURCE", "source_id": "ONLY_THIS_SOURCE"},
        )
        out = provider(contract())
        self.assertFalse(out["pass"])
        self.assertFalse(out["acquisition_or_experiment_attempted"])
        self.assertEqual(calls, [])
        self.assertTrue(any(
            row.get("stage") == "BOUND_SOURCE_OBSERVATION_NOT_GLOBALLY_EXPANDED"
            for row in out["trace"]
        ))

    def test_wrong_wake_condition_is_rejected(self):
        def wrong(_payload):
            return {
                "pass": True,
                "independently_verified": True,
                "verification_authority_mutated": False,
                "witness_id": "wrong",
                "independent_receipt_sha256": "a" * 64,
                "evidence_sha256": "b" * 64,
                "satisfied_wake_condition": "SOME_OTHER_WAKE",
            }

        provider = p.make_provider(
            independent_verifier=wrong,
            frontier_committer=commit,
            existing_receipt_lookup=lambda request: [{
                "candidate_id": "existing-good",
                "source_surface": "CANONICAL_BRAIN_RECEIPT",
            }],
            backend_providers=providers("retrieved-good"),
            discovery_delegated=True,
        )
        with self.assertRaisesRegex(
            p.EvidenceAcquisitionProviderError,
            "DOES_NOT_SATISFY_BOUND_WAKE_CONDITION",
        ):
            provider(contract())

    def test_commit_without_real_frontier_change_is_rejected(self):
        def bad_commit(_payload):
            return {
                "pass": True,
                "frontier_changed": False,
                "verification_authority_mutated": False,
                "new_frontier_digest": "c" * 64,
                "commit_receipt_sha256": "d" * 64,
            }

        provider = p.make_provider(
            independent_verifier=verified,
            frontier_committer=bad_commit,
            existing_receipt_lookup=lambda request: [{
                "candidate_id": "existing-good",
                "source_surface": "CANONICAL_BRAIN_RECEIPT",
            }],
            backend_providers=providers("retrieved-good"),
            discovery_delegated=True,
        )
        with self.assertRaisesRegex(
            p.EvidenceAcquisitionProviderError,
            "DID_NOT_CHANGE_FRONTIER",
        ):
            provider(contract())

    def test_reuse_lookup_is_mandatory(self):
        with self.assertRaisesRegex(ValueError, "EXISTING_RECEIPT_LOOKUP"):
            p.make_provider(
                independent_verifier=verified,
                frontier_committer=commit,
                existing_receipt_lookup=None,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
