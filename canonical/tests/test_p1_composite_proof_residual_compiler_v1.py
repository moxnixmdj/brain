from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.p1_composite_proof_residual_compiler_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]

def j(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def s(path: str):
    return (ROOT / path).read_text(encoding="utf-8")

def live():
    return dict(
        binding=j("canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"),
        reconciliation=j("canonical/governance/P1_COMPOSITE_PROOF_ROLE_RECONCILIATION_V1.json"),
        v4_verification=j("canonical/verification/TRAJECTORY_TYPED_IR_V4_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
        v4_candidate_source=s("canonical/runtime/trajectory_failure_typed_ir_candidate_v4.py"),
        v4_proof_source=s("canonical/runtime/trajectory_failure_typed_ir_proof_v4.py"),
        v4_tests_source=s("canonical/tests/test_trajectory_failure_typed_ir_v4.py"),
        terminal_scope_audit=j("canonical/governance/P1_TERMINAL_EXECUTION_SCOPE_MISMATCH_QUARANTINE_V1.json").get("verification") and
            j("canonical/runtime/P1_TERMINAL_EXECUTION_SCOPE_AUDIT_RESULT_V1.json")
            if (ROOT / "canonical/runtime/P1_TERMINAL_EXECUTION_SCOPE_AUDIT_RESULT_V1.json").exists()
            else _audit_fixture(),
        terminal_suite_source=s("canonical/runtime/contract_native_proof_suites.py"),
    )

def _audit_fixture():
    # Canonical audit runtime is deterministic; fixture binds only its published result shape.
    return {
        "status": "FAIL_CLOSED__EXECUTED_P1_TERMINAL_INSTRUMENTATION_NARROWER_THAN_FROZEN_P1_BINDING",
        "scope_mismatch_proved": True,
        "executed_route": {
            "candidate_output_keys_scored": ["cause_step", "repair_id", "evidence_steps"]
        },
    }

class Tests(unittest.TestCase):
    def test_live_residual_is_exact_and_zero_credit(self):
        out = evaluate(**live())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["required_check_count"], 8)
        self.assertEqual(out["required_mutation_count"], 9)
        self.assertEqual(len(out["proved_checks"]), 6)
        self.assertEqual(len(out["open_checks"]), 2)
        self.assertEqual(len(out["proved_mutations"]), 4)
        self.assertEqual(len(out["open_mutations"]), 5)
        self.assertFalse(out["whole_p1_contract_restored"])
        self.assertFalse(out["recovery_transport_authorized"])
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)

    def test_scope_and_tool_state_remain_explicitly_open(self):
        out = evaluate(**live())
        row = out["partial_checks"][
            "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT"
        ]
        self.assertTrue(any("SCOPE_HAS_NO_EXPLICIT" in x for x in row))
        self.assertTrue(any("TOOL_STATE_HAS_NO_EXPLICIT" in x for x in row))

    def test_receipt_support_is_not_upgraded_from_unscored_field(self):
        out = evaluate(**live())
        row = out["partial_checks"][
            "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS"
        ]
        self.assertIn(
            "INDEPENDENT_V4_SCORER_DOES_NOT_VALIDATE_SUPPORTING_RECEIPTS_FIELD",
            row,
        )

    def test_partition_omission_fails_closed(self):
        x = live()
        x["reconciliation"] = copy.deepcopy(x["reconciliation"])
        x["reconciliation"]["proof_roles"]["V4_TYPED_CROSS_DOMAIN_PREFLIGHT"].pop()
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("PROPOSED_CHECK_PARTITION_NOT_EXACT", out["errors"])

    def test_fake_supporting_receipt_scorer_change_invalidates_residual_logic(self):
        x = live()
        x["v4_proof_source"] += '\ncandidate.get("supporting_receipts")\n'
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("V4_SCORER_SHAPE_UNEXPECTED__UPDATE_RESIDUAL_LOGIC", out["errors"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
