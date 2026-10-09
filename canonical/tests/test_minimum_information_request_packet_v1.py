import unittest

from canonical.runtime.minimum_information_request_packet_v1 import build


class Tests(unittest.TestCase):
    def test_proof_requests_are_preserved_without_gaining_authority(self):
        proof_request = {
            "schema": "PROJECT_BRAIN_DOMAIN_MAPPING_MINIMUM_PROOF_REQUEST_V1",
            "truth_kind": "DOMAIN_MAPPING_RELATION",
            "raw_span": "loss-absorbing cushion",
            "source_id": "doc:A",
            "scope_id": "finance:regulatory-capital:2026",
            "target_concept_id": "CCOB",
            "required_relation": "SEMANTIC_IDENTITY",
            "next_proof_targets": ["AUTHENTICATED_SHARED_CONCEPT_IDENTITY"],
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
        out = build(
            task_id="t1",
            goal="Resolve the term.",
            decision_payload={"context_id": "ctx"},
            predicate_id="domain-mapping-sha256:abc",
            reason="OPEN__SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED",
            acquisition_plan={
                "pass": True,
                "action": "RESEARCH_MINIMUM_AUTHENTICATED_FACT",
                "external_research_authorized": True,
            },
            proof_requests=[proof_request],
        )
        self.assertEqual(
            out["schema"],
            "PROJECT_BRAIN_MINIMUM_POLICY_CHANGING_INFORMATION_REQUEST_V1",
        )
        self.assertEqual(out["proof_requests"], [proof_request])
        self.assertTrue(out["external_research_authorized"])
        self.assertFalse(out["information_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_invalid_proof_request_shape_fails_closed(self):
        out = build(
            task_id="t1",
            goal="Resolve the term.",
            decision_payload={"context_id": "ctx"},
            predicate_id="p",
            reason="open",
            acquisition_plan={"pass": True, "action": "X"},
            proof_requests=["not-a-mapping"],
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
