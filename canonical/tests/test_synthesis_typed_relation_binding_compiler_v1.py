import json
import unittest

from canonical.runtime.synthesis_typed_relation_binding_compiler_v1 import solve

SCHEMA = "PROJECT_BRAIN_SYNTHESIS_TYPED_RELATION_BINDING_INPUT_V1"


def e(eid, cid, relation="SUPPORTS", confidence=1.0, strength=1.0, group="g1"):
    return {
        "evidence_id": eid,
        "claim_id": cid,
        "relation": relation,
        "confidence": confidence,
        "strength": strength,
        "independence_group": group,
        "provenance": [{"source": "fixture", "ref": "fixture://" + eid}],
    }


def case(claims, evidence, policy=None):
    task = {"claims": claims, "evidence": evidence}
    if policy is not None:
        task["policy"] = policy
    return {"schema": SCHEMA, "task": task}


class TypedRelationBindingCompilerTests(unittest.TestCase):
    def test_zero_evidence_required_claim_becomes_explicit_insufficient_binding(self):
        out = solve(case([{"claim_id": "C1", "required": True}], []))
        self.assertEqual(out["status"], "FAIL_CLOSED_INSUFFICIENT_REQUIRED_SUPPORT")
        self.assertEqual(out["compiled_support_bindings"], [
            {"claim_id": "C1", "status": "INSUFFICIENT", "evidence_ids": []}
        ])
        self.assertEqual(out["guard_result"]["insufficient_required_claims"], ["C1"])

    def test_support_compiles_to_supported_and_guard_ready(self):
        out = solve(case(
            [{"claim_id": "C1", "required": True}],
            [e("E1", "C1")],
        ))
        self.assertEqual(out["status"], "READY_FOR_SYNTHESIS")
        self.assertEqual(out["compiled_support_bindings"][0]["status"], "SUPPORTED")
        self.assertEqual(out["guard_result"]["supported_claims"], ["C1"])

    def test_balanced_support_conflict_compiles_to_conflicted(self):
        out = solve(case(
            [{"claim_id": "C1", "required": True}],
            [e("E1", "C1", "SUPPORTS", group="g1"),
             e("E2", "C1", "CONTRADICTS", group="g2")],
        ))
        self.assertEqual(out["status"], "READY_FOR_SYNTHESIS")
        self.assertEqual(out["compiled_support_bindings"][0]["status"], "CONFLICTED")
        self.assertEqual(out["guard_result"]["uncertainty_claims"], ["C1"])

    def test_contradiction_only_does_not_become_supported(self):
        out = solve(case(
            [{"claim_id": "C1", "required": True}],
            [e("E1", "C1", "CONTRADICTS")],
        ))
        self.assertEqual(out["status"], "FAIL_CLOSED_INSUFFICIENT_REQUIRED_SUPPORT")
        self.assertEqual(out["compiled_support_bindings"][0]["status"], "INSUFFICIENT")

    def test_optional_insufficient_does_not_block_required_ready_claim(self):
        out = solve(case(
            [{"claim_id": "REQ", "required": True},
             {"claim_id": "OPT", "required": False}],
            [e("E1", "REQ")],
        ))
        self.assertEqual(out["status"], "READY_FOR_SYNTHESIS")
        self.assertEqual(
            [x["status"] for x in out["compiled_support_bindings"]],
            ["SUPPORTED", "INSUFFICIENT"],
        )

    def test_provenance_transport_is_reversible_canonical_json(self):
        out = solve(case(
            [{"claim_id": "C1", "required": True}],
            [e("E1", "C1")],
        ))
        encoded = out["guard_result"]["claim_to_provenance"]["C1"][0]
        self.assertEqual(
            json.loads(encoded),
            {"source": "fixture", "ref": "fixture://E1"},
        )

    def test_unknown_claim_reference_fails_closed(self):
        out = solve(case(
            [{"claim_id": "C1", "required": True}],
            [e("E1", "MISSING")],
        ))
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("EVIDENCE_CLAIM_REFERENCE_UNKNOWN", out["reason"])

    def test_duplicate_ids_fail_closed(self):
        out = solve(case(
            [{"claim_id": "C1", "required": True},
             {"claim_id": "C1", "required": False}],
            [],
        ))
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("DUPLICATE_CLAIM_ID", out["reason"])

    def test_unknown_relation_fails_closed(self):
        bad = e("E1", "C1")
        bad["relation"] = "MAYBE"
        out = solve(case([{"claim_id": "C1", "required": True}], [bad]))
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("EVIDENCE_RELATION_INVALID", out["reason"])

    def test_unknown_semantic_field_fails_closed(self):
        c = case([{"claim_id": "C1", "required": True}], [])
        c["task"]["claims"][0]["magic_entailment"] = True
        out = solve(c)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("UNSUPPORTED_FIELD", out["reason"])

    def test_policy_is_delegated_to_verified_kernel(self):
        out = solve(case(
            [{"claim_id": "C1", "required": True}],
            [e("E1", "C1", confidence=0.2)],
            {"minimum_support_ratio": 0.95},
        ))
        # support ratio is still 1.0 for pure support, so this remains supported.
        self.assertEqual(out["compiled_support_bindings"][0]["status"], "SUPPORTED")

    def test_nonclaims_are_explicit(self):
        out = solve(case([{"claim_id": "C1", "required": True}], []))
        self.assertEqual(
            out["semantic_entailment_status"],
            "UPSTREAM_TYPED_RELATIONS_REQUIRED__NOT_INFERRED",
        )
        self.assertEqual(out["factual_correctness_status"], "UNVERIFIED")
        self.assertEqual(out["source_quality_status"], "UNVERIFIED")
        self.assertEqual(out["audience_relevance_status"], "UNVERIFIED")
        self.assertEqual(out["model_dependency_count"], 0)
        self.assertFalse(out["terminal_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
