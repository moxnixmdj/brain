import unittest

from canonical.runtime.required_claim_sufficiency_adapter_v1 import (
    RequiredClaimAdapterError,
    classify_required_claims,
)

SCHEMA = "PROJECT_BRAIN_TYPED_REQUIRED_CLAIM_SET_V1"


def ev(eid, relation="SUPPORTS", confidence=1.0, strength=1.0, group="g1"):
    return {
        "evidence_id": eid,
        "relation": relation,
        "confidence": confidence,
        "strength": strength,
        "independence_group": group,
        "provenance": [{"source": "fixture", "ref": "fixture://" + eid}],
    }


def payload(claims, policy=None):
    out = {"schema": SCHEMA, "claims": claims}
    if policy is not None:
        out["policy"] = policy
    return out


class RequiredClaimSufficiencyAdapterTests(unittest.TestCase):
    def test_zero_evidence_required_claim_is_explicit_insufficient(self):
        out = classify_required_claims(payload([
            {"claim_id": "C1", "required": True, "evidence": []},
        ]))
        self.assertEqual(out["status"], "REQUIRED_CLAIMS_NOT_READY")
        self.assertEqual(out["output_claim_count"], 1)
        self.assertEqual(out["claim_omission_count"], 0)
        self.assertEqual(out["claims"][0]["state"], "INSUFFICIENT")
        self.assertEqual(out["claims"][0]["terminal_reason"],
                         "NO_ADMISSIBLE_ALTERNATIVE_MEETS_EVIDENCE_THRESHOLD")

    def test_supporting_evidence_closes_typed_claim(self):
        out = classify_required_claims(payload([
            {"claim_id": "C1", "required": True, "evidence": [ev("E1")]},
        ]))
        self.assertEqual(out["status"], "ALL_REQUIRED_CLAIMS_SUPPORTED")
        self.assertTrue(out["all_required_claims_supported"])
        self.assertEqual(out["claims"][0]["state"], "SUPPORTED")
        self.assertEqual(out["claims"][0]["kernel_status"], "DECIDED")

    def test_contradiction_only_is_insufficient_not_silent(self):
        out = classify_required_claims(payload([
            {
                "claim_id": "C1",
                "required": True,
                "evidence": [ev("E1", relation="CONTRADICTS")],
            },
        ]))
        self.assertEqual(out["claims"][0]["state"], "INSUFFICIENT")
        self.assertEqual(out["claim_omission_count"], 0)

    def test_balanced_support_and_contradiction_is_conflicted(self):
        out = classify_required_claims(payload([
            {
                "claim_id": "C1",
                "required": True,
                "evidence": [
                    ev("E1", "SUPPORTS", group="g1"),
                    ev("E2", "CONTRADICTS", group="g2"),
                ],
            },
        ]))
        self.assertEqual(out["claims"][0]["state"], "CONFLICTED")
        self.assertEqual(out["status"], "REQUIRED_CLAIMS_NOT_READY")

    def test_optional_claim_does_not_block_required_readiness(self):
        out = classify_required_claims(payload([
            {"claim_id": "REQ", "required": True, "evidence": [ev("E1")]},
            {"claim_id": "OPT", "required": False, "evidence": []},
        ]))
        self.assertEqual(out["status"], "ALL_REQUIRED_CLAIMS_SUPPORTED")
        self.assertEqual([x["state"] for x in out["claims"]],
                         ["SUPPORTED", "INSUFFICIENT"])

    def test_all_input_claims_are_preserved_in_order(self):
        out = classify_required_claims(payload([
            {"claim_id": "A", "evidence": []},
            {"claim_id": "B", "evidence": [ev("EB")]},
            {"claim_id": "C", "required": False, "evidence": []},
        ]))
        self.assertEqual([x["claim_id"] for x in out["claims"]], ["A", "B", "C"])
        self.assertEqual(out["input_claim_count"], 3)
        self.assertEqual(out["output_claim_count"], 3)
        self.assertEqual(out["claim_omission_count"], 0)

    def test_provenance_ledger_survives_adapter(self):
        evidence = ev("E1")
        out = classify_required_claims(payload([
            {"claim_id": "C1", "evidence": [evidence]},
        ]))
        self.assertEqual(out["claims"][0]["evidence_ledger"][0]["provenance"],
                         evidence["provenance"])

    def test_duplicate_claim_id_fails_closed(self):
        with self.assertRaisesRegex(RequiredClaimAdapterError, "DUPLICATE_CLAIM_ID"):
            classify_required_claims(payload([
                {"claim_id": "C1", "evidence": []},
                {"claim_id": "C1", "evidence": []},
            ]))

    def test_unknown_relation_fails_closed(self):
        bad = ev("E1")
        bad["relation"] = "MAYBE"
        with self.assertRaisesRegex(RequiredClaimAdapterError, "EVIDENCE_RELATION_INVALID"):
            classify_required_claims(payload([
                {"claim_id": "C1", "evidence": [bad]},
            ]))

    def test_unknown_semantic_field_fails_closed(self):
        with self.assertRaisesRegex(RequiredClaimAdapterError, "UNSUPPORTED_FIELD"):
            classify_required_claims(payload([
                {"claim_id": "C1", "evidence": [], "magic_entailment": True},
            ]))

    def test_custom_thresholds_are_delegated_to_verified_kernel(self):
        out = classify_required_claims(payload([
            {
                "claim_id": "C1",
                "evidence": [ev("E1", confidence=0.6, strength=1.0)],
            },
        ], policy={"minimum_support_ratio": 0.9}))
        # One supporting group has support ratio 1.0, so the ratio threshold passes.
        self.assertEqual(out["claims"][0]["state"], "SUPPORTED")

    def test_model_and_authority_nonclaims_are_explicit(self):
        out = classify_required_claims(payload([
            {"claim_id": "C1", "evidence": []},
        ]))
        self.assertEqual(out["model_dependency_count"], 0)
        self.assertEqual(out["semantic_entailment_status"],
                         "UPSTREAM_TYPED_RELATIONS_REQUIRED__NOT_INFERRED_HERE")
        self.assertEqual(out["general_evidence_sufficiency_status"], "NOT_CLAIMED")
        self.assertFalse(out["terminal_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main()
