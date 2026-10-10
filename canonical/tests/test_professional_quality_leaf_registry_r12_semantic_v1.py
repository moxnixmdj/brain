from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_leaf_binder_v2 as binder


ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/"canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261011_V3.json"
R12_SEM="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"


class Tests(unittest.TestCase):
    def evaluate(self, registry_path=REG):
        return binder.evaluate(registry_path=registry_path,repo_root=ROOT)

    def test_successor_registry_derives_thirteen_of_twenty_four(self):
        out=self.evaluate()
        self.assertTrue(out["existing_evidence_current"],out)
        self.assertEqual(out["structural_errors"],[])
        self.assertEqual(out["rejected_receipt_count"],0)
        self.assertEqual(len(out["verified_execution_leaf_ids"]),12)
        self.assertEqual(out["verified_semantic_leaf_ids"],[R12_SEM])
        self.assertEqual(out["verified_leaf_count"],13)
        self.assertEqual(out["open_leaf_count"],11)
        self.assertEqual(len(out["open_semantic_leaf_ids"]),11)
        self.assertEqual(out["open_execution_leaf_ids"],[])
        self.assertFalse(out["promotion_ready"])
        self.assertFalse(out["pass"])
        self.assertFalse(out["terminal_authority"])

    def test_r12_semantic_receipt_is_actually_admitted(self):
        out=self.evaluate()
        rows=[x for x in out["receipt_results"] if x["leaf_id"]==R12_SEM]
        self.assertEqual(len(rows),1,rows)
        self.assertTrue(rows[0]["admitted"],rows[0])
        self.assertEqual(rows[0]["errors"],[])

    def test_receipt_blob_drift_reopens_r12_semantic_leaf(self):
        d=json.loads(REG.read_text(encoding="utf-8"))
        d["leaf_receipts"][R12_SEM][0]["git_blob_sha"]="0"*40
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"registry.json"
            p.write_text(json.dumps(d),encoding="utf-8")
            out=self.evaluate(p)
        self.assertNotIn(R12_SEM,out["verified_semantic_leaf_ids"])
        self.assertIn(R12_SEM,out["open_semantic_leaf_ids"])
        rows=[x for x in out["receipt_results"] if x["leaf_id"]==R12_SEM]
        self.assertEqual(len(rows),1)
        self.assertFalse(rows[0]["admitted"])
        self.assertIn("RECEIPT_FILE_NOT_CURRENT",rows[0]["errors"])

    def test_one_semantic_leaf_does_not_promote_professional_quality(self):
        out=self.evaluate()
        self.assertEqual(out["verified_leaf_count"],13)
        self.assertFalse(out["promotion_ready"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
