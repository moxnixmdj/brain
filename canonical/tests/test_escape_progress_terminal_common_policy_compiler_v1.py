from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path
import unittest

from canonical.runtime.escape_progress_shared_gap_audit_v3 import audit

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=json.loads((ROOT/"canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json").read_text())
BINDING=json.loads((ROOT/"canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V5.json").read_text())

def gap_a_row():
    return next(x for x in MANIFEST["rows"] if x["route_group"]=="GAP_A_ACQUISITION_TOTALITY")

def inputs(mode="UNIVERSAL"):
    row=gap_a_row()
    oid=row["obligation_id"]
    policy_id="policy:brain-owned:"+oid
    protocol={
        "family":oid,
        "proof_mode":"TARGET_FREE_SCOPE_COMPLETE",
        "status":"DEFINED_RESULT_OPEN",
        "common_policy_id":policy_id,
    }
    evidence={
        "id":"E:"+oid,
        "family":oid,
        "mode":mode,
        "verified":True,
        "independent":True,
        "contamination_clean":True,
        "binds_frozen_protocol":True,
        "scope_relation":"EXACT",
        "closes_entire_protocol":True,
        "safe":True,
        "result":{"all_admissible_inputs_proved":True,"formal_completeness":True},
    }
    policy_binding={
        "schema":"PROJECT_BRAIN_ESCAPE_PROGRESS_COMMON_POLICY_BINDING_V1",
        "obligation_id":oid,
        "common_policy_id":policy_id,
        "currently_available":True,
        "brain_owned":True,
        "resource_admissible":True,
        "independently_verified":True,
        "exact_byte_bound":True,
        "verification_receipt_path":"canonical/verification/test_common_policy_binding.json",
        "verification_receipt_git_blob_sha":"1"*40,
    }
    return row,protocol,evidence,policy_binding

