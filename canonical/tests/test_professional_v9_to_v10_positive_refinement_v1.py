from __future__ import annotations
import unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import professional_v9_to_v10_positive_refinement_v1 as r

ROOT=Path(__file__).resolve().parents[2]

class Tests(unittest.TestCase):
 def test_exact_current_refinement_passes(self):
  out=r.verify(repo_root=ROOT)
  self.assertTrue(out["pass"],out)
  self.assertTrue(out["positive_route_refinement_proved"])
  self.assertFalse(out["new_positive_behavior_added"])
  self.assertTrue(out["foreign_verifier_rejected_preexecution"])
 def test_v10_blob_drift_fails_closed(self):
  with patch.object(r,"V10_BLOB","0"*40):
   out=r.verify(repo_root=ROOT)
  self.assertFalse(out["pass"])
  self.assertIn("BLOB_DRIFT",out["reason"])
 def test_subject_drift_fails_closed(self):
  with patch.object(r,"V10_SUBJECT_SHA256","0"*64):
   out=r.verify(repo_root=ROOT)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"V10_SUBJECT_IDENTITY_DRIFT")
 def test_approved_verifier_drift_fails_closed(self):
  with patch.object(r,"APPROVED_VERIFIER_BLOB","0"*40):
   out=r.verify(repo_root=ROOT)
  self.assertFalse(out["pass"])
  self.assertIn("BLOB_DRIFT",out["reason"])

if __name__=="__main__":unittest.main(verbosity=2)
