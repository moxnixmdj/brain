from __future__ import annotations
import json, unittest
from pathlib import Path
from canonical.runtime import composition_component_proof_slicer_v1 as slicer

ROOT=Path(__file__).resolve().parents[2]
INPUT="canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V5.json"
EXPECTED="canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_CANDIDATE_V5.json"

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

class CompositionComponentProofSliceV5Tests(unittest.TestCase):
    def test_slicer_recomputes_exact_expected_component_states(self):
        actual=slicer.evaluate(load(INPUT))
        expected=load(EXPECTED)
        self.assertEqual(actual["schema"], expected["schema"])
        self.assertEqual(actual["claim_id"], expected["claim_id"])
        self.assertEqual(actual["interfaces"], expected["interfaces"])
        self.assertFalse(actual["all_used_component_interfaces_scoped_proved"])
        proved=[x["component_id"] for x in actual["interfaces"] if x["state"]=="SCOPED_PROVED"]
        self.assertEqual(proved,["memory","recovery","delegation"])

    def test_exactly_three_of_twelve_and_nine_open(self):
        actual=slicer.evaluate(load(INPUT))
        proved=[x for x in actual["interfaces"] if x["state"]=="SCOPED_PROVED"]
        opened=[x for x in actual["interfaces"] if x["state"]=="OPEN"]
        self.assertEqual(len(actual["interfaces"]),12)
        self.assertEqual(len(proved),3)
        self.assertEqual(len(opened),9)

    def test_recovery_receipt_does_not_cover_adjacent_components(self):
        actual=slicer.evaluate(load(INPUT))
        rows={x["component_id"]:x for x in actual["interfaces"]}
        self.assertEqual(rows["recovery"]["state"],"SCOPED_PROVED")
        self.assertEqual(rows["memory"]["supporting_receipt_ids"],["COMPOSITION_OWNED_FAMILY_BRIDGE_V2::LONG_HORIZON_MEMORY_AND_CONTINUITY::memory"])
        self.assertEqual(rows["browser/computer action"]["state"],"OPEN")
        self.assertEqual(rows["debugging"]["state"],"OPEN")
        self.assertEqual(rows["tool discovery"]["state"],"OPEN")
        self.assertEqual(rows["evidence synthesis"]["state"],"OPEN")
        self.assertEqual(rows["artifact production"]["state"],"OPEN")

    def test_parent_composition_remains_open(self):
        actual=slicer.evaluate(load(INPUT))
        self.assertEqual(actual["status"],"RESIDUAL_COMPONENT_INTERFACE_PROOFS_OPEN")
        self.assertFalse(actual["all_used_component_interfaces_scoped_proved"])
        self.assertEqual(actual["capability_credit_delta"],0)
        self.assertEqual(actual["family_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
