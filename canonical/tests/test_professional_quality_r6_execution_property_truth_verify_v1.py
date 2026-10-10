from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r6_execution_property_truth_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def docs():
    out={}
    for key in ("manifest","graph","catalog","scope_batch_verify","r6_binding_verify"):
        rel,_=v.PINS[key]
        out[key]=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    return out

class R6ExecutionPropertyTruthV1Tests(unittest.TestCase):
    def test_real_exact_bound_r6_execution_acceptance_passes_one_leaf_only(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["leaf_property_truth_authority"])
        self.assertEqual(out["observed_case_counts"]["total"],31)
        self.assertFalse(out["unknown_defeater_completeness_proved"])
        self.assertFalse(out["r6_semantic_leaf_closed"])
        self.assertFalse(out["r6_root_closed"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_manifest_acceptance_drift_fails_closed(self):
        d=docs()
        row=next(x for x in d["manifest"]["roots"] if x["root_id"]==v.ROOT_ID)
        row["execution_leaf"]["acceptance"]="WEAKER_ACCEPTANCE"
        out=v.evaluate_documents(d["manifest"],d["graph"],d["catalog"],d["scope_batch_verify"],d["r6_binding_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R6_EXECUTION_ACCEPTANCE_DRIFT")

    def test_catalog_root_binding_drift_fails_closed(self):
        d=docs()
        target=next(x for x in d["catalog"]["challenges"] if x["id"]=="C23_PSEUDOREPLICATION")
        target["root_ids"]=[]
        out=v.evaluate_documents(d["manifest"],d["graph"],d["catalog"],d["scope_batch_verify"],d["r6_binding_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R6_DEFEATER_BINDING_DRIFT")

    def test_scope_batch_must_remain_complete(self):
        d=docs()
        d["scope_batch_verify"]["independent_replay"]["scope_complete_count"]=23
        out=v.evaluate_documents(d["manifest"],d["graph"],d["catalog"],d["scope_batch_verify"],d["r6_binding_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R6_SCOPE_BATCH_INCOMPLETE")

if __name__=="__main__":
    unittest.main(verbosity=2)
