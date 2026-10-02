from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.temporal_proof_transport_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class TemporalProofTransportTests(unittest.TestCase):
    def live(self):
        return dict(
            transport=load("canonical/governance/DELEGATION_TEMPORAL_PROOF_TRANSPORT_V1.json"),
            protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
            registry=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
            binding=load("canonical/governance/DELEGATION_T2_OBJECTIVE_TERMINAL_BINDING_V1.json"),
            binding_verification=load("canonical/verification/CURRENT_OBJECTIVE_BINDINGS_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json"),
            scope_relation=load("canonical/governance/DELEGATION_SCOPE_EQUIVALENCE_RELATION_V1.json"),
            scope_verification=load("canonical/verification/DELEGATION_SCOPE_GATE_V2_V3_REPAIR_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
            executor_manifest=load("canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json"),
            terminal_result=load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
        )

    def test_live_delegation_transport_candidate_is_ready(self):
        out = evaluate(**self.live())
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "TRANSPORT_CANDIDATE_READY__FULL_HISTORY_CI_AND_INDEPENDENT_WITNESS_VERIFICATION_REQUIRED",
        )
        self.assertEqual(out["transported_terminal_receipt"]["source_case_count"], 132)
        w = out["candidate_witness"]
        self.assertEqual(w["family"], "SUBAGENT_DELEGATION_AND_COORDINATION")
        self.assertEqual(w["result"]["brain_lower_bound"], 1.0)
        self.assertEqual(w["result"]["theoretical_upper_bound"], 1.0)
        self.assertFalse(w["verified"])
        self.assertFalse(w["independent"])
        self.assertFalse(out["promotion_authority"])

    def test_binding_hash_change_fails_closed(self):
        x = self.live()
        x["transport"] = copy.deepcopy(x["transport"])
        x["transport"]["history_identity"]["current_binding_blob_sha"] = "0" * 40
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("BINDING_BLOB_NOT_IDENTICAL_ACROSS_TIME", out["errors"])

    def test_external_binding_receipt_must_match_exact_blob(self):
        x = self.live()
        x["binding_verification"] = copy.deepcopy(x["binding_verification"])
        row = next(r for r in x["binding_verification"]["verified_jobs"] if r["behavior_id"] == "TASK_TO_DELEGATION_GRAPH_001")
        row["binding_blob_sha"] = "0" * 40
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("EXTERNAL_BINDING_BLOB_MISMATCH", out["errors"])

    def test_scope_relation_must_be_stronger(self):
        x = self.live()
        x["scope_relation"] = copy.deepcopy(x["scope_relation"])
        x["scope_relation"]["oracle_relation"]["relation"] = "UNKNOWN"
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("ORACLE_NOT_PROVEN_STRONGER", out["errors"])

    def test_scope_verification_must_remain_admissible(self):
        x = self.live()
        x["scope_verification"] = copy.deepcopy(x["scope_verification"])
        x["scope_verification"]["verdict"]["admissible"] = False
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("SCOPE_SUBSTITUTION_NOT_ADMISSIBLE", out["errors"])

    def test_partial_family_mapping_fails_closed(self):
        x = self.live()
        x["registry"] = copy.deepcopy(x["registry"])
        x["registry"]["family_to_residual_contracts"]["SUBAGENT_DELEGATION_AND_COORDINATION"] = [
            "TASK_TO_DELEGATION_GRAPH_001",
            "OTHER",
        ]
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("BEHAVIOR_NOT_EXACT_WHOLE_FAMILY_RESIDUAL", out["errors"])

    def test_one_terminal_failure_fails_closed(self):
        x = self.live()
        x["terminal_result"] = copy.deepcopy(x["terminal_result"])
        x["terminal_result"]["direct_terminal_population"]["routes"]["TASK_TO_DELEGATION_GRAPH_001"]["passes"] = 131
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("NOT_ALL_FROZEN_CASES_PASS", out["errors"])

    def test_executor_identity_change_fails_closed(self):
        x = self.live()
        x["transport"] = copy.deepcopy(x["transport"])
        x["transport"]["stable_executor_identity"]["executor_blob_sha"] = "0" * 40
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("EXECUTOR_BLOB_CHANGED", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
