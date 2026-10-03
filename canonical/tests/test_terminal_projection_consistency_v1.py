from __future__ import annotations
import copy,unittest
from canonical.runtime.terminal_projection_consistency_v1 import PATHS,_load,_sha,evaluate_documents
class T(unittest.TestCase):
 def live(self):
  d={k:_load(v) for k,v in PATHS.items()}; s={v:_sha(v) for v in PATHS.values()}; return d,s
 def ev(self,d,s): return evaluate_documents(d["authority"],d["closure"],d["matrix"],d["atomic_bindings"],d["delegation_acceptance"],d["recovery_acceptance"],s)
 def test_live(self):
  d,s=self.live(); o=self.ev(d,s); self.assertTrue(o["pass"],o); self.assertEqual((o["acceptance_closed_families"],o["acceptance_open_families"]),(4,15)); self.assertEqual((o["atomic_predicates_proved"],o["atomic_predicates_unresolved"]),(11,27))
 def test_authority_regression(self):
  d,s=self.live(); d=copy.deepcopy(d); d["authority"]["truth"]["opus55_acceptance"]="3/19_PASS__16/19_OPEN"; self.assertFalse(self.ev(d,s)["pass"])
 def test_atomic_regression(self):
  d,s=self.live(); d=copy.deepcopy(d); d["atomic_bindings"]["saturation"]["proved_predicate_count"]=10; d["atomic_bindings"]["saturation"]["unresolved_predicate_count"]=28; self.assertFalse(self.ev(d,s)["pass"])
 def test_recovery_disappearance(self):
  d,s=self.live(); d=copy.deepcopy(d); d["closure"]["opus55_acceptance_summary"]["calibrated_families"].remove("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"); self.assertFalse(self.ev(d,s)["pass"])
 def test_stale_pointer(self):
  d,s=self.live(); d=copy.deepcopy(d); d["authority"]["sources"]["terminal_closure_manifest"]["git_blob_sha"]="0"*40; self.assertFalse(self.ev(d,s)["pass"])
if __name__=="__main__": unittest.main(verbosity=2)
