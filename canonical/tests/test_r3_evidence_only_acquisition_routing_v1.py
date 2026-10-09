from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import r3_improvement_queue_driver_v1 as driver
from canonical.runtime import one_shot_verified_closure_v1 as v1
from canonical.runtime import one_shot_reality_closure_v2 as v2


BLOCKER = driver.R3_EVIDENCE_ONLY_BLOCKER


def compiled_gap():
    return {
        "pass": True,
        "root1_positive_gap_established": True,
        "witness_id": "r3-root1-adapter-gap:" + "a" * 64,
        "witness": {
            "blocked_success_work_id": "blocked:w1",
            "observation_id": "observation:w1",
            "proof_capsule_sha256": "b" * 64,
            "replay_capsule_sha256": "c" * 64,
            "adapter_author_context_sha256": "d" * 64,
            "adapter_frontier_sha256": "e" * 64,
            "verification_authority_sha256": "f" * 64,
        },
        "repair_class_reduction": {
            "admissible_repair_classes": ["NEW_DISTINGUISHING_EVIDENCE"],
            "preferred_repair_order": ["NEW_DISTINGUISHING_EVIDENCE"],
            "must_acquire_new_distinguishing_evidence": True,
            "retained_proof_class": (
                "INSUFFICIENT_FOR_NONSELF_REFERENTIAL_VERIFICATION"
            ),
        },
    }


