from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
R2=ROOT/"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
ROOT65=ROOT/"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V65.json"
TERMINAL=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
REC=ROOT/"canonical/governance/R2_V77_REGCAP_MREL_NO_DESCRIPTOR_RECONCILIATION_20261010_V1.json"

def load(p): return json.loads(p.read_text(encoding="utf-8"))
def blob(p):
    raw=p.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r2=load(R2); cls.root=load(ROOT65); cls.rec=load(REC)

    def test_current_r2_is_v77_and_points_exact_root65(self):
        self.assertIn("__V77__",self.r2["status"])
        self.assertEqual(self.r2["scheduler_cut"]["path"],"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V65.json")
        self.assertEqual(self.r2["scheduler_cut"]["git_blob_sha"],blob(ROOT65))

    def test_root65_supersedes_exact_v64(self):
        self.assertEqual(self.root["schema"],"PROJECT_BRAIN_ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V65")
        self.assertEqual(self.root["supersedes"]["path"],"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V64.json")
        self.assertEqual(self.root["supersedes"]["git_blob_sha"],"88d62359c8e3cd4c4c6c775355e4370c63ea251b")

    def test_route_and_family_counts_unchanged(self):
        self.assertEqual(self.r2["direct_adequacy"]["current_route_count"],39)
        self.assertEqual(self.r2["direct_adequacy"]["bounded_family_count"],36)
        self.assertEqual(self.rec["semantic_delta"]["direct_route_count_before"],39)
        self.assertEqual(self.rec["semantic_delta"]["direct_route_count_after"],39)
        self.assertEqual(self.rec["semantic_delta"]["bounded_family_count_before"],36)
        self.assertEqual(self.rec["semantic_delta"]["bounded_family_count_after"],36)

    def test_one_finance_residual_remains(self):
        self.assertIn("ONE_PRIMARY_FINANCE_SEMANTIC_RESIDUAL_REMAINS",self.r2["status"])
        self.assertEqual(self.rec["semantic_delta"]["primary_internal_unsolved_count_before"],1)
        self.assertEqual(self.rec["semantic_delta"]["primary_internal_unsolved_count_after"],1)
        self.assertFalse(self.rec["semantic_delta"]["finance_tail_closed"])

    def test_new_positive_subregion_is_recorded(self):
        rows=self.r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]["verified_positive_subregions"]
        row=next(x for x in rows if isinstance(x,dict) and x.get("id")=="REGCAP_CCOB_CCYB_MREL_NO_DESCRIPTOR_PAIR_DOMAIN_TRUTH")
        self.assertFalse(row["descriptor_required"])
        self.assertFalse(row["global_semantic_identity_authority"])
        self.assertFalse(row["open_world_candidate_universe_complete"])
        self.assertFalse(row["terminal_authority"])

    def test_residual_is_narrowed_not_deleted(self):
        tail=self.r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        old=self.rec["residual_refinement"]["before"]
        new=self.rec["residual_refinement"]["after"]
        self.assertNotIn(old,tail["remaining_boundary"])
        self.assertIn(new,tail["remaining_boundary"])
        self.assertIn("WITH_ONLY_SHARED_LOSS_ABSORPTION_REMAIN_OPEN",tail["remaining_boundary"])

    def test_reuse_guidance_and_policy_flags_are_live(self):
        tail=self.r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        self.assertIn("REUSE_VERIFIED_REGCAP_MREL_NO_DESCRIPTOR_PAIR_DOMAIN_TRUTH",tail["required_action"])
        pol=self.r2["fixed_point_information_policy"]
        self.assertTrue(pol["regcap_mrel_no_descriptor_pair_domain_truth_bound"])
        self.assertFalse(pol["regcap_mrel_no_descriptor_pair_global_identity_authority"])

    def test_capability_receipts_are_exact_current_blobs(self):
        pairs=[
          ("canonical/runtime/regcap_mrel_no_descriptor_pair_v1.py","b66f45b7f9cc8aeeb68fc1ed4a962b6b4ac2474a"),
          ("canonical/verification/REGCAP_MREL_NO_DESCRIPTOR_PAIR_VERIFY_20261010_V1.json","e4a0229b96a6ae6f178f76af2d76cb7f088516ba"),
          ("canonical/runtime/domain_mapping_truth_certificate_v1.py","681954586f0864de8882e547619d2bbdd8ced001"),
          ("canonical/verification/DOMAIN_TRUTH_REGCAP_MREL_NO_DESCRIPTOR_VERIFY_20261010_V2.json","395cb3e7ac01ebb7891e6ce4c958733d5cb9ff4b"),
        ]
        for rel,expected in pairs:
            self.assertEqual(blob(ROOT/rel),expected,rel)

    def test_terminal_authority_is_unchanged(self):
        self.assertEqual(blob(TERMINAL),"8170b237ef6629d83987e9e1709b2c55c08daa16")
        self.assertEqual(self.rec["predecessor"]["terminal_blob_sha"],self.rec["successor"]["terminal_blob_sha"])
        self.assertEqual(self.rec["semantic_delta"]["terminal_credit_delta"],0)

    def test_global_nonclaims_remain_false(self):
        self.assertFalse(self.rec["semantic_delta"]["global_semantic_identity_closed"])
        self.assertFalse(self.rec["semantic_delta"]["open_world_ontology_mapping_closed"])
        self.assertEqual(self.rec["accounting"]["terminal_credit_delta"],0)

if __name__=="__main__": unittest.main(verbosity=2)
