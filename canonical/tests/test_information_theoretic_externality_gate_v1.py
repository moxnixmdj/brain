from __future__ import annotations

import unittest

from canonical.runtime import information_theoretic_externality_gate_v1 as gate


class InformationTheoreticExternalityGateV1Tests(unittest.TestCase):
    def test_no_certificate_never_becomes_external(self):
        out = gate.verify_certificate(None, pending=[{"work_id": "w1"}])
        self.assertFalse(out["pass"])
        self.assertFalse(out["irreducible_external_information_proved"])
        self.assertEqual(out["reason"], "PROOF_CARRYING_EXTERNALITY_CERTIFICATE_REQUIRED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