class R3EvidenceOnlyAcquisitionRoutingV1Tests(unittest.TestCase):
    def test_driver_compiles_redacted_content_addressed_request(self):
        request = driver._compile_r3_distinguishing_evidence_request(
            {"work_id": "handoff:w1"},
            compiled_gap(),
        )
        self.assertIsInstance(request, dict)
        self.assertEqual(request["schema"], driver.R3_EVIDENCE_REQUEST_SCHEMA)
        self.assertEqual(
            request["request_kind"],
            "R3_SUCCESS_VERIFICATION_DISTINGUISHING_EVIDENCE",
        )
        self.assertEqual(request["observation_id"], "observation:w1")
        self.assertEqual(request["proof_capsule_sha256"], "b" * 64)
        self.assertEqual(request["replay_capsule_sha256"], "c" * 64)
        self.assertFalse(request["full_benchmark_default"])
        self.assertTrue(
            request["broad_acquisition_forbidden_without_minimality_proof"]
        )
        self.assertFalse(request["verification_authority_mutation_allowed"])
        self.assertEqual(len(request["request_sha256"]), 64)

    def test_v1_classifies_structured_r3_request_as_pending_acquisition(self):
        request = driver._compile_r3_distinguishing_evidence_request(
            {"work_id": "handoff:w1"},
            compiled_gap(),
        )
        action = {
            "blockers": [{
                "work_id": "handoff:w1",
                "kind": driver.FRONTIER_EXPANSION_KIND,
                "blocker": BLOCKER,
                "evidence_acquisition_request": request,
            }]
        }
        blockers = v1._extract_blockers([action])
        residual = v1.classify_residual(
            blockers,
            pending=[{
                "work_id": "handoff:w1",
                "kind": driver.FRONTIER_EXPANSION_KIND,
            }],
        )
        self.assertEqual(residual["class"], "PENDING_ACQUISITION_OR_EXPERIMENT")
        self.assertFalse(residual["internally_solvable_gap_remaining"])
        self.assertTrue(residual["pending_acquisition_or_experiment_required"])
        self.assertEqual(residual["evidence_blockers"], [BLOCKER])
        self.assertEqual(residual["r3_acquisition_request_count"], 1)
        self.assertEqual(
            residual["r3_acquisition_requests"][0]["request_sha256"],
            request["request_sha256"],
        )

    def test_v2_preserves_r3_request_and_emits_zero_constructive_contracts(self):
        request = driver._compile_r3_distinguishing_evidence_request(
            {"work_id": "handoff:w1"},
            compiled_gap(),
        )
        closure = {
            "schema": v1.SCHEMA,
            "status": "OPEN__INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
            "pass": False,
            "initial_frontier_digest": "i0",
            "final_frontier_digest": "f0",
            "final_state_sha256": "s0",
            "residual": {
                "internal_blockers": [
                    "EXTERNALITY_NOT_PROVED__CONTINUE_INTERNAL_SEARCH_SYNTHESIS_OR_BYPASS"
                ],
                "evidence_blockers": [BLOCKER],
                "pending_acquisition_or_experiment_required": True,
                "internal_unsolved": True,
                "r3_acquisition_requests": [request],
            },
        }
        pending = [{
            "schema": v2.SEMANTIC_WORK_SCHEMA,
            "work_id": "handoff:w1",
            "work_digest": "1" * 64,
            "kind": driver.FRONTIER_EXPANSION_KIND,
            "status": "PENDING",
            "payload": {"observation_id": "observation:w1"},
        }]
        gap = v2.compile_gap_contract(closure, pending_work=pending)
        self.assertEqual(gap["gap_class"], "PENDING_ACQUISITION_OR_EXPERIMENT")
        self.assertEqual(gap["constructive_capability_contract_count"], 0)
        self.assertEqual(gap["basis"]["r3_acquisition_request_count"], 1)

        decision = v2.compile_decision_sufficient_contract(gap)
        kinds = {
            row["kind"]
            for row in decision["representation"]["policy_changing_requirements"]
        }
        self.assertIn("R3_STRUCTURED_DISTINGUISHING_EVIDENCE_REQUEST", kinds)
        self.assertNotIn("CONSTRUCTIVE_CONTRACT", kinds)

        minimum = v2.compile_minimum_information_contract(gap, decision)
        self.assertEqual(minimum["request_count"], 1)
        self.assertEqual(minimum["structured_r3_request_count"], 1)
        row = minimum["requests"][0]
        self.assertEqual(
            row["kind"],
            "R3_STRUCTURED_DISTINGUISHING_EVIDENCE_ACQUISITION",
        )
        self.assertEqual(row["r3_observation_id"], "observation:w1")
        self.assertEqual(row["source_request_sha256"], request["request_sha256"])
        self.assertFalse(row["full_benchmark_default"])

    def test_v2_evidence_provider_receives_exact_structured_r3_request(self):
        request = driver._compile_r3_distinguishing_evidence_request(
            {"work_id": "handoff:w1"},
            compiled_gap(),
        )
        first = {
            "schema": v1.SCHEMA,
            "status": "OPEN__INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
            "pass": False,
            "initial_frontier_digest": "i0",
            "final_frontier_digest": "f0",
            "final_state_sha256": "s0",
            "residual": {
                "internal_blockers": [
                    "EXTERNALITY_NOT_PROVED__CONTINUE_INTERNAL_SEARCH_SYNTHESIS_OR_BYPASS"
                ],
                "evidence_blockers": [BLOCKER],
                "pending_acquisition_or_experiment_required": True,
                "internal_unsolved": True,
                "r3_acquisition_requests": [request],
            },
        }
        second = {
            "schema": v1.SCHEMA,
            "status": "PASS",
            "pass": True,
            "fixed_point": True,
            "initial_frontier_digest": "i1",
            "final_frontier_digest": "f1",
            "final_state_sha256": "s1",
            "residual": {
                "internal_blockers": [],
                "evidence_blockers": [],
            },
        }
        seen = {}

        def provider(contract):
            seen.update(contract)
            return {
                "pass": True,
                "frontier_changed": True,
                "verification_authority_mutated": False,
                "receipt_sha256": "9" * 64,
                "acquisition_or_experiment_attempted": True,
                "evidence_trace_sha256": "8" * 64,
            }

        with patch.object(v2.v1, "run", side_effect=[first, second]):
            out = v2.run(
                repo_root=".",
                evidence_acquisition_provider=provider,
            )
        self.assertTrue(out["pass"], out)
        minimum = seen["minimum_information_contract"]
        self.assertEqual(minimum["structured_r3_request_count"], 1)
        row = minimum["requests"][0]
        self.assertEqual(row["r3_witness_id"], request["witness_id"])
        self.assertEqual(row["source_request_sha256"], request["request_sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
