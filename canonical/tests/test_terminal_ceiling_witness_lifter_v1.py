from __future__ import annotations
import json
import unittest
from pathlib import Path
from canonical.runtime.terminal_ceiling_witness_lifter_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class Tests(unittest.TestCase):
    def live(self):
        return dict(
            family="TOOL_DISCOVERY_SELECTION_AND_LEARNING",
            behavior_id="TOOL_ROUTE_DISCOVERY_AND_SELECTION_001",
            binding_path="canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json",
            protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
            registry=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
            binding=load("canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"),
            executor_manifest=load("canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json"),
            terminal_result=load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
        )

    def test_live_tool_discovery_candidate_is_ceiling(self):
        out = evaluate(**self.live())
        self.assertTrue(out["pass"], out)
        w = out["candidate_witness"]
        self.assertEqual(w["family"], "TOOL_DISCOVERY_SELECTION_AND_LEARNING")
        self.assertEqual(w["source_case_count"], 180)
        self.assertEqual(w["result"]["brain_lower_bound"], 1.0)
        self.assertEqual(w["result"]["theoretical_upper_bound"], 1.0)
        self.assertFalse(w["verified"])
        self.assertFalse(w["independent"])
        self.assertFalse(out["promotion_authority"])

    def test_population_mismatch_fails_closed(self):
        x = self.live()
        x["binding"] = json.loads(json.dumps(x["binding"]))
        x["binding"]["source_pool"]["terminal_sample_count"] = 181
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("FROZEN_POPULATION_COUNT_MISMATCH", out["errors"])

    def test_partial_family_mapping_fails_closed(self):
        x = self.live()
        x["registry"] = json.loads(json.dumps(x["registry"]))
        x["registry"]["family_to_residual_contracts"]["TOOL_DISCOVERY_SELECTION_AND_LEARNING"] = [
            "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001", "OTHER"
        ]
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("BEHAVIOR_NOT_EXACT_WHOLE_FAMILY_RESIDUAL", out["errors"])

    def test_one_failure_fails_closed(self):
        x = self.live()
        x["terminal_result"] = json.loads(json.dumps(x["terminal_result"]))
        x["terminal_result"]["direct_terminal_population"]["routes"]["TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"]["passes"] = 179
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("NOT_ALL_FROZEN_CASES_PASS", out["errors"])

    def test_missing_predeclared_comparator_deletion_intent_fails(self):
        x = self.live()
        x["binding"] = json.loads(json.dumps(x["binding"]))
        x["binding"]["purpose"] = "GENERAL_PREFLIGHT"
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("PREWAVE_COMPARATOR_DELETION_INTENT_MISSING", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
