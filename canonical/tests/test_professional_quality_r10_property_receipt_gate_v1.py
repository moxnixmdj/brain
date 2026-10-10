from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
MODULE=ROOT/"canonical/runtime/professional_quality_r10_property_receipt_gate_v1.py"
CLAIM_ID="205a864e7d7a56a14a46bb75923cc9b11126d479676d26d88803831da1197294"
LEAF_ID="PQ::R10_ANALYSIS_DECISION::EXECUTION"
SLOTS=(
    "target_and_hard_constraints_frozen",
    "decision_state_lossless",
    "uncertainty_semantics_typed",
    "aggregation_and_risk_policy_precommitted",
    "veto_constraints_preserved",
    "model_or_analysis_multiplicity_resolved_or_escalated",
    "evidence_packet_complete",
    "stopping_rule_precommitted",
    "absolute_floor_not_inferred_from_weak_baseline",
)

def git_blob(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def sha256_json(value)->str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(raw).hexdigest()

def load_gate():
    if not MODULE.is_file():
        raise AssertionError("R10 property receipt gate runtime is missing")
    spec=importlib.util.spec_from_file_location("r10_property_gate",MODULE)
    mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod

def make_slot(root:Path,slot_id:str,*,verifier_pass=True,receipt_mutator=None):
    ev=root/"evidence"/f"{slot_id}.json"
    vr=root/"verifiers"/f"{slot_id}.py"
    rr=root/"receipts"/f"{slot_id}.json"
    ev.parent.mkdir(parents=True,exist_ok=True)
    vr.parent.mkdir(parents=True,exist_ok=True)
    rr.parent.mkdir(parents=True,exist_ok=True)
    ev.write_text(json.dumps({"claim_id":CLAIM_ID,"leaf_id":LEAF_ID,"slot_id":slot_id}),encoding="utf-8")
    vr.write_text(
        "def verify_property(*, root, evidence_path, claim_id, leaf_id, slot_id):\n"
        f"    return {{'pass': {verifier_pass!r}, 'claim_id': claim_id, 'leaf_id': leaf_id, 'slot_id': slot_id, 'fact': 'checked'}}\n",
        encoding="utf-8",
    )
    rerun={"pass":verifier_pass,"claim_id":CLAIM_ID,"leaf_id":LEAF_ID,"slot_id":slot_id,"fact":"checked"}
    evref={"path":str(ev.relative_to(root)),"git_blob_sha":git_blob(ev)}
    vrref={"path":str(vr.relative_to(root)),"git_blob_sha":git_blob(vr)}
    receipt={
        "schema":"PROJECT_BRAIN_PROFESSIONAL_R10_PROPERTY_EVIDENCE_RECEIPT_V1",
        "status":"PASS__INDEPENDENT_R10_PROPERTY_EVIDENCE",
        "pass":True,
        "verifier_protocol":"PROFESSIONAL_R10_PROPERTY_EVIDENCE_VERIFIER_V1",
        "independent":True,
        "property_claim_verified":True,
        "claim_id":CLAIM_ID,
        "leaf_id":LEAF_ID,
        "slot_id":slot_id,
        "proof_mode":"INDEPENDENT_REPLAY",
        "evidence":dict(evref),
        "semantic_verifier":dict(vrref),
        "verifier_result_sha256":sha256_json(rerun),
        "errors":[],
        "terminal_credit_delta":0,
    }
    if receipt_mutator:
        receipt_mutator(receipt)
    rr.write_text(json.dumps(receipt),encoding="utf-8")
    return {
        "slot_id":slot_id,
        "status":"PROVED_CURRENT",
        "evidence":evref,
        "semantic_verifier":vrref,
        "independent_verification":{"path":str(rr.relative_to(root)),"git_blob_sha":git_blob(rr)},
    }

class R10PropertyReceiptGateV1Tests(unittest.TestCase):
    def structural(self):
        return {
            "pass":True,
            "structural_policy_compliance_only":True,
            "underlying_fact_truth_authority":False,
            "whole_leaf_property_truth_proved":False,
            "claim_id":CLAIM_ID,
            "leaf_id":LEAF_ID,
            "slot_results":{s:True for s in SLOTS},
        }

    def test_structural_pass_without_receipts_stays_open(self):
        gate=load_gate()
        out=gate.evaluate(
            repo_root=ROOT,
            claim_id=CLAIM_ID,
            structural_verdict=self.structural(),
            property_slots={},
            detection_completeness_slot=None,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(set(out["missing_property_receipt_slots"]),set(SLOTS))
        self.assertFalse(out["detection_completeness_proved"])
        self.assertFalse(out["whole_leaf_property_truth_proved"])

    def test_all_receipts_plus_detection_can_prove_bounded_property(self):
        gate=load_gate()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            slots={s:make_slot(root,s) for s in SLOTS}
            detection=make_slot(root,"DEFEATER_DETECTION_COMPLETENESS")
            out=gate.evaluate(
                repo_root=root,
                claim_id=CLAIM_ID,
                structural_verdict=self.structural(),
                property_slots=slots,
                detection_completeness_slot=detection,
            )
            self.assertTrue(out["pass"],out)
            self.assertTrue(out["detection_completeness_proved"])
            self.assertTrue(out["whole_leaf_property_truth_proved"])
            self.assertFalse(out["quality_authority"])
            self.assertFalse(out["terminal_authority"])

    def test_hash_shaped_but_missing_receipt_fails(self):
        gate=load_gate()
        slot={
            "slot_id":SLOTS[0],
            "status":"PROVED_CURRENT",
            "evidence":{"path":"missing.json","git_blob_sha":"a"*40},
            "semantic_verifier":{"path":"missing.py","git_blob_sha":"b"*40},
            "independent_verification":{"path":"missing.receipt.json","git_blob_sha":"c"*40},
        }
        out=gate.evaluate(
            repo_root=ROOT,
            claim_id=CLAIM_ID,
            structural_verdict=self.structural(),
            property_slots={SLOTS[0]:slot},
            detection_completeness_slot=None,
        )
        self.assertFalse(out["pass"])
        self.assertIn("EVIDENCE_FILE_MISSING",out["property_slot_results"][SLOTS[0]]["errors"])

    def test_stored_pass_cannot_override_verifier_rejection(self):
        gate=load_gate()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            slot=make_slot(root,SLOTS[0],verifier_pass=False)
            out=gate.evaluate(
                repo_root=root,
                claim_id=CLAIM_ID,
                structural_verdict=self.structural(),
                property_slots={SLOTS[0]:slot},
                detection_completeness_slot=None,
            )
            self.assertFalse(out["pass"])
            self.assertIn("SEMANTIC_VERIFIER_REJECTED_EVIDENCE",out["property_slot_results"][SLOTS[0]]["errors"])

    def test_foreign_claim_receipt_fails(self):
        gate=load_gate()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            slot=make_slot(root,SLOTS[0],receipt_mutator=lambda r:r.__setitem__("claim_id","0"*64))
            out=gate.evaluate(
                repo_root=root,
                claim_id=CLAIM_ID,
                structural_verdict=self.structural(),
                property_slots={SLOTS[0]:slot},
                detection_completeness_slot=None,
            )
            self.assertFalse(out["pass"])
            self.assertIn("RECEIPT_CLAIM_MISMATCH",out["property_slot_results"][SLOTS[0]]["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
