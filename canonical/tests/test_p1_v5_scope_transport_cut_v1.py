from __future__ import annotations
import copy
import unittest
from canonical.runtime import p1_v5_scope_transport_cut_v1 as cut

class Tests(unittest.TestCase):
    def sources(self):
        return cut._load(cut.BINDING),cut._load(cut.QUARANTINE),cut._load(cut.V4),cut._load(cut.V5)

    def test_live_sources_compress_to_three_transport_atoms_without_clearance(self):
        out=cut.evaluate()
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertEqual(out["transport_atom_count"],3)
        self.assertEqual({x["surface"] for x in out["transport_atoms"]},cut.EXPECTED_SURFACES)
        self.assertFalse(out["can_clear_p1_scope_quarantine"])
        self.assertFalse(out["next_proof_cut"]["full_terminal_replay_authorized"])
        self.assertEqual(out["new_reality_units_consumed"],0)

    def test_missing_surface_fails_closed(self):
        b,q,v4,v5=self.sources(); b=copy.deepcopy(b)
        b["direct_surface_bindings"]=b["direct_surface_bindings"][:-1]
        out=cut._evaluate(b,q,v4,v5)
        self.assertEqual(out["status"],"FAIL_CLOSED__SOURCE_DRIFT")
        self.assertIn("DIRECT_SURFACE_SET_DRIFT",out["errors"])

    def test_spoofed_v5_scope_count_fails_closed(self):
        b,q,v4,v5=self.sources(); v5=copy.deepcopy(v5)
        v5["verified"]["explicit_scope_case_count"]=25
        out=cut._evaluate(b,q,v4,v5)
        self.assertEqual(out["status"],"FAIL_CLOSED__SOURCE_DRIFT")
        self.assertIn("V5_SCOPE_CASE_COUNT_DRIFT",out["errors"])

    def test_spoofed_v5_credit_or_authority_fails_closed(self):
        b,q,v4,v5=self.sources(); v5=copy.deepcopy(v5)
        v5["capability_credit_delta"]=1
        v5["promotion_authority"]=True
        out=cut._evaluate(b,q,v4,v5)
        self.assertEqual(out["status"],"FAIL_CLOSED__SOURCE_DRIFT")
        self.assertIn("V5_NONZERO_CREDIT:capability_credit_delta",out["errors"])
        self.assertIn("V5_UNEXPECTED_AUTHORITY",out["errors"])

    def test_v4_clearance_bit_cannot_be_reused_as_authority(self):
        b,q,v4,v5=self.sources(); v4=copy.deepcopy(v4)
        v4["result"]["can_clear_p1_scope_quarantine"]=True
        out=cut._evaluate(b,q,v4,v5)
        self.assertEqual(out["status"],"FAIL_CLOSED__SOURCE_DRIFT")
        self.assertIn("V4_UNEXPECTED_CLEARANCE",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
