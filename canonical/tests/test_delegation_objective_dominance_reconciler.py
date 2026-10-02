from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path

from canonical.runtime.delegation_objective_dominance_reconciler import (
    BINDING, BINDING_RECEIPT, LIVE_INPUT, reconcile,
)

class DelegationObjectiveDominanceReconcilerTests(unittest.TestCase):
    def test_live_repo_is_ready_for_promotion_law(self):
        root=Path(__file__).resolve().parents[2]
        out=reconcile(root)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["comparator_deletion_admissible"])
        self.assertTrue(out["prewave_route_ready_for_promotion_law"])
        self.assertEqual(out["terminal_results_observed"],0)
        self.assertFalse(out["execution_authority"])

    def test_missing_independent_receipt_fails_closed(self):
        root=Path(__file__).resolve().parents[2]
        live=(root/LIVE_INPUT).read_text()
        binding=(root/BINDING).read_text()
        with tempfile.TemporaryDirectory() as td:
            shadow=Path(td)
            for rel,raw in ((LIVE_INPUT,live),(BINDING,binding)):
                p=shadow/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(raw)
            out=reconcile(shadow)
        self.assertFalse(out["pass"])

    def test_dimension_drift_fails_closed(self):
        root=Path(__file__).resolve().parents[2]
        live=(root/LIVE_INPUT).read_text()
        binding=json.loads((root/BINDING).read_text())
        receipt=(root/BINDING_RECEIPT).read_text()
        binding["objective_dimensions"]=binding["objective_dimensions"][:-1]
        with tempfile.TemporaryDirectory() as td:
            shadow=Path(td)
            for rel,raw in (
                (LIVE_INPUT,live),
                (BINDING,json.dumps(binding)),
                (BINDING_RECEIPT,receipt),
            ):
                p=shadow/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(raw)
            out=reconcile(shadow)
        self.assertFalse(out["pass"])
        self.assertIn("OBJECTIVE_DIMENSION_BINDING_MISMATCH",out["errors"])

if __name__=="__main__":
    unittest.main()
