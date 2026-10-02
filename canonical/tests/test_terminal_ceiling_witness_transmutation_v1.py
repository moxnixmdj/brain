from __future__ import annotations
import copy, json, unittest
from pathlib import Path
from canonical.runtime.acceptance_proof_transmuter_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]

def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

class Tests(unittest.TestCase):
    def setUp(self):
        self.protocols = load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
        self.input = load("canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json")
        self.witness = load("canonical/governance/TOOL_DISCOVERY_ACCEPTANCE_CEILING_WITNESS_V1.json")
        self.verification = load("canonical/verification/TERMINAL_CEILING_WITNESS_LIFTER_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")

    def row(self, out, family):
        return next(r for r in out["families"] if r["family"] == family)

    def test_exact_live_integration_closes_only_tool_discovery(self):
        self.assertEqual(self.verification["status"], "INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_8_BRAIN_BLOBS__5_LIFTER_TESTS_PASS__ZERO_CREDIT")
        self.assertTrue(self.witness["verified"])
        self.assertTrue(self.witness["independent"])
        out = evaluate(self.protocols, self.input)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual((out["family_count"], out["closed_family_count"], out["open_family_count"]), (19, 3, 16))
        closed = {r["family"] for r in out["families"] if r["result_status"] == "PASS"}
        self.assertEqual(closed, {
            "EXACT_SYMBOLIC_COMPUTATION",
            "LONG_HORIZON_MEMORY_AND_CONTINUITY",
            "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
        })
        row = self.row(out, "TOOL_DISCOVERY_SELECTION_AND_LEARNING")
        self.assertEqual(row["closure_mode"], "ABSOLUTE_DOMINANCE")
        self.assertEqual(row["witness_id"], "TOOL_DISCOVERY_TERMINAL_CEILING_ABSOLUTE_DOMINANCE_20261002_V1")
        self.assertEqual(row["witness_reason"], "THEORETICAL_CEILING_DOMINANCE")

    def test_remove_full_protocol_flag_reverts_to_2_of_19(self):
        x = copy.deepcopy(self.input)
        x["evidence"][0]["closes_entire_protocol"] = False
        out = evaluate(self.protocols, x)
        self.assertEqual((out["closed_family_count"], out["open_family_count"]), (2, 17))
        row = self.row(out, "TOOL_DISCOVERY_SELECTION_AND_LEARNING")
        self.assertEqual(row["result_status"], "DEFINED_RESULT_OPEN")
        self.assertIn("DOES_NOT_CLOSE_ENTIRE_PROTOCOL", row["rejections"][0]["reasons"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
