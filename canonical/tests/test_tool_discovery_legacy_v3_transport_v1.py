from __future__ import annotations
import unittest
from canonical.runtime import tool_discovery_information_safe_proof_v2 as proof
from canonical.runtime import tool_discovery_legacy_v3_transport_v1 as tr

class Tests(unittest.TestCase):
    def test_semantic_quotient_exhaustion(self):
        out=tr.semantic_quotient_exhaustion()
        self.assertTrue(out["pass"],out.get("failures"))
        self.assertGreater(out["cases"],1000)
    def test_all_360_synthetic_frozen_generator_stages_transport(self):
        receipts=[]
        for ordinal in range(180):
            case=proof.generate_case(81277,ordinal)
            for stage in (1,2):
                public=proof.public_stage(case,stage,receipts)
                self.assertTrue(tr.compare_one(public)["equivalent"],(ordinal,stage))
    def test_version_epoch_transport(self):
        public={
          "required_capabilities":["a"],
          "tools":[{"tool_id":"x","cost":1.0,"available":True,"authorized":True}],
          "version_events":[{"kind":"TOOL_VERSION_CHANGED","tool_id":"x","new_epoch":3}],
          "prior_probe_receipts":[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"x","capability":"a","epoch":0,"supported":True},
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"x","capability":"a","epoch":3,"supported":False},
          ],
        }
        self.assertTrue(tr.compare_one(public)["equivalent"])
        self.assertEqual(tr.normalize_action(tr.legacy.next_action(public)),("ESCALATE",))
    def test_empty_required_is_explicitly_outside_legacy_transport_domain(self):
        with self.assertRaises(tr.TransportError):
            tr.compare_one({"required_capabilities":[],"tools":[]})
    def test_candidate_zero_credit(self):
        out=tr.prove_transport_candidate()
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__": unittest.main(verbosity=2)
