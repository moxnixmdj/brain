from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r7_execution_property_truth_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def docs():
    out={}
    for key in ("manifest","catalog","scope_batch_verify","source_receipt","causal_verify"):
        rel,_=v.PINS[key]
        out[key]=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    return out

class R7ExecutionPropertyTruthV1Tests(unittest.TestCase):
    def test_real_exact_r7_execution_acceptance_passes_one_leaf_only(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["leaf_property_truth_authority"])
        self.assertEqual(out["observed_case_counts"]["total"],9)
        self.assertEqual(set(out["canonical_r7_defeater_ids"]),v.EXPECTED_R7_DEFEATERS)
        self.assertFalse(out["r7_semantic_leaf_closed"])
        self.assertFalse(out["r7_root_closed"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_manifest_acceptance_drift_fails_closed(self):
        d=docs()
        row=next(x for x in d["manifest"]["roots"] if x["root_id"]==v.ROOT_ID)
        row["execution_leaf"]["acceptance"]="WEAKER"
        out=v.evaluate_documents(d["manifest"],d["catalog"],d["scope_batch_verify"],d["source_receipt"],d["causal_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R7_EXECUTION_ACCEPTANCE_DRIFT")

    def test_catalog_drift_fails_closed(self):
        d=docs()
        row=next(x for x in d["catalog"]["challenges"] if x["id"]=="C31_EDIT_SEQUENCE_INTERACTION")
        row["root_ids"]=[x for x in row["root_ids"] if x!=v.ROOT_ID]
        out=v.evaluate_documents(d["manifest"],d["catalog"],d["scope_batch_verify"],d["source_receipt"],d["causal_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R7_DEFEATER_CATALOG_DRIFT")

    def test_scope_batch_must_stay_24_of_24(self):
        d=docs()
        d["scope_batch_verify"]["independent_replay"]["scope_complete_count"]=23
        out=v.evaluate_documents(d["manifest"],d["catalog"],d["scope_batch_verify"],d["source_receipt"],d["causal_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"WHOLE_LEAF_SCOPE_BATCH_NOT_24_OF_24")

    def test_positive_receipt_cannot_be_pass_to_pass(self):
        d=docs()
        d["source_receipt"]["real_execution"]["predecessor_result"]["outcome"]="PASS"
        d["source_receipt"]["real_execution"]["predecessor_result"]["return_code"]=0
        out=v.evaluate_documents(d["manifest"],d["catalog"],d["scope_batch_verify"],d["source_receipt"],d["causal_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R7_EXECUTION_PROPERTY_CHALLENGE_FAILED")

if __name__=="__main__":
    unittest.main(verbosity=2)
