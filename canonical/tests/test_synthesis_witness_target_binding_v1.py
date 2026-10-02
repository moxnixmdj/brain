from __future__ import annotations
import copy, json, unittest
from pathlib import Path
from canonical.runtime.synthesis_witness_target_binding_verifier_v1 import (
    CANDIDATE, REGISTRY, P3, P3_VERIFY, WAVE, POST, TARGETS, blob_sha, evaluate, load
)

class SynthesisWitnessTargetBindingTests(unittest.TestCase):
    def docs(self):
        docs=[load(x) for x in (CANDIDATE, REGISTRY, P3, P3_VERIFY, WAVE, POST, TARGETS)]
        shas={
            "registry":blob_sha(REGISTRY),"p3":blob_sha(P3),"p3_verify":blob_sha(P3_VERIFY),
            "wave":blob_sha(WAVE),"post":blob_sha(POST),"targets":blob_sha(TARGETS),
        }
        return docs,shas

    def test_live_candidate_passes(self):
        docs,shas=self.docs()
        out=evaluate(*docs,shas)
        self.assertTrue(out["pass"],out)
        self.assertEqual(len(out["proved_atoms"]),7)
        self.assertEqual(out["remaining_target_atoms"],["metric:matched_quality"])
        self.assertEqual(out["metric_bounds"],{})
        self.assertTrue(out["contamination_clean"])

    def test_numeric_bound_invention_fails(self):
        docs,shas=self.docs()
        docs[0]=copy.deepcopy(docs[0])
        docs[0]["metric_bounds"]={"matched_quality_noninferiority":{"lower":0}}
        out=evaluate(*docs,shas)
        self.assertFalse(out["pass"])
        self.assertIn("NUMERIC_METRIC_BOUNDS_FORBIDDEN",out["errors"])

    def test_atom_overclaim_fails(self):
        docs,shas=self.docs()
        docs[0]=copy.deepcopy(docs[0])
        docs[0]["proved_atoms"].append("metric:matched_quality")
        out=evaluate(*docs,shas)
        self.assertFalse(out["pass"])
        self.assertIn("PROVED_ATOMS_MISMATCH",out["errors"])

    def test_contamination_fails_closed(self):
        docs,shas=self.docs()
        docs[4]=copy.deepcopy(docs[4])
        rows=docs[4]["reduction_input"]["wave"]["parent_portfolio_receipts"]["T1"]
        hit=next(x for x in rows if x.get("behavior_id")=="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001")
        hit["tuning_replay"]=True
        out=evaluate(*docs,shas)
        self.assertFalse(out["pass"])
        self.assertIn("T1_CONTAMINATION_FLAG_FAIL",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
