from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_quality_r1_execution_property_truth_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def docs():
    out={}
    for key,(rel,_) in v.PINS.items():
        if key in {"manifest","catalog","structural_verify","scope_batch_verify","schema","registry"}:
            out[key]=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    return out

class R1ExecutionPropertyTruthV1Tests(unittest.TestCase):
    def test_exact_current_r1_execution_acceptance_passes_one_leaf_only(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["leaf_property_truth_authority"])
        self.assertGreaterEqual(out["observed_case_counts"]["total"],25)
        self.assertFalse(out["detection_completeness_proved"])
        self.assertFalse(out["r1_semantic_leaf_closed"])
        self.assertFalse(out["r1_root_closed"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_manifest_acceptance_drift_fails_closed(self):
        d=docs()
        row=next(x for x in d["manifest"]["roots"] if x["root_id"]==v.ROOT_ID)
        row["execution_leaf"]["acceptance"]="WEAKER"
        out=v.evaluate_documents(d["manifest"],d["catalog"],d["scope_batch_verify"],d["structural_verify"],d["schema"],d["registry"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R1_EXECUTION_ACCEPTANCE_DRIFT")

    def test_structural_replay_must_be_exact_21_of_21(self):
        d=docs()
        d["structural_verify"]["replay"]["tests_passed"]=20
        out=v.evaluate_documents(d["manifest"],d["catalog"],d["scope_batch_verify"],d["structural_verify"],d["schema"],d["registry"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R1_STRUCTURAL_REPLAY_NOT_21_OF_21")

    def test_r1_catalog_membership_drift_fails_closed(self):
        d=docs()
        target=next(x for x in d["catalog"]["challenges"] if x["id"]=="C78_CONTEXT_TRUNCATION_OBLIGATION_DROP")
        target["root_ids"]=[]
        out=v.evaluate_documents(d["manifest"],d["catalog"],d["scope_batch_verify"],d["structural_verify"],d["schema"],d["registry"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R1_DEFEATER_CATALOG_DRIFT")

    def test_live_registry_required_field_omission_is_caught(self):
        d=docs()
        d["registry"]=copy.deepcopy(d["registry"])
        del d["registry"]["active_contracted_residuals"][0]["scope"]
        out=v.evaluate_documents(d["manifest"],d["catalog"],d["scope_batch_verify"],d["structural_verify"],d["schema"],d["registry"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R1_LIVE_CONTRACT_POSITIVE_RECOMPUTE_FAILED")

if __name__=="__main__":
    unittest.main(verbosity=2)
