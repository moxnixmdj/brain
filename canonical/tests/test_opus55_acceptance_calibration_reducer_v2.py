from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from canonical.runtime.opus55_acceptance_calibration_reducer_v2 import evaluate

ROOT=Path(__file__).resolve().parents[2]
def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class Tests(unittest.TestCase):
    def live(self):
        return [
            load("canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json"),
            load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
            load("canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json"),
        ]

    def test_live_effective_calibration_is_exactly_3_of_19(self):
        out=evaluate(*self.live())
        self.assertEqual(out["errors"],[])
        self.assertFalse(out["pass"])
        self.assertEqual(out["behavioral_pass_family_count"],19)
        self.assertEqual(out["acceptance_calibrated_family_count"],3)
        self.assertEqual(out["acceptance_pending_family_count"],16)
        self.assertEqual(set(out["acceptance_calibrated_families"]),{
            "EXACT_SYMBOLIC_COMPUTATION",
            "LONG_HORIZON_MEMORY_AND_CONTINUITY",
            "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
        })
        row=next(r for r in out["families"] if r["family"]=="TOOL_DISCOVERY_SELECTION_AND_LEARNING")
        self.assertEqual(row["proof_source"],"VERIFIED_FULL_PROTOCOL_STRONGER_WITNESS")
        self.assertEqual(row["effective_closure_mode"],"ABSOLUTE_DOMINANCE")
        self.assertEqual(row["effective_witness_id"],"TOOL_DISCOVERY_TERMINAL_CEILING_ABSOLUTE_DOMINANCE_20261002_V1")

    def test_without_transmutation_witness_reverts_to_2_of_19(self):
        e,p,r,t=self.live()
        t=copy.deepcopy(t); t["evidence"]=[]
        out=evaluate(e,p,r,t)
        self.assertEqual(out["acceptance_calibrated_family_count"],2)
        self.assertEqual(out["acceptance_pending_family_count"],17)
        self.assertNotIn("TOOL_DISCOVERY_SELECTION_AND_LEARNING",out["acceptance_calibrated_families"])

    def test_behavioral_pass_is_still_required(self):
        e,p,r,t=self.live()
        r=copy.deepcopy(r)
        r["family_verdict"]["passed_families"].remove("TOOL_DISCOVERY_SELECTION_AND_LEARNING")
        out=evaluate(e,p,r,t)
        self.assertEqual(out["acceptance_calibrated_family_count"],2)
        self.assertIn("TOOL_DISCOVERY_SELECTION_AND_LEARNING",out["behavioral_missing_families"])

    def test_malformed_transmutation_fails_closed(self):
        e,p,r,t=self.live()
        t=copy.deepcopy(t); t["evidence"]="not-a-list"
        out=evaluate(e,p,r,t)
        self.assertIn("TRANSMUTATION_FAIL_CLOSED",out["errors"])
        self.assertFalse(out["pass"])

if __name__=="__main__":
    unittest.main(verbosity=2)
