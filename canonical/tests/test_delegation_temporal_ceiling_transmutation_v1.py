from __future__ import annotations
import json
import unittest
from pathlib import Path

from canonical.runtime.acceptance_proof_transmuter_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class DelegationTemporalCeilingTransmutationTests(unittest.TestCase):
    def setUp(self):
        self.protocols = load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
        self.input = load("canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json")
        self.witness = load("canonical/governance/DELEGATION_ACCEPTANCE_CEILING_WITNESS_V1.json")
        self.transport_verification = load(
            "canonical/verification/DELEGATION_TEMPORAL_PROOF_TRANSPORT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
        )

    def row(self, out, family):
        return next(r for r in out["families"] if r["family"] == family)

    def test_historical_delegation_transport_remains_verified_but_current_protocol_is_already_pass(self):
        self.assertIn("INDEPENDENT_PUBLIC_RUNNER_PASS", self.transport_verification["status"])
        self.assertTrue(self.witness["verified"])
        self.assertTrue(self.witness["independent"])

        out = evaluate(self.protocols, self.input)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(
            (out["family_count"], out["closed_family_count"], out["open_family_count"]),
            (19, 4, 15),
        )

        closed = {r["family"] for r in out["families"] if r["result_status"] == "PASS"}
        self.assertEqual(
            closed,
            {
                "EXACT_SYMBOLIC_COMPUTATION",
                "LONG_HORIZON_MEMORY_AND_CONTINUITY",
                "SUBAGENT_DELEGATION_AND_COORDINATION",
                "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
            },
        )

        delegation = self.row(out, "SUBAGENT_DELEGATION_AND_COORDINATION")
        self.assertEqual(delegation["closure_mode"], "ALREADY_PASS")
        self.assertIsNone(delegation["witness_id"])

        recovery = self.row(out, "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")
        self.assertEqual(recovery["closure_mode"], "ABSOLUTE_DOMINANCE")
        self.assertEqual(recovery["witness_id"], "RECOVERY_UNIVERSAL_SCOPE_OBJECTIVE_BOUND_20261003_V2")

        tool_discovery = self.row(out, "TOOL_DISCOVERY_SELECTION_AND_LEARNING")
        self.assertEqual(tool_discovery["result_status"], "DEFINED_RESULT_OPEN")

    def test_removing_recovery_witness_returns_to_three_of_nineteen_without_reopening_delegation(self):
        x = json.loads(json.dumps(self.input))
        x["evidence"] = [
            e for e in x["evidence"]
            if e["family"] != "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"
        ]
        out = evaluate(self.protocols, x)
        self.assertEqual((out["closed_family_count"], out["open_family_count"]), (3, 16))
        self.assertEqual(
            self.row(out, "SUBAGENT_DELEGATION_AND_COORDINATION")["result_status"],
            "PASS",
        )
        self.assertEqual(
            self.row(out, "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")["result_status"],
            "DEFINED_RESULT_OPEN",
        )

    def test_tool_discovery_is_not_reintroduced_by_historical_delegation_transport(self):
        out = evaluate(self.protocols, self.input)
        row = self.row(out, "TOOL_DISCOVERY_SELECTION_AND_LEARNING")
        self.assertEqual(row["result_status"], "DEFINED_RESULT_OPEN")
        self.assertIsNone(row["witness_id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
