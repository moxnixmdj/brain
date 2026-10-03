from __future__ import annotations
import unittest
from canonical.runtime.tool_discovery_proof_router_v2 import route, _sha, PARTITION_SCHEMA

POL={"independent_verified":True,"exact_byte_bound":True,"program_soundness_verified":True,"policy_version":"V8"}
IDS={"independent_verified":True,"identity_scope_complete":True,"scope_relation":"EXACT","common_brain_opus_authority":True}

def receipt(p):
    return {"independent_verified":True,"partition_version":"V2","minimum_reality_partition_verified":True,"partition_result_sha256":_sha(p)}

def base(**kw):
    x={"schema":PARTITION_SCHEMA,"identity_scope_complete":True,"recommended_safe_probe":None,"irreducible_routes":[]}
    x.update(kw)
    return x

class Tests(unittest.TestCase):
    def call(self,p,pol=None,ids=None,r=None):
        return route(policy_receipt=pol or POL,identity_scope_receipt=ids or IDS,partition_result=p,partition_receipt=r or receipt(p))

    def test_universal_region(self):
        p=base(status="UNIVERSAL_PROOF_ELIGIBLE__DECISION_OBSERVABILITY_CLOSED",minimum_reality_action="UNIVERSAL_PROOF",universal_proof_eligible=True,safe_progress_available=False,matched_comparator_required_now=False)
        out=self.call(p)
        self.assertEqual(out["status"],"UNIVERSAL_REGION__FORMAL_PROGRAM_PROOF_ONLY")
        self.assertFalse(out["matched_comparator_allowed_now"])

    def test_safe_region_precedes_matched(self):
        p=base(status="SAFE_PROGRESS_REQUIRED__PROBE_BEFORE_MATCHED_EVIDENCE",minimum_reality_action="SAFE_PROBE",universal_proof_eligible=False,safe_progress_available=True,matched_comparator_required_now=False,recommended_safe_probe={"tool_id":"T1","capability":"A"})
        out=self.call(p)
        self.assertEqual(out["status"],"SAFE_OBSERVATION_REQUIRED__MATCHED_EVIDENCE_FORBIDDEN_YET")
        self.assertEqual(out["recommended_safe_probe"],{"tool_id":"T1","capability":"A"})
        self.assertFalse(out["execution_authority"])

    def test_matched_only_after_safe_closure(self):
        p=base(status="MATCHED_COMPARATOR_REQUIRED__IRREDUCIBLE_OBSERVABILITY_BOUND",minimum_reality_action="MATCHED_COMPARATOR",universal_proof_eligible=False,safe_progress_available=False,matched_comparator_required_now=True,irreducible_routes=[{"tool_id":"T1","unsafe_unknown_capabilities":["A"]}])
        out=self.call(p)
        self.assertEqual(out["status"],"MATCHED_ONLY_RESIDUAL__SAFE_OBSERVATION_CLOSED")
        self.assertTrue(out["matched_comparator_allowed_now"])

    def test_v5_is_rejected(self):
        p=base(status="UNIVERSAL_PROOF_ELIGIBLE__DECISION_OBSERVABILITY_CLOSED",minimum_reality_action="UNIVERSAL_PROOF",universal_proof_eligible=True,safe_progress_available=False,matched_comparator_required_now=False)
        pol=dict(POL); pol["policy_version"]="V5"
        self.assertIn("POLICY_NOT_V6_OR_SUCCESSOR",self.call(p,pol=pol)["failures"])

    def test_self_certified_policy_is_rejected(self):
        p=base(status="UNIVERSAL_PROOF_ELIGIBLE__DECISION_OBSERVABILITY_CLOSED",minimum_reality_action="UNIVERSAL_PROOF",universal_proof_eligible=True,safe_progress_available=False,matched_comparator_required_now=False)
        pol=dict(POL); pol["exact_byte_bound"]=False
        self.assertEqual(self.call(p,pol=pol)["status"],"FAIL_CLOSED")

    def test_common_authority_is_required(self):
        p=base(status="UNIVERSAL_PROOF_ELIGIBLE__DECISION_OBSERVABILITY_CLOSED",minimum_reality_action="UNIVERSAL_PROOF",universal_proof_eligible=True,safe_progress_available=False,matched_comparator_required_now=False)
        ids=dict(IDS); ids["common_brain_opus_authority"]=False
        self.assertIn("COMMON_BRAIN_OPUS_AUTHORITY_NOT_VERIFIED",self.call(p,ids=ids)["failures"])

    def test_partition_receipt_binds_exact_result(self):
        p=base(status="UNIVERSAL_PROOF_ELIGIBLE__DECISION_OBSERVABILITY_CLOSED",minimum_reality_action="UNIVERSAL_PROOF",universal_proof_eligible=True,safe_progress_available=False,matched_comparator_required_now=False)
        r=receipt(p); r["partition_result_sha256"]="sha256:"+"0"*64
        self.assertIn("PARTITION_RECEIPT_RESULT_DIGEST_MISMATCH",self.call(p,r=r)["failures"])

    def test_exactly_one_region(self):
        p=base(status="SAFE_PROGRESS_REQUIRED__PROBE_BEFORE_MATCHED_EVIDENCE",minimum_reality_action="SAFE_PROBE",universal_proof_eligible=True,safe_progress_available=True,matched_comparator_required_now=False,recommended_safe_probe={"tool_id":"T1","capability":"A"})
        self.assertIn("PARTITION_NOT_EXACTLY_ONE_OF_THREE_REGIONS",self.call(p)["failures"])

    def test_safe_region_requires_probe_payload(self):
        p=base(status="SAFE_PROGRESS_REQUIRED__PROBE_BEFORE_MATCHED_EVIDENCE",minimum_reality_action="SAFE_PROBE",universal_proof_eligible=False,safe_progress_available=True,matched_comparator_required_now=False)
        self.assertIn("SAFE_REGION_WITHOUT_PROBE",self.call(p)["failures"])

    def test_matched_region_requires_irreducibility_witness(self):
        p=base(status="MATCHED_COMPARATOR_REQUIRED__IRREDUCIBLE_OBSERVABILITY_BOUND",minimum_reality_action="MATCHED_COMPARATOR",universal_proof_eligible=False,safe_progress_available=False,matched_comparator_required_now=True)
        self.assertIn("MATCHED_REGION_WITHOUT_IRREDUCIBILITY_WITNESS",self.call(p)["failures"])

    def test_zero_credit_all_routes(self):
        p=base(status="UNIVERSAL_PROOF_ELIGIBLE__DECISION_OBSERVABILITY_CLOSED",minimum_reality_action="UNIVERSAL_PROOF",universal_proof_eligible=True,safe_progress_available=False,matched_comparator_required_now=False)
        out=self.call(p)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
