from __future__ import annotations
import unittest
from canonical.runtime.opus55_acceptance_calibration_reducer_v1 import evaluate

class AcceptanceCalibrationTests(unittest.TestCase):
    def fixture(self):
        envelope={"families":[{"id":f"F{i}"} for i in range(19)]}
        protocols={"protocols":[{"family":f"F{i}","proof_mode":"X","status":"PASS"} for i in range(19)]}
        reduction={"family_verdict":{"valid":True,"passed_families":[f"F{i}" for i in range(19)]}}
        return envelope,protocols,reduction

    def test_all_protocol_results_pass(self):
        out=evaluate(*self.fixture())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["acceptance_pending_family_count"],0)

    def test_behavioral_pass_does_not_override_open_protocol(self):
        args=list(self.fixture())
        args[1]["protocols"][3]["status"]="DEFINED_RESULT_OPEN"
        out=evaluate(*args)
        self.assertFalse(out["pass"])
        self.assertIn("F3",out["acceptance_pending_families"])

    def test_missing_behavioral_pass_fails_closed(self):
        args=list(self.fixture())
        args[2]["family_verdict"]["passed_families"].remove("F7")
        out=evaluate(*args)
        self.assertFalse(out["pass"])
        self.assertIn("F7",out["behavioral_missing_families"])

    def test_protocol_family_set_mismatch_fails_closed(self):
        args=list(self.fixture())
        args[1]["protocols"].pop()
        out=evaluate(*args)
        self.assertFalse(out["pass"])
        self.assertIn("PROTOCOL_FAMILY_SET_MISMATCH",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
