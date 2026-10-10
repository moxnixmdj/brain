from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from canonical.runtime import professional_quality_r2_candidate_branch_basis_v1 as g

PROFILE={
 "schema":g.PROFILE_SCHEMA,
 "behavior_id":"PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
 "steps":["A","B","C"],
 "escalation_triggers":["X","Y"],
}

class Tests(unittest.TestCase):
 def root(self):
  td=tempfile.TemporaryDirectory()
  root=Path(td.name); p=root/g.PROFILE_PATH; p.parent.mkdir(parents=True)
  p.write_text(json.dumps(PROFILE,separators=(",",":")),encoding="utf-8")
  # Tests exercise behavior by rebinding the expected blob to the fixture bytes.
  return td,root,p
 def call(self):
  td,root,p=self.root()
  old=g.PROFILE_BLOB
  try:
   g.PROFILE_BLOB=g._git_blob(p)
   out=g.generate(target_instance={"kind":"doc","audience":"board"},incumbent={"plan_id":"inc-1"},repo_root=root)
   return td,out
  finally:
   g.PROFILE_BLOB=old
 def test_finite_deterministic_basis_and_incumbent_preserved(self):
  td,a=self.call()
  try:
   self.assertTrue(a["pass"],a);self.assertEqual(a["candidate_count"],6)
   self.assertEqual(a["incumbent_branch_count"],1)
   self.assertEqual(sum(x["incumbent_preserved"] for x in a["candidates"]),1)
   self.assertFalse(a["global_candidate_search_complete"])
   self.assertFalse(a["candidate_artifact_realization_complete"])
  finally: td.cleanup()
 def test_deterministic_ids(self):
  td,a=self.call()
  try:
   td2,b=self.call()
   try:self.assertEqual([x["candidate_id"] for x in a["candidates"]],[x["candidate_id"] for x in b["candidates"]])
   finally:td2.cleanup()
  finally:td.cleanup()
 def test_target_changes_universe(self):
  td,root,p=self.root();old=g.PROFILE_BLOB
  try:
   g.PROFILE_BLOB=g._git_blob(p)
   a=g.generate(target_instance={"x":1},incumbent={"p":1},repo_root=root)
   b=g.generate(target_instance={"x":2},incumbent={"p":1},repo_root=root)
   self.assertNotEqual(a["candidate_universe_sha256"],b["candidate_universe_sha256"])
  finally:g.PROFILE_BLOB=old;td.cleanup()
 def test_incumbent_changes_universe(self):
  td,root,p=self.root();old=g.PROFILE_BLOB
  try:
   g.PROFILE_BLOB=g._git_blob(p)
   a=g.generate(target_instance={"x":1},incumbent={"p":1},repo_root=root)
   b=g.generate(target_instance={"x":1},incumbent={"p":2},repo_root=root)
   self.assertNotEqual(a["candidate_universe_sha256"],b["candidate_universe_sha256"])
  finally:g.PROFILE_BLOB=old;td.cleanup()
 def test_profile_blob_mismatch_fails_closed(self):
  td,root,p=self.root()
  try:
   out=g.generate(target_instance={"x":1},incumbent={"p":1},repo_root=root)
   self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"PINNED_EXECUTION_PROFILE_UNAVAILABLE")
  finally:td.cleanup()
 def test_duplicate_profile_step_fails_closed(self):
  td,root,p=self.root();doc=dict(PROFILE);doc["steps"]=["A","A"];p.write_text(json.dumps(doc,separators=(",",":")),encoding="utf-8");old=g.PROFILE_BLOB
  try:
   g.PROFILE_BLOB=g._git_blob(p)
   out=g.generate(target_instance={"x":1},incumbent={"p":1},repo_root=root)
   self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"PROFILE_STEPS_NOT_UNIQUE")
  finally:g.PROFILE_BLOB=old;td.cleanup()
 def test_missing_target_or_incumbent_fails_closed(self):
  self.assertEqual(g.generate(target_instance={},incumbent={"p":1})["reason"],"TARGET_INSTANCE_REQUIRED")
  self.assertEqual(g.generate(target_instance={"x":1},incumbent={})["reason"],"INCUMBENT_REQUIRED")

if __name__=="__main__":unittest.main()
