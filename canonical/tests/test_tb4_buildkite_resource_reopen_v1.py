from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.tb4_buildkite_resource_reopen_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]
CUT = ROOT / "canonical/governance/TB4_MINIMUM_CARRIER_RECOVERY_CUT_V1.json"
RECEIPT = ROOT / "canonical/verification/BUILDKITE_ZERO_CASE_RUNTIME_RECEIPT_20261006_V1.json"

class Tests(unittest.TestCase):
    def docs(self):
        return json.loads(CUT.read_text()), json.loads(RECEIPT.read_text())

    def test_current_buildkite_receipt_binds_resource_envelope_only(self):
        cut, receipt = self.docs()
        out = evaluate(cut, receipt)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["resource_envelope_bound"])
        self.assertEqual(out["current_upper_bound_successes"], 180)
        self.assertEqual(out["projected_upper_bound_successes_if_eight_bind"], 220)
        self.assertEqual(out["required_successes"], 220)
        self.assertFalse(out["zero_cost_hard_stop_bound"])
        self.assertFalse(out["task_identity_bound"])
        self.assertFalse(out["protocol_equivalence_bound"])
        self.assertFalse(out["full_attainability_route_reopened"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_memory_shortfall_fails_closed(self):
        cut, receipt = self.docs()
        receipt = copy.deepcopy(receipt)
        receipt["measured_runtime"]["mem_total_kb"] = 16000 * 1024
        out = evaluate(cut, receipt)
        self.assertFalse(out["pass"])
        self.assertIn("MEMORY_ENVELOPE_NOT_MET", out["errors"])

    def test_terminal_case_consumption_fails_closed(self):
        cut, receipt = self.docs()
        receipt = copy.deepcopy(receipt)
        receipt["accounting"]["terminal_cases_consumed"] = 1
        out = evaluate(cut, receipt)
        self.assertFalse(out["pass"])
        self.assertIn("TERMINAL_CASES_CONSUMED", out["errors"])

    def test_wrong_shape_fails_closed(self):
        cut, receipt = self.docs()
        receipt = copy.deepcopy(receipt)
        receipt["provider_execution"]["queue"]["instance_shape"] = "LINUX_AMD64_4X16"
        out = evaluate(cut, receipt)
        self.assertFalse(out["pass"])
        self.assertIn("WRONG_INSTANCE_SHAPE", out["errors"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
