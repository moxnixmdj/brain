from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ACT = ROOT / "canonical/governance/P1_COMPOSITE_PROOF_RESTORATION_ACTIVATION_V2.json"
BIND = ROOT / "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
RAW = ROOT / "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"
READJ = ROOT / "canonical/verification/P1_COMPOSITE_PROOF_READJUDICATION_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class P1CompositeProofRestorationActivationV2Tests(unittest.TestCase):
    def test_exact_frozen_contract_counts_and_partition(self):
        act = load(ACT)
        binding = load(BIND)
        evaluator = binding["evaluator"]
        self.assertEqual(len(evaluator["required_checks"]), 8)
        self.assertEqual(len(evaluator["required_mutations"]), 9)
        self.assertEqual(act["proof_join"]["complete_required_check_count"], 8)
        self.assertEqual(act["proof_join"]["complete_required_mutation_count"], 9)
        self.assertTrue(act["proof_join"]["check_partition_exact"])
        self.assertTrue(act["proof_join"]["mutation_partition_exact"])

    def test_independent_readjudication_repairs_all_predeclared_mutations(self):
        act = load(ACT)
        readj = load(READJ)
        self.assertTrue(readj["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"), readj)
        self.assertIn("ALL_NINE_REQUIRED_MUTATIONS_ARE_EXECUTABLY_KILLED", readj["verified"])
        self.assertIn("ZERO_TERMINAL_V3_REPLAY", readj["verified"])
        self.assertEqual(act["proof_join"]["predeclared_v4_role"]["existing_cross_product_cases"], 168)
        self.assertEqual(act["proof_join"]["predeclared_v4_role"]["strict_readjudication_failures"], 0)
        self.assertEqual(act["proof_join"]["predeclared_v4_role"]["assigned_mutations_killed"], 6)
        self.assertEqual(act["proof_join"]["frozen_terminal_role"]["assigned_mutations_killed"], 3)

    def test_preserved_terminal_t0_t2_receipts_match_exact_p1_binding(self):
        act = load(ACT)
        raw = load(RAW)
        receipts = raw["reduction_input"]["wave"]["parent_portfolio_receipts"]
        for portfolio in ("T0", "T2"):
            rows = [
                row for row in receipts[portfolio]
                if row["behavior_id"] == "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
            ]
            self.assertEqual(len(rows), 1, (portfolio, rows))
            row = rows[0]
            self.assertEqual(row["binding_blob"], "8703c6aa08227467a619a7ae90d0d61f8e54da39")
            self.assertEqual(row["case_id"], f"{portfolio}::TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001::aggregate::30")
            self.assertTrue(row["direct_instrumentation_pass"], row)
            self.assertTrue(row["parent_terminal_acceptance_pass"], row)
            self.assertTrue(row["load_bearing"], row)
            self.assertFalse(row["case_replaced"], row)
            self.assertFalse(row["tuning_replay"], row)
            self.assertFalse(row["result_to_runtime_feedback"], row)
        terminal = act["proof_join"]["frozen_terminal_role"]
        self.assertEqual(terminal["t0_p1_aggregate_cases"], 30)
        self.assertEqual(terminal["t2_p1_aggregate_cases"], 30)
        self.assertTrue(terminal["t0_direct_instrumentation_pass"])
        self.assertTrue(terminal["t2_direct_instrumentation_pass"])
        self.assertTrue(terminal["t0_parent_terminal_acceptance_pass"])
        self.assertTrue(terminal["t2_parent_terminal_acceptance_pass"])
        self.assertFalse(terminal["terminal_v3_replayed"])

    def test_restoration_is_contract_only_not_opus_acceptance(self):
        act = load(ACT)
        disp = act["quarantine_disposition_candidate"]
        self.assertEqual(
            disp["WHOLE_FROZEN_P1_CONTRACT_PASS"],
            "RESTORE_AFTER_INDEPENDENT_PROJECTION_VERIFICATION",
        )
        self.assertEqual(
            disp["POSTWAVE_12_OF_12_WHOLE_CONTRACT_CLAIM"],
            "RESTORE_AFTER_INDEPENDENT_PROJECTION_VERIFICATION",
        )
        self.assertEqual(
            disp["P1_WITNESS_TRANSPORT_INTO_RECOVERY_ACCEPTANCE"],
            "REMAINS_SEPARATE__NO_AUTOMATIC_TRANSPORT",
        )
        self.assertEqual(act["opus55_predicate_credit_delta"], 0)
        self.assertEqual(act["capability_credit_delta"], 0)
        self.assertEqual(act["family_credit_delta"], 0)
        self.assertFalse(act["promotion_authority"])
        self.assertFalse(act["execution_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
