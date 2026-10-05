from __future__ import annotations
import copy
import unittest

from canonical.runtime import synthesis_bound_claim_guard_v2 as guard


def base_case():
    return {
        "task": {
            "claims": [
                {"claim_id": "C1", "required": True},
                {"claim_id": "C2", "required": False},
            ],
            "evidence": [
                {"evidence_id": "E1", "provenance": ["SRC-A"]},
                {"evidence_id": "E2", "provenance": ["SRC-B", "SRC-C"]},
            ],
            "support_bindings": [
                {"claim_id": "C1", "status": "SUPPORTED", "evidence_ids": ["E1"]},
                {"claim_id": "C2", "status": "CONFLICTED", "evidence_ids": ["E2"]},
            ],
        }
    }


class Tests(unittest.TestCase):
    def test_ready_preserves_evidence_provenance_and_conflict(self):
        out = guard.solve(base_case())
        self.assertEqual(out["status"], "READY_FOR_SYNTHESIS")
        self.assertEqual(out["insufficient_required_claims"], [])
        self.assertEqual(out["claim_to_evidence"]["C1"], ["E1"])
        self.assertEqual(out["claim_to_provenance"]["C2"], ["SRC-B", "SRC-C"])
        self.assertEqual(out["uncertainty_claims"], ["C2"])
        self.assertFalse(out["terminal_authority"])

    def test_missing_required_binding_fails_closed(self):
        case = base_case()
        case["task"]["support_bindings"] = [case["task"]["support_bindings"][1]]
        out = guard.solve(case)
        self.assertEqual(out["status"], "FAIL_CLOSED_INSUFFICIENT_REQUIRED_SUPPORT")
        self.assertEqual(out["insufficient_required_claims"], ["C1"])

    def test_unsupported_required_binding_fails_closed(self):
        case = base_case()
        case["task"]["support_bindings"][0] = {
            "claim_id": "C1",
            "status": "UNSUPPORTED",
            "evidence_ids": ["E1"],
        }
        out = guard.solve(case)
        self.assertEqual(out["status"], "FAIL_CLOSED_INSUFFICIENT_REQUIRED_SUPPORT")
        self.assertEqual(out["insufficient_required_claims"], ["C1"])

    def test_supported_claim_requires_evidence(self):
        case = base_case()
        case["task"]["support_bindings"][0]["evidence_ids"] = []
        out = guard.solve(case)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "POSITIVE_SUPPORT_REQUIRES_EVIDENCE")

    def test_unknown_evidence_reference_fails_closed(self):
        case = base_case()
        case["task"]["support_bindings"][0]["evidence_ids"] = ["MISSING"]
        out = guard.solve(case)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "SUPPORT_BINDING_EVIDENCE_INVALID")

    def test_empty_provenance_fails_closed(self):
        case = base_case()
        case["task"]["evidence"][0]["provenance"] = []
        out = guard.solve(case)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "EVIDENCE_ID_OR_PROVENANCE_INVALID")

    def test_duplicate_claim_id_fails_closed(self):
        case = base_case()
        case["task"]["claims"].append(copy.deepcopy(case["task"]["claims"][0]))
        out = guard.solve(case)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "CLAIM_ID_OR_REQUIRED_INVALID")

    def test_nonmapping_input_fails_closed(self):
        out = guard.solve(None)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "INPUT_INVALID")

    def test_whitespace_only_claim_id_fails_closed(self):
        case = base_case()
        case["task"]["claims"][0]["claim_id"] = "   "
        out = guard.solve(case)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "CLAIM_ID_OR_REQUIRED_INVALID")

    def test_whitespace_only_evidence_provenance_fails_closed(self):
        case = base_case()
        case["task"]["evidence"][0]["provenance"] = ["   "]
        out = guard.solve(case)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "EVIDENCE_ID_OR_PROVENANCE_INVALID")

    def test_whitespace_padded_evidence_id_fails_closed(self):
        case = base_case()
        case["task"]["evidence"][0]["evidence_id"] = " E1 "
        out = guard.solve(case)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "EVIDENCE_ID_OR_PROVENANCE_INVALID")

    def test_optional_without_binding_does_not_block_required_route(self):
        case = base_case()
        case["task"]["support_bindings"] = [case["task"]["support_bindings"][0]]
        out = guard.solve(case)
        self.assertEqual(out["status"], "READY_FOR_SYNTHESIS")
        self.assertEqual(out["supported_claims"], ["C1"])
        self.assertNotIn("C2", out["claim_to_evidence"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
