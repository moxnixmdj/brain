import json
from pathlib import Path
import tempfile
import unittest
from canonical.runtime import professional_quality_r2_candidate_branch_basis_v2 as base
from canonical.runtime import professional_quality_r2_repaired_v7_rekey_adapter_v1 as adapter

PROFILE={"schema":base.PROFILE_SCHEMA,"behavior_id":"PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001","steps":["A","B"],"escalation_triggers":["X"]}

class Tests(unittest.TestCase):
 def root(self):
  td=tempfile.TemporaryDirectory(); root=Path(td.name); p=root/base.PROFILE_PATH; p.parent.mkdir(parents=True)
  p.write_text(json.dumps(PROFILE,separators=(",",":")),encoding="utf-8")
  return td,root,p
 def run_pair(self):
  td,root,p=self.root(); old=base.PROFILE_BLOB
  base.PROFILE_BLOB=base._git_blob(p)
  try:
   x={"x":1}; y={"p":1}
   return td,base.generate(target_instance=x,incumbent=y,repo_root=root),adapter.generate(target_instance=x,incumbent=y,repo_root=root)
  finally: base.PROFILE_BLOB=old
 def test_exact_branch_bijection_and_rekey(self):
  td,a,b=self.run_pair()
  try:
   self.assertTrue(a["pass"] and b["pass"])
   self.assertEqual([x["operator"] for x in a["candidates"]],[x["operator"] for x in b["candidates"]])
   self.assertEqual([x["ordinal"] for x in a["candidates"]],[x["ordinal"] for x in b["candidates"]])
   self.assertTrue(all(x["candidate_id"]!=y["candidate_id"] for x,y in zip(a["candidates"],b["candidates"])))
   self.assertEqual(b["subject_id"],adapter.NEW_ID); self.assertFalse(b["global_candidate_search_complete"])
  finally: td.cleanup()
 def test_base_subject_drift_fails_closed(self):
  old=base.SUBJECT_SHA256; base.SUBJECT_SHA256="bad"
  try:self.assertEqual(adapter.generate(target_instance={"x":1},incumbent={"p":1})["reason"],"BASE_SUBJECT_IDENTITY_DRIFT")
  finally:base.SUBJECT_SHA256=old
 def test_missing_target_preserves_fail_closed(self):
  self.assertFalse(adapter.generate(target_instance={},incumbent={"p":1})["pass"])
 def test_no_authority_escalation(self):
  td,a,b=self.run_pair()
  try:self.assertFalse(b["quality_authority"]);self.assertFalse(b["terminal_authority"]);self.assertEqual(b["terminal_credit_delta"],0)
  finally:td.cleanup()

if __name__=="__main__":unittest.main()
