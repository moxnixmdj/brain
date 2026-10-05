from __future__ import annotations
import copy, unittest
from canonical.runtime import p1_v6_direct_surface_scope_transport_v1 as rel

class Tests(unittest.TestCase):
 def test_live_transport_passes_without_terminal_credit(self):
  out=rel.evaluate()
  self.assertTrue(out["status"].startswith("PASS__"),out)
  self.assertTrue(out["all_three_scope_relations_proved"])
  self.assertEqual(len(out["surface_relations"]),3)
  self.assertTrue(all(out["transport_witnesses"].values()))
  self.assertFalse(out["v5_rescue_evidence_admissible"])
  self.assertFalse(out["terminal_surface_proof_complete"])
  self.assertFalse(out["can_clear_p1_scope_quarantine"])
  self.assertEqual(out["new_reality_units_consumed"],0)

 def test_transport_witnesses_cover_full_binding_mutation_classes(self):
  w=rel._transport_witnesses()
  required={
   "FULL_192_FROZEN_TYPED_CROSS_PRODUCT","DROP_PROVENANCE_OR_VISIBLE_RECEIPTS_FAILS_CLOSED",
   "DOWNSTREAM_OR_LATER_SYMPTOM_DIAGNOSIS_REJECTED","UNFALSIFIABLE_EXTRA_DIAGNOSIS_REJECTED",
   "REPAIR_WITH_NO_CAUSAL_RESCUE_REJECTED","NONIDENTIFIABLE_FORCE_UNIQUE_REJECTED",
   "MECHANISM_CLASS_SWAP_REJECTED","DROP_CAUSAL_PREDECESSOR_REJECTED",
   "SYMPTOM_ONLY_REPAIR_NONRESCUE","PARTIAL_INTERACTION_REPAIR_NONRESCUE",
  }
  self.assertEqual(set(w),required)
  self.assertTrue(all(w.values()),w)

 def test_v5_falsification_is_load_bearing(self):
  vf=rel._load(rel.V5_FALSIFICATION)
  self.assertFalse(vf["finding"]["heterogeneous_intervention_rescue_supported"])
  self.assertTrue(vf["finding"]["counterexample_trajectory_deleted_still_rescued"])
  self.assertTrue(vf["finding"]["counterexample_task_removed_still_rescued"])

 def test_normalization_boundary_is_exact(self):
  b=rel._load(rel.BINDING)
  self.assertEqual(b["decomposition"]["normalization_boundary"],rel.EXPECTED_NORMALIZATION)
  self.assertEqual(b["decomposition"]["owned_behavior"],rel.EXPECTED_OWNED)

 def test_all_surface_contract_pointers_are_exact(self):
  p=rel._load(rel.PORTFOLIOS)
  for _,(pid,sid) in rel.EXPECTED_SURFACES.items():
   s=rel._surface(p,pid,sid)
   self.assertIsNotNone(s)
   self.assertEqual(s["direct_proof_contracts"],rel.CONTRACTS)
   self.assertEqual(s["evaluator"],rel.ROUTES)
   self.assertIn(rel.ROUTE,s["proof_routes"])

 def test_full_binding_check_and_mutation_sets_are_exact(self):
  b=rel._load(rel.BINDING)
  self.assertEqual(set(b["evaluator"]["required_checks"]),rel.EXPECTED_CHECKS)
  self.assertEqual(set(b["evaluator"]["required_mutations"]),rel.EXPECTED_MUTATIONS)

 def test_exact_v6_and_authority_blobs_are_frozen(self):
  for path,sha in rel.EXPECTED_BLOBS.items():
   self.assertEqual(rel._blob_sha(path),sha,path)

if __name__=="__main__":
 unittest.main(verbosity=2)
