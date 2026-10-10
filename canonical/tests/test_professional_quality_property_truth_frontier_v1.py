from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_property_truth_frontier_v1 as f

ROOT=Path(__file__).resolve().parents[2]

def load(key):
    rel,_=f.PINS[key]
    return json.loads((ROOT/rel).read_text())

class PropertyTruthFrontierV1Tests(unittest.TestCase):
    def setUp(self):
        self.manifest=load("manifest")
        self.catalog=load("catalog")
        self.scope=load("scope_batch_verify")
        self.known=load("known_defeater_verify")
        self.r10=load("r10_execution_guard_verify")

    def project(self):
        return f.project_documents(self.manifest,self.catalog,self.scope,self.known,self.r10)

    def test_real_projection_localizes_without_property_credit(self):
        out=self.project()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["leaf_count"],24)
        self.assertEqual(out["scope_complete_count"],24)
        self.assertEqual(out["known_defeater_count"],80)
        self.assertEqual(out["property_truth_ready_count"],0)
        self.assertEqual(out["property_truth_closed_count"],0)
        self.assertFalse(out["known_defeater_set_complete_proved"])
        self.assertFalse(out["unknown_defeater_completeness_proved"])
        self.assertFalse(out["terminal_authority"])

    def test_all_roots_have_known_defeaters_but_that_is_not_completeness(self):
        out=self.project()
        self.assertEqual(len(out["known_defeater_root_counts"]),12)
        self.assertTrue(all(v>0 for v in out["known_defeater_root_counts"].values()))
        self.assertEqual(out["known_defeater_root_counts"]["R10_ANALYSIS_DECISION"],17)
        self.assertFalse(out["known_defeater_set_complete_proved"])

    def test_r10_execution_is_enforcement_verified_but_detection_open(self):
        out=self.project()
        row=next(r for r in out["rows"] if r["leaf_id"]=="PQ::R10_ANALYSIS_DECISION::EXECUTION")
        self.assertTrue(row["root_specific_enforcement_verified"])
        self.assertFalse(row["detection_completeness_proved"])
        self.assertFalse(row["whole_leaf_property_truth_proved"])
        self.assertEqual(row["exact_residual"],"DEFEATER_DETECTION_AND_REQUIRED_PROOF_SLOT_COMPLETENESS")

    def test_catalog_completeness_self_claim_is_rejected(self):
        catalog=deepcopy(self.catalog)
        catalog["hard_nonclaims"]=[x for x in catalog["hard_nonclaims"] if x!="NO_CLAIM_DEFEATER_SET_COMPLETE"]
        out=f.project_documents(self.manifest,catalog,self.scope,self.known,self.r10)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"DEFEATER_COMPLETENESS_NONCLAIM_MISSING")

    def test_r10_detection_overclaim_is_rejected(self):
        r10=deepcopy(self.r10)
        r10["open_residual"]["detection_completeness_proved"]=True
        out=f.project_documents(self.manifest,self.catalog,self.scope,self.known,r10)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R10_DETECTION_COMPLETENESS_OVERCLAIM")

    def test_scope_batch_drift_fails_closed(self):
        scope=deepcopy(self.scope)
        scope["independent_replay"]["scope_complete_count"]=23
        out=f.project_documents(self.manifest,self.catalog,scope,self.known,self.r10)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"SCOPE_BATCH_COUNTS_INVALID")

if __name__=="__main__":
    unittest.main(verbosity=2)
