from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.p1_composite_proof_counterexample_audit_v1 import (
    evaluate,
    terminal_unfalsifiable_diagnosis_counterexample,
    v4_dropped_provenance_counterexample,
)

ROOT = Path(__file__).resolve().parents[2]
RECON = ROOT / "canonical/governance/P1_COMPOSITE_PROOF_ROLE_RECONCILIATION_V1.json"


class P1CompositeProofCounterexampleAuditTests(unittest.TestCase):
    def test_v4_drop_provenance_mutation_survives_current_scorer(self):
        out = v4_dropped_provenance_counterexample()
        self.assertTrue(out["counterexample_holds"], out)
        self.assertGreater(out["failed_check_receipt_lists_erased"], 0)
        self.assertEqual(out["candidate_supporting_receipts"], [])
        self.assertTrue(out["scorer_pass_after_mutation"])

    def test_terminal_unfalsifiable_diagnosis_mutation_survives_current_scorer(self):
        out = terminal_unfalsifiable_diagnosis_counterexample()
        self.assertTrue(out["counterexample_holds"], out)
        self.assertTrue(out["baseline_pass"])
        self.assertTrue(out["scorer_pass_after_mutation"])
        self.assertFalse(out["mutated_diagnosis"]["falsifiable"])

    def test_live_composite_restoration_stays_quarantined(self):
        out = evaluate()
        self.assertTrue(out["audit_valid"], out)
        self.assertFalse(out["candidate_composite_restoration_admissible"])
        self.assertFalse(out["whole_p1_contract_restored"])
        self.assertEqual(out["terminal_results_replayed"], 0)
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertFalse(out["promotion_authority"])

    def test_reconciliation_role_drift_fails_closed(self):
        doc = json.loads(RECON.read_text(encoding="utf-8"))
        doc = copy.deepcopy(doc)
        doc["mutation_roles"]["T0_T2_TERMINAL_INTERVENTION_RESCUE"].remove(
            "UNFALSIFIABLE_DIAGNOSIS"
        )
        out = evaluate(doc)
        self.assertFalse(out["audit_valid"])
        self.assertIn(
            "EXPECTED_UNFALSIFIABLE_DIAGNOSIS_NOT_ASSIGNED_TO_TERMINAL",
            out["errors"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
