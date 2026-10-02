from __future__ import annotations
import copy,json,tempfile,unittest
from pathlib import Path
from canonical.runtime.cad_t0_post_refreeze_composition_guard_v2 import (
    evaluate,FREEZE,BINDING,OCR_RECEIPT,POP_RECEIPT
)

ROOT=Path(__file__).resolve().parents[2]

class CadPostRefreezeCompositionGuardV2Tests(unittest.TestCase):
    def test_live_repo_passes(self):
        out=evaluate(ROOT)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["prewave_route_ready_for_promotion_law"])
        self.assertFalse(out["execution_authority"])
        self.assertEqual(out["terminal_results_observed"],0)

    def fixture(self):
        names=[FREEZE,BINDING,OCR_RECEIPT,POP_RECEIPT]
        return {p:json.loads((ROOT/p).read_text(encoding="utf-8")) for p in names}

    def run_fixture(self,objs):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for rel,obj in objs.items():
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
            # binding hashes are content-addressed; repair the fixture's actual JSON blob refs
            import hashlib
            def blob(rel):
                raw=(root/rel).read_bytes()
                return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
            objs[BINDING]["candidate_freeze"]["blob_sha"]=blob(FREEZE)
            objs[BINDING]["population"]["independent_verification_blob_sha"]=blob(POP_RECEIPT)
            objs[BINDING]["ocr_bridge"]["verification_blob_sha"]=blob(OCR_RECEIPT)
            (root/BINDING).write_text(json.dumps(objs[BINDING],indent=2)+"\n",encoding="utf-8")
            return evaluate(root)

    def test_hidden_reference_visibility_fails_closed(self):
        f=self.fixture();f[BINDING]["evaluator"]["hidden_reference_candidate_visible"]=True
        out=self.run_fixture(f);self.assertFalse(out["pass"])
        self.assertIn("HIDDEN_REFERENCE_VISIBLE",out["errors"])

    def test_adaptive_selection_fails_closed(self):
        f=self.fixture();f[BINDING]["population"]["adaptive_selection"]=True
        out=self.run_fixture(f);self.assertFalse(out["pass"])
        self.assertIn("POPULATION_FAIL_CLOSED_FLAG_INVALID:adaptive_selection",out["errors"])

    def test_spent_task_promotion_fails_closed(self):
        f=self.fixture();f[BINDING]["fresh_evidence_policy"]["spent_external_task_role"]="PROMOTION"
        out=self.run_fixture(f);self.assertFalse(out["pass"])
        self.assertIn("SPENT_TASK_PROMOTION_LEAK",out["errors"])

    def test_receipt_status_must_be_independent_pass(self):
        f=self.fixture();f[POP_RECEIPT]["status"]="DRAFT"
        out=self.run_fixture(f);self.assertFalse(out["pass"])
        self.assertIn("POPULATION_RECEIPT_NOT_INDEPENDENT_PASS",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
