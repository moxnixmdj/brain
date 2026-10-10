import unittest
from unittest.mock import patch
from canonical.runtime import professional_r12_safe_meta_composition_v1 as s

class Tests(unittest.TestCase):
    def test_verified_positive_stays_positive(self):
        o=s.classify_v9_result({"final_step_outcome":"POSITIVE_CERTIFICATE","positive_certification_authorized":True,"material_totality_proved":True,"v9_executable_r12_totality_semantics_verified":True,"status":"ROUTE__P1_ORDINARY"})
        self.assertEqual(o["status"],"SAFE_POSITIVE_VERIFIED")
        self.assertTrue(o["positive_certification_authorized"])
        self.assertIsNone(o["blocking_diagnostic"])
    def test_positive_without_totality_is_demoted(self):
        o=s.classify_v9_result({"final_step_outcome":"POSITIVE_CERTIFICATE","positive_certification_authorized":True,"material_totality_proved":False,"v9_executable_r12_totality_semantics_verified":True,"status":"BAD"})
        self.assertEqual(o["status"],"SAFE_NONPOSITIVE_FAIL_CLOSED")
        self.assertFalse(o["positive_certification_authorized"])
    def test_reason_becomes_explicit_diagnostic(self):
        o=s.classify_v9_result({"status":"FAIL_CLOSED","reason":"MISSING_EVIDENCE"})
        self.assertEqual(o["blocking_diagnostic"]["value"],"MISSING_EVIDENCE")
    def test_abstain_status_is_explicit_diagnostic(self):
        o=s.classify_v9_result({"status":"ABSTAIN__P1_AUTHENTICATED_FINAL_DECISION","final_step_outcome":"ABSTAIN","positive_certification_authorized":False})
        self.assertEqual(o["status"],"SAFE_NONPOSITIVE_FAIL_CLOSED")
        self.assertFalse(o["positive_certification_authorized"])
        self.assertTrue(o["blocking_diagnostic"]["value"])
    def test_nonmapping_never_positive(self):
        o=s.classify_v9_result(None)
        self.assertFalse(o["positive_certification_authorized"])
        self.assertEqual(o["status"],"SAFE_NONPOSITIVE_FAIL_CLOSED")
    @patch.object(s.v9,"route")
    def test_wrapper_never_upgrades_v9_failure(self,r):
        r.return_value={"status":"FAIL_CLOSED","reason":"X","positive_certification_authorized":False}
        o=s.route({"x":1})
        self.assertFalse(o["positive_certification_authorized"])
        self.assertEqual(o["status"],"SAFE_NONPOSITIVE_FAIL_CLOSED")
    @patch.object(s.v9,"route")
    def test_wrapper_preserves_exact_verified_positive_only(self,r):
        r.return_value={"status":"ROUTE__P1_ORDINARY","final_step_outcome":"POSITIVE_CERTIFICATE","positive_certification_authorized":True,"material_totality_proved":True,"v9_executable_r12_totality_semantics_verified":True}
        o=s.route({"x":1})
        self.assertEqual(o["status"],"SAFE_POSITIVE_VERIFIED")
        self.assertTrue(o["positive_certification_authorized"])
        self.assertFalse(o["stronger_semantic_sufficiency_claim_proved"])
    @patch.object(s.v9,"route")
    def test_v9_exception_becomes_fail_closed_diagnostic(self,r):
        r.side_effect=RuntimeError("boom")
        o=s.route({"x":1})
        self.assertEqual(o["status"],"SAFE_NONPOSITIVE_FAIL_CLOSED")
        self.assertFalse(o["positive_certification_authorized"])
        self.assertEqual(o["blocking_diagnostic"]["value"],"V9_EXCEPTION:RuntimeError")
    def test_positive_control_abstraction_exhaustive(self):
        vals=(False,True)
        for final_is_positive in vals:
            for authorized in vals:
                for totality in vals:
                    for semantics in vals:
                        o=s.classify_v9_result({
                            "final_step_outcome":"POSITIVE_CERTIFICATE" if final_is_positive else "ABSTAIN",
                            "positive_certification_authorized":authorized,
                            "material_totality_proved":totality,
                            "v9_executable_r12_totality_semantics_verified":semantics,
                            "status":"CASE",
                        })
                        expected=final_is_positive and authorized and totality and semantics
                        self.assertEqual(o["status"]=="SAFE_POSITIVE_VERIFIED",expected)
                        if not expected:
                            self.assertFalse(o["positive_certification_authorized"])
                            self.assertIsNotNone(o["blocking_diagnostic"])

if __name__=="__main__": unittest.main(verbosity=2)
