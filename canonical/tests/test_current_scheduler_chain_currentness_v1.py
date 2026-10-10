import json,unittest
from pathlib import Path

from canonical.runtime import capability_parallel_frontier_post_composition_v2 as adapter
from canonical.runtime import capability_parallel_frontier_v2 as core

ROOT=Path(__file__).resolve().parents[2]

def load(rel):
 return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class T(unittest.TestCase):
 def test_current_scheduler_chain_uses_v15_dynamic_currentness(self):
  sp="canonical/governance/CURRENT_DEVELOPMENT_SCHEDULER.json"
  mp="canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
  fp="canonical/governance/CURRENT_LIVE_WORK_FRONTIER.json"
  s,m,f=map(load,[sp,mp,fp])

  self.assertEqual(
   s["authoritative_activation"],
   "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261010_V15.json",
  )
  self.assertEqual(
   s["runtime"],
   "canonical/runtime/capability_parallel_frontier_post_composition_v2.py",
  )
  self.assertEqual(
   s["primary_entrypoint"],
   "canonical.runtime.capability_parallel_frontier_post_composition_v2.plan_current_post_composition_frontier",
  )
  self.assertEqual(
   m["current_development_scheduler"]["activation"],
   "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261010_V15.json",
  )
  self.assertEqual(
   m["current_development_scheduler"]["primary_runtime"],
   "canonical/runtime/capability_parallel_frontier_post_composition_v2.py",
  )

  refreshed=adapter.refresh_post_composition_currentness(f,root=ROOT)
  bound={x["path"]:x["git_blob_sha"] for x in refreshed["scope"]["source_set"]}
  for rel in (adapter.PROF,adapter.ASSURANCE,adapter.BYTES,adapter.R2):
   self.assertEqual(bound[rel],adapter._git_blob_sha(ROOT/rel),rel)

  supported={adapter.PROF,adapter.ASSURANCE,adapter.BYTES,adapter.R2}
  for row in refreshed["scope"]["source_set"]:
   if row["path"] in supported:
    continue
   self.assertEqual(row["git_blob_sha"],adapter._git_blob_sha(ROOT/row["path"]),row["path"])

  out=adapter.plan_current_post_composition_frontier()
  self.assertTrue(out["frontier_currentness"]["currentness_verified"])
  self.assertTrue(out["dynamic_currentness"]["professional_pointer_follow"])
  self.assertTrue(out["dynamic_currentness"]["assurance_pointer_follow"])
  self.assertTrue(out["dynamic_currentness"]["bytes_pointer_follow"])
  self.assertTrue(out["dynamic_currentness"]["r2_pointer_follow"])
  self.assertFalse(out["execution_authority"])
  self.assertFalse(out["promotion_authority"])
  self.assertEqual(out["terminal_credit_delta"],0)

 def test_unmodeled_source_drift_is_not_silently_followed(self):
  f=core.load_current_frontier()
  row=next(
   x for x in f["scope"]["source_set"]
   if x["path"]=="canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
  )
  row["git_blob_sha"]="0"*40
  refreshed=adapter.refresh_post_composition_currentness(f,root=ROOT)
  with self.assertRaisesRegex(core.ParallelFrontierError,"LIVE_WORK_FRONTIER_STALE"):
   core.plan_parallel_frontier(refreshed)

if __name__=="__main__":
 unittest.main(verbosity=2)
