from __future__ import annotations
import copy
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

    def test_exact_live_integration_closes_delegation_as_fourth_family(self):
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
                "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
                "SUBAGENT_DELEGATION_AND_COORDINATION",
            },
        )
        row = self.row(out, "SUBAGENT_DELEGATION_AND_COORDINATION")
        self.assertEqual(row["closure_mode"], "ABSOLUTE_DOMINANCE")
        self.assertEqual(
            row["witness_id"],
            "DELEGATION_TEMPORAL_TERMINAL_CEILING_ABSOLUTE_DOMINANCE_20261002_V1",
        )
        self.assertEqual(row["witness_reason"], "THEORETICAL_CEILING_DOMINANCE")

    def test_remove_delegation_witness_reverts_to_three_of_nineteen(self):
        x = copy.deepcopy(self.input)
        x["evidence"] = [
            e for e in x["evidence"]
            if e["family"] != "SUBAGENT_DELEGATION_AND_COORDINATION"
        ]
        out = evaluate(self.protocols, x)
        self.assertEqual((out["closed_family_count"], out["open_family_count"]), (3, 16))
        self.assertEqual(
            self.row(out, "SUBAGENT_DELEGATION_AND_COORDINATION")["result_status"],
            "DEFINED_RESULT_OPEN",
        )

    def test_weaken_full_protocol_flag_reverts_delegation_to_open(self):
        x = copy.deepcopy(self.input)
        d = next(e for e in x["evidence"] if e["family"] == "SUBAGENT_DELEGATION_AND_COORDINATION")
        d["closes_entire_protocol"] = False
        out = evaluate(self.protocols, x)
        self.assertEqual((out["closed_family_count"], out["open_family_count"]), (3, 16))
        row = self.row(out, "SUBAGENT_DELEGATION_AND_COORDINATION")
        self.assertEqual(row["result_status"], "DEFINED_RESULT_OPEN")
        reasons = [reason for rej in row["rejections"] for reason in rej["reasons"]]
        self.assertIn("DOES_NOT_CLOSE_ENTIRE_PROTOCOL", reasons)

    def test_unverified_witness_reverts_delegation_to_open(self):
        x = copy.deepcopy(self.input)
        d = next(e for e in x["evidence"] if e["family"] == "SUBAGENT_DELEGATION_AND_COORDINATION")
        d["verified"] = False
        out = evaluate(self.protocols, x)
        self.assertEqual((out["closed_family_count"], out["open_family_count"]), (3, 16))
        reasons = [
            reason
            for rej in self.row(out, "SUBAGENT_DELEGATION_AND_COORDINATION")["rejections"]
            for reason in rej["reasons"]
        ]
        self.assertIn("NOT_VERIFIED", reasons)


if __name__ == "__main__":
    unittest.main(verbosity=2)
