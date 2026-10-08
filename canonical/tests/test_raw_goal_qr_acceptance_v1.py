import unittest
from canonical.runtime import raw_goal_qr_acceptance_v1 as qr

GOAL = 'Generate a QR code image for the text "brain-qr-42" and save it to canonical/astra_runtime/tmp/R2_QR_TEST.png'

class T(unittest.TestCase):
    def test_preflight(self):
        out = qr.preflight(GOAL)
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["capability_id"], qr.QR_CAPABILITY_ID)
        self.assertEqual(out["payload"], "brain-qr-42")

if __name__ == "__main__":
    unittest.main(verbosity=2)
