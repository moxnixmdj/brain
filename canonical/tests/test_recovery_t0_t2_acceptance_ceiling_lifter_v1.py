from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.recovery_t0_t2_acceptance_ceiling_lifter_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads((ROOT / path).read_text())


def live_inputs():
    return {
        "protocols": load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
        "registry": load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
        "predicates": load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
        "basis": load("canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json"),
        "binding": load("canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"),
        "terminal": load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
        "relation": load("canonical/governance/RECOVERY_T0_T2_ACCEPTANCE_SCOPE_RELATION_V1.json"),
    }


class RecoveryCeilingLifterTests(unittest.TestCase):
    def test_live_candidate_is_zero_credit_and_covers_all_three_predicates(self):
        out = evaluate(**live_inputs())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["source_case_count"], 60)
        self.assertFalse(out["candidate_witness"]["verified"])
        self.assertFalse(out["candidate_witness"]["independent"])
        self.assertEqual(
            set(out["candidate_witness"]["covered_atomic_predicates"]),
            {
                "RECOVERY_TERMINAL_NONINFERIOR",
                "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
                "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
            },
        )
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)

    def test_missing_terminal_recovery_target_fails_closed(self):
        x = live_inputs()
        x["relation"] = copy.deepcopy(x["relation"])
        x["relation"]["target_atomic_predicates"].remove("RECOVERY_TERMINAL_NONINFERIOR")
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("RELATION_ATOMIC_TARGET_SET_INCOMPLETE", out["errors"])

    def test_execution_snapshot_route_must_have_been_prewave_admissible(self):
        x = live_inputs()
        x["basis"] = copy.deepcopy(x["basis"])
        row = next(
            r for r in x["basis"]["contracts"]
            if r["behavior_id"] == "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
        )
        row["prewave_admissible"] = False
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("EXECUTION_BASIS_PREWAVE_ADMISSION_MISSING", out["errors"])

    def test_separate_terminal_and_causal_predicates_are_both_required(self):
        x = live_inputs()
        x["predicates"] = copy.deepcopy(x["predicates"])
        x["predicates"]["predicates"] = [
            r for r in x["predicates"]["predicates"]
            if r["id"] != "RECOVERY_TERMINAL_NONINFERIOR"
        ]
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn(
            "RECOVERY_PREDICATE_MISSING:RECOVERY_TERMINAL_NONINFERIOR",
            out["errors"],
        )

    def test_contaminated_parent_receipt_fails_closed(self):
        x = live_inputs()
        x["terminal"] = copy.deepcopy(x["terminal"])
        rows = x["terminal"]["reduction_input"]["wave"]["parent_portfolio_receipts"]["T0"]
        row = next(r for r in rows if r["behavior_id"] == "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001")
        row["tuning_replay"] = True
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("RECOVERY_RECEIPT_CONTAMINATED:T0", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
