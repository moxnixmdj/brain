import unittest
from canonical.runtime.prewave_direct_proof_preflight import (
    p0_preflight,p1_preflight,p2_preflight,p3_preflight,run_all
)

class PrewaveDirectProofPreflightTests(unittest.TestCase):
    def test_p0(self):
        r=p0_preflight(); self.assertTrue(r["pass"],r)
    def test_p1(self):
        r=p1_preflight(); self.assertTrue(r["pass"],r); self.assertTrue(r["nonidentifiable_abstention_pass"],r)
    def test_p2(self):
        r=p2_preflight(); self.assertTrue(r["pass"],r)
    def test_p3(self):
        r=p3_preflight(); self.assertTrue(r["pass"],r)
    def test_all(self):
        r=run_all(); self.assertEqual(r["status"],"PASS",r)
        self.assertEqual(r["fresh_terminal_evidence_consumed"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
