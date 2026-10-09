from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.coverage_claim_scope_guard_v1 import compute_claim_id
from canonical.runtime import claim_instance_assurance_binder_v1 as b

MISSION="7ad5f82d8434966781bf97c725d482e10133fc7c"


def receipt():
    return {
        "schema": b.R7_RECEIPT_SCHEMA,
        "status": "PASS__REAL_PROFESSIONAL_CODE_EDIT_AB__OLD_FAIL_NEW_PASS__CLAIM_SCOPED_R7_CAUSAL_INSTANCE__ZERO_TERMINAL_CREDIT",
        "root_id": b.R7_ROOT,
        "claim_scope": {
            "kind": "EXACT_SINGLE_EDIT_PROFESSIONAL_CODE_INTERVENTION_INSTANCE",
            "artifact": "canonical/runtime/assurance_closure_compiler_v1.py",
            "intervention": "MAKE_SUPPORTED_DEFEATER_DOMINANCE_ORDER_INDEPENDENT",
            "claimed_effect": "THE_ORDER_REGRESSION_TEST_CHANGES_FROM_FAIL_ON_PREDECESSOR_TO_PASS_ON_REPAIRED_RUNTIME",
            "reusable_global_design_rule_claimed": False,
        },
        "r7_defeater_disposition": {
            "C28_PREDICTIVE_PRESCRIPTIVE_GAP": {
                "claim_scoped_state": "DISCHARGED_FOR_THIS_EXACT_INSTANCE",
                "reason": "actual executed A/B"
            },
            "C29_COMPOUND_EDIT_ATTRIBUTION": {
                "claim_scoped_state": "PROVEN_IRRELEVANT_TO_THIS_CLAIM_SCOPE",
                "reason": "single atomic treatment"
            },
            "C30_TREATMENT_VERSION_NONINVARIANCE": {
                "claim_scoped_state": "DISCHARGED_FOR_THIS_EXACT_INSTANCE",
                "reason": "content addressed versions"
            },
            "C31_EDIT_SEQUENCE_INTERACTION": {
                "claim_scoped_state": "PROVEN_IRRELEVANT_TO_THIS_CLAIM_SCOPE",
                "reason": "single transition"
            },
        },
        "conclusions": {
            "exact_claim_scoped_professional_edit_causality_proved": True,
            "r7_global_root_closed": False,
        },
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def make_claim(r):
    claim={
        "claim_kind": "PROPERTY_CERTIFICATE",
        "mission_blob_sha": MISSION,
        "scope_sha256": b.sha256_value(r["claim_scope"]),
        "target_predicate_sha256": b.sha256_value(r["claim_scope"]["claimed_effect"]),
        "semantics_sha256": b.sha256_value(r["r7_defeater_disposition"]),
        "epoch": "2026-10-09",
        "authority_id": "PROJECT_BRAIN_CURRENT_MISSION_OBJECTIVE",
        "terminal_credit_delta": 0,
    }
    claim["claim_id"]=compute_claim_id(claim)
    return claim


class ClaimInstanceAssuranceBinderV1Tests(unittest.TestCase):
    def materialize(self, root:Path, r:dict):
        path=root/"canonical/verification/r7.json"
        path.parent.mkdir(parents=True,exist_ok=True)
        raw=(json.dumps(r,indent=2)+"\n").encode()
        path.write_bytes(raw)
        return "canonical/verification/r7.json", b.git_blob_sha(raw)

    def bundle(self, root:Path, r:dict|None=None):
        r=receipt() if r is None else r
        path,sha=self.materialize(root,r)
        return {
            "schema": b.BUNDLE_SCHEMA,
            "claim": make_claim(r),
            "required_root_ids": [b.R7_ROOT],
            "evidence": [{
                "adapter_id": "PROFESSIONAL_QUALITY_R7_SINGLE_EDIT_CAUSAL_INSTANCE_V1",
                "path": path,
                "git_blob_sha": sha,
            }],
        }

    def test_exact_r7_claim_instance_closes_without_global_promotion(self):
        with tempfile.TemporaryDirectory() as td:
            out=b.evaluate(self.bundle(Path(td)),current_mission_blob_sha=MISSION,repo_root=td)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["domain_semantic_closure"])
        self.assertTrue(out["domain_execution_closure"])
        self.assertEqual(out["closure_scope"],"FROZEN_CLAIM_INSTANCE_ONLY")
        self.assertFalse(out["global_domain_closure"])
        self.assertFalse(out["global_mission_completion_derivable"])
        self.assertFalse(out["live_default"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)

    def test_stale_mission_binding_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            out=b.evaluate(self.bundle(Path(td)),current_mission_blob_sha="different",repo_root=td)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"CLAIM_SCOPE_INVALID")
        self.assertIn("MISSION_BINDING_STALE",out["claim_errors"])

    def test_tampered_evidence_bytes_fail_hash_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bundle=self.bundle(root)
            (root/bundle["evidence"][0]["path"]).write_text("{}\n")
            out=b.evaluate(bundle,current_mission_blob_sha=MISSION,repo_root=root)
        self.assertEqual(out["reason"],"EVIDENCE_GIT_BLOB_SHA_MISMATCH")

    def test_unregistered_adapter_cannot_self_certify(self):
        with tempfile.TemporaryDirectory() as td:
            bundle=self.bundle(Path(td))
            bundle["evidence"][0]["adapter_id"]="CALLER_SAYS_PASS"
            out=b.evaluate(bundle,current_mission_blob_sha=MISSION,repo_root=td)
        self.assertEqual(out["reason"],"EVIDENCE_ADAPTER_UNREGISTERED")

    def test_incomplete_defeater_disposition_is_rejected(self):
        r=receipt()
        del r["r7_defeater_disposition"]["C31_EDIT_SEQUENCE_INTERACTION"]
        with tempfile.TemporaryDirectory() as td:
            bundle=self.bundle(Path(td),r)
            out=b.evaluate(bundle,current_mission_blob_sha=MISSION,repo_root=td)
        self.assertEqual(out["reason"],"EVIDENCE_ADAPTER_REJECTED")
        self.assertEqual(out["adapter_reason"],"R7_DEFEATER_SET_INCOMPLETE_OR_EXTRA")

    def test_claim_scope_digest_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            bundle=self.bundle(Path(td))
            bundle["claim"]["scope_sha256"]="0"*64
            bundle["claim"]["claim_id"]=compute_claim_id(bundle["claim"])
            out=b.evaluate(bundle,current_mission_blob_sha=MISSION,repo_root=td)
        self.assertEqual(out["reason"],"CLAIM_SCOPE_NOT_BOUND_TO_EVIDENCE")

    def test_target_predicate_digest_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            bundle=self.bundle(Path(td))
            bundle["claim"]["target_predicate_sha256"]="1"*64
            bundle["claim"]["claim_id"]=compute_claim_id(bundle["claim"])
            out=b.evaluate(bundle,current_mission_blob_sha=MISSION,repo_root=td)
        self.assertEqual(out["reason"],"CLAIM_TARGET_NOT_BOUND_TO_EVIDENCE")

    def test_required_root_without_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            bundle=self.bundle(Path(td))
            bundle["required_root_ids"].append("R4_MEASUREMENT_CONSTRUCT")
            out=b.evaluate(bundle,current_mission_blob_sha=MISSION,repo_root=td)
        self.assertEqual(out["reason"],"REQUIRED_ROOT_EVIDENCE_MISSING")
        self.assertEqual(out["missing_root_ids"],["R4_MEASUREMENT_CONSTRUCT"])

    def test_global_open_ended_mission_claim_kind_is_forbidden(self):
        with tempfile.TemporaryDirectory() as td:
            bundle=self.bundle(Path(td))
            bundle["claim"]["claim_kind"]="GLOBAL_OPEN_ENDED_MISSION_COMPLETE"
            bundle["claim"]["claim_id"]=compute_claim_id(bundle["claim"])
            out=b.evaluate(bundle,current_mission_blob_sha=MISSION,repo_root=td)
        self.assertEqual(out["reason"],"CLAIM_SCOPE_INVALID")
        self.assertIn("CLAIM_KIND_NOT_ALLOWED",out["claim_errors"])


if __name__=="__main__":
    unittest.main()
