from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r10_execution_property_truth_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def docs():
    out={}
    for key in ("manifest","profile","catalog","constitution","scope_gate_verify"):
        rel,_=v.PINS[key]
        out[key]=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    return out

class R10ExecutionPropertyTruthV1Tests(unittest.TestCase):
    def test_real_exact_bound_r10_execution_acceptance_passes_one_leaf_only(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["leaf_property_truth_authority"])
        self.assertEqual(out["observed_case_counts"]["total"],38)
        self.assertFalse(out["detection_completeness_proved"])
        self.assertFalse(out["r10_semantic_leaf_closed"])
        self.assertFalse(out["r10_root_closed"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_manifest_acceptance_drift_fails_closed(self):
        d=docs()
        row=next(x for x in d["manifest"]["roots"] if x["root_id"]==v.ROOT_ID)
        row["execution_leaf"]["acceptance"]="WEAKER_ACCEPTANCE"
        out=v.evaluate_documents(d["manifest"],d["profile"],d["catalog"],d["constitution"],d["scope_gate_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R10_EXECUTION_ACCEPTANCE_DRIFT")

    def test_scope_gate_must_be_complete_and_property_ready(self):
        d=docs()
        d["scope_gate_verify"]["consequence"]["whole_leaf_scope_complete"]=False
        out=v.evaluate_documents(d["manifest"],d["profile"],d["catalog"],d["constitution"],d["scope_gate_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R10_WHOLE_LEAF_SCOPE_NOT_COMPLETE")

    def test_catalog_loss_breaks_property_challenge(self):
        d=docs()
        rows=d["catalog"].get("defeaters") or d["catalog"].get("attack_classes") or d["catalog"].get("nodes") or d["catalog"].get("challenges")
        target=next(x for x in rows if x.get("id")=="C48_ANALYSIS_CHERRY_PICK")
        field="root_ids" if isinstance(target.get("root_ids"),list) else "target_root_ids"
        target[field]=[x for x in target[field] if x!=v.ROOT_ID]
        out=v.evaluate_documents(d["manifest"],d["profile"],d["catalog"],d["constitution"],d["scope_gate_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R10_EXECUTION_PROPERTY_CHALLENGE_FAILED")

    def test_missing_near_miss_trigger_breaks_property_challenge(self):
        d=docs()
        d["profile"]["escalation_triggers"]=[
            x for x in d["profile"]["escalation_triggers"]
            if x!="NEAR_DECISION_BOUNDARY"
        ]
        out=v.evaluate_documents(d["manifest"],d["profile"],d["catalog"],d["constitution"],d["scope_gate_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R10_EXECUTION_PROPERTY_CHALLENGE_FAILED")

if __name__=="__main__":
    unittest.main(verbosity=2)
