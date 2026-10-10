from __future__ import annotations
from copy import deepcopy
import importlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]

def verifier():
    try:
        return importlib.import_module("canonical.runtime.professional_quality_r9_execution_property_truth_verify_v1")
    except ModuleNotFoundError:
        raise AssertionError("R9_PROPERTY_VERIFIER_MISSING")

def docs(v):
    out={}
    for key in ("manifest","profile","catalog","scope_batch_verify","censoring_verify"):
        rel,_=v.PINS[key]
        out[key]=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    return out

class R9ExecutionPropertyTruthV1Tests(unittest.TestCase):
    def test_real_exact_bound_r9_execution_acceptance_passes_one_leaf_only(self):
        v=verifier()
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["leaf_property_truth_authority"])
        self.assertEqual(out["claim_id"],v.CLAIM_ID)
        self.assertEqual(out["observed_case_counts"]["known_adversarial"],13)
        self.assertGreaterEqual(out["observed_case_counts"]["total"],24)
        self.assertFalse(out["detection_completeness_proved"])
        self.assertFalse(out["r9_semantic_leaf_closed"])
        self.assertFalse(out["r9_root_closed"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_manifest_acceptance_drift_fails_closed(self):
        v=verifier(); d=docs(v)
        row=next(x for x in d["manifest"]["roots"] if x["root_id"]==v.ROOT_ID)
        row["execution_leaf"]["acceptance"]="WEAKER_ACCEPTANCE"
        out=v.evaluate_documents(d["manifest"],d["profile"],d["catalog"],d["scope_batch_verify"],d["censoring_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R9_EXECUTION_ACCEPTANCE_DRIFT")

    def test_scope_batch_must_bind_exact_manifest_and_pass_all_24(self):
        v=verifier(); d=docs(v)
        d["scope_batch_verify"]["independent_replay"]["scope_complete_count"]=23
        out=v.evaluate_documents(d["manifest"],d["profile"],d["catalog"],d["scope_batch_verify"],d["censoring_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R9_WHOLE_LEAF_SCOPE_BATCH_NOT_COMPLETE")

    def test_censoring_verification_must_be_exact_and_complete(self):
        v=verifier(); d=docs(v)
        d["censoring_verify"]["replay"]["exhaustive_final_success_counts_checked"]=210
        out=v.evaluate_documents(d["manifest"],d["profile"],d["catalog"],d["scope_batch_verify"],d["censoring_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R9_CENSORING_VERIFICATION_INCOMPLETE")

    def test_catalog_loss_breaks_property_challenge(self):
        v=verifier(); d=docs(v)
        target=next(x for x in d["catalog"]["challenges"] if x["id"]=="C45_DEPLOYMENT_SUPPORT_SHIFT")
        target["root_ids"]=[x for x in target["root_ids"] if x!=v.ROOT_ID]
        out=v.evaluate_documents(d["manifest"],d["profile"],d["catalog"],d["scope_batch_verify"],d["censoring_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R9_EXECUTION_PROPERTY_CHALLENGE_FAILED")

    def test_profile_trigger_loss_breaks_property_challenge(self):
        v=verifier(); d=docs(v)
        d["profile"]["escalation_triggers"]=[x for x in d["profile"]["escalation_triggers"] if x!="POPULATION_CONTEXT_OPERATOR_OR_TIME_TRANSPORT_GAP"]
        out=v.evaluate_documents(d["manifest"],d["profile"],d["catalog"],d["scope_batch_verify"],d["censoring_verify"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R9_EXECUTION_PROPERTY_CHALLENGE_FAILED")

if __name__=="__main__":
    unittest.main(verbosity=2)
