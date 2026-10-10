from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch
import unittest

from canonical.runtime import professional_r1_v10_semantic_totality_candidate_v1 as v


class Tests(unittest.TestCase):
    def test_current_exact_r1_candidate_passes_without_r4_self_credit(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["positive_witness_verified"])
        self.assertTrue(out["positive_witness_nonvacuous"])
        self.assertTrue(out["claim_scoped_totality_proved"])
        self.assertTrue(out["cc_r1_reality_containment_proved"])
        self.assertTrue(out["cc_r2_mission_soundness_proved"])
        self.assertTrue(out["cc_r3_terminal_closure_proved"])
        self.assertFalse(out["r4_proof_realization_authority"])
        self.assertFalse(out["independent_verified"])
        self.assertFalse(out["semantic_leaf_property_truth_authority"])
        self.assertEqual(
            set(out["resolved_or_decision_null_r1_challenge_ids"]),
            v.EXPECTED_CHALLENGES,
        )

    def test_target_compiler_rejection_blocks_candidate(self):
        with patch.object(v.target,"certify",return_value={"pass":False}):
            out=v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R1_TARGET_SEMANTIC_COMPILER_REJECTED")

    def test_scope_incompleteness_blocks_candidate(self):
        real=v.claims.verify
        def altered(*args,**kwargs):
            out=deepcopy(real(*args,**kwargs))
            row=[r for r in out["rows"] if r["leaf_id"]==v.LEAF_ID][0]
            row["whole_leaf_scope_complete"]=False
            return out
        with patch.object(v.claims,"verify",side_effect=altered):
            out=v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R1_WHOLE_DOMAIN_OR_SCOPE_NOT_PROVED")

    def test_challenge_set_drift_blocks_candidate(self):
        real=v._load
        def altered(root,rel,expected):
            doc=deepcopy(dict(real(root,rel,expected)))
            if rel==v.CHALLENGE_PATH:
                doc["challenges"]=[
                    x for x in doc["challenges"]
                    if x.get("id")!="C02_AMBIGUOUS_SPEC_WINNER"
                ]
            return doc
        with patch.object(v,"_load",side_effect=altered):
            out=v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R1_CHALLENGE_SET_DRIFT")

    def test_binder_fail_closed_shape_is_load_bearing(self):
        bad={
            "pass":True,
            "unknown_or_mismatch_authorized":True,
            "required_totality_fields":list(v.binder.REQUIRED_TOTALITY_FIELDS),
        }
        with patch.object(v.binder,"prove_fail_closed_shape",return_value=bad):
            out=v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"SEMANTIC_ADMISSION_FAIL_CLOSED_SHAPE_NOT_PROVED")

    def test_arbitrary_prompt_source_completeness_and_unique_best_are_not_assumed(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["arbitrary_prompt_completeness_assumed"])
        self.assertFalse(out["source_extraction_completeness_assumed"])
        self.assertFalse(out["unique_best_plan_assumed"])

    def test_candidate_cannot_self_mint_terminal_or_property_authority(self):
        out=v.verify()
        for key in (
            "r4_proof_realization_authority","independent_verified",
            "semantic_leaf_property_truth_authority","quality_authority",
            "acceptance_authority","promotion_authority","terminal_authority",
        ):
            self.assertFalse(out[key],key)
        self.assertEqual(out["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
