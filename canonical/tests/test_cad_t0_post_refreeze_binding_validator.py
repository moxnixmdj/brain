from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime.cad_t0_post_refreeze_binding_validator import BINDING,FREEZE,POP_RECEIPT,OCR_RECEIPT,validate

class CadT0PostRefreezeBindingValidatorTests(unittest.TestCase):
    def test_live_repo_passes(self):
        root=Path(__file__).resolve().parents[2]
        out=validate(root)
        self.assertTrue(out["pass"],out)
        self.assertGreater(out["dependency_cone_count"],0)
        self.assertEqual(out["terminal_results_observed"],0)
        self.assertFalse(out["execution_authority"])

    def test_candidate_freeze_drift_fails_closed(self):
        root=Path(__file__).resolve().parents[2]
        files={rel:(root/rel).read_text() for rel in (BINDING,FREEZE,POP_RECEIPT,OCR_RECEIPT)}
        freeze=json.loads(files[FREEZE])
        first=next(iter(freeze["exact_cad_dependency_cone"]))
        freeze["exact_cad_dependency_cone"][first]="0"*40
        with tempfile.TemporaryDirectory() as td:
            shadow=Path(td)
            for rel,raw in files.items():
                p=shadow/rel;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(json.dumps(freeze) if rel==FREEZE else raw)
            out=validate(shadow)
        self.assertFalse(out["pass"])

    def test_spent_task_promotion_is_rejected(self):
        root=Path(__file__).resolve().parents[2]
        data=json.loads((root/BINDING).read_text())
        data["fresh_evidence_policy"]["spent_external_task_role"]="PROMOTION"
        with tempfile.TemporaryDirectory() as td:
            shadow=Path(td)
            # This shadow is intentionally incomplete; the policy error must survive fail-closed.
            for rel in (BINDING,FREEZE,POP_RECEIPT,OCR_RECEIPT):
                src=(root/rel).read_text()
                p=shadow/rel;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(json.dumps(data) if rel==BINDING else src)
            out=validate(shadow)
        self.assertFalse(out["pass"])
        self.assertIn("SPENT_TASK_POLICY_INVALID",out["errors"])

if __name__=="__main__":
    unittest.main()
