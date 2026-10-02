from __future__ import annotations
import json,unittest
from pathlib import Path
from canonical.runtime.recovery_t0_t2_acceptance_ceiling_lifter_v1 import evaluate

ROOT=Path(__file__).resolve().parents[2]

def load(path):
    return json.loads((ROOT/path).read_text())

class RecoveryCeilingLifterTests(unittest.TestCase):
    def test_live_candidate_is_quarantined_fail_closed(self):
        out=evaluate(
            protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
            registry=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
            predicates=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
            binding=load("canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"),
            terminal=load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
            relation=load("canonical/governance/RECOVERY_T0_T2_ACCEPTANCE_SCOPE_RELATION_V1.json"),
        )
        self.assertFalse(out["pass"],out)
        self.assertIsNone(out["candidate_witness"])
        self.assertIn("P1_EXECUTED_TERMINAL_SCOPE_MISMATCH_QUARANTINE_ACTIVE",out["errors"])
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
