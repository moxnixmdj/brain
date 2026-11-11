from __future__ import annotations
import json
import unittest
from pathlib import Path

from canonical.runtime.postwave_evidence_reconciler_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class Tests(unittest.TestCase):
    def live(self):
        return dict(
            spec=load("canonical/governance/POSTWAVE_EVIDENCE_RECONCILIATION_INPUT_V1.json"),
            current_binding_verification=load("canonical/verification/CURRENT_OBJECTIVE_BINDINGS_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json"),
            reopened_routes=load("canonical/governance/OPUS55_REOPENED_OBJECTIVE_ROUTE_RESIDUAL_V1.json"),
            executor_manifest=load("canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json"),
            terminal_result=load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
        )

    def test_live_reconciliation_exposes_delegation_ceiling_and_recovery_scope_evidence(self):
        out = evaluate(**self.live())
        self.assertTrue(out["pass"], out)
        self.assertEqual(len(out["candidate_predicate_witnesses"]), 1)
        d = out["candidate_predicate_witnesses"][0]
        self.assertEqual(d["predicate_id"], "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR")
        self.assertEqual(d["source_case_count"], 132)
        self.assertEqual(d["result"]["brain_lower_bound"], 1.0)
        self.assertEqual(d["result"]["theoretical_upper_bound"], 1.0)
        self.assertFalse(d["verified"])
        self.assertFalse(d["independent"])
        self.assertEqual(len(out["scope_valid_terminal_evidence"]), 1)
        r = out["scope_valid_terminal_evidence"][0]
        self.assertEqual(r["predicate_id"], "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR")
        self.assertEqual(r["required_portfolios"], ["T0", "T2"])
        self.assertFalse(r["closes_entire_predicate"])
        self.assertFalse(out["promotion_authority"])

    def test_snapshot_blob_drift_fails_closed(self):
        x = self.live()
        x["spec"] = json.loads(json.dumps(x["spec"]))
        x["spec"]["routes"][0]["execution_snapshot_binding_blob_sha"] = "0" * 40
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertTrue(any("CURRENT_BINDING_DIFFERS_FROM_EXECUTION_SNAPSHOT" in e for e in out["errors"]))

    def test_current_independent_binding_receipt_mismatch_fails(self):
        x = self.live()
        x["current_binding_verification"] = json.loads(json.dumps(x["current_binding_verification"]))
        x["current_binding_verification"]["verified_jobs"][0]["binding_blob_sha"] = "1" * 40
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertTrue(any("CURRENT_BINDING_BLOB_MISMATCH" in e for e in out["errors"]))

    def test_wrong_execution_snapshot_commit_fails(self):
        x = self.live()
        x["terminal_result"] = json.loads(json.dumps(x["terminal_result"]))
        x["terminal_result"]["execution_snapshot_commit"] = "bad"
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("EXECUTION_SNAPSHOT_COMMIT_MISMATCH", out["errors"])

    def test_replay_guard_failure_fails(self):
        x = self.live()
        x["terminal_result"] = json.loads(json.dumps(x["terminal_result"]))
        x["terminal_result"]["result_guards"]["no_tuning_replay"] = False
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("TUNING_REPLAY_GUARD_FAILED", out["errors"])

    def test_direct_failure_never_lifts_ceiling(self):
        x = self.live()
        x["terminal_result"] = json.loads(json.dumps(x["terminal_result"]))
        x["terminal_result"]["direct_terminal_population"]["routes"]["TASK_TO_DELEGATION_GRAPH_001"]["passes"] = 131
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertEqual(out["candidate_predicate_witnesses"], [])

    def test_parent_binding_mismatch_fails(self):
        x = self.live()
        x["terminal_result"] = json.loads(json.dumps(x["terminal_result"]))
        rows = x["terminal_result"]["reduction_input"]["wave"]["parent_portfolio_receipts"]["T0"]
        row = next(r for r in rows if r.get("behavior_id") == "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001")
        row["binding_blob"] = "2" * 40
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertTrue(any("PARENT_RECEIPT_BINDING_BLOB_MISMATCH:T0" in e for e in out["errors"]))

    def test_partial_scope_declaration_cannot_be_promoted(self):
        x = self.live()
        x["reopened_routes"] = json.loads(json.dumps(x["reopened_routes"]))
        route = next(r for r in x["reopened_routes"]["routes"] if r.get("behavior_id") == "TASK_TO_DELEGATION_GRAPH_001")
        route["scope_relation"] = "PARTIAL_ONLY"
        out = evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertTrue(any("FULL_PROTOCOL_REPLACEMENT_SCOPE_NOT_DECLARED" in e for e in out["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
