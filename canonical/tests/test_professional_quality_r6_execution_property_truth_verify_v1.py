from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r6_execution_property_truth_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def docs():
    out={}
    for key in ("manifest","catalog","graph","scope_batch_verify","binder_verify","currentgen_verify","order_verify","defeater80_verify"):
        rel,_=v.PINS[key]
        out[key]=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    return out

class R6ExecutionPropertyTruthV1Tests(unittest.TestCase):
    def evaluate(self,d):
        return v.evaluate_documents(
            d["manifest"],d["catalog"],d["graph"],d["scope_batch_verify"],
            d["binder_verify"],d["currentgen_verify"],d["order_verify"],d["defeater80_verify"],
        )

    def test_exact_r6_execution_acceptance_passes_one_leaf_only(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["leaf_property_truth_authority"])
        self.assertEqual(out["observed_case_counts"]["canonical_r6_defeater_activations"],15)
        self.assertEqual(out["observed_case_counts"]["total"],22)
        self.assertFalse(out["r6_semantic_leaf_closed"])
        self.assertFalse(out["r6_root_closed"])
        self.assertFalse(out["global_evidence_completeness_proved"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_manifest_acceptance_drift_fails_closed(self):
        d=docs()
        row=next(x for x in d["manifest"]["roots"] if x["root_id"]==v.ROOT_ID)
        row["execution_leaf"]["acceptance"]="WEAKER"
        out=self.evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R6_EXECUTION_ACCEPTANCE_DRIFT")

    def test_catalog_loss_fails_closed(self):
        d=docs()
        row=next(x for x in d["catalog"]["challenges"] if x["id"]=="C77_PROVENANCE_OR_RECEIPT_FORGERY")
        row["root_ids"]=[x for x in row["root_ids"] if x!=v.ROOT_ID]
        out=self.evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R6_DEFEATER_CATALOG_DRIFT")

    def test_scope_batch_must_remain_complete(self):
        d=docs()
        d["scope_batch_verify"]["independent_replay"]["scope_complete_count"]=23
        out=self.evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"WHOLE_LEAF_SCOPE_BATCH_NOT_24_OF_24")

    def test_binder_mutation_proof_cannot_drop_stale_basis_guard(self):
        d=docs()
        d["binder_verify"]["proved"]=[
            x for x in d["binder_verify"]["proved"]
            if x!="RECEIPT_VERIFICATION_BASIS_MUST_BE_CONTENT_ADDRESSED_AND_CURRENT"
        ]
        out=self.evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R6_EXECUTION_PROPERTY_CHALLENGE_FAILED")

    def test_uvck_current_generation_replay_required(self):
        d=docs()
        d["currentgen_verify"]["replay"]["tests_passed"]=17
        out=self.evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"UVCK_CURRENT_GENERATION_REPLAY_INVALID")

if __name__=="__main__":
    unittest.main(verbosity=2)
