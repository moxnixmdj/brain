from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.parent_multiplex_terminal_ceiling_witness_lifter_v1 import (
    evaluate,
    git_blob_sha,
)

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class ParentMultiplexCeilingLifterTests(unittest.TestCase):
    def live(self):
        binding_path = "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
        return dict(
            family="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
            behavior_id="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
            binding_path=binding_path,
            binding_blob_sha=git_blob_sha(ROOT / binding_path),
            protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
            registry=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
            binding=load(binding_path),
            current_binding_verification=load(
                "canonical/verification/CURRENT_OBJECTIVE_BINDINGS_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json"
            ),
            executor_manifest=load(
                "canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json"
            ),
            terminal_result=load(
                "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"
            ),
        )

    def test_live_recovery_candidate_reaches_parent_multiplex_ceiling(self):
        out = evaluate(**self.live())
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "CANDIDATE_WITNESS_READY__INDEPENDENT_VERIFICATION_REQUIRED",
        )
        w = out["candidate_witness"]
        self.assertEqual(w["family"], "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")
        self.assertEqual(w["source_case_count"], 60)
        self.assertEqual(w["source_portfolios"], ["T0", "T2"])
        self.assertEqual(w["result"]["brain_lower_bound"], 1.0)
        self.assertEqual(w["result"]["theoretical_upper_bound"], 1.0)
        self.assertFalse(w["verified"])
        self.assertFalse(w["independent"])
        self.assertFalse(out["promotion_authority"])

    def test_family_must_map_exactly_to_one_residual(self):
        x = self.live()
        x["registry"] = copy.deepcopy(x["registry"])
        x["registry"]["family_to_residual_contracts"][
            "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"
        ] = [
            "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
            "OTHER",
        ]
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("BEHAVIOR_NOT_EXACT_WHOLE_FAMILY_RESIDUAL", out["errors"])

    def test_current_binding_must_be_independently_revalidated_by_exact_blob(self):
        x = self.live()
        x["current_binding_verification"] = copy.deepcopy(
            x["current_binding_verification"]
        )
        for row in x["current_binding_verification"]["verified_jobs"]:
            if row.get("behavior_id") == "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
                row["binding_blob_sha"] = "bad"
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("CURRENT_BINDING_EXACT_BYTE_VERIFICATION_MISSING", out["errors"])

    def test_missing_required_parent_portfolio_fails(self):
        x = self.live()
        x["terminal_result"] = copy.deepcopy(x["terminal_result"])
        rows = x["terminal_result"]["reduction_input"]["wave"][
            "parent_portfolio_receipts"
        ]["T2"]
        x["terminal_result"]["reduction_input"]["wave"][
            "parent_portfolio_receipts"
        ]["T2"] = [
            r
            for r in rows
            if r.get("behavior_id") != "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
        ]
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("REQUIRED_PARENT_RECEIPT_COUNT_MISMATCH:T2", out["errors"])

    def test_direct_instrumentation_failure_fails(self):
        x = self.live()
        x["terminal_result"] = copy.deepcopy(x["terminal_result"])
        for row in x["terminal_result"]["reduction_input"]["wave"][
            "parent_portfolio_receipts"
        ]["T0"]:
            if row.get("behavior_id") == "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
                row["direct_instrumentation_pass"] = False
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("PARENT_DIRECT_INSTRUMENTATION_NOT_PASS:T0", out["errors"])

    def test_parent_terminal_acceptance_failure_fails(self):
        x = self.live()
        x["terminal_result"] = copy.deepcopy(x["terminal_result"])
        for row in x["terminal_result"]["reduction_input"]["wave"][
            "parent_portfolio_receipts"
        ]["T2"]:
            if row.get("behavior_id") == "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
                row["parent_terminal_acceptance_pass"] = False
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("PARENT_TERMINAL_ACCEPTANCE_NOT_PASS:T2", out["errors"])

    def test_binding_must_require_causal_rescue_and_scope_coverage(self):
        x = self.live()
        x["binding"] = copy.deepcopy(x["binding"])
        x["binding"]["terminal_acceptance"]["any_load_bearing_p1_failure_blocks_behavior_proof"] = False
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("LOAD_BEARING_FAILURE_NOT_FATAL", out["errors"])

    def test_protocol_must_still_be_open(self):
        x = self.live()
        x["protocols"] = copy.deepcopy(x["protocols"])
        for row in x["protocols"]["protocols"]:
            if row.get("family") == "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY":
                row["status"] = "PASS"
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("FAMILY_PROTOCOL_NOT_OPEN", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
