from __future__ import annotations

import json
from pathlib import Path
import unittest

from canonical.runtime import professional_v8_r12_reuse_closure_v1 as v

ROOT=Path(__file__).resolve().parents[2]


def auth(**extra):
    return {
        "independent_verified":True,
        "exact_byte_bound":True,
        "conclusion":"success",
        **extra,
    }


def cover_problem():
    state_id="v8-run-1"
    return {
        "state_id":state_id,
        "worlds":[{"world_id":"w0"},{"world_id":"w1"}],
        "world_set_completeness_receipt":auth(
            policy_relevant_world_set_complete=True,
            state_id=state_id,
        ),
        "policies":[{
            "policy_id":"p-common",
            "adequate_world_ids":["w0","w1"],
            "cost_units":1,
            "adequacy_receipt":auth(
                policy_id="p-common",
                policy_adequate_on_every_listed_world=True,
                policy_safe_on_every_listed_world=True,
                hard_constraint_scope_complete=True,
                brain_owned=True,
                deployed_exact=True,
                resource_bound_proved=True,
            ),
        }],
        "discriminators":[],
    }


def problem():
    return {
        "semantic_property_claim_id":v.PROPERTY_CLAIM_ID,
        "semantic_scope_claim_id":v.SCOPE_CLAIM_ID,
        "semantic_obligation":v.OBLIGATION,
        "target_scope_semantics":v.TARGET_SCOPE_SEMANTICS,
        "v8_subject_id":v.V8_SUBJECT_ID,
        "v8_subject_sha256":v.V8_SUBJECT_SHA256,
        "real_exact_run":True,
        "content_addressed":True,
        "policy_cover_problem":cover_problem(),
    }


def verify_for(p):
    return {
        "pass":True,
        "independent_verified":True,
        "independent_verifier_id":"independent-test-verifier",
        "problem_sha256":v._canonical_sha256(p),
        "semantic_property_claim_id":v.PROPERTY_CLAIM_ID,
        "semantic_scope_claim_id":v.SCOPE_CLAIM_ID,
        "semantic_obligation":v.OBLIGATION,
        "v8_subject_id":v.V8_SUBJECT_ID,
        "v8_subject_sha256":v.V8_SUBJECT_SHA256,
        "policy_relevant_world_set_complete":True,
        "policy_cover_replay_pass":True,
        "positive_route_observed":True,
    }


def r12():
    return json.loads((ROOT/v.R12_RECON_PATH).read_text(encoding="utf-8"))


class Tests(unittest.TestCase):
    def test_exact_current_v8_reuses_and_reverifies_c1_to_c7(self):
        out=v.verify_preserved_c1_c7()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["preserved_c1_c7_v8_reverified"])
        self.assertEqual(out["preserved_clause_count"],7)
        self.assertFalse(out["v8_c8_nonvacuity_proved"])
        self.assertFalse(out["semantic_property_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_observable_policy_cover_can_close_only_v8_c8_and_cc_r3(self):
        p=problem()
        out=v.evaluate_v8_totality_cover(p,verify_for(p),r12_reconciliation=r12())
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["v8_c8_nonvacuity_proved"])
        self.assertTrue(out["v8_material_defeater_totality_proved"])
        self.assertTrue(out["cc_r3_terminal_closure_proved"])
        self.assertFalse(out["r4_proof_realization_authority"])
        self.assertFalse(out["semantic_property_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_incomplete_world_set_fails_before_cc_r3(self):
        p=problem()
        p["policy_cover_problem"]["world_set_completeness_receipt"]["policy_relevant_world_set_complete"]=False
        iv=verify_for(p)
        out=v.evaluate_v8_totality_cover(p,iv,r12_reconciliation=r12())
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"POLICY_COVER_TOTALITY_NOT_PROVED")
        self.assertFalse(out["cc_r3_terminal_closure_proved"])

    def test_old_or_wrong_subject_cannot_transport(self):
        p=problem()
        p["v8_subject_id"]="OLD-V7"
        out=v.evaluate_v8_totality_cover(p,verify_for(p),r12_reconciliation=r12())
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"V8_COVER_BINDING_MISMATCH:v8_subject_id")

    def test_positive_route_must_be_independently_observed(self):
        p=problem()
        iv=verify_for(p)
        iv["positive_route_observed"]=False
        out=v.evaluate_v8_totality_cover(p,iv,r12_reconciliation=r12())
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"V8_COVER_INDEPENDENT_VERIFY_MISMATCH:positive_route_observed")

    def test_problem_digest_must_match_exact_bytes(self):
        p=problem()
        iv=verify_for(p)
        p["policy_cover_problem"]["policies"][0]["cost_units"]=2
        out=v.evaluate_v8_totality_cover(p,iv,r12_reconciliation=r12())
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"V8_COVER_INDEPENDENT_VERIFY_MISMATCH:problem_sha256")


if __name__=="__main__":
    unittest.main(verbosity=2)
