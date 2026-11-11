from __future__ import annotations
import unittest
from canonical.runtime.tool_discovery_proof_router_v1 import route,_sha

POL={"independent_verified":True,"policy_version":"V8"}
IDS={"independent_verified":True,"identity_scope_complete":True,"scope_relation":"EXACT"}
LOW={"independent_verified":True,"lower_bound_verified":True}

def receipt(p):
    return {"independent_verified":True,"partition_result_sha256":_sha(p)}

def universal():
    return {
      "identity_scope_complete":True,
      "minimum_reality_action":"UNIVERSAL_PROOF",
      "universal_proof_eligible":True,
      "safe_progress_available":False,
      "matched_comparator_required_now":False,
    }

def safe():
    return {
      "identity_scope_complete":True,
      "minimum_reality_action":"SAFE_PROBE",
      "universal_proof_eligible":False,
      "safe_progress_available":True,
      "matched_comparator_required_now":False,
      "recommended_safe_probe":{"tool_id":"CHEAP","capability":"A"},
    }

def matched():
    return {
      "identity_scope_complete":True,
      "minimum_reality_action":"MATCHED_COMPARATOR",
      "universal_proof_eligible":False,
      "safe_progress_available":False,
      "matched_comparator_required_now":True,
      "irreducible_routes":[{"tool_id":"CHEAP","unsafe_unknown_capabilities":["A"]}],
    }

class Tests(unittest.TestCase):
    def _route(self,p,pol=POL,ids=IDS,low=LOW,rec=None):
        return route(
          policy_receipt=pol,
          identity_scope_receipt=ids,
          partition_result=p,
          partition_receipt=receipt(p) if rec is None else rec,
          lower_bound_receipt=low,
        )

    def test_universal_region_routes_without_reality(self):
        out=self._route(universal())
        self.assertEqual(out["status"],"UNIVERSAL_REGION__NO_SAFE_OR_MATCHED_REALITY_NEEDED_FOR_THIS_PARTITION")
        self.assertFalse(out["safe_probe_needed_for_this_partition"])
        self.assertFalse(out["matched_comparator_needed_for_this_partition"])

    def test_safe_probe_precedes_matched_evidence(self):
        out=self._route(safe())
        self.assertEqual(out["status"],"SAFE_PROBE_REQUIRED__MATCHED_EVIDENCE_FORBIDDEN_BEFORE_SAFE_OBSERVATION_CLOSURE")
        self.assertEqual(out["recommended_safe_probe"],{"tool_id":"CHEAP","capability":"A"})
        self.assertFalse(out["matched_comparator_needed_now"])

    def test_matched_region_requires_irreducible_witness(self):
        out=self._route(matched())
        self.assertEqual(out["status"],"MATCHED_ONLY_RESIDUAL__SAFE_OBSERVATION_EXHAUSTED")
        self.assertEqual(out["irreducible_route_count"],1)
        self.assertTrue(out["matched_comparator_needed_now"])

    def test_v6_and_v7_are_rejected_as_stale(self):
        for version in ("V6","V7"):
            bad={"independent_verified":True,"policy_version":version}
            out=self._route(universal(),pol=bad)
            self.assertEqual(out["status"],"FAIL_CLOSED")
            self.assertIn("POLICY_NOT_V8_OR_SUCCESSOR",out["failures"])

    def test_partition_flags_cannot_launder_safe_region_to_matched(self):
        p=safe()
        p["matched_comparator_required_now"]=True
        out=self._route(p)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("PARTITION_FLAGS_INCONSISTENT_WITH_ACTION",out["failures"])

    def test_safe_region_requires_concrete_probe(self):
        p=safe(); p["recommended_safe_probe"]=None
        out=self._route(p)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("SAFE_REGION_WITHOUT_PROBE",out["failures"])

    def test_matched_region_cannot_skip_irreducibility_witness(self):
        p=matched(); p["irreducible_routes"]=[]
        out=self._route(p)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("MATCHED_REGION_WITHOUT_IRREDUCIBLE_WITNESS",out["failures"])

    def test_partition_receipt_must_bind_exact_result(self):
        p=universal()
        rec=receipt(p); rec["partition_result_sha256"]="sha256:"+"0"*64
        out=self._route(p,rec=rec)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("PARTITION_RECEIPT_RESULT_DIGEST_MISMATCH",out["failures"])

    def test_lower_bound_receipt_is_required(self):
        bad=dict(LOW); bad["lower_bound_verified"]=False
        out=self._route(universal(),low=bad)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("LOWER_BOUND_THEOREM_NOT_VERIFIED",out["failures"])

    def test_zero_credit_all_three_routes(self):
        for p in (universal(),safe(),matched()):
            out=self._route(p)
            self.assertFalse(out["acceptance_proved"])
            self.assertEqual(out["new_reality_units_consumed"],0)
            self.assertEqual(out["incremental_spend_usd"],0)
            self.assertEqual(out["capability_credit_delta"],0)
            self.assertEqual(out["family_credit_delta"],0)
            self.assertFalse(out["execution_authority"])
            self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