class EscapeTerminalPolicyCompilerTests(unittest.TestCase):
    def compiler(self):
        spec=importlib.util.find_spec("canonical.runtime.escape_progress_terminal_common_policy_compiler_v1")
        self.assertIsNotNone(spec)
        return importlib.import_module("canonical.runtime.escape_progress_terminal_common_policy_compiler_v1")

    def test_universal_scope_complete_proof_compiles_to_v3_terminal_policy(self):
        compiler=self.compiler()
        row,protocol,evidence,policy=inputs()
        out=compiler.compile_candidate(row,protocol,evidence,policy)
        self.assertTrue(out["pass"],out)
        proof=out["row_proof"]
        self.assertEqual(proof["resolution_mode"],"TERMINAL_COMMON_POLICY")
        self.assertEqual(proof["common_policy_id"],policy["common_policy_id"])
        self.assertTrue(proof["authenticated_scope_complete_certificate"])
        self.assertTrue(proof["safe_over_entire_current_decision_region"])
        self.assertNotIn("finite_outcome_ids",proof)
        result=audit(MANIFEST,BINDING,{row["obligation_id"]:proof})
        r=next(x for x in result["rows"] if x["obligation_id"]==row["obligation_id"])
        self.assertTrue(r["closed"],r)

    def test_unverified_policy_binding_fails_closed(self):
        compiler=self.compiler()
        row,protocol,evidence,policy=inputs()
        policy["independently_verified"]=False
        out=compiler.compile_candidate(row,protocol,evidence,policy)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"POLICY_BINDING_NOT_INDEPENDENTLY_VERIFIED")

    def test_policy_identity_mismatch_fails_closed(self):
        compiler=self.compiler()
        row,protocol,evidence,policy=inputs()
        policy["common_policy_id"]="policy:other"
        out=compiler.compile_candidate(row,protocol,evidence,policy)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"COMMON_POLICY_ID_BINDING_MISMATCH")

    def test_unsafe_acceptance_evidence_fails_closed(self):
        compiler=self.compiler()
        row,protocol,evidence,policy=inputs()
        evidence["safe"]=False
        out=compiler.compile_candidate(row,protocol,evidence,policy)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"REGION_WIDE_SAFETY_PROOF_REQUIRED")

    def test_matched_comparator_is_not_target_free(self):
        compiler=self.compiler()
        row,protocol,evidence,policy=inputs("MATCHED_COMPARATOR")
        evidence["result"]={"noninferiority_pass":True}
        out=compiler.compile_candidate(row,protocol,evidence,policy)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"TARGET_FREE_SCOPE_COMPLETE_MODE_REQUIRED")

    def test_absolute_dominance_without_complete_scope_does_not_compile(self):
        compiler=self.compiler()
        row,protocol,evidence,policy=inputs("ABSOLUTE_DOMINANCE")
        evidence["result"]={"direction":"higher","brain_lower_bound":1.0,"theoretical_upper_bound":1.0}
        out=compiler.compile_candidate(row,protocol,evidence,policy)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"SCOPE_COMPLETE_ACCEPTANCE_NOT_PROVED")

    def test_absolute_dominance_with_universal_scope_completeness_compiles(self):
        compiler=self.compiler()
        row,protocol,evidence,policy=inputs("ABSOLUTE_DOMINANCE")
        evidence["scope_completeness"]={
            "verified":True,
            "independent":True,
            "basis":"UNIVERSAL_FORMAL_SCOPE_PROOF",
            "all_admissible_target_inputs_proved":True,
            "formal_completeness":True,
            "receipt":"canonical/verification/test_scope_complete.json",
        }
        evidence["result"]={"direction":"higher","brain_lower_bound":1.0,"theoretical_upper_bound":1.0}
        out=compiler.compile_candidate(row,protocol,evidence,policy)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["row_proof"]["certificate_mode"],"ABSOLUTE_DOMINANCE")

    def test_compiler_grants_no_execution_or_credit(self):
        compiler=self.compiler()
        row,protocol,evidence,policy=inputs()
        out=compiler.compile_candidate(row,protocol,evidence,policy)
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["acceptance_credit_delta"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["ownership_credit_delta"],0)
        self.assertEqual(out["terminal_credit_delta"],0)


    def test_unavailable_policy_fails_closed(self):
        compiler=self.compiler()
        row,protocol,evidence,policy=inputs()
        policy["currently_available"]=False
        out=compiler.compile_candidate(row,protocol,evidence,policy)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"COMMON_POLICY_CURRENT_AVAILABILITY_NOT_PROVED")

    def test_non_owned_policy_fails_closed(self):
        compiler=self.compiler()
        row,protocol,evidence,policy=inputs()
        policy["brain_owned"]=False
        out=compiler.compile_candidate(row,protocol,evidence,policy)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"COMMON_POLICY_BRAIN_OWNERSHIP_NOT_PROVED")

    def test_resource_inadmissible_policy_fails_closed(self):
        compiler=self.compiler()
        row,protocol,evidence,policy=inputs()
        policy["resource_admissible"]=False
        out=compiler.compile_candidate(row,protocol,evidence,policy)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"COMMON_POLICY_RESOURCE_ADMISSIBILITY_NOT_PROVED")

    def test_policy_binding_requires_exact_verification_receipt_blob(self):
        compiler=self.compiler()
        row,protocol,evidence,policy=inputs()
        policy["verification_receipt_git_blob_sha"]="not-a-git-blob"
        out=compiler.compile_candidate(row,protocol,evidence,policy)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"POLICY_BINDING_VERIFICATION_RECEIPT_BLOB_INVALID")

    def test_family_binding_mismatch_fails_closed(self):
        compiler=self.compiler()
        row,protocol,evidence,policy=inputs()
        evidence["family"]="OTHER"
        out=compiler.compile_candidate(row,protocol,evidence,policy)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"OBLIGATION_PROTOCOL_EVIDENCE_POLICY_BINDING_MISMATCH")

    def test_exhaustive_finite_scope_compiles(self):
        compiler=self.compiler()
        row,protocol,evidence,policy=inputs("EXHAUSTIVE_FINITE")
        evidence["result"]={"exhaustive":True,"all_cases_pass":True}
        out=compiler.compile_candidate(row,protocol,evidence,policy)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["row_proof"]["certificate_mode"],"EXHAUSTIVE_FINITE")

    def test_post_compile_tampering_is_rejected_by_v3_digest(self):
        compiler=self.compiler()
        row,protocol,evidence,policy=inputs()
        out=compiler.compile_candidate(row,protocol,evidence,policy)
        self.assertTrue(out["pass"],out)
        proof=dict(out["row_proof"])
        proof["resource_admissible"]=False
        result=audit(MANIFEST,BINDING,{row["obligation_id"]:proof})
        r=next(x for x in result["rows"] if x["obligation_id"]==row["obligation_id"])
        self.assertFalse(r["closed"])
        self.assertIn(
            f'{row["obligation_id"]}:COMMON_POLICY_RESOURCE_ADMISSIBILITY_NOT_PROVED',
            r["missing_predicates"],
        )
        self.assertIn(
            f'{row["obligation_id"]}:CONTENT_ADDRESS_PROOF_INVALID',
            r["missing_predicates"],
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
