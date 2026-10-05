from __future__ import annotations
import unittest
from canonical.runtime.opus55_typed_coverage_dominance_bridge_v1 import compile_typed_sandwich

U="a"*40
def base():
    return {
        "universe_id":"OMEGA-V1",
        "universe_sha":U,
        "universe_atoms":["A","B","C","D"],
        "coverage_certificates":[{
            "id":"C1","universe_id":"OMEGA-V1","universe_sha":U,
            "source_sha":"b"*40,"cells":["A","B","C"],
            "independent_or_objective":True,"u_subset_domain_proved":True,
        }],
        "dominance_certificates":[{
            "id":"B1","universe_id":"OMEGA-V1","universe_sha":U,
            "source_sha":"c"*40,"cells":["A","B"],
            "independent_or_objective":True,"scope_complete":True,
            "b_subset_q_proved":True,
        }],
    }

class Tests(unittest.TestCase):
    def test_exact_residual(self):
        v=compile_typed_sandwich(base())
        self.assertEqual(v["status"],"OPEN")
        self.assertEqual(v["residual"],["C"])

    def test_closure(self):
        m=base(); m["dominance_certificates"][0]["cells"]=["A","B","C"]
        v=compile_typed_sandwich(m)
        self.assertEqual(v["status"],"CLOSED")
        self.assertTrue(v["behavioral_parity_certificate_sufficient"])

    def test_coverage_intersection_tightens(self):
        m=base()
        m["coverage_certificates"].append({
            "id":"C2","universe_id":"OMEGA-V1","universe_sha":U,
            "source_sha":"d"*40,"cells":["B","C","D"],
            "independent_or_objective":True,"u_subset_domain_proved":True,
        })
        v=compile_typed_sandwich(m)
        self.assertEqual(v["c_star"],["B","C"])
        self.assertEqual(v["residual"],["C"])

    def test_cross_universe_id_fails_closed(self):
        m=base(); m["dominance_certificates"][0]["universe_id"]="OTHER"
        v=compile_typed_sandwich(m)
        self.assertEqual(v["status"],"FAIL_CLOSED")
        self.assertIn("UNIVERSE_ID_MISMATCH",v["reason"])

    def test_same_id_different_universe_sha_fails_closed(self):
        m=base(); m["dominance_certificates"][0]["universe_sha"]="e"*40
        v=compile_typed_sandwich(m)
        self.assertEqual(v["status"],"FAIL_CLOSED")
        self.assertIn("UNIVERSE_SHA_MISMATCH",v["reason"])

    def test_missing_source_content_address_fails_closed(self):
        m=base(); m["coverage_certificates"][0]["source_sha"]="not-a-sha"
        v=compile_typed_sandwich(m)
        self.assertEqual(v["status"],"FAIL_CLOSED")
        self.assertIn("INVALID_CONTENT_ADDRESS",v["reason"])

    def test_unknown_region_fails_closed(self):
        m=base(); m["coverage_certificates"][0]["cells"].append("Z")
        v=compile_typed_sandwich(m)
        self.assertEqual(v["status"],"FAIL_CLOSED")
        self.assertIn("UNKNOWN_REGION",v["reason"])

    def test_scope_incomplete_dominance_fails_closed(self):
        m=base(); m["dominance_certificates"][0]["scope_complete"]=False
        v=compile_typed_sandwich(m)
        self.assertEqual(v["status"],"FAIL_CLOSED")
        self.assertIn("scope_complete_REQUIRED_TRUE",v["reason"])

    def test_no_coverage_fails_closed(self):
        m=base(); m["coverage_certificates"]=[]
        v=compile_typed_sandwich(m)
        self.assertEqual(v["status"],"FAIL_CLOSED")
        self.assertIn("NO_COVERAGE_CERTIFICATE",v["reason"])

if __name__=="__main__":
    unittest.main(verbosity=2)
