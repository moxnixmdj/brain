from __future__ import annotations
import hashlib, json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
R2=ROOT/"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TERMINAL=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
FIXED=ROOT/"canonical/runtime/general_adequate_decision_fixed_point_v2.py"
V19=ROOT/"canonical/runtime/r2_direct_end_to_end_adequacy_v19.py"
V21=ROOT/"canonical/runtime/r2_direct_end_to_end_adequacy_v21.py"
WRAPPER=ROOT/"canonical/runtime/r2_direct_live_admission_v1.py"
DEFAULT_RUNTIME=ROOT/"canonical/governance/CURRENT_DEFAULT_RUNTIME_INTEGRATION.json"
SUCCESSOR_IDS={
"DIRECT_ADEQUACY::CROSS_DOCUMENT_NATURAL_EFFECT_LATTICE_V3",
"DIRECT_ADEQUACY::CROSS_DOCUMENT_SEMANTIC_EDGE_LATTICE_V4",
"DIRECT_ADEQUACY::CROSS_DOCUMENT_SEMANTIC_REGISTRY_LATTICE_V5",
"DIRECT_ADEQUACY::SOURCE_BOUND_REGCAP_IDENTITY_NYFED_CCOB_V1",
}
def blob(path):
 raw=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(path): return json.loads(path.read_text(encoding="utf-8"))
class R2V57V19AuthorityReconciliationTests(unittest.TestCase):
 def test_live_controller_uses_default_runtime_over_current_r2_baseline(self):
  r2=load(R2); d=r2["direct_adequacy"]; source=FIXED.read_text(encoding="utf-8")
  self.assertIn("from canonical.runtime import r2_direct_live_admission_v1 as direct_adequacy",source)
  self.assertEqual(d["direct_runtime_path"],"canonical/runtime/r2_direct_end_to_end_adequacy_v19.py")
  self.assertEqual(d["direct_runtime_git_blob_sha"],blob(V19))
  current=load(DEFAULT_RUNTIME); rt=current["r2_default_route_runtime"]
  self.assertEqual(rt["stable_wrapper_git_blob_sha"],blob(WRAPPER))
  self.assertEqual(rt["verified_static_backend"]["runtime_git_blob_sha"],blob(V21))
  self.assertEqual(rt["current_r2_activation_baseline"]["activation_route_count"],39)
 def test_activation_contains_all_live_successors(self):
  r2=load(R2); d=r2["direct_adequacy"]; p=ROOT/d["activation_path"]
  self.assertEqual(d["activation_git_blob_sha"],blob(p))
  a=load(p); ids={x["route_id"] for x in a["current_routes"]}
  self.assertEqual(len(ids),39)
  self.assertTrue(SUCCESSOR_IDS.issubset(ids),sorted(SUCCESSOR_IDS-ids))
  self.assertEqual(a["runtime"],"canonical/runtime/r2_direct_end_to_end_adequacy_v19.py")
  self.assertEqual(d["current_route_count"],39); self.assertEqual(d["bounded_family_count"],36)
 def test_scheduler_and_terminal_are_same_projection(self):
  r2=load(R2); t=load(TERMINAL); p=ROOT/r2["scheduler_cut"]["path"]
  self.assertEqual(r2["scheduler_cut"]["git_blob_sha"],blob(p)); cut=load(p)
  for obj in (r2["scheduler_result"],cut["scheduler_result"]):
   self.assertEqual(obj["direct_route_count"],39); self.assertEqual(obj["bounded_family_count"],36)
  self.assertEqual(t["live_truth"]["r2_direct_adequacy_route_count"],39)
  self.assertEqual(t["live_truth"]["r2_direct_adequacy_bounded_family_count"],36)
  self.assertEqual(t["r2_scheduler_precedence"]["current_scheduler_git_blob_sha"],blob(p))
  self.assertIn("CURRENT_R2_V",t["status"])
if __name__=="__main__": unittest.main(verbosity=2)
