import unittest

from canonical.runtime.certified_scope_fragment_v1 import parse_scope
from canonical.runtime.source_aligned_semantic_proof_v3 import (
    typed_context_sha256,
    verify_proof,
)
from canonical.runtime.proof_carrying_semantic_refinement_v3 import resolve_from_source_proof


class SourceAlignedSemanticProofV3Tests(unittest.TestCase):
    def _typed(self, value=True):
        ctx={
            "schema_id":"FINANCE_TYPED_CONTEXT_V1",
            "fields":{
                "exception_holds":{"type":"BOOL","value":value},
                "exposure":{"type":"DECIMAL_STRING","value":"125.50"},
            },
        }
        return ctx, typed_context_sha256(ctx)

    def test_exact_content_addressed_bool_can_certify_policy(self):
        ctx,digest=self._typed(True)
        claim={
            "claim_id":"typed",
            "kind":"TYPED_FIELD_VALUE",
            "schema_id":"FINANCE_TYPED_CONTEXT_V1",
            "field_name":"exception_holds",
            "field_type":"BOOL",
            "value":True,
        }
        checked=verify_proof(
            "Authoritative structured fact bundle.",
            source_id="s",
            claims=[claim],
            typed_context=ctx,
            expected_typed_context_sha256=digest,
        )
        self.assertEqual(checked["status"],"PROOF_CHECKED")
        atom=checked["proved_constraint_ids"][0]
        out=resolve_from_source_proof(
            "Authoritative structured fact bundle.",
            source_id="s",
            claims=[claim],
            typed_context=ctx,
            expected_typed_context_sha256=digest,
            decision_basis=[atom],
            policy_conditions={"exception_policy":{"op":"ATOM","id":atom}},
        )
        self.assertEqual(out["status"],"COMMON_POLICY_CERTIFIED")
        self.assertEqual(out["certified_common_policies"],["exception_policy"])

    def test_wrong_context_digest_fails_closed(self):
        ctx,_=self._typed(True)
        claim={
            "claim_id":"typed","kind":"TYPED_FIELD_VALUE",
            "schema_id":"FINANCE_TYPED_CONTEXT_V1","field_name":"exception_holds",
            "field_type":"BOOL","value":True,
        }
        out=verify_proof(
            "Authoritative structured fact bundle.",
            source_id="s",
            claims=[claim],
            typed_context=ctx,
            expected_typed_context_sha256="0"*64,
        )
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("TYPED_CONTEXT_CONTENT_ADDRESS_MISMATCH",out["errors"])

    def test_wrong_claimed_value_cannot_discharge_policy(self):
        ctx,digest=self._typed(True)
        wrong={
            "claim_id":"typed","kind":"TYPED_FIELD_VALUE",
            "schema_id":"FINANCE_TYPED_CONTEXT_V1","field_name":"exception_holds",
            "field_type":"BOOL","value":False,
        }
        checked=verify_proof(
            "Authoritative structured fact bundle.",
            source_id="s",
            claims=[wrong],
            typed_context=ctx,
            expected_typed_context_sha256=digest,
        )
        self.assertEqual(checked["status"],"PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(checked["proved_constraint_ids"],[])

    def test_declared_type_mismatch_is_rejected(self):
        ctx,digest=self._typed(True)
        bad={
            "claim_id":"typed","kind":"TYPED_FIELD_VALUE",
            "schema_id":"FINANCE_TYPED_CONTEXT_V1","field_name":"exception_holds",
            "field_type":"STRING","value":"true",
        }
        checked=verify_proof(
            "Authoritative structured fact bundle.",
            source_id="s",
            claims=[bad],
            typed_context=ctx,
            expected_typed_context_sha256=digest,
        )
        self.assertEqual(checked["status"],"PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(checked["rejected_claims"][0]["reason"],"TYPED_FIELD_DECLARED_TYPE_MISMATCH")

    def test_scope_plus_typed_fact_can_jointly_certify_policy(self):
        text="Apply the rule unless the exception holds."
        p=parse_scope(text,source="s")["parse"]
        scope_claim={
            "claim_id":"scope","kind":"SCOPE_RELATION",
            "scope_id":p["scope_id"],"relation":p["relation"],
            "operator_id":p["operator_id"],
            "left_role":p["left_role"],"left_span":p["left_span"],
            "right_role":p["right_role"],"right_span":p["right_span"],
        }
        ctx,digest=self._typed(True)
        typed_claim={
            "claim_id":"typed","kind":"TYPED_FIELD_VALUE",
            "schema_id":"FINANCE_TYPED_CONTEXT_V1","field_name":"exception_holds",
            "field_type":"BOOL","value":True,
        }
        checked=verify_proof(
            text,source_id="s",claims=[scope_claim,typed_claim],
            typed_context=ctx,expected_typed_context_sha256=digest,
        )
        self.assertEqual(checked["status"],"PROOF_CHECKED")
        self.assertEqual(len(checked["proved_constraint_ids"]),2)
        scope_atom,typed_atom=checked["proved_constraint_ids"]
        out=resolve_from_source_proof(
            text,source_id="s",claims=[scope_claim,typed_claim],
            typed_context=ctx,expected_typed_context_sha256=digest,
            decision_basis=[scope_atom,typed_atom],
            policy_conditions={
                "exception_branch":{
                    "op":"AND","args":[
                        {"op":"ATOM","id":scope_atom},
                        {"op":"ATOM","id":typed_atom},
                    ],
                }
            },
        )
        self.assertEqual(out["status"],"COMMON_POLICY_CERTIFIED")
        self.assertEqual(out["certified_common_policies"],["exception_branch"])


if __name__=="__main__":
    unittest.main()
