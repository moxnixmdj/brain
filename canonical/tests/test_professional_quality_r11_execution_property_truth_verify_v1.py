from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r11_execution_property_truth_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def docs():
    out={}
    for key in (
        "manifest","profile","catalog","root_binding_verify",
        "firewall_scoped_verify","scope_batch_verify",
    ):
        rel,_=v.PINS[key]
        out[key]=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    return out

def evaluate(d):
    return v.evaluate_documents(
        d["manifest"],d["profile"],d["catalog"],d["root_binding_verify"],
        d["firewall_scoped_verify"],d["scope_batch_verify"],
    )

class R11ExecutionPropertyTruthV1Tests(unittest.TestCase):
    def test_real_exact_bound_r11_execution_acceptance_passes_one_leaf_only(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["leaf_property_truth_authority"])
        self.assertEqual(out["observed_case_counts"]["total"],44)
        self.assertFalse(out["detection_completeness_proved"])
        self.assertFalse(out["r11_semantic_leaf_closed"])
        self.assertFalse(out["r11_root_closed"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_manifest_acceptance_drift_fails_closed(self):
        d=docs()
        row=next(x for x in d["manifest"]["roots"] if x["root_id"]==v.ROOT_ID)
        row["execution_leaf"]["acceptance"]="WEAKER_ACCEPTANCE"
        out=evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R11_EXECUTION_ACCEPTANCE_DRIFT")

    def test_scope_batch_must_remain_24_of_24(self):
        d=docs()
        d["scope_batch_verify"]["independent_replay"]["scope_complete_count"]=23
        out=evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"WHOLE_LEAF_SCOPE_BATCH_NOT_COMPLETE")

    def test_root_subject_binding_authority_required(self):
        d=docs()
        d["root_binding_verify"]["root_subject_binding_authority"]=False
        out=evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R11_ROOT_SUBJECT_BINDING_NOT_AUTHORITATIVE")

    def test_firewall_scoped_receipt_cannot_overclaim_leaf_credit(self):
        d=docs()
        d["firewall_scoped_verify"]["current_state"]["global_leaf_credit"]=True
        out=evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R11_FIREWALL_SCOPED_VERIFY_OVERCLAIMS")

    def test_catalog_loss_breaks_property_challenge(self):
        d=docs()
        rows=d["catalog"].get("defeaters") or d["catalog"].get("attack_classes") or d["catalog"].get("nodes") or d["catalog"].get("challenges")
        target=next(x for x in rows if x.get("id")=="C53_PROMPT_INJECTION_JUDGE_CONTROL")
        field="root_ids" if isinstance(target.get("root_ids"),list) else "target_root_ids"
        target[field]=[x for x in target[field] if x!=v.ROOT_ID]
        out=evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R11_EXECUTION_PROPERTY_CHALLENGE_FAILED")

    def test_missing_adaptive_trigger_breaks_property_challenge(self):
        d=docs()
        d["profile"]["escalation_triggers"]=[
            x for x in d["profile"]["escalation_triggers"]
            if x!="ADAPTIVE_CONTAMINATION_OR_HOLDOUT_EXPOSURE"
        ]
        out=evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"R11_EXECUTION_PROPERTY_CHALLENGE_FAILED")

    def test_claim_substitution_breaks_guard_directly(self):
        d=docs()
        out=v._guard(d["profile"],d["catalog"],claim_id="0"*64)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"CLAIM_ID_MISMATCH")

if __name__=="__main__":
    unittest.main(verbosity=2)
