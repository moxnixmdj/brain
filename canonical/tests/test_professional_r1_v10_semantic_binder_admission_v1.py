from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_semantic_admission_binder_v3 as binder
from canonical.runtime import professional_semantic_v2_v10_claim_batch_v1 as claims


ROOT=Path(__file__).resolve().parents[2]
RECEIPT=ROOT/"canonical/verification/PROFESSIONAL_QUALITY_R1_V10_SEMANTIC_LEAF_RECEIPT_20261011_V1.json"
MANIFEST=ROOT/"canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261011_V2.json"
LEAF_ID="PQ::R1_TARGET_SPECIFICATION::SEMANTIC"
ROOT_ID="R1_TARGET_SPECIFICATION"
MANIFEST_BLOB="8ae72d7d44047ac9dec1b014c34a44f9933f0215"


def current():
    batch=claims.verify(root=ROOT)
    assert batch["pass"],batch
    rows=[r for r in batch["rows"] if r["leaf_id"]==LEAF_ID]
    assert len(rows)==1
    claim=rows[0]
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    mrows=[r for r in manifest["roots"] if r["root_id"]==ROOT_ID]
    assert len(mrows)==1
    return claim,mrows[0]


class Tests(unittest.TestCase):
    def validate(self,receipt):
        claim,mrow=current()
        return binder.validate_semantic_receipt(
            receipt,
            claim,
            leaf_id=LEAF_ID,
            root_id=ROOT_ID,
            acceptance=mrow["semantic_leaf"]["acceptance"],
            contract=mrow["contract"],
            manifest_git_blob_sha=MANIFEST_BLOB,
            repo_root=ROOT,
        )

    def test_exact_r1_receipt_is_admitted_by_unchanged_v3_binder(self):
        receipt=json.loads(RECEIPT.read_text(encoding="utf-8"))
        out=self.validate(receipt)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["positive_semantic_admission_authorized"])
        self.assertTrue(out["claim_scoped_totality_proved"])
        self.assertTrue(out["cc_r1_reality_containment_proved"])
        self.assertTrue(out["cc_r2_mission_soundness_proved"])
        self.assertTrue(out["cc_r3_terminal_closure_proved"])
        self.assertTrue(out["r4_proof_realization_authority"])
        self.assertFalse(out["semantic_leaf_property_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_missing_totality_premise_reopens_receipt(self):
        receipt=json.loads(RECEIPT.read_text(encoding="utf-8"))
        receipt["cc_r3_terminal_closure_proved"]=False
        out=self.validate(receipt)
        self.assertFalse(out["pass"])
        self.assertIn("CC_R3_TERMINAL_CLOSURE_PROVED_REQUIRED",out["errors"])

    def test_stale_basis_hash_reopens_receipt(self):
        receipt=json.loads(RECEIPT.read_text(encoding="utf-8"))
        receipt["verification_basis"][0]["git_blob_sha"]="0"*40
        out=self.validate(receipt)
        self.assertFalse(out["pass"])
        self.assertIn("VERIFICATION_BASIS_STALE",out["errors"])
        self.assertIn("INDEPENDENT_SEMANTIC_TOTALITY_BASIS_REQUIRED",out["errors"])

    def test_wrong_current_claim_id_reopens_receipt(self):
        receipt=json.loads(RECEIPT.read_text(encoding="utf-8"))
        receipt["semantic_claim_id"]="0"*64
        out=self.validate(receipt)
        self.assertFalse(out["pass"])
        self.assertIn("SEMANTIC_CLAIM_ID_MISMATCH",out["errors"])

    def test_global_authority_remains_zero_after_admission(self):
        receipt=json.loads(RECEIPT.read_text(encoding="utf-8"))
        out=self.validate(receipt)
        self.assertTrue(out["pass"],out)
        for key in (
            "semantic_leaf_property_truth_authority","quality_authority",
            "acceptance_authority","promotion_authority","terminal_authority",
        ):
            self.assertFalse(out[key],key)


if __name__=="__main__":
    unittest.main(verbosity=2)
